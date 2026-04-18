from free_hr.chat.citations import count_oob, extract_citations
from free_hr.chat.schemas import ContextRef


def _refs(n: int) -> list[ContextRef]:
    return [ContextRef(idx=i, kind="law", chunk_id=f"id-{i}", label=f"L{i}", text="") for i in range(1, n + 1)]


def test_extract_citations_preserves_first_occurrence_order():
    refs = _refs(3)
    text = "结论A [#2]。再看[#1]和[#2]，最后 [#3]。"
    out = extract_citations(text, refs)
    assert [c["idx"] for c in out] == [2, 1, 3]


def test_extract_citations_filters_out_of_bound():
    refs = _refs(2)
    text = "A [#1][#9][#2][#17]"
    out = extract_citations(text, refs)
    assert [c["idx"] for c in out] == [1, 2]


def test_count_oob_counts_every_occurrence():
    refs = _refs(2)
    text = "[#1][#5][#5][#2]"
    assert count_oob(text, refs) == 2
