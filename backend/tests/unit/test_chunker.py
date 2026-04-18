from free_hr.knowledge_ingest.chunker import chunk_law

SAMPLE = """第一章 总则
第一条 为了规范用人单位的规章制度，制定本法。
第二条 本法适用于中华人民共和国境内的企业、个体经济组织。
第二章 劳动合同的订立
第十条 建立劳动关系，应当订立书面劳动合同。
第三十九条 劳动者有下列情形之一的，用人单位可以解除劳动合同：
（一）在试用期间被证明不符合录用条件的；
（二）严重违反用人单位的规章制度的；
（三）严重失职，营私舞弊，给用人单位造成重大损害的。
"""


def test_chunk_law_splits_by_article():
    chunks = chunk_law("劳动合同法", SAMPLE)
    nos = [c.article_no for c in chunks]
    assert "第一条" in nos
    assert "第十条" in nos
    assert "第三十九条" in nos


def test_chunk_law_attaches_chapter():
    chunks = chunk_law("劳动合同法", SAMPLE)
    first = next(c for c in chunks if c.article_no == "第一条")
    tenth = next(c for c in chunks if c.article_no == "第十条")
    assert "总则" in (first.chapter or "")
    assert "劳动合同的订立" in (tenth.chapter or "")


def test_chunk_law_hashes_are_stable_and_unique():
    a = chunk_law("劳动合同法", SAMPLE)
    b = chunk_law("劳动合同法", SAMPLE)
    assert [c.content_hash for c in a] == [c.content_hash for c in b]
    assert len({c.content_hash for c in a}) == len(a)


def test_long_article_splits_by_subclause():
    long_article = "第九十九条 " + "".join(
        f"（{chr(0x4E00 + i)}）详细条款正文" + "x" * 200 for i in range(5)
    )
    chunks = chunk_law("某大法", long_article)
    assert len(chunks) > 1
    assert all(len(c.text) <= 1000 for c in chunks)
