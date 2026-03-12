"""
Tests for memory.py — uses in-process fallback (no Qdrant required).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Force fallback mode by patching QDRANT_AVAILABLE before import
import memory as mem_module
mem_module.QDRANT_AVAILABLE = False

from memory import MemoryManager


def make_manager():
    """Create a fresh manager with in-process fallback."""
    m = MemoryManager.__new__(MemoryManager)
    m.persona_id = "mike"
    m._qdrant = None
    m._embedder = None
    from memory import _InMemoryStore
    m._store = _InMemoryStore()
    return m


def test_store_and_retrieve_basic():
    mgr = make_manager()
    mgr.store("Mike prefers bullet points over long paragraphs", memory_type="fact", domains=["admin"])
    results = mgr.retrieve("communication style", domains=["admin"])
    assert len(results) == 1
    assert "bullet points" in results[0]["content"]


def test_domain_filtering_blocks_wrong_domain():
    mgr = make_manager()
    mgr.store("NVDA is up 8% on earnings beat", memory_type="episode", domains=["finance"])
    mgr.store("Acme renewal call is Thursday", memory_type="episode", domains=["sales"])

    finance_results = mgr.retrieve("stock market", domains=["finance"])
    sales_results = mgr.retrieve("client meeting", domains=["sales"])

    assert all("NVDA" in r["content"] for r in finance_results)
    assert all("Acme" in r["content"] for r in sales_results)
    # Finance query should not return sales memory
    assert not any("Acme" in r["content"] for r in finance_results)


def test_auto_domain_classification():
    mgr = make_manager()
    # No explicit domain — should auto-classify
    mgr.store("Flight to Helsinki confirmed, seat 14A", memory_type="fact")
    results = mgr.retrieve("travel", domains=["travel"])
    assert len(results) == 1
    assert "Helsinki" in results[0]["content"]


def test_memory_type_filter():
    mgr = make_manager()
    mgr.store("Mike dismissed TSLA alert", memory_type="episode", domains=["finance"])
    mgr.store("Mike prefers morning meetings", memory_type="fact", domains=["admin"])

    episodes = mgr.retrieve("", memory_type="episode", domains=["finance"])
    facts = mgr.retrieve("", memory_type="fact", domains=["admin"])

    assert all(r["type"] == "episode" for r in episodes)
    assert all(r["type"] == "fact" for r in facts)


def test_index_and_search_files():
    mgr = make_manager()
    mgr.index_file(
        path="/app/data/files/Acme_Pricing_Tiers.md",
        content="Pricing tiers: Starter $15/seat, Professional $35/seat, Enterprise $55/seat. "
                "Volume discounts: 50+ seats 15% off.",
        domains=["sales"],
    )
    mgr.index_file(
        path="/app/data/files/Helsinki_Travel_Guide.md",
        content="Helsinki travel guide. Photography spots, craft beer, sauna etiquette.",
        domains=["travel"],
    )

    sales_files = mgr.search_files("pricing discount", domains=["sales"])
    travel_files = mgr.search_files("sauna photography", domains=["travel"])

    assert len(sales_files) == 1
    assert "Acme_Pricing_Tiers" in sales_files[0]["filename"]
    assert len(travel_files) == 1
    assert "Helsinki" in travel_files[0]["filename"]

    # Sales query should not return travel file
    assert not any("Helsinki" in f["filename"] for f in sales_files)


def test_format_for_prompt():
    mgr = make_manager()
    memories = [
        {"type": "fact", "content": "Mike dismissed TSLA alert last week"},
        {"type": "episode", "content": "Acme call went well, Tom wants volume discount"},
    ]
    files = [
        {"filename": "Acme_Pricing_Tiers.md", "domains": ["sales"],
         "summary": "Pricing tiers and volume discounts for Acme renewal"},
    ]
    result = mgr.format_for_prompt(memories, files)
    assert "### Relevant Memory:" in result
    assert "### Relevant Files:" in result
    assert "TSLA" in result
    assert "Acme_Pricing_Tiers" in result


def test_list_all_files():
    mgr = make_manager()
    mgr.index_file("/files/a.md", "content a", domains=["sales"])
    mgr.index_file("/files/b.md", "content b", domains=["travel"])
    all_files = mgr.list_all_files()
    assert len(all_files) == 2


if __name__ == "__main__":
    tests = [
        test_store_and_retrieve_basic,
        test_domain_filtering_blocks_wrong_domain,
        test_auto_domain_classification,
        test_memory_type_filter,
        test_index_and_search_files,
        test_format_for_prompt,
        test_list_all_files,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed")
