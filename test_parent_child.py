"""Unit tests for the pure P800 parent-child helpers.

The helpers are intentionally stdlib-only, so this test loads the module by path
instead of importing ``app.retrieval`` (whose package __init__ imports Chroma's
runtime dependencies).
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from app.evaluation.metrics import evidence_coverage

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "app" / "retrieval" / "parent_child.py"
_SPEC = importlib.util.spec_from_file_location("derag_parent_child_under_test", MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
parent_child = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(parent_child)

split_children = parent_child.split_children
aggregate_parents = parent_child.aggregate_parents


def _parent(chunk_id: str, text: str, *, start: int = 100, document_id: str = "doc"):
    return {
        "chunk_id": chunk_id,
        "corpus_version": "corpus-v1",
        "condition": "s800",
        "document_id": document_id,
        "article_ids": ["article-1"],
        "start": start,
        "end": start + len(text),
        "text": text,
    }


def _child(chunk_id: str, parent_id: str, *, indexable: bool = True):
    return {
        "chunk_id": chunk_id,
        "parent_id": parent_id,
        "corpus_version": "corpus-v1",
        "document_id": "doc",
        "start": 0,
        "end": 10,
        "text": chunk_id,
        "indexable": indexable,
    }


class SplitChildrenTests(unittest.TestCase):
    def test_children_cover_parent_without_overlap_and_respect_limit(self):
        text = (
            "Article 1\n"
            "This is a short sentence. "
            + "This sentence is long enough to fill a child block. " * 8
            + "x" * 300
        )
        parent = _parent("parent-1", text)
        children = split_children([parent], child_chars=120, min_child_chars=20)

        self.assertEqual("".join(child["text"] for child in children), text)
        self.assertEqual(children[0]["start"], parent["start"])
        self.assertEqual(children[-1]["end"], parent["end"])
        self.assertTrue(all(0 < child["end"] - child["start"] <= 120 for child in children))
        self.assertTrue(all(child["parent_id"] == "parent-1" for child in children))
        self.assertTrue(all(child["parent_start"] == parent["start"] for child in children))
        self.assertTrue(all(child["parent_end"] == parent["end"] for child in children))
        self.assertTrue(all(child["condition"] == "p800" for child in children))
        self.assertTrue(all(child["parent_condition"] == "s800" for child in children))
        self.assertEqual(children[0]["parent_article_ids"], ["article-1"])

        # Stable IDs: re-running on the same frozen parent produces identical output.
        again = split_children([parent], child_chars=120, min_child_chars=20)
        self.assertEqual(children, again)

    def test_short_span_is_kept_but_not_indexable(self):
        parent = _parent("parent-2", "A\n" + "B" * 100)
        children = split_children([parent], child_chars=50, min_child_chars=20)

        self.assertEqual("".join(child["text"] for child in children), parent["text"])
        self.assertEqual(children[0]["text"], "A\n")
        self.assertFalse(children[0]["indexable"])
        self.assertTrue(all(child["indexable"] for child in children[1:]))

    def test_invalid_parent_interval_is_rejected(self):
        parent = _parent("parent-3", "short text")
        parent["end"] += 1
        with self.assertRaises(ValueError):
            split_children([parent], child_chars=20, min_child_chars=5)

    def test_invalid_parameters_are_rejected(self):
        parent = _parent("parent-4", "text")
        with self.assertRaises(ValueError):
            split_children([parent], child_chars=0)
        with self.assertRaises(ValueError):
            split_children([parent], child_chars=20, min_child_chars=21)


class AggregateParentsTests(unittest.TestCase):
    def setUp(self):
        self.parents = {
            "p-a": _parent("p-a", "A" * 60, start=0),
            "p-b": _parent("p-b", "B" * 60, start=60),
        }
        self.children = {
            "c-a1": _child("c-a1", "p-a"),
            "c-a2": _child("c-a2", "p-a"),
            "c-a3": _child("c-a3", "p-a"),
            "c-b1": _child("c-b1", "p-b"),
            "c-b2": _child("c-b2", "p-b"),
            "c-short": _child("c-short", "p-a", indexable=False),
        }

    def test_child_hits_are_deduplicated_to_parents(self):
        found = [
            ("c-a1", 0.10),  # 0.90
            ("c-a2", 0.20),  # 0.80
            ("c-a3", 0.30),  # 0.70
            ("c-b1", 0.15),  # 0.85
            ("c-b2", 0.40),  # 0.60
            ("c-short", 0.01),  # must be ignored, not indexed
        ]
        hits = aggregate_parents(found, self.children, self.parents, top_k=2)

        self.assertEqual([hit["chunk_id"] for hit in hits], ["p-a", "p-b"])
        self.assertEqual([hit["rank"] for hit in hits], [1, 2])
        self.assertEqual(hits[0]["matched_child_id"], "c-a1")
        self.assertEqual(hits[0]["matched_child_count"], 3)
        self.assertEqual(hits[1]["matched_child_id"], "c-b1")
        self.assertEqual(hits[1]["matched_child_count"], 2)

    def test_top_k_none_returns_all_parents_and_duplicates_are_ignored(self):
        found = [("c-a1", 0.10), ("c-a1", 0.10), ("c-b1", 0.15)]
        hits = aggregate_parents(found, self.children, self.parents, top_k=None)

        self.assertEqual([hit["chunk_id"] for hit in hits], ["p-a", "p-b"])
        self.assertEqual(hits[0]["matched_child_count"], 1)

    def test_unknown_child_or_parent_is_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_parents([("missing", 0.1)], self.children, self.parents)

        broken_children = {"c-a1": _child("c-a1", "missing-parent")}
        with self.assertRaises(ValueError):
            aggregate_parents([("c-a1", 0.1)], broken_children, self.parents)

    def test_invalid_top_k_is_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_parents([], self.children, self.parents, top_k=0)

    def test_parent_hits_can_be_measured_with_the_existing_hit_metric(self):
        # Evidence crosses the p-a / p-b boundary; the union of both parents covers it.
        evidence = [{"document_id": "doc", "start": 40, "end": 80}]
        found = [("c-a1", 0.10), ("c-b1", 0.15)]
        hits = aggregate_parents(found, self.children, self.parents, top_k=2)

        self.assertTrue(evidence_coverage(hits, evidence, 2)["all"])
        self.assertFalse(evidence_coverage(hits, evidence, 1)["all"])


if __name__ == "__main__":
    unittest.main()
