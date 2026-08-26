"""Offline tests for pure utility functions.

Covers: intents_match, split_text_into_chunks, IPC serialization,
text preprocessing, file_parser chunking.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.services.synthetica_simulation_runner import intents_match
from backend.app.utils.file_parser import split_text_into_chunks


# ---------------------------------------------------------------------------
# intents_match
# ---------------------------------------------------------------------------

class TestIntentsMatch:
    def test_exact_match(self):
        assert intents_match("COOPERATE", "COOPERATE")

    def test_case_insensitive(self):
        assert intents_match("cooperate", "COOPERATE")
        assert intents_match("Defect", "DEFECT")

    def test_none_none(self):
        assert intents_match(None, None)

    def test_none_vs_value(self):
        assert not intents_match(None, "IDLE")
        assert not intents_match("IDLE", None)

    def test_mismatch(self):
        assert not intents_match("COOPERATE", "DEFECT")

    def test_empty_strings(self):
        assert intents_match("", "")

    def test_non_string_coercion(self):
        assert intents_match(123, "123")
        assert intents_match("GATHER_LOCAL", 123) is False


# ---------------------------------------------------------------------------
# split_text_into_chunks
# ---------------------------------------------------------------------------

class TestSplitTextIntoChunks:
    def test_short_text_single_chunk(self):
        chunks = split_text_into_chunks("Hello world")
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_empty_text(self):
        chunks = split_text_into_chunks("")
        assert chunks == []

    def test_whitespace_only(self):
        chunks = split_text_into_chunks("   ")
        assert chunks == []

    def test_long_text_splits(self):
        text = "A. " * 200
        chunks = split_text_into_chunks(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1

    def test_chunks_have_content(self):
        text = "The quick brown fox jumps over the lazy dog. " * 50
        chunks = split_text_into_chunks(text, chunk_size=200, overlap=30)
        for chunk in chunks:
            assert len(chunk) > 0
            assert len(chunk) <= 300  # some leniency for sentence boundaries

    def test_no_overlap_at_end(self):
        text = "A" * 1000
        chunks = split_text_into_chunks(text, chunk_size=200, overlap=0)
        assert len(chunks) >= 5
