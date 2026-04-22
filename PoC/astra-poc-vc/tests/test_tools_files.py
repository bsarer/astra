"""Tests for tools_files.py — verifies file discovery and domain routing."""
import sys, os, json, types
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

import memory as mem_module
mem_module.QDRANT_AVAILABLE = False

import tools_files


def test_list_user_files_returns_files():
    result = json.loads(tools_files.list_user_files.invoke({}))
    assert result["file_count"] > 0, "Expected at least one file"
    assert result["count"] == result["file_count"] + result["folder_count"]
    filenames = [f["filename"] for f in result["files"]]
    assert any("Acme" in f for f in filenames), f"Acme file missing: {filenames}"
    assert any("Helsinki" in f for f in filenames), f"Helsinki file missing: {filenames}"


def test_list_user_files_has_domain_tags():
    result = json.loads(tools_files.list_user_files.invoke({}))
    for f in result["files"]:
        assert "domains" in f, f"Missing domains on {f['filename']}"
        assert len(f["domains"]) > 0, f"Empty domains on {f['filename']}"


def test_list_user_files_includes_pdf_and_image_categories():
    result = json.loads(tools_files.list_user_files.invoke({}))
    filenames = {f["filename"]: f for f in result["files"]}
    assert "Acme_Renewal_Brief.pdf" in filenames
    assert filenames["Acme_Renewal_Brief.pdf"]["category"] == "documents"
    assert "NovaTech_Booth_Mock.png" in filenames
    assert filenames["NovaTech_Booth_Mock.png"]["category"] == "images"
    folder_paths = {folder["path"] for folder in result["folders"]}
    assert "Downloads" in folder_paths
    assert "Images" in folder_paths
    assert result["folder_count"] >= 2


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


def test_search_files_sales_query():
    result = json.loads(tools_files.search_user_files.invoke({"query": "Acme pricing"}))
    assert len(result["results"]) > 0, "No results for sales query"
    assert "sales" in result["domains_searched"], f"Wrong domain: {result['domains_searched']}"


def test_search_files_travel_query():
    result = json.loads(tools_files.search_user_files.invoke({"query": "Helsinki travel"}))
    assert len(result["results"]) > 0, "No results for travel query"
    assert "travel" in result["domains_searched"], f"Wrong domain: {result['domains_searched']}"


def test_index_all_files():
    count = tools_files.index_all_files()
    assert count >= 4, f"Expected at least 4 files indexed, got {count}"


def test_preview_user_file_data_contains_summary_card():
    preview = tools_files.preview_user_file_data("Acme_Pricing_Tiers.md")
    assert preview["filename"] == "Acme_Pricing_Tiers.md"
    assert preview["summary_card"]["points"], "Expected summary points"
    assert preview["analysis"]["mode"] == "text"
    assert "sales" in preview["domains"]


def test_preview_user_file_data_supports_pdf_and_image():
    pdf_preview = tools_files.preview_user_file_data("Acme_Renewal_Brief.pdf")
    assert pdf_preview["preview_type"] == "pdf"
    assert pdf_preview["summary_card"]["points"]

    image_preview = tools_files.preview_user_file_data("NovaTech_Booth_Mock.png")
    assert image_preview["preview_type"] == "image"
    assert image_preview["analysis"]["classification"] == "images"


def test_open_user_file_data_includes_viewer_payload():
    opened = tools_files.open_user_file_data("Acme_Pricing_Tiers.md")
    assert opened["preview_type"] == "text"
    assert opened["viewer"]["kind"] == "text"
    assert opened["viewer"]["raw_url"].endswith("/Acme_Pricing_Tiers.md/raw")
    assert "pricing" in opened["content"].lower()
    assert opened["summary_card"]["headline"]


