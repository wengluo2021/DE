"""Retrieval-only evaluation of the P800 parent-child extension.

The baseline is the already-saved S800 run in ``exports/*/evaluation.json``.  No
LLM call is made here: this script answers the first question, "does child-level
retrieval put better S800 parents into the top 5?"  If it does, generation can be
run separately with the same 30 frozen questions.

Typical use::

    python -m scripts.eval_p800 --config config/experiment.formal-a.json

The script writes JSON/CSV evidence under ``<data_dir>/extension/p800/eval-*``.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from app.config import ROOT, load_settings
from app.data import corpus_loader
from app.evaluation.data import load_gold
from app.evaluation.metrics import evidence_coverage
from app.retrieval.embedding import LocalEmbedder
from app.retrieval.parent_child import aggregate_parents
from app.retrieval.vector_store import ChromaStore


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _find_baseline() -> Path | None:
    candidates = sorted(
        (ROOT / "exports").glob("*/evaluation.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _load_baseline(path: Path) -> tuple[dict[str, dict], dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = {
        row["case_id"]: row
        for row in data.get("cases", [])
        if row.get("condition") == "s800"
    }
    return rows, data


def _rate(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _summary(records: list[dict], baseline_path: Path | None, run: dict) -> dict:
    answerable = [record for record in records if record["answerable"]]
    p800 = {
        "hit_at_1": {
            "any": _rate(sum(record["p800"]["hit_at_1"]["any"] is True for record in answerable), len(answerable)),
            "all": _rate(sum(record["p800"]["hit_at_1"]["all"] is True for record in answerable), len(answerable)),
        },
        "hit_at_5": {
            "any": _rate(sum(record["p800"]["hit_at_5"]["any"] is True for record in answerable), len(answerable)),
            "all": _rate(sum(record["p800"]["hit_at_5"]["all"] is True for record in answerable), len(answerable)),
        },
        "candidate_coverage": {
            "any": _rate(sum(record["p800"]["candidate"]["any"] is True for record in answerable), len(answerable)),
            "all": _rate(sum(record["p800"]["candidate"]["all"] is True for record in answerable), len(answerable)),
        },
        "context_chars": {
            "count": len([record for record in answerable if record["p800"]["context_chars"] is not None]),
            "median": statistics.median([record["p800"]["context_chars"] for record in answerable
                                          if record["p800"]["context_chars"] is not None])
            if any(record["p800"]["context_chars"] is not None for record in answerable) else None,
            "min": min((record["p800"]["context_chars"] for record in answerable
                        if record["p800"]["context_chars"] is not None), default=None),
            "max": max((record["p800"]["context_chars"] for record in answerable
                        if record["p800"]["context_chars"] is not None), default=None),
        },
        "retrieve_ms": {
            "median": statistics.median([record["p800"]["retrieve_ms"] for record in answerable])
            if answerable else None,
        },
    }

    baseline = [record for record in answerable if record["s800"]["hit_at_5"]["all"] is not None]
    s800 = None
    paired = None
    if baseline:
        s800 = {
            "hit_at_1": {
                "any": _rate(sum(record["s800"]["hit_at_1"]["any"] is True for record in baseline), len(baseline)),
                "all": _rate(sum(record["s800"]["hit_at_1"]["all"] is True for record in baseline), len(baseline)),
            },
            "hit_at_5": {
                "any": _rate(sum(record["s800"]["hit_at_5"]["any"] is True for record in baseline), len(baseline)),
                "all": _rate(sum(record["s800"]["hit_at_5"]["all"] is True for record in baseline), len(baseline)),
            },
            "context_chars": {
                "count": len([record for record in baseline if record["s800"]["context_chars"] is not None]),
                "median": statistics.median([record["s800"]["context_chars"] for record in baseline
                                              if record["s800"]["context_chars"] is not None])
                if any(record["s800"]["context_chars"] is not None for record in baseline) else None,
            },
        }
        paired = {}
        for key in ("hit_at_5", "hit_at_1"):
            wins = losses = ties = 0
            for record in baseline:
                p_value = record["p800"][key]["all"]
                s_value = record["s800"][key]["all"]
                if p_value == s_value:
                    ties += 1
                elif p_value is True:
                    wins += 1
                else:
                    losses += 1
            paired[key] = {"p800_wins": wins, "s800_wins": losses, "ties": ties}

    return {
        "run": run,
        "answerable_cases": len(answerable),
        "all_cases": len(records),
        "baseline": str(baseline_path) if baseline_path else None,
        "p800": p800,
        "s800": s800,
        "paired": paired,
    }


def _write_csv(path: Path, records: list[dict]) -> None:
    fields = [
        "case_id", "answerable", "question",
        "p800_hit1_any", "p800_hit1_all", "p800_hit5_any", "p800_hit5_all",
        "p800_candidate_any", "p800_candidate_all",
        "p800_context_chars", "p800_retrieve_ms", "p800_parent_count", "p800_child_count",
        "s800_hit1_any", "s800_hit1_all", "s800_hit5_any", "s800_hit5_all",
        "s800_context_chars",
        "delta_hit5_all", "delta_context_chars",
        "top_parent_ids", "matched_child_ids",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            p800 = record["p800"]
            s800 = record["s800"]
            writer.writerow({
                "case_id": record["case_id"],
                "answerable": record["answerable"],
                "question": record["question"],
                "p800_hit1_any": p800["hit_at_1"]["any"],
                "p800_hit1_all": p800["hit_at_1"]["all"],
                "p800_hit5_any": p800["hit_at_5"]["any"],
                "p800_hit5_all": p800["hit_at_5"]["all"],
                "p800_candidate_any": p800["candidate"]["any"],
                "p800_candidate_all": p800["candidate"]["all"],
                "p800_context_chars": p800["context_chars"],
                "p800_retrieve_ms": p800["retrieve_ms"],
                "p800_parent_count": p800["parent_count"],
                "p800_child_count": p800["child_count"],
                "s800_hit1_any": s800["hit_at_1"]["any"],
                "s800_hit1_all": s800["hit_at_1"]["all"],
                "s800_hit5_any": s800["hit_at_5"]["any"],
                "s800_hit5_all": s800["hit_at_5"]["all"],
                "s800_context_chars": s800["context_chars"],
                "delta_hit5_all": record["delta_hit5_all"],
                "delta_context_chars": record["delta_context_chars"],
                "top_parent_ids": json.dumps(p800["top_parent_ids"], ensure_ascii=False),
                "matched_child_ids": json.dumps(p800["matched_child_ids"], ensure_ascii=False),
            })


def _main() -> int:
    parser = argparse.ArgumentParser(description="Retrieval-only P800 vs saved S800 evaluation")
    parser.add_argument("--config", help="experiment JSON (default: DERAG_CONFIG or config/experiment.json)")
    parser.add_argument("--out", help="P800 extension directory (default: <data_dir>/extension/p800)")
    parser.add_argument("--output-dir", help="evaluation output directory (default: <out>/eval-<stamp>)")
    parser.add_argument("--baseline", help="saved evaluation.json containing s800 rows")
    parser.add_argument("--no-baseline", action="store_true", help="run P800 only")
    parser.add_argument("--candidate-k", type=int, default=50,
                        help="number of child hits before parent aggregation (default 50)")
    parser.add_argument("--limit", type=int, help="only evaluate the first N gold cases (smoke test)")
    args = parser.parse_args()
    if args.candidate_k < 5:
        parser.error("--candidate-k must be at least 5")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")

    settings = load_settings(args.config)
    config = settings.retrieval_config()
    data_dir = Path(config["data_dir"])
    extension_dir = Path(args.out) if args.out else data_dir / "extension" / "p800"
    if not extension_dir.is_absolute():
        extension_dir = ROOT / extension_dir
    manifest = json.loads((extension_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("state") != "completed":
        raise ValueError("P800 index is not completed; run scripts.build_p800 first")
    parents = {row["chunk_id"]: row for row in _read_jsonl(extension_dir / "parents.jsonl")}
    children = {row["chunk_id"]: row for row in _read_jsonl(extension_dir / "children.jsonl")}
    if len(parents) != manifest["counts"]["parents"] or len(children) != manifest["counts"]["children"]:
        raise ValueError("P800 manifest counts differ from the JSONL exports")

    baseline_path = None if args.no_baseline else Path(args.baseline) if args.baseline else _find_baseline()
    if baseline_path is not None and not baseline_path.is_absolute():
        baseline_path = ROOT / baseline_path
    baseline_rows: dict[str, dict] = {}
    if baseline_path is not None:
        baseline_rows, baseline_data = _load_baseline(baseline_path)
        if baseline_data.get("corpus_version") != config["corpus_version"]:
            raise ValueError("Baseline corpus version differs from the active configuration")

    loader = corpus_loader(data_dir, formal=settings.experiment.mode == "formal")
    gold = load_gold(settings, loader)
    cases = gold.cases[:args.limit] if args.limit else gold.cases

    embedder = LocalEmbedder(config["embedding"])
    store = None
    try:
        store = ChromaStore(extension_dir / "chroma" / manifest["index_version"])
        collection = store.collection("p800")
        collection.count()
        records: list[dict] = []
        for case in cases:
            evidence = [item.model_dump(mode="json") for item in case.evidence]
            record = {
                "case_id": case.case_id,
                "question": case.question,
                "answerable": case.answerable,
                "p800": None,
                "s800": None,
                "delta_hit5_all": None,
                "delta_context_chars": None,
            }
            if case.answerable:
                start = perf_counter()
                vector = embedder.encode([case.question], query=True, ids=["question"])[0]
                found = store.query("p800", vector, args.candidate_k)
                hits = aggregate_parents(found, children, parents, top_k=5)
                all_parents = aggregate_parents(found, children, parents, top_k=None)
                elapsed = (perf_counter() - start) * 1000
                hit1 = evidence_coverage(hits, evidence, 1)
                hit5 = evidence_coverage(hits, evidence, 5)
                candidate = evidence_coverage(all_parents, evidence, len(all_parents))
                record["p800"] = {
                    "hit_at_1": hit1,
                    "hit_at_5": hit5,
                    "candidate": candidate,
                    "context_chars": sum(len(hit["text"]) for hit in hits),
                    "retrieve_ms": elapsed,
                    "parent_count": len(all_parents),
                    "child_count": len(found),
                    "top_parent_ids": [hit["chunk_id"] for hit in hits],
                    "matched_child_ids": [hit["matched_child_id"] for hit in hits],
                }
                baseline = baseline_rows.get(case.case_id)
                if baseline is not None:
                    metrics = baseline.get("metrics") or {}
                    b_hit1 = metrics.get("hit_at_1") or {"any": None, "all": None}
                    b_hit5 = metrics.get("hit_at_5") or {"any": None, "all": None}
                    b_context = metrics.get("context_chars")
                    record["s800"] = {
                        "hit_at_1": b_hit1,
                        "hit_at_5": b_hit5,
                        "context_chars": b_context,
                    }
                    if b_hit5.get("all") is not None:
                        record["delta_hit5_all"] = int(hit5["all"]) - int(b_hit5["all"])
                    if b_context is not None:
                        record["delta_context_chars"] = record["p800"]["context_chars"] - b_context
                else:
                    record["s800"] = {
                        "hit_at_1": {"any": None, "all": None},
                        "hit_at_5": {"any": None, "all": None},
                        "context_chars": None,
                    }
            else:
                record["p800"] = {
                    "hit_at_1": {"any": None, "all": None},
                    "hit_at_5": {"any": None, "all": None},
                    "candidate": {"any": None, "all": None},
                    "context_chars": None,
                    "retrieve_ms": None,
                    "parent_count": None,
                    "child_count": None,
                    "top_parent_ids": [],
                    "matched_child_ids": [],
                }
                record["s800"] = {
                    "hit_at_1": {"any": None, "all": None},
                    "hit_at_5": {"any": None, "all": None},
                    "context_chars": None,
                }
            records.append(record)
            print(f"evaluated {case.case_id}", flush=True)

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_dir = Path(args.output_dir) if args.output_dir else extension_dir / f"eval-{stamp}"
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        run = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "corpus_version": config["corpus_version"],
            "index_version": manifest["index_version"],
            "child_chars": manifest["material"]["child_chars"],
            "min_child_chars": manifest["material"]["min_child_chars"],
            "candidate_k": args.candidate_k,
            "top_k": 5,
            "gold_version": gold.gold_version,
            "limit": args.limit,
        }
        summary = _summary(records, baseline_path, run)
        (output_dir / "p800-eval.json").write_text(
            json.dumps({"run": run, "summary": summary, "cases": records},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
        (output_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
        _write_csv(output_dir / "p800-cases.csv", records)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"wrote {output_dir}")
        return 0
    finally:
        if store is not None:
            store.close()


if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except Exception as exc:
        print(f"P800 evaluation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
