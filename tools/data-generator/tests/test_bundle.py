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
