"""P800 parent-child extension: split S800 parents into sentence-aligned children.

This module intentionally uses only the standard library.  It can therefore be
unit-tested without Chroma, torch or BGE-M3.  The parent chunks are B's frozen
``s800`` chunks; the child chunks are new ``p800`` records that are embedded for
retrieval.  At query time child hits are de-duplicated back to their parent, so
the language model still receives complete 800-character legal units.

Design notes
------------
* Parent boundaries are never changed.  ``P800`` and ``S800`` therefore return
  the same evidence unit; only the retrieval granularity differs.
* Children are non-overlapping and cover each parent exactly once.  They are
  packed on sentence boundaries and only hard-split when one sentence exceeds
  ``child_chars``.
* ``min_child_chars`` prevents headings or whitespace fragments from becoming
  noise vectors.  Such spans remain in the parent but are marked
  ``indexable=False`` and are not written to Chroma.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

# Kept local so this module has no package-relative imports.  The pattern is the
# same sentence/paragraph boundary used by app.retrieval.chunking.BOUNDARY.
_BOUNDARY = re.compile(
    r"[。！？；](?:[”’」』])?[ \t]*(?:\n+)?|"
    r'''[.!?;](?:["'”’])?(?=\s|$)[ \t]*(?:\n+)?|\n+'''
)


def _edges(text: str, start: int, end: int) -> list[int]:
    """Return absolute sentence/paragraph cut positions in ``text[start:end]``."""
    edges = [start]
    edges.extend(start + match.end() for match in _BOUNDARY.finditer(text[start:end]))
    if edges[-1] != end:
        edges.append(end)
    return edges


def _pack(text: str, start: int, end: int, limit: int) -> list[tuple[int, int]]:
    """Greedily pack sentences up to ``limit``; hard-split only an overlong sentence."""
    edges = _edges(text, start, end)
    spans: list[tuple[int, int]] = []
    pending: tuple[int, int] | None = None
    for left, right in zip(edges, edges[1:]):
        if left == right:
            continue
        if right - left > limit:
            if pending is not None:
                spans.append(pending)
                pending = None
            spans.extend((pos, min(pos + limit, right)) for pos in range(left, right, limit))
        elif pending is not None and right - pending[0] <= limit:
            pending = (pending[0], right)
        else:
            if pending is not None:
                spans.append(pending)
            pending = (left, right)
    if pending is not None:
        spans.append(pending)
    return spans


def _child_id(parent: Mapping[str, Any], start: int, end: int, child_chars: int) -> str:
    """Stable ID independent of build order; identical inputs always collide safely."""
    key = (
        f"{parent['corpus_version']}|parent_child|{child_chars}|"
        f"{parent['chunk_id']}|{start}|{end}"
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def split_children(
    parents: Iterable[Mapping[str, Any]],
    *,
    child_chars: int = 250,
    min_child_chars: int = 40,
) -> list[dict[str, Any]]:
    """Split S800 parent chunks into sentence-aligned P800 children.

    Parameters
    ----------
    parents:
        Iterable of B's S800 chunk dictionaries.  Required keys: ``chunk_id``,
        ``corpus_version``, ``document_id``, ``start``, ``end``, ``text``.
    child_chars:
        Maximum child length in Python characters (default 250).
    min_child_chars:
        Spans shorter than this remain in the parent but are marked
        ``indexable=False`` so they do not become noisy vectors.

    Returns
    -------
    A flat list of child dictionaries in parent order and child order.
    """
    if type(child_chars) is not int or child_chars <= 0:
        raise ValueError("child_chars must be a positive integer")
    if type(min_child_chars) is not int or not 0 <= min_child_chars <= child_chars:
        raise ValueError("min_child_chars must be an integer between 0 and child_chars")

    result: list[dict[str, Any]] = []
    for parent in parents:
        text = parent.get("text")
        start = parent.get("start")
        end = parent.get("end")
        if not isinstance(text, str) or not text:
            raise ValueError("parent text must be a non-empty string")
        if type(start) is not int or type(end) is not int or end - start != len(text):
            raise ValueError("parent interval must match its text length")

        spans = _pack(text, 0, len(text), child_chars)
        cursor = 0
        for index, (left, right) in enumerate(spans):
            if left != cursor or right <= left:
                raise ValueError("child spans must be contiguous and non-empty")
            cursor = right
            child_text = text[left:right]
            absolute_start = start + left
            absolute_end = start + right
            result.append(
                {
                    "chunk_id": _child_id(parent, absolute_start, absolute_end, child_chars),
                    "corpus_version": parent["corpus_version"],
                    "condition": "p800",
                    "boundary_method": "parent_child",
                    "target_chars": child_chars,
                    "document_id": parent["document_id"],
                    # Child-level article coverage is not recomputed here; the
                    # parent hit carries the authoritative article IDs/labels.
                    "article_ids": [],
                    "parent_article_ids": list(parent.get("article_ids", [])),
                    "start": absolute_start,
                    "end": absolute_end,
                    "text": child_text,
                    "parent_id": parent["chunk_id"],
                    "parent_start": start,
                    "parent_end": end,
                    "parent_condition": parent.get("condition", "s800"),
                    "child_index": index,
                    "indexable": len(child_text) >= min_child_chars,
                }
            )
        if cursor != len(text):
            raise ValueError("child spans do not cover the parent text")
    return result


def aggregate_parents(
    found: Sequence[tuple[str, float]],
    children: Mapping[str, Mapping[str, Any]],
    parents: Mapping[str, Mapping[str, Any]],
    *,
    top_k: int | None = 5,
) -> list[dict[str, Any]]:
    """Group child hits by parent, rank parents, and return parent-level hits.

    ``found`` is the ordered ``(child_id, cosine_distance)`` list returned by
    Chroma.  A parent's score is the best score among its retrieved children
    (``1 - distance``).  This avoids a length bias: a long parent with many
    weak children should not outrank a parent with one strong match.
    """
    if top_k is not None and (type(top_k) is not int or top_k <= 0):
        raise ValueError("top_k must be a positive integer or None")

    grouped: dict[str, dict[str, Any]] = {}
    seen_children: set[str] = set()
    for child_id, distance in found:
        if child_id in seen_children:
            continue
        seen_children.add(child_id)
        child = children.get(child_id)
        if child is None:
            raise ValueError(f"retrieved child is absent from the child export: {child_id}")
        if not child.get("indexable", True):
            continue
        parent_id = child.get("parent_id")
        parent = parents.get(parent_id)
        if parent is None:
            raise ValueError(f"child points to an absent parent: {parent_id}")
        try:
            score = 1.0 - float(distance)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid distance for child {child_id}") from exc

        entry = grouped.get(parent_id)
        if entry is None:
            grouped[parent_id] = {
                "parent": parent,
                "best_score": score,
                "best_child": child,
                "child_count": 1,
                "child_ids": [child_id],
            }
        else:
            entry["child_count"] += 1
            entry["child_ids"].append(child_id)
            if score > entry["best_score"] or (
                score == entry["best_score"] and child_id < entry["best_child"]["chunk_id"]
            ):
                entry["best_score"] = score
                entry["best_child"] = child

    ordered = sorted(
        grouped.values(),
        key=lambda entry: (-entry["best_score"], entry["parent"]["chunk_id"]),
    )
    if top_k is not None:
        ordered = ordered[:top_k]

    hits: list[dict[str, Any]] = []
    for rank, entry in enumerate(ordered, 1):
        parent = entry["parent"]
        child = entry["best_child"]
        hits.append(
            {
                "rank": rank,
                "score": entry["best_score"],
                "chunk_id": parent["chunk_id"],
                "corpus_version": parent["corpus_version"],
                "condition": "p800",
                "document_id": parent["document_id"],
                "article_ids": list(parent.get("article_ids", [])),
                "start": parent["start"],
                "end": parent["end"],
                "text": parent["text"],
                "parent_condition": parent.get("condition", "s800"),
                "matched_child_id": child["chunk_id"],
                "matched_child_start": child["start"],
                "matched_child_end": child["end"],
                "matched_child_score": entry["best_score"],
                "matched_child_count": entry["child_count"],
                "matched_child_ids": list(entry["child_ids"]),
            }
        )
    return hits
