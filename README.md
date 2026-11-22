# P800 parent–child retrieval extension

This folder is **only Member D's additive extension**. It is not a copy of the group project, and it does not include A/B/C's source, data, results, or presentation.

It adds a third retrieval strategy on top of the existing DERag codebase:

- parent = an existing S800 structural chunk (≤800 characters);
- child = a 250-character sentence-aligned slice of that parent;
- index only the child vectors;
- retrieve Top-50 children, group by parent, score each parent by its best child, and return the Top-5 parents;
- the LLM still reads the full parent, so the evidence unit is unchanged.

## Files

| File | Destination in the existing project | Purpose |
|---|---|---|
| `app/retrieval/parent_child.py` | `app/retrieval/parent_child.py` | Pure split/aggregation logic; no heavy imports |
| `scripts/build_p800.py` | `scripts/build_p800.py` | Reuse S800 parents, build an independent child index |
| `scripts/eval_p800.py` | `scripts/eval_p800.py` | Retrieval-only, paired evaluation against saved S800 results |
| `tests/test_parent_child.py` | `tests/test_parent_child.py` | 9 unit tests for coverage, stable IDs, dedupe, Top-5, hit metric |
| `docs/父子分块扩展.md` | `docs/父子分块扩展.md` | Method, metrics, commands, limitations |

## Integration: add only, no core edits

For the retrieval-only experiment, **no existing file needs to be modified**:

1. Copy the five files into the same relative paths in the existing DERag checkout.
2. The package does not change `config/experiment.formal-a.json`, `CONDITIONS`, the four index versions, or the 120 saved records.
3. It creates only `data/formal_corpus/extension/p800/`.

`git status` should show only five untracked additions.

See [INTEGRATION.md](INTEGRATION.md) for the exact placement and the optional (not implemented) generation-integration notes.

## Verify

From the existing project root, with its `.venv` and dependencies:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_parent_child.py -q
```

Expected: `9 passed`.

The tests only load the pure module; they do not need BGE-M3, Chroma, or an API key.

## Run the retrieval-only pilot

```powershell
# 1. No model needed: checks the split on the frozen corpus
& '.\.venv\Scripts\python.exe' -m scripts.build_p800 `
  --config config/experiment.formal-a.json --dry-run

# 2. Builds the child index; needs the project BGE-M3 files
& '.\.venv\Scripts\python.exe' -m scripts.build_p800 `
  --config config/experiment.formal-a.json

# 3. Retrieval-only comparison with the saved S800 run; no API key
& '.\.venv\Scripts\python.exe' -m scripts.eval_p800 `
  --config config/experiment.formal-a.json `
  --baseline exports/20261120-232137-eval-ca61c0c0/evaluation.json
```

Expected dry-run counts on the current frozen corpus:

| Item | Count |
|---|---:|
| S800 parents | 625 |
| All child spans | 2,343 |
| Indexed children (≥40 chars) | 2,099 |
| Parents with at least one indexed child | 620 / 625 |

Results are written under `data/formal_corpus/extension/p800/eval-<UTC time>/`.

## Status and boundaries

- **Implemented and tested:** split, aggregation, build script, retrieval-only evaluator, 9 unit tests.
- **Not run in this package:** the real BGE-M3/Chroma P800 retrieval run, 30 generation calls, manual/AI scoring, and UI integration.
- **No performance claim is made.** The 7-case diagnostic in the base project is headroom, not a P800 result.
- The 5 chapter-heading parents shorter than 40 characters are not indexed; the build manifest lists their IDs.
- The extension uses Python character lengths, the same convention as F400/S400/F800/S800.

## What is intentionally not here

- the full DERag source tree;
- A/B/C's modules, data, frozen corpus, or results;
- model weights, `.venv`, Chroma indexes, SQLite databases;
- the 15-minute presentation and PDF;
- the full `artifacts/` stage history.

Those belong to the existing group repository or the separate presentation deliverable.
