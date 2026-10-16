import pytest
from agent.tools import doc_search


def test_chunking_splits_on_citable_headings():
    chunks = doc_search.chunk_documents()
    refs = {(c.source, c.ref) for c in chunks}
    assert ("pfmea.md", "Row 14") in refs
    assert ("control_plan.md", "Item 6") in refs
    assert len(chunks) > 40


def test_every_chunk_carries_its_quote():
    for c in doc_search.chunk_documents():
        assert c.quote.strip()
        assert len(c.quote) <= 600


def test_meaning_based_match_finds_pfmea_row_14():
    """PRD 4: 'solder bridging' must match 'peak temperature above limit' by meaning."""
    hits = doc_search.search_quality_docs(
        "solder bridging caused by reflow peak temperature above the profile limit", k=3)
    top = hits[0]
    assert top.source == "pfmea.md"
    assert top.ref == "Row 14"
    assert "Solder bridging" in top.quote


def test_profile_verification_query_finds_control_plan_item_6():
    hits = doc_search.search_quality_docs(
        "what must be done to the reflow profile after oven maintenance", k=3)
    assert any(h.source == "control_plan.md" and h.ref == "Item 6" for h in hits)


def test_k_is_respected():
    assert len(doc_search.search_quality_docs("solder bridging", k=2)) == 2


def test_empty_query_raises():
    with pytest.raises(ValueError, match="empty query"):
        doc_search.search_quality_docs("  ")
