import pytest

from dylan.hybrid.features import UnificationError
from dylan.hybrid.polydefinites import agreement_trace
from dylan.hybrid.traces import DSAdapter, replay


@pytest.mark.parametrize("sentence,predicates", [
    ("ο άνθρωπος ο μεγάλος περπατάει", ["person", "big"]),
    ("ο μεγάλος ο άνθρωπος περπατάει", ["person", "big"]),
    ("ο μεγάλος ο κόκκινος ο άνθρωπος περπατάει", ["person", "big", "red"]),
    ("η γυναίκα η μεγάλη περπατάει", ["woman", "big"]),
    ("το παιδί το μεγάλο περπατάει", ["child", "big"]),
    ("ο άνθρωπος ο μεγάλος ο κόκκινος περπατάει", ["person", "big", "red"]),
])
def test_shared_reference_and_all_words_preserved(sentence, predicates):
    adapter = DSAdapter("2026-smg-classical", extensions=("polydefinites",))
    try:
        result = adapter.probe(sentence, complete=True)
        assert result["status"] == "complete", result["failure"]
        assert len(result["frames"]) == len(sentence.split())
        formula = next(label for label in result["state"]["nodes"][0]["labels"] if label.startswith("Fo("))
        assert formula.count("ι") == 1
        assert all(p in formula for p in predicates)
        assert replay(result)["verified"]
        assert agreement_trace(sentence.split())
    finally:
        adapter.close()


@pytest.mark.parametrize("sentence", [
    "ο άνθρωπος η μεγάλη περπατάει", "ο άνθρωπος ο μεγάλη περπατάει",
    "ο ο άνθρωπος περπατάει", "ο μεγάλος ο κόκκινος περπατάει",
    "ένας άνθρωπος ο μεγάλος περπατάει", "ο άνθρωπος ο περπατάει",
    "ο άνθρωπος ο μεγάλος περπατάω",
])
def test_boundaries_are_constraints_not_token_deletion(sentence):
    adapter = DSAdapter("2026-smg-classical", extensions=("polydefinites",))
    try:
        assert adapter.probe(sentence, complete=True)["status"] != "complete"
    finally:
        adapter.close()


def test_extension_is_opt_in_and_incomplete_article_leaves_requirement():
    original = DSAdapter("2026-smg-classical")
    hybrid = DSAdapter("2026-smg-classical", extensions=("polydefinites",))
    try:
        assert original.probe("ο άνθρωπος ο μεγάλος περπατάει", complete=True)["status"] != "complete"
        result = hybrid.probe("ο άνθρωπος ο")
        assert any("POLY-ADJECTIVE" in p["requirement"] for p in result["state"]["pending"])
        with pytest.raises(UnificationError):
            agreement_trace("ο γυναίκα".split())
    finally:
        original.close()
        hybrid.close()