def test_preview_user_file_data_caches_ingestion_metadata(monkeypatch, tmp_path):
    note = tmp_path / "Pricing_Brief.md"
    note.write_text("# Pricing Brief\nAcme pricing and discount summary.", encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    preview = tools_files.preview_user_file_data("Pricing_Brief.md")
    meta_path = tmp_path / ".astra_meta.json"

    assert preview["analysis"]["mode"] == "text"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "Pricing_Brief.md" in meta
    assert meta["Pricing_Brief.md"]["mode"] == "text"
    assert meta["Pricing_Brief.md"]["summary_short"]


def test_create_markdown_document_data(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    created = tools_files.create_markdown_document_data(
        title="Weekly Brief",
        sections=[
            {"heading": "Overview", "body": "Pipeline is up and risks are contained."},
            {"heading": "Next Steps", "bullets": ["Call Acme", "Send follow-up notes"]},
        ],
        destination_subdirectory="Notes",
    )

    created_path = tmp_path / "Notes" / "Weekly_Brief.md"
    assert created["filename"] == "Weekly_Brief.md"
    assert created_path.exists()
    content = created_path.read_text(encoding="utf-8")
    assert "# Weekly Brief" in content
    assert "## Overview" in content
    assert "## Next Steps" in content


def test_merge_markdown_files_data(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))
    (tmp_path / "One.md").write_text("# One\nAlpha notes", encoding="utf-8")
    (tmp_path / "Two.md").write_text("# Two\nBeta notes", encoding="utf-8")

    merged = tools_files.merge_markdown_files_data(
        paths=["One.md", "Two.md"],
        output_filename="Merged.md",
        title="Combined Notes",
    )

    merged_path = tmp_path / "Merged.md"
    assert merged["filename"] == "Merged.md"
    assert merged["merged_from"] == ["One.md", "Two.md"]
    content = merged_path.read_text(encoding="utf-8")
    assert "# Combined Notes" in content
    assert "## Sources" in content
    assert "Alpha notes" in content
    assert "Beta notes" in content
    assert "\n# One\n" not in content
    assert "\n# Two\n" not in content


def test_create_markdown_document_data_autofills_sections_from_matching_files(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))
    (tmp_path / "Acme_Pricing_Tiers.md").write_text(
        "# Acme Pricing\nThree tiers are available for commercial accounts.",
        encoding="utf-8",
    )
    (tmp_path / "Helsinki_Travel_Guide.md").write_text(
        "# Helsinki Guide\nMarket Square and the Design District are key stops.",
        encoding="utf-8",
    )

    created = tools_files.create_markdown_document_data(
        title="Acme Pricing and Helsinki Guide",
        filename="Acme_Pricing_and_Helsinki_Guide.md",
        sections=[
            {"heading": "Acme pricing"},
            {"heading": "Helsinki guide"},
        ],
        introduction="Combined note prepared from existing files.",
    )

    created_path = tmp_path / "Acme_Pricing_and_Helsinki_Guide.md"
    assert created["filename"] == "Acme_Pricing_and_Helsinki_Guide.md"
    content = created_path.read_text(encoding="utf-8")
    assert "Three tiers are available" in content
    assert "Market Square and the Design District" in content
    assert "\n# Acme Pricing\n" not in content
    assert "\n# Helsinki Guide\n" not in content


def test_create_pdf_document_data(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))
    monkeypatch.setattr(tools_files, "_render_pdf_document_bytes", lambda **kwargs: b"%PDF-1.4\ncreated")
    monkeypatch.setattr(tools_files, "_refresh_saved_file_metadata", lambda path: None)
    monkeypatch.setattr(
        tools_files,
        "_build_preview_payload",
        lambda path, base=None: {"filename": path.name, "path": tools_files._safe_relative_str(base or tmp_path, path)},
    )

    created = tools_files.create_pdf_document_data(
        title="Board Summary",
        sections=[{"heading": "Overview", "body": "Quarter closed above plan."}],
        destination_subdirectory="Docs",
    )

    created_path = tmp_path / "Docs" / "Board_Summary.pdf"
    assert created["filename"] == "Board_Summary.pdf"
    assert created_path.exists()
    assert created_path.read_bytes().startswith(b"%PDF-1.4")


def test_merge_pdf_files_data(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))
    (tmp_path / "A.pdf").write_bytes(b"%PDF-a")
    (tmp_path / "B.pdf").write_bytes(b"%PDF-b")
    monkeypatch.setattr(tools_files, "_render_pdf_document_bytes", lambda **kwargs: b"%PDF-cover")

    class _FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class _FakeReader:
        def __init__(self, source):
            self.pages = [_FakePage("page text")]

    class _FakeWriter:
        def __init__(self):
            self.pages = []

        def add_page(self, page):
            self.pages.append(page)

        def write(self, buffer):
            buffer.write(b"%PDF-merged")

    fake_pypdf = types.SimpleNamespace(PdfReader=_FakeReader, PdfWriter=_FakeWriter)
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    captured = {}

    def _fake_write_pdf_file_data(*, filename, content, destination_subdirectory=""):
        captured["filename"] = filename
        captured["content"] = content
        captured["destination_subdirectory"] = destination_subdirectory
        return {"filename": filename, "path": filename}

    monkeypatch.setattr(tools_files, "_write_pdf_file_data", _fake_write_pdf_file_data)

    merged = tools_files.merge_pdf_files_data(
        paths=["A.pdf", "B.pdf"],
        output_filename="Merged.pdf",
        title="Q1 Packet",
    )

    assert merged["filename"] == "Merged.pdf"
    assert merged["merged_from"] == ["A.pdf", "B.pdf"]
    assert captured["filename"] == "Merged.pdf"
    assert captured["content"].startswith(b"%PDF-merged")


