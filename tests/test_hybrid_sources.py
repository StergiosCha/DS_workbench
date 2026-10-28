import io
from pathlib import Path
import zipfile

import pytest

from dylan.hybrid.sources import RemoteArchive, safe_member, selected


def test_selective_archive_reads_and_crc_verification():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr("Data and analysis/Data/trials.csv", "a,b\n1,2\n")
        zipped.writestr("Fitted models/fit.rds", bytes(range(256)) * 1000)
    payload = buffer.getvalue()
    reads = []

    def fetch(url, start, end):
        reads.append((start, end))
        return payload[start:end + 1]

    remote = RemoteArchive("https://example.test/study.zip", len(payload), fetch)
    with zipfile.ZipFile(remote) as zipped:
        assert zipped.read("Data and analysis/Data/trials.csv") == b"a,b\n1,2\n"
    assert reads and all(0 <= a <= b < len(payload) for a, b in reads)


@pytest.mark.parametrize("name", ["../x", "/x", "ok/../../x", "a\\..\\x"])
def test_archive_traversal_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        safe_member(tmp_path, name)


def test_default_selection_excludes_large_models_and_raw_participant_files():
    assert selected("Data and analysis/Data/S1_data.csv")
    assert not selected("Data and analysis/Fitted models/fit.rds")
    assert selected("Data and analysis/Fitted models/fit.rds", fits=True)
    assert not selected("Data and analysis/PsychoPy data/subjId1.csv")
    assert selected("Data and analysis/PsychoPy data/subjId1.csv", raw=True)
    assert safe_member(Path("/tmp/test"), "Data/trials.csv") == Path("/tmp/test/Data/trials.csv")
