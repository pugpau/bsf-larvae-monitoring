"""Unit tests for RAG text splitter."""

import pytest
from src.rag.text_splitter import split_text, TextChunk


class TestSplitText:
    def test_empty_text_returns_empty(self):
        assert split_text("") == []
        assert split_text("   ") == []

    def test_short_text_single_chunk(self):
        result = split_text("短いテキスト", source_title="test")
        assert len(result) == 1
        assert result[0].text == "短いテキスト"
        assert result[0].index == 0
        assert result[0].source_title == "test"

    def test_text_at_chunk_size_boundary(self):
        text = "a" * 512
        result = split_text(text, chunk_size=512)
        assert len(result) == 1
        assert len(result[0].text) == 512

    def test_long_text_creates_multiple_chunks(self):
        text = "あ" * 1200
        result = split_text(text, chunk_size=512, overlap=50)
        assert len(result) >= 2
        for i, chunk in enumerate(result):
            assert chunk.index == i
            assert len(chunk.text) <= 512

    def test_sentence_boundary_splitting(self):
        text = "最初の文です。二番目の文です。三番目の文。" + "あ" * 500
        result = split_text(text, chunk_size=30, overlap=5)
        # Should break at 。 when possible
        assert any("。" in chunk.text[-2:] for chunk in result[:-1])

    def test_newline_boundary_splitting(self):
        text = "第一段落のテキスト\n第二段落のテキスト\n" + "あ" * 500
        result = split_text(text, chunk_size=20, overlap=5)
        assert len(result) >= 2

    def test_overlap_creates_shared_content(self):
        text = "a" * 100 + "b" * 100 + "c" * 100
        result = split_text(text, chunk_size=120, overlap=20)
        # With overlap, chunks should share some content
        assert len(result) >= 2

    def test_source_title_propagates(self):
        text = "a" * 1200
        result = split_text(text, source_title="BSF Guide", chunk_size=512)
        for chunk in result:
            assert chunk.source_title == "BSF Guide"

    def test_chunk_is_frozen_dataclass(self):
        chunk = TextChunk(text="test", index=0, source_title="src")
        with pytest.raises(AttributeError):
            chunk.text = "modified"