def test_create_folder_data_and_browse_subdirectory(monkeypatch, tmp_path):
    nested = tmp_path / "Notes"
    nested.mkdir()
    (nested / "Brief.md").write_text("# Brief\nFolder scoped note", encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    created = tools_files.create_folder_data("Archive")
    assert created["path"] == "Archive"

    result = json.loads(tools_files.list_user_files.invoke({"subdirectory": "Notes"}))
    assert result["current_directory"] == "Notes"
    assert result["breadcrumbs"][-1]["path"] == "Notes"
    assert result["files"][0]["filename"] == "Brief.md"


def test_delete_user_folder_data_recursive(monkeypatch, tmp_path):
    nested = tmp_path / "Archive"
    nested.mkdir()
    (nested / "keep.md").write_text("# Keep\nfolder content", encoding="utf-8")
    (nested / "Sub").mkdir()
    (nested / "Sub" / "more.md").write_text("# More\nnested", encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    deleted = tools_files.delete_user_folder_data("Archive")
    assert deleted["deleted"] is True
    assert deleted["path"] == "Archive"
    assert deleted["deleted_file_count"] == 2
    assert not (tmp_path / "Archive").exists()


def test_file_mutation_tools(monkeypatch, tmp_path):
    source = tmp_path / "Draft.md"
    source.write_text("# Draft\nhello", encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    created = json.loads(tools_files.create_user_folder.invoke({"name": "Archive"}))
    assert created["path"] == "Archive"

    moved = json.loads(
        tools_files.move_user_file.invoke({"path": "Draft.md", "destination_subdirectory": "Archive"})
    )
    assert moved["path"] == "Archive/Draft.md"

    renamed = json.loads(
        tools_files.rename_user_file.invoke({"path": "Archive/Draft.md", "new_name": "Final.md"})
    )
    assert renamed["path"] == "Archive/Final.md"

    deleted = json.loads(tools_files.delete_user_file.invoke({"path": "Archive/Final.md"}))
    assert deleted["deleted"] is True

    removed_folder = json.loads(tools_files.delete_user_folder.invoke({"path": "Archive"}))
    assert removed_folder["deleted"] is True
    assert removed_folder["path"] == "Archive"


def test_move_multiple_files(monkeypatch, tmp_path):
    """move_multiple_files moves all files in one call and deduplicates names."""
    (tmp_path / "A.md").write_text("# A", encoding="utf-8")
    (tmp_path / "B.md").write_text("# B", encoding="utf-8")
    (tmp_path / "C.md").write_text("# C", encoding="utf-8")
    dest = tmp_path / "Archive"
    dest.mkdir()
    (dest / "A.md").write_text("# existing A", encoding="utf-8")  # pre-existing conflict
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    result = json.loads(
        tools_files.move_multiple_files.invoke(
            {"paths": ["A.md", "B.md", "C.md"], "destination_subdirectory": "Archive"}
        )
    )
    assert result["moved_count"] == 3
    assert result["error_count"] == 0
    # A.md should be deduped to A_2.md
    moved_names = [m["moved_to"] for m in result["moved"]]
    assert any("A_2.md" in name for name in moved_names), f"Expected deduped A_2.md in {moved_names}"
    assert any("B.md" in name for name in moved_names)
    assert any("C.md" in name for name in moved_names)


def test_move_multiple_files_directory_path(monkeypatch, tmp_path):
    """move_multiple_files reports an error for directory paths instead of crashing."""
    (tmp_path / "Sub").mkdir()
    (tmp_path / "Sub" / "file.md").write_text("# content", encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    result = json.loads(
        tools_files.move_multiple_files.invoke(
            {"paths": ["Sub"], "destination_subdirectory": ""}
        )
    )
    assert result["error_count"] == 1
    assert result["moved_count"] == 0
    assert "folder" in result["errors"][0]["error"].lower()


def test_move_files_in_folder_to_root(monkeypatch, tmp_path):
    source = tmp_path / "Physics & Labs"
    source.mkdir()
    (source / "A.md").write_text("# A", encoding="utf-8")
    (source / "B.pdf").write_bytes(b"%PDF-1.4\n")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    result = json.loads(
        tools_files.move_files_in_folder.invoke(
            {"source_subdirectory": "Physics & Labs", "destination_subdirectory": ""}
        )
    )

    assert result["source"] == "Physics & Labs"
    assert result["destination"] == "root"
    assert result["moved_count"] == 2
    assert (tmp_path / "A.md").exists()
    assert (tmp_path / "B.pdf").exists()
    assert not (source / "A.md").exists()


def test_categorize_user_files_by_type(monkeypatch, tmp_path):
    (tmp_path / "Plan.md").write_text("# Plan", encoding="utf-8")
    (tmp_path / "Brief.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "Mock.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    result = json.loads(tools_files.categorize_user_files.invoke({"group_by": "type"}))

    assert result["group_by"] == "type"
    assert result["moved_count"] == 3
    assert (tmp_path / "Documents" / "Plan.md").exists()
    assert (tmp_path / "Documents" / "Brief.pdf").exists()
    assert (tmp_path / "Images" / "Mock.png").exists()


def test_categorize_user_files_by_name_dry_run(monkeypatch, tmp_path):
    (tmp_path / "Acme_Pricing.md").write_text("# Pricing", encoding="utf-8")
    (tmp_path / "Helsinki_Notes.md").write_text("# Notes", encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    result = json.loads(
        tools_files.categorize_user_files.invoke({"group_by": "name", "dry_run": True})
    )

    assert result["group_by"] == "name"
    assert result["dry_run"] is True
    assert result["moved_count"] == 2
    assert any(move["folder"].endswith("Acme") for move in result["moved"])
    assert any(move["folder"].endswith("Helsinki") for move in result["moved"])
    assert (tmp_path / "Acme_Pricing.md").exists()
    assert (tmp_path / "Helsinki_Notes.md").exists()


def test_categorize_user_files_by_meaning(monkeypatch, tmp_path):
    (tmp_path / "Acme_Pricing.md").write_text("# Pricing", encoding="utf-8")
    (tmp_path / "Helsinki_Travel_Guide.md").write_text("# Travel", encoding="utf-8")
    (tmp_path / "Reminder_Task.md").write_text("# Reminder", encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    result = json.loads(tools_files.categorize_user_files.invoke({"group_by": "meaning"}))

    assert result["group_by"] == "meaning"
    assert result["moved_count"] == 3
    assert (tmp_path / "Sales" / "Acme_Pricing.md").exists()
    assert (tmp_path / "Travel" / "Helsinki_Travel_Guide.md").exists()
    assert (tmp_path / "Admin" / "Reminder_Task.md").exists()


def test_delete_multiple_files(monkeypatch, tmp_path):
    (tmp_path / "A.md").write_text("# A", encoding="utf-8")
    (tmp_path / "B.md").write_text("# B", encoding="utf-8")
    (tmp_path / "Folder").mkdir()
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    result = json.loads(
        tools_files.delete_multiple_files.invoke(
            {"paths": ["A.md", "B.md", "Folder", "missing.md"]}
        )
    )

    assert result["deleted_count"] == 2
    assert result["error_count"] == 2
    assert not (tmp_path / "A.md").exists()
    assert not (tmp_path / "B.md").exists()
    assert any(error["path"] == "Folder" for error in result["errors"])
    assert any(error["path"] == "missing.md" for error in result["errors"])


def test_move_user_file_directory_gives_clear_error(monkeypatch, tmp_path):
    """move_user_file returns a clear error when a directory path is given."""
    (tmp_path / "Sub").mkdir()
    (tmp_path / "Sub" / "file.md").write_text("# content", encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    result = json.loads(
        tools_files.move_user_file.invoke({"path": "Sub", "destination_subdirectory": ""})
    )
    assert "error" in result
    assert "folder" in result["error"].lower()


def test_list_user_files_timeframe_yesterday(monkeypatch, tmp_path):
    yesterday_file = tmp_path / "Yesterday_Notes.md"
    today_file = tmp_path / "Today_Notes.md"
    yesterday_file.write_text("# Notes\nClient pricing summary", encoding="utf-8")
    today_file.write_text("# Notes\nCurrent quarter update", encoding="utf-8")

    now = Path(__file__).stat().st_mtime
    os.utime(yesterday_file, (now - 86400, now - 86400))
    os.utime(today_file, (now, now))

    monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

    result = json.loads(tools_files.list_user_files.invoke({"timeframe": "yesterday"}))
    filenames = [f["filename"] for f in result["files"]]
    assert "Yesterday_Notes.md" in filenames
    assert "Today_Notes.md" not in filenames
    assert result["count"] == result["file_count"] + result["folder_count"]


if __name__ == "__main__":
    tests = [
        test_list_user_files_returns_files,
        test_list_user_files_has_domain_tags,
        test_list_user_files_includes_pdf_and_image_categories,
        test_acme_file_tagged_sales,
        test_helsinki_file_tagged_travel,
        test_search_files_sales_query,
        test_search_files_travel_query,
        test_index_all_files,
        test_preview_user_file_data_contains_summary_card,
        test_preview_user_file_data_supports_pdf_and_image,
        test_create_folder_data_and_browse_subdirectory,
        test_categorize_user_files_by_type,
        test_categorize_user_files_by_name_dry_run,
        test_categorize_user_files_by_meaning,
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
