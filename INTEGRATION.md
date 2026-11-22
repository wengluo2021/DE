# Integration notes

## Required change set: none to existing files

The retrieval-only P800 extension is deliberately additive.

| Action | Path |
|---|---|
| Add | `app/retrieval/parent_child.py` |
| Add | `scripts/build_p800.py` |
| Add | `scripts/eval_p800.py` |
| Add | `tests/test_parent_child.py` |
| Add | `docs/父子分块扩展.md` |

Copy these five files into the same relative paths in the existing DERag checkout. Do not modify the frozen experiment configuration or the four `CONDITIONS`.

Example (replace the target with your existing checkout):

```powershell
$target = 'D:\gitcode\Edit\DE'
$src = 'C:\path\to\P800-extension'

Copy-Item "$src\app\retrieval\parent_child.py" "$target\app\retrieval\" -Force
Copy-Item "$src\scripts\build_p800.py"          "$target\scripts\" -Force
Copy-Item "$src\scripts\eval_p800.py"           "$target\scripts\" -Force
Copy-Item "$src\tests\test_parent_child.py"     "$target\tests\" -Force
Copy-Item "$src\docs\父子分块扩展.md"              "$target\docs\" -Force
```

### Why no core edit is required

- `build_p800.py` imports the existing `chunks_for_condition`, `LocalEmbedder`, and `ChromaStore`; it writes a separate extension directory.
- `eval_p800.py` imports the existing gold loader and the existing `evidence_coverage` metric; it reads the saved S800 export as baseline.
- `parent_child.py` is standard-library-only and is not imported by the core app.
- `test_parent_child.py` loads the pure module by path, so it does not add a runtime dependency.

## Verify the checkout is clean

From the existing project root, after copying:

```powershell
git status --short
```

Expected: five untracked additions, no modified tracked files.

```text
?? app/retrieval/parent_child.py
?? docs/父子分块扩展.md
?? scripts/build_p800.py
?? scripts/eval_p800.py
?? tests/test_parent_child.py
```

## Optional: generation/UI integration (not implemented)

The package evaluates retrieval only. It does not add `p800` to the web UI, `ExperimentSettings.conditions`, `SearchHit` contracts, or the evaluation loop.

If the retrieval pilot improves Hit@5, a later change would need to:

1. allow `p800` as an extension condition (without changing the frozen four-condition experiment fingerprint);
2. pass parent-level hits through the existing QA/citation contracts;
3. add the condition to an extension evaluation run or a separate result viewer;
4. rerun the same 30 questions with the same prompt/model for a generation comparison.

That is intentionally not included here because it is untested and would change the frozen pipeline. Keep this package as the additive P800 module until the retrieval result is available.
