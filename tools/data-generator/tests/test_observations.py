import random, statistics, sys, tempfile
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

import bundle
import fixture
import observations as obs

ANCHOR = date(2026, 9, 18)


def elements():
    d = Path(tempfile.mkdtemp())
    fixture.write(d)
    b = bundle.load(d)
    return b.elements_for(b.mappings[0])


def by_concept(els, uuid):
    return next(e for e in els if e.concept.uuid == uuid)


# --- key count distribution -------------------------------------------------

@pytest.mark.parametrize("p50,p95", [(12, 34), (7, 29), (4, 22), (2, 20)])
def test_key_count_reproduces_both_percentiles(p50, p95):
    """The measured pairs from Q6. Reproducing the mean alone builds the wrong index."""
    kc = obs.KeyCount(p50=p50, p95=p95)
    rng = random.Random(7)
    n = sorted(kc.sample(rng, cap=10_000) for _ in range(40_000))
    assert abs(statistics.median(n) - p50) <= max(1, p50 * 0.1)
    assert abs(n[int(0.95 * len(n))] - p95) <= max(1, p95 * 0.1)


def test_key_count_never_exceeds_the_elements_available():
    kc = obs.KeyCount(p50=12, p95=34)
    rng = random.Random(1)
    assert all(kc.sample(rng, cap=3) <= 3 for _ in range(1000))


def test_key_count_rejects_a_p95_below_the_median():
    with pytest.raises(ValueError):
        obs.KeyCount(p50=10, p95=4)


# --- values -----------------------------------------------------------------

def test_coded_single_select_returns_one_of_that_concepts_own_answers():
    els = elements()
    e = by_concept(els, fixture.CODED)
    rng = random.Random(3)
    for _ in range(200):
        assert obs.value_for(e, rng, ANCHOR) in fixture.ANSWERS[:3]


def test_coded_multi_select_returns_a_list_without_repeats():
    els = elements()
    e = next(x for x in els if x.multi_select)
    rng = random.Random(3)
    for _ in range(200):
        v = obs.value_for(e, rng, ANCHOR)
        assert isinstance(v, list) and v and len(set(v)) == len(v)
        assert set(v) <= set(fixture.ANSWERS[:3])


def test_numeric_stays_inside_the_concepts_absolute_range():
    els = elements()
    e = by_concept(els, fixture.NUMERIC)
    rng = random.Random(5)
    assert all(2.0 <= obs.value_for(e, rng, ANCHOR) <= 8.0 for _ in range(500))


def test_reference_datatypes_return_none_without_a_pool():
    from bundle import Concept, Element
    e = Element(uuid="x", concept=Concept(uuid="c", name="Where", data_type="Location"),
                multi_select=False, mandatory=False)
    assert obs.value_for(e, random.Random(1), ANCHOR) is None
    pool = {"Location": ["loc-1", "loc-2"]}
    assert obs.value_for(e, random.Random(1), ANCHOR, reference_uuids=pool) in pool["Location"]


# --- whole observations -----------------------------------------------------

def test_every_key_is_a_concept_uuid_from_the_form():
    els = elements()
    allowed = {e.concept.uuid for e in els}
    rng = random.Random(11)
    kc = obs.KeyCount(p50=2, p95=4)
    for _ in range(500):
        assert set(obs.generate(els, kc, rng, ANCHOR)) <= allowed


def test_mandatory_elements_are_filled_first():
    els = elements()
    rng = random.Random(13)
    kc = obs.KeyCount(p50=1, p95=1)
    filled = [obs.generate(els, kc, rng, ANCHOR) for _ in range(300)]
    assert all(fixture.CODED in f for f in filled if f)


def test_which_concepts_appear_varies_across_rows():
    """A generator that always fills the same elements produces a narrower index than production."""
    els = elements()
    rng = random.Random(17)
    kc = obs.KeyCount(p50=2, p95=3)
    seen = {frozenset(obs.generate(els, kc, rng, ANCHOR)) for _ in range(400)}
    assert len(seen) > 1


def test_same_seed_gives_the_same_dataset():
    els = elements()
    kc = obs.KeyCount(p50=3, p95=4)
    a = [obs.generate(els, kc, random.Random(99), ANCHOR) for _ in range(20)]
    b = [obs.generate(els, kc, random.Random(99), ANCHOR) for _ in range(20)]
    assert a == b


def test_no_elements_yields_an_empty_observation():
    assert obs.generate([], obs.KeyCount(p50=5, p95=9), random.Random(1), ANCHOR) == {}
