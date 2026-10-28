import pytest

from dylan.decision.client import DecisionClient, content_hash
from dylan.hybrid.assistance import draft, rank
from dylan.hybrid.correspondence import project
from dylan.hybrid.traces import DSAdapter
from dylan.lexical_expansion import proposal


def test_lfg_projection_preserves_arguments_and_pending_object():
    adapter = DSAdapter()
    try:
        adapter.probe("John likes")
        partial = project(adapter.parser)
        assert partial["checks"]["pending"][0]["function"] == "OBJ"
        adapter.probe("John likes Mary", complete=True)
        complete = project(adapter.parser, closed=True)
        assert complete["checks"]["complete"]
        assert [m["semantic_value"] for m in complete["structure"]["mappings"]] == ["john", "mary"]
    finally:
        adapter.close()


def test_llm_proposal_is_compiled_but_not_installed():
    raw = {"entries": [proposal("glimmers", "glimmer", "intransitive", ["object"])]}
    result = draft("The lamp", "glimmers", proposal=raw)
    assert result["status"] == "compiled_for_review"
    assert result["compiled"] and result["installed"] is False
    raw["entries"][0]["template"] = "invented-function-word"
    with pytest.raises(ValueError):
        draft("The lamp", "glimmers", proposal=raw)


@pytest.mark.parametrize("text, expected", [
    ("John gives Mary a book", {"SUBJ": "john", "OBJ": "mary", "OBJ2": "book"}),
    ("John gives a book to Mary", {"SUBJ": "john", "OBJ": "book", "OBL": "mary"}),
])
def test_lfg_functions_follow_declared_dative_frame(text, expected):
    adapter = DSAdapter()
    try:
        assert adapter.probe(text, complete=True)["status"] == "complete"
        result = project(adapter.parser, closed=True)
        assert result["checks"]["complete"]
        for mapping in result["structure"]["mappings"]:
            assert expected[mapping["function"]] in mapping["semantic_value"]
    finally:
        adapter.close()


def test_jev_recorded_answers_keep_same_candidates_and_uncertainty(tmp_path):
    client = DecisionClient("stub", log_path=tmp_path / "decisions.jsonl")
    result = rank("John walked to the", "bank", client=client)
    if result["status"] == "no_dictionary_candidates":
        pytest.skip("Optional WordNet index not installed")
    record = result["record"]
    assert record["stub"]
    assert all("uncertain" in q["criteria"] for q in record["questions"].values())
    key = content_hash([client.provider["provider"], client.provider["model"], record["idea"],
                        record["state"], record["questions"]])
    replay = DecisionClient("stub", recorded={key: record["answers"]}, log_path=tmp_path / "replayed.jsonl")
    repeated = rank("John walked to the", "bank", client=replay)
    assert repeated["status"] == "judged"
    assert repeated["candidates"] == result["candidates"]
    assert repeated["record"]["recorded"]
