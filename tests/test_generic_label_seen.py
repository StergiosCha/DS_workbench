"""E0.5: labels that fall through to GenericLabel are recorded at parse time (wide-coverage-plan.md, M0)."""

from __future__ import annotations

from dylan.tree.label.labels import GenericLabel, generic_label_seen, label_factory_create


def test_generic_label_fallthrough_is_recorded_at_parse_time() -> None:
    spec = "UnsupportedFeature(acc)"
    generic_label_seen.discard(spec)
    label = label_factory_create(spec)
    assert isinstance(label, GenericLabel)
    assert spec in generic_label_seen


def test_known_labels_are_not_recorded() -> None:
    before = set(generic_label_seen)
    assert not isinstance(label_factory_create("Ty(e)"), GenericLabel)
    assert not isinstance(label_factory_create("Mood(Imp)"), GenericLabel)
    assert generic_label_seen == before
