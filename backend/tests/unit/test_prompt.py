import uuid
from datetime import date
from free_hr.chat.prompt import build_context_refs, render_context_block
from free_hr.knowledge_store.schemas import CaseChunkHit, LawChunkHit


def _law(text, score, art="第X条"):
    return LawChunkHit(
        id=uuid.uuid4(), law_name="劳动合同法", article_no=art, chapter=None,
        text=text, region="national", source_url=None, effective_date=date(2008, 1, 1), score=score,
    )


def _case(text, score):
    return CaseChunkHit(
        id=uuid.uuid4(), case_title="示例", case_no="(2023)京01民终1号", court=None,
        judgment_date=None, text=text, source_url=None, score=score,
    )


def test_build_context_refs_sorts_by_score_and_assigns_idx():
    refs = build_context_refs([_law("A", 0.3), _law("B", 0.9)], [_case("C", 0.7)])
    assert [r.idx for r in refs] == [1, 2, 3]
    assert refs[0].text == "B"
    assert refs[1].text == "C"
    assert refs[2].text == "A"


def test_build_context_refs_truncates_at_budget():
    big = "x" * 4000
    refs = build_context_refs([_law(big, 0.9, "第1条"), _law(big, 0.8, "第2条"), _law(big, 0.7, "第3条")], [])
    assert len(refs) == 2  # 第三条超预算被截


def test_build_context_refs_dedupes_same_chunk_id():
    same = _law("A", 0.9)
    refs = build_context_refs([same, same], [])
    assert len(refs) == 1


def test_render_context_block_contains_numbering_and_labels():
    refs = build_context_refs([_law("劳动者严重违反规章制度", 0.9, "第三十九条")], [_case("案例正文", 0.8)])
    block = render_context_block(refs)
    assert "[#1]" in block
    assert "[#2]" in block
    assert "法条·劳动合同法·第三十九条" in block
    assert "案例·(2023)京01民终1号" in block


def test_render_context_block_handles_empty():
    block = render_context_block([])
    assert "未找到相关法条" in block
