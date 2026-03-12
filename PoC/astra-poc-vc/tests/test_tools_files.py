"""Tests for tools_files.py — verifies file discovery and domain routing."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import memory as mem_module
mem_module.QDRANT_AVAILABLE = False

import tools_files


def test_list_user_files_returns_files():
    result = json.loads(tools_files.list_user_files.invoke({}))
    assert result["count"] > 0, "Expected at least one file"
    filenames = [f["filename"] for f in result["files"]]
    assert any("Acme" in f for f in filenames), f"Acme file missing: {filenames}"
    assert any("Helsinki" in f for f in filenames), f"Helsinki file missing: {filenames}"


def test_list_user_files_has_domain_tags():
    result = json.loads(tools_files.list_user_files.invoke({}))
    for f in result["files"]:
        assert "domains" in f, f"Missing domains on {f['filename']}"
        assert len(f["domains"]) > 0, f"Empty domains on {f['filename']}"


def test_acme_file_tagged_sales():
    result = json.loads(tools_files.list_user_files.invoke({}))
    acme = next((f for f in result["files"] if "Acme" in f["filename"]), None)
    assert acme is not None, "Acme file not found"
    assert "sales" in acme["domains"], f"Acme not tagged sales: {acme['domains']}"


def test_helsinki_file_tagged_travel():
    result = json.loads(tools_files.list_user_files.invoke({}))
    helsinki = next((f for f in result["files"] if "Helsinki" in f["filename"]), None)
    assert helsinki is not None, "Helsinki file not found"
    assert "travel" in helsinki["domains"], f"Helsinki not tagged travel: {helsinki['domains']}"


def test_read_user_file_acme():
    result = tools_files.read_user_file.invoke({"filename": "Acme_Pricing_Tiers.md"})
    assert "pricing" in result.lower(), "Pricing content missing"
    assert "discount" in result.lower(), "Discount content missing"


def test_read_user_file_not_found():
    result = tools_files.read_user_file.invoke({"filename": "nonexistent_file.md"})
    assert "not found" in result.lower() or "error" in result.lower()


def test_search_files_sales_query():
    result = json.loads(tools_files.search_user_files.invoke({"query": "Acme pricing discount seats"}))
    assert len(result["results"]) > 0, "No results for sales query"
    assert "sales" in result["domains_searched"], f"Wrong domain: {result['domains_searched']}"


def test_search_files_travel_query():
    result = json.loads(tools_files.search_user_files.invoke({"query": "Helsinki sauna photography"}))
    assert len(result["results"]) > 0, "No results for travel query"
    assert "travel" in result["domains_searched"], f"Wrong domain: {result['domains_searched']}"


def test_index_all_files():
    count = tools_files.index_all_files()
    assert count >= 4, f"Expected at least 4 files indexed, got {count}"


if __name__ == "__main__":
    tests = [
        test_list_user_files_returns_files,
        test_list_user_files_has_domain_tags,
        test_acme_file_tagged_sales,
        test_helsinki_file_tagged_travel,
        test_read_user_file_acme,
        test_read_user_file_not_found,
        test_search_files_sales_query,
        test_search_files_travel_query,
        test_index_all_files,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            import traceback; traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed")
