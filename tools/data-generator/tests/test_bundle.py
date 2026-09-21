import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bundle
import fixture


def load():
    d = Path(tempfile.mkdtemp())
    fixture.write(d)
    return bundle.load(d)


def test_voided_concepts_dropped():
    assert fixture.VOIDED not in load().concepts


def test_voided_mapping_dropped():
    b = load()
    assert [m.form_uuid for m in b.mappings] == [fixture.FORM]


def test_generatable_elements_exclude_media_questiongroup_voided_and_answerless_coded():
    b = load()
    got = {e.concept.uuid for e in b.elements_for(b.mappings[0])}
    assert got == {fixture.CODED, fixture.NUMERIC, fixture.TEXT}


def test_voided_element_and_voided_group_dropped():
    b = load()
    assert {e.uuid for e in b.elements_for(b.mappings[0])} == {"e1", "e2", "e3", "e4"}


def test_voided_answer_is_not_offered():
    b = load()
    assert set(b.concepts[fixture.CODED].answer_uuids) == set(fixture.ANSWERS[:3])


def test_absolute_range_comes_from_concepts_file_not_the_embedded_copy():
    b = load()
    numeric = next(e for e in b.elements_for(b.mappings[0]) if e.concept.uuid == fixture.NUMERIC)
    assert (numeric.concept.low_absolute, numeric.concept.high_absolute) == (2.0, 8.0)


def test_concept_uuids_spans_live_mappings_only():
    assert load().concept_uuids() == {fixture.CODED, fixture.NUMERIC, fixture.TEXT}


def test_media_elements_are_counted_not_silently_dropped():
    """They stay out of generated observations, but the count is what sizes media load (D5.1)."""
    b = load()
    got = {e.concept_name for e in b.media_for(b.mappings[0])}
    assert got == {"Photo", "Recording"}
    assert all(e.concept.uuid != fixture.MEDIA for e in b.elements_for(b.mappings[0]))


def test_media_bounds_separate_mandatory_from_optional():
    b = load()
    mandatory, every = b.media_per_form_type()["IndividualProfile"]
    assert (mandatory, every) == (1.0, 2.0)


def test_read_only_is_read_off_the_concept_key_values():
    """readOnly decides whether a media element is captured on the device at all, so it is the
    difference between the reported figure and zero."""
    b = load()
    by_name = {e.concept_name: e for e in b.media_for(b.mappings[0])}
    assert by_name["Photo"].read_only is True
    assert by_name["Recording"].read_only is False


def test_form_types_with_no_media_report_zero_rather_than_vanishing():
    b = load()
    per_type = b.media_per_form_type()
    assert set(per_type) == {"IndividualProfile"}
    assert per_type["IndividualProfile"][1] == 2.0
