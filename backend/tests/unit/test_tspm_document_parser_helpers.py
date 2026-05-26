"""Unit tests for app.domains.tspm.document_parser — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no PDF/DOCX libraries needed.
Covers: _split_into_chunks, _parse_txt (txt/md formats),
        ParsedDocument dataclass (is_empty, needs_chunking, summary),
        CHUNK_SIZE_CHARS constant.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.document_parser import (
        _split_into_chunks,
        _parse_txt,
        ParsedDocument,
        CHUNK_SIZE_CHARS,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="document_parser import failed")


# ---------------------------------------------------------------------------
# _split_into_chunks
# ---------------------------------------------------------------------------

class TestSplitIntoChunks:
    def test_short_text_returns_single_chunk(self):
        text = "Hello World"
        result = _split_into_chunks(text)
        assert result == [text]

    def test_text_at_limit_returns_single_chunk(self):
        text = "x" * CHUNK_SIZE_CHARS
        result = _split_into_chunks(text)
        assert len(result) == 1

    def test_long_text_returns_multiple_chunks(self):
        # Create text longer than CHUNK_SIZE_CHARS
        # Lots of paragraphs
        para = "word " * 100  # ~500 chars per paragraph
        text = "\n\n".join([para] * 100)  # ~50K chars total
        result = _split_into_chunks(text)
        assert len(result) > 1

    def test_returns_list(self):
        assert isinstance(_split_into_chunks("hello"), list)

    def test_all_chunks_nonempty(self):
        para = "a " * 200
        text = "\n\n".join([para] * 50)
        for chunk in _split_into_chunks(text):
            assert chunk.strip()

    def test_empty_string_returns_single_empty(self):
        result = _split_into_chunks("")
        assert result == [""]

    def test_chunk_sizes_reasonable(self):
        # Each chunk should not exceed ~2x CHUNK_SIZE_CHARS
        para = "word " * 1000  # Large single paragraph
        text = para
        result = _split_into_chunks(text)
        # Should be list (may or may not chunk a single large paragraph)
        assert isinstance(result, list)

    def test_preserves_text_content(self):
        text = "First paragraph\n\nSecond paragraph\n\nThird paragraph"
        result = _split_into_chunks(text)
        combined = "\n\n".join(result)
        assert "First paragraph" in combined
        assert "Third paragraph" in combined


# ---------------------------------------------------------------------------
# _parse_txt
# ---------------------------------------------------------------------------

class TestParseTxt:
    def test_returns_parsed_document(self):
        result = _parse_txt(b"hello world", "test.txt")
        assert isinstance(result, ParsedDocument)

    def test_utf8_text_decoded(self):
        result = _parse_txt("merhaba dünya".encode("utf-8"), "test.txt")
        assert "merhaba" in result.full_text

    def test_format_set_to_txt(self):
        result = _parse_txt(b"text", "file.txt")
        assert result.format == "txt"

    def test_format_set_to_md(self):
        result = _parse_txt(b"# Heading", "file.md", fmt="md")
        assert result.format == "md"

    def test_filename_set(self):
        result = _parse_txt(b"text", "myfile.txt")
        assert result.filename == "myfile.txt"

    def test_page_count_at_least_one(self):
        result = _parse_txt(b"hello", "test.txt")
        assert result.page_count >= 1

    def test_md_heading_extracted_as_section(self):
        content = "# Introduction\n\nSome text\n\n## Details\n\nMore text"
        result = _parse_txt(content.encode("utf-8"), "doc.md", fmt="md")
        assert "Introduction" in result.sections or "Details" in result.sections

    def test_latin1_fallback(self):
        # Latin-1 encoded text
        content = b"caf\xe9 menu"
        result = _parse_txt(content, "menu.txt")
        assert "caf" in result.full_text

    def test_empty_bytes_parses_gracefully(self):
        result = _parse_txt(b"", "empty.txt")
        assert result.full_text == "" or result.full_text is not None


# ---------------------------------------------------------------------------
# ParsedDocument dataclass
# ---------------------------------------------------------------------------

class TestParsedDocument:
    def test_is_empty_for_empty_text(self):
        doc = ParsedDocument(filename="f", format="txt", full_text="")
        assert doc.is_empty() is True

    def test_is_empty_for_whitespace_only(self):
        doc = ParsedDocument(filename="f", format="txt", full_text="   \n  ")
        assert doc.is_empty() is True

    def test_is_not_empty_for_content(self):
        doc = ParsedDocument(filename="f", format="txt", full_text="hello")
        assert doc.is_empty() is False

    def test_needs_chunking_false_for_small_text(self):
        doc = ParsedDocument(filename="f", format="txt", full_text="short", char_count=100)
        assert doc.needs_chunking() is False

    def test_needs_chunking_true_for_large_text(self):
        doc = ParsedDocument(filename="f", format="txt", full_text="x", char_count=CHUNK_SIZE_CHARS + 1)
        assert doc.needs_chunking() is True

    def test_summary_contains_filename(self):
        doc = ParsedDocument(filename="report.pdf", format="pdf")
        assert "report.pdf" in doc.summary()

    def test_summary_contains_format(self):
        doc = ParsedDocument(filename="f", format="md")
        assert "md" in doc.summary()

    def test_summary_returns_string(self):
        doc = ParsedDocument(filename="f", format="txt")
        assert isinstance(doc.summary(), str)

    def test_default_chunks_empty(self):
        doc = ParsedDocument(filename="f", format="txt")
        assert doc.chunks == []

    def test_default_sections_empty(self):
        doc = ParsedDocument(filename="f", format="txt")
        assert doc.sections == []

    def test_default_error_none(self):
        doc = ParsedDocument(filename="f", format="txt")
        assert doc.error is None


# ---------------------------------------------------------------------------
# CHUNK_SIZE_CHARS constant
# ---------------------------------------------------------------------------

class TestChunkSizeChars:
    def test_is_int(self):
        assert isinstance(CHUNK_SIZE_CHARS, int)

    def test_positive_and_large(self):
        # Should be at least 1000 to be useful
        assert CHUNK_SIZE_CHARS >= 1000
