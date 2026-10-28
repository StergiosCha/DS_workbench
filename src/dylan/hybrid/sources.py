"""Verified selective retrieval of public OSF ZIP members.

HTTP ranges avoid downloading multi-gigabyte collections of fitted models.
ZIP CRCs verify retrieved members; SHA256s and source metadata form a manifest.
The archive hash is recorded but is NOT claimed verified by selective retrieval.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import ssl
import time
from urllib.request import Request, urlopen
import zipfile

import certifi

API = "https://api.osf.io/v2/nodes/7v8mt/files/osfstorage/?page%5Bsize%5D=100"
PARENT = "https://api.osf.io/v2/nodes/ymndq/"


def request(url: str, start: int | None = None, end: int | None = None) -> bytes:
    headers = {"User-Agent": "DS-Workbench-Hybrid/0.1", "Accept-Encoding": "identity"}
    if start is not None:
        headers["Range"] = f"bytes={start}-{end}"
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=45,
                         context=ssl.create_default_context(cafile=certifi.where())) as response:
                if start is not None:
                    value = response.headers.get("Content-Range", "")
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", value)
                    if response.status != 206 or not match:
                        raise ValueError("Server did not honor the byte range; download aborted.")
                    if (int(match[1]), int(match[2])) != (start, end):
                        raise ValueError(f"Wrong Content-Range: {value}")
                    limit = end - start + 1
                    data = response.read(limit + 1)
                    if len(data) != limit:
                        raise ValueError("Incomplete or oversized byte range.")
                    return data
                return response.read(16 * 1024 * 1024 + 1)
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise AssertionError("unreachable")


class RemoteArchive(io.RawIOBase):
    """Seekable bounded HTTP file usable by Python's CRC-checking ZipFile."""

    def __init__(self, url: str, size: int, fetch=request):
        self.url, self.size, self.fetch = url, size, fetch
        self.position = 0
        self.transferred = 0
        self.cache: list[tuple[int, bytes]] = []

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        pos = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if pos < 0:
            raise ValueError("Negative seek")
        self.position = pos
        return pos

    def read(self, count=-1):
        count = min(self.size - self.position, count if count >= 0 else self.size)
        if count <= 0:
            return b""
        start = self.position
        self.position += count
        for offset, data in self.cache:
            if offset <= start and start + count <= offset + len(data):
                return data[start - offset:start - offset + count]
        # Reading ahead greatly reduces redirects for nearby ZIP members.
        stop = min(self.size - 1, start + max(count, 131072) - 1)
        data = self.fetch(self.url, start, stop)
        if len(data) != stop - start + 1:
            raise ValueError("Truncated archive range")
        self.transferred += len(data)
        self.cache.append((start, data))
        self.cache = self.cache[-8:]
        return data[:count]


def safe_member(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"Unsafe archive member: {name}")
    result = root.joinpath(*path.parts)
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError("Archive destination escapes root")
    return result


def selected(name: str, fits: bool = False, raw: bool = False) -> bool:
    if name == "PsychoPy/experiment.py":
        return True
    if "PsychoPy data/" in name:
        return raw and name.endswith(".csv")
    if "Fitted models/" in name:
        return fits and name.endswith("/fit.rds")
    return (name.startswith("Data and analysis/") and
            name.endswith((".csv", ".R", ".Rmd", ".html", ".txt"))) or (
        name.startswith("Stimulus generation/") and name.endswith((".csv", ".R", ".Rmd")))


def acquire(root: Path, studies=(1, 2, 3, 4), *, fits=False, raw=False) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(request(API))
    parent = json.loads(request(PARENT))
    (root / "osf-files.json").write_text(json.dumps(metadata, indent=2))
    (root / "osf-project.json").write_text(json.dumps(parent, indent=2))
    license_relation = parent["data"].get("relationships", {}).get("license", {})
    license_url = license_relation.get("links", {}).get("related", {}).get("href")
    if license_url:
        (root / "osf-license.json").write_bytes(request(license_url))
    (root / "license.txt").write_bytes(request("https://osf.io/download/r73vx/"))
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "schema": 1, "doi": "10.1038/s41562-025-02387-z", "project": PARENT,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(), "files": [],
        "archive_hash_verification": "not performed: selected members only",
        "license_metadata": parent["data"].get("relationships", {}).get("license", {}),
    }
    known = {x["destination"]: x for x in manifest["files"]}
    for item in metadata["data"]:
        name = item["attributes"]["name"]
        if name == "README.md":
            data = request(item["links"]["download"])
            (root / "upstream-README.md").write_bytes(data)
        if name not in {f"Study {n}.zip" for n in studies}:
            continue
        number = int(name.split()[1].split(".")[0])
        archive = RemoteArchive(item["links"]["download"], item["attributes"]["size"])
        with zipfile.ZipFile(archive) as zipped:
            (root / f"study{number}-inventory.json").write_text(json.dumps([
                {"name": i.filename, "size": i.file_size, "compressed": i.compress_size,
                 "crc32": i.CRC} for i in zipped.infolist()], indent=2))
            for member in zipped.infolist():
                if member.is_dir() or not selected(member.filename, fits, raw):
                    continue
                destination = safe_member(root / f"study{number}", member.filename)
                relative = str(destination.relative_to(root))
                old = known.get(relative)
                if old and destination.exists() and old["source_modified"] == item["attributes"]["date_modified"]:
                    if hashlib.sha256(destination.read_bytes()).hexdigest() == old["sha256"]:
                        continue
                if member.file_size > (250_000_000 if fits else 25_000_000):
                    raise ValueError(f"Member exceeds retrieval bound: {member.filename}")
                data = zipped.read(member)  # Validates CRC32 and decompression.
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                known[relative] = {
                    "study": number, "archive": name, "member": member.filename,
                    "destination": relative, "source_url": item["links"]["download"],
                    "source_modified": item["attributes"]["date_modified"],
                    "archive_hashes": item["attributes"].get("extra", {}).get("hashes", {}),
                    "size": len(data), "crc32": member.CRC,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                manifest["files"] = sorted(known.values(), key=lambda x: x["destination"])
                manifest_path.write_text(json.dumps(manifest, indent=2))
                print(f"Study {number}: {member.filename} ({len(data):,} bytes)", flush=True)
        print(f"Study {number}: transferred {archive.transferred:,} bytes", flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/hybrid/sources"))
    parser.add_argument("--studies", type=int, nargs="+", choices=range(1, 5), default=[1, 2, 3, 4])
    parser.add_argument("--fits", action="store_true")
    parser.add_argument("--raw", action="store_true")
    args = parser.parse_args()
    acquire(args.output, args.studies, fits=args.fits, raw=args.raw)


if __name__ == "__main__":
    main()
