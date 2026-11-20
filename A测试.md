# A Module Test Guide (for team members)

Record date: 2026-11-19. This guide follows the team member operation approach of [B测试.md](./B测试.md) to check A's official data, character positions, official delivery package, and standard test question set. For implementation principles and field explanations, see [A开发文档.md](./A开发文档.md).

**Suggested order: confirm delivery files → prepare environment → read-only validation → 19 automated tests → normal loading → verify evidence → verify regeneration as needed → report results.**

The main commands apply to Windows PowerShell and Python 3.13.11. Local verification used the existing project environment; team members should run them in their own environment and record the results. These A checks do not require a GPU, model weights, a Chroma instance, or an LLM API key.

## 1. What this guide can test

| Check | Verification content |
| --- | --- |
| Source and snapshot | The registered official HTML exists and the file hash matches |
| Cleaning and structure | Five documents, 121 main provisions; chapter, section, article, and annex positions are valid |
| Source traceability | `text[start:end]` is verbatim identical to the provision or evidence excerpt |
| Formal package | Five-document scope, file hashes, adapted fields, and unified corpus version |
| Standard question set | 30 unique question IDs, 24 answerable / 6 refusal, 42-segment evidence, and version binding |
| Exception handling | Explicit failure for missing files, hash mismatch, version mismatch, duplicate IDs, missing/extra items in formal documents, etc. |
| Reproducibility | Re-running with the same snapshot and rules leaves artifact hashes unchanged |

Passing the above checks shows that the data and interface inputs can be verified. For this version, answer completeness, evidence support relationships, and refusal conditions have been manually reviewed by lead A, with no issues found; actual retrieval performance and system answer correctness will be evaluated by B and C in subsequent testing.

## 2. Confirm the project directory and delivery files

In PowerShell, go to the project root directory. The local example is:

```powershell
Set-Location 'D:\gitcode\Edit\DE'
Get-Location
Get-ChildItem -LiteralPath . -Name
```

On other computers, replace the path in the first line with your own project directory. All subsequent relative paths are based on this; do not enter `scripts` or `app` before running.

The root directory should contain at least:

```text
DE/
  app/retrieval/types.py
  scripts/process_documents.py
  scripts/validate_data.py
  scripts/export_corpus.py
  scripts/build_gold.py
  tests/test_corpus_batch.py
  tests/test_corpus_freeze.py
  tests/test_gold_eval.py
  data/sources.json
  data/raw/                          # Five official HTML files
  data/processed/                    # Five pairs of txt / JSON
  data/corpus_manifest.json
  data/formal_corpus/manifest.json
  data/formal_corpus/raw/             # Five snapshot copies
  data/formal_corpus/processed/       # Five adapted JSON files
  data/sample_corpus/                 # Single-document integration package
  data/eval/gold.jsonl
  data/eval/manifest.json
  data/eval/sample.jsonl
  data/eval/sample_manifest.json
  artifacts/a_review/                # Review report
  A开发文档.md
  A测试.md
```

If the directory contains only B's synthetic test data, first obtain A's delivery directory or a team version that includes A's artifacts. Do not fill gaps with same-named files from other sources, and do not treat `fixture-en-v2` as the formal five-document version.

If this is a Git workspace, you can record the current code state read-only for feedback:

```powershell
git status --short
git rev-parse --short HEAD
```

When there are uncommitted files, the commit number alone cannot describe all current data content; when providing feedback, also record the corpus and question set versions. This guide does not require committing, pushing, or overwriting your own workspace.

## 3. Set up the environment and install the dependencies required by A

First check Python:

```powershell
py -3.13 --version
```

The currently verified version is Python 3.13.11. If `.venv` is absent, create it; if an environment with the correct version already exists, you can skip the creation command:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe --version
```

A's command-line data processing and normal package imports directly use the following dependencies; versions come from the repository's existing dependency declarations:

```powershell
.\.venv\Scripts\python.exe -m pip install beautifulsoup4==4.15.0 soupsieve==4.1.2 filelock==4.2.10
.\.venv\Scripts\python.exe -m pip check
```

| Dependency | Purpose | Registered location |
| --- | --- | --- |
| `beautifulsoup4` | Parse saved HTML | `requirements.txt` |
| `soupsieve` | Beautiful Soup selector support | `requirements.txt` |
| `filelock` | Index service dependency loaded during normal import of `app.retrieval` | `requirements-b.txt` |

`pip check` normally outputs `No broken requirements found.`. The first dependency installation requires access to the package source; after installation, A's cleaning, validation, loading, and question set generation use local files.

Here you run `unittest`; no additional pytest installation is required. When testing B's Chroma and real embeddings, install B's full runtime and test dependencies according to `B测试.md`; this set of A checks will not download model weights. Team members who have already installed B's environment still need to confirm that the HTML parsing dependencies are present.

All commands explicitly use the project interpreter; no virtual environment activation is needed. Even if the terminal shows another environment name, the `.venv` in the command takes precedence.

## 4. Perform read-only validation first

### 4.1 Full corpus

```powershell
.\.venv\Scripts\python.exe scripts\validate_data.py --scope corpus
$LASTEXITCODE
```

The final summary for the current version should contain:

```text
documents=5
main_articles=121
result=ok
0
```

The program also prints the structure and interval check counts for each document. 121 comes from adding 35, 27, 27, 21, and 11 items; it is not a padded question count.

### 4.2 Formal question set

```powershell
.\.venv\Scripts\python.exe scripts\validate_data.py --scope eval
$LASTEXITCODE
```

The expected summary is:

```text
scope=eval
corpus_version=794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795
questions=30 answerable=24 refusal=6
result=ok
0
```

These two commands do not generate or rewrite the corpus or question set. `result=ok` should appear together with process exit code 0; on failure, retain the file, document, or question ID and interval from the error.

To check only one corpus, run:

```powershell
.\.venv\Scripts\python.exe scripts\validate_data.py --scope corpus --document-id eu_unfair_terms_93_13
```

`--scope eval` checks the entire question set and is not used together with `--document-id`.

## 5. Run A's 19 automated tests

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_corpus_batch tests.test_corpus_freeze tests.test_gold_eval
$LASTEXITCODE
```

The current expected result is:

```text
Ran 19 tests in ...s

OK
0
```

| Module | Number of items | Main exceptions and behaviors |
| --- | ---: | --- |
| `tests.test_corpus_batch` | 8 | Mutually exclusive parameters, empty lists, duplicate IDs, missing snapshots, hash mismatches, partial failures, missing artifacts / unregistered files, section mirrors |
| `tests.test_corpus_freeze` | 6 | Missing processed files, modified official snapshots, version mismatches, duplicate exports, missing items in the official manifest, and multiple rejections |
| `tests.test_gold_eval` | 5 | Evidence attribution and mismatches, duplicate attachment clause numbers, refusal evidence, duplicate question numbers, versions, hashes, CRLF, and parameters |

A single test may check multiple related exceptions, so each exception name in the table above cannot be counted as a separate test item. After new tests are added, use the actual number of test cases; do not delete tests just to keep 19 items.

These test cases create exceptions using in-memory objects or copies in temporary directories; the official files remain unchanged. Parameter errors or `result=failed` in the output may come from intentionally triggered counterexamples; the whole run must still end with `OK` and exit code 0. If `FAILED`, `ERROR`, or a traceback appears, do not ignore it just because an expected failure line was seen.

If you need to keep local run logs, write them to a separate directory to avoid overwriting the accepted review report:

```powershell
New-Item -ItemType Directory -Path .\artifacts\a_local_tests -Force | Out-Null
.\.venv\Scripts\python.exe -m unittest tests.test_corpus_batch tests.test_corpus_freeze tests.test_gold_eval 2>&1 | Tee-Object -FilePath .\artifacts\a_local_tests\unittest.txt
$LASTEXITCODE
```

## 6. Normal import and loading of the official package and sample package

Run the entire block below in PowerShell. It loads the loader through the normal package import, checks the five official documents and the independent sample, and verifies that the clause content matches the accepted artifacts:

```powershell
@'
import json
from pathlib import Path
from app.retrieval.types import formal_loader

root = Path.cwd()
packages = [
    ("formal_corpus", "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795", 5, 121),
    ("sample_corpus", "41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50", 1, 35),
]
for name, version, expected_docs, expected_articles in packages:
    docs = formal_loader(root / "data" / name)(version)
    assert len(docs) == expected_docs
    assert sum(len(doc["articles"]) for doc in docs) == expected_articles
    for doc in docs:
        document_id = doc["document_id"]
        accepted = json.loads((root / "data/processed" / f"{document_id}.json").read_text(encoding="utf-8"))
        assert doc["text"].encode("utf-8") == (root / "data/processed" / f"{document_id}.txt").read_bytes()
        for article, original in zip(doc["articles"], accepted["articles"], strict=True):
            for key in ("article_id", "text", "start", "end"):
                assert article[key] == original[key]
            assert article["label"] == f"Article {original['number']}"
            assert article["chapter"] == original["chapter_id"]
            assert article["section"] == original["section_id"]
            assert doc["text"][article["start"]:article["end"]] == article["text"]
    print(f"PASS {name}: documents={len(docs)}, articles={expected_articles}")
'@ | .\.venv\Scripts\python.exe -
$LASTEXITCODE
```

Expected output is two PASS lines: official package 5 documents / 121 clauses, sample package 1 documents / 35 clauses, with a final exit code of 0.

The loading directory for the official package is `data/formal_corpus`; you cannot pass `data/processed`, nor can you rename the project-level `corpus_manifest.json` to impersonate B's manifest.

## 7. Verify standard questions, evidence, and question set version

The script below only reads the official package and question set, validates all evidence slices, and recomputes the distribution:

```powershell
@'
import hashlib
import json
from collections import Counter
from pathlib import Path
from app.retrieval.types import formal_loader

root = Path.cwd()
manifest = json.loads((root / "data/eval/manifest.json").read_text(encoding="utf-8"))
raw = (root / "data/eval/gold.jsonl").read_bytes()
expected_version = "9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d"
assert hashlib.sha256(raw).hexdigest() == manifest["gold_version"] == manifest["gold_sha256"] == expected_version
assert manifest["corpus_version"] == "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
cases = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
assert len(cases) == len({case["case_id"] for case in cases}) == 30
assert sum(case["should_refuse"] is False for case in cases) == 24
assert sum(case["should_refuse"] is True for case in cases) == 6
docs = {doc["document_id"]: doc for doc in formal_loader(root / "data/formal_corpus")(manifest["corpus_version"])}
lengths = []
for case in cases:
    assert case["corpus_version"] == manifest["corpus_version"]
    if case["should_refuse"]:
        assert case["evidence"] == [] and case["key_facts"] == []
        assert case["refusal_reason"].strip()
    for item in case["evidence"]:
        text = docs[item["document_id"]]["text"]
        assert text[item["start"]:item["end"]] == item["quote"]
        assert 0 < len(item["quote"]) < 400
        lengths.append(len(item["quote"]))
types = dict(Counter(case["question_type"] for case in cases))
assert types == manifest["question_types"] == {"single_article": 13, "multi_evidence": 11, "unanswerable": 6}
assert len(lengths) == 42 and min(lengths) == 68 and max(lengths) == 393
print("PASS gold: questions=30, answerable=24, refusal=6, evidence=42, lengths=68..393")
'@ | .\.venv\Scripts\python.exe -
$LASTEXITCODE
```

The complete structural validation of evidence attribution is still performed by `--scope eval` in section 4. The standalone script above is for visually seeing the question count, hashes, and slice relationships; it does not replace that validator.

You can also use PowerShell to quickly view the question set file hash:

```powershell
Get-FileHash -LiteralPath .\data\eval\gold.jsonl -Algorithm SHA256
```

The uppercase hexadecimal shown by PowerShell and the lowercase value in the manifest represent the same SHA-256.

## 8. What to check against the source text

Source review checks in the order "question → reference answer → key facts → evidence → other paragraphs of the same article and related structure"; it does not end as soon as the quote is seen in the body text.

| Sample | Key checks |
| --- | --- |
| First, middle, and last article of each regulation | Whether the title, paragraphs, negations, and exceptions are complete, and whether the ranges correspond |
| Articles 5–9 of the fourth document | Article 5 belongs directly to Chapter 2; Article 6/7 and Article 8/9 belong to two different sections |
| Article 11 of the fifth document | The article ends before the signature block; the signature block, footnotes, and attachments are not merged into the main article |
| `gold-crd-withdrawal-refund` | The three evidence passages cover paragraphs 13(1), (2), and (3) respectively; do not miss the additional delivery fee, the deferred refund, and the condition that the trader collects the goods themselves |
| `gold-sgd-two-year-liability` | The general two-year period, the longer period, and the condition that a shorter period may be agreed for second-hand goods but must be at least one year |
| `gold-ucpd-pyramid-scheme` | Evidence comes from Articles 5 and `eu_unfair_practices_2005_29:annex:I` respectively |
| Six refusal questions | Whether the five full texts, preambles, and attachments contain rules sufficient to answer, without judging by a single keyword |

The existing five documents and 30 questions have completed AI-assisted source review and human review. Lead A has confirmed that review is complete and no issues were found; the human review status is updated accordingly. When later versions are revised or team members retest, please record the actual reviewer, date, document or question number, issues found, and basis.

The browser visual check was confirmed as passed by Lead A on 2026-11-19, with no issues found. The DOM comparisons in each AI report are still retained separately. The cleaning of box styles in attachments into plain numbers is an existing formatting limitation and must be understood together with the corresponding completion instructions.

## 9. Verify repeated generation as needed

This section rewrites the cleaned files, official package, and question set. For routine acceptance, complete the read-only validation first; when you need to check pipeline reproducibility, then execute the following sequence:

```powershell
.\.venv\Scripts\python.exe scripts\process_documents.py --all
.\.venv\Scripts\python.exe scripts\export_corpus.py
.\.venv\Scripts\python.exe scripts\build_gold.py
.\.venv\Scripts\python.exe scripts\validate_data.py --scope corpus
.\.venv\Scripts\python.exe scripts\validate_data.py --scope eval
```

Each command should exit 0. Cleaning should succeed 5 and fail 0; the official export is still 5 documents, 121 clauses, and the original corpus version; the question set is still the original `gold_version`. The commands do not need to access live EUR-Lex and use saved snapshots.

To check the 44 protected files in the final report all at once, you can use the following script. It first validates the report baseline, then executes the rebuild commands in order; it stops if any step fails or any file hash changes.

```powershell
@'
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path.cwd()
report = (root / "artifacts/a_review/a_final_validation.md").read_text(encoding="utf-8")
expected = {
    path.strip(): value
    for path, value in re.findall(r"^\| ((?:data|artifacts)/[^|]+) \| `([a-f0-9]{64})` \|$", report, re.M)
}
sources = json.loads((root / "data/sources.json").read_text(encoding="utf-8"))["sources"]
for source in sources:
    name = Path(source["snapshot"]["path"]).name
    expected[f"data/formal_corpus/raw/{name}"] = source["snapshot"]["sha256"]
assert len(expected) == 44

def check_hashes():
    for relative, value in expected.items():
        path = root / relative
        assert path.is_file(), f"Missing: {relative}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == value, f"Changed: {relative}"

check_hashes()
commands = [
    ["scripts/process_documents.py", "--all"],
    ["scripts/export_corpus.py"],
    ["scripts/build_gold.py"],
    ["scripts/validate_data.py", "--scope", "corpus"],
    ["scripts/validate_data.py", "--scope", "eval"],
]
for args in commands:
    subprocess.run([sys.executable, *args], check=True)
    check_hashes()
print("PASS: 44 protected files match the recorded baseline after regeneration")
'@ | .\.venv\Scripts\python.exe -
$LASTEXITCODE
```

This is the reproduction script for the current version baseline. When a new official data version is released in the future, the new review records should be updated accordingly; do not merely modify the report hashes to let changes pass.

`scripts/export_sample.py` rewrites the single-document sample and sample question manifest and is not part of the official rebuild process above; it does not need to be run for routine acceptance.

## 10. How files and versions are handed to B and C

### 10.1 What B receives

- The complete `data/formal_corpus/`, including the in-package manifest, five HTML copies, and five adapted JSON files.
- The unified `corpus_version=794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795`.
- `data/corpus_manifest.json` and its source, structure, and review records, for traceability checks.

B's `data_dir` points to the official package directory. Acceptance of the four chunk groups, embeddings, index, and retrieval follows B's test guide; the 19 item results in this guide cannot be used as retrieval quality results.

### 10.2 What C receives

- `data/eval/gold.jsonl` and `data/eval/manifest.json`.
- The corresponding official corpus package and the two fixed versions.
- The question set and final review records, with a statement that human review is complete and no issues were found.

C also fixes `corpus_version` and `gold_version`. When answering, the system takes the question as input and retrieves sources on its own; the reference answers and evidence are used only for scoring comparison. A formal run of the four conditions will produce 120 per-question records; this still requires actual execution, and no answer accuracy can be derived from this guide.

## 11. FAQ

| Symptom | Resolution |
| --- | --- |
| `No module named bs4` / `soupsieve` | Install the HTML parsing dependencies from Section 3 using the same `.venv` interpreter |
| `No module named filelock` on normal import | Install the filelock already registered in `requirements-b.txt`; do not bypass package initialization |
| Cannot find `app`, `scripts`, or data files | Return to the project root containing these directories and check that all delivered files are present |
| `Missing A corpus manifest` | Verify that the formal package directory is passed to the loader and that `manifest.json` does exist inside the package |
| `VERSION_MISMATCH` / `SOURCE_MISMATCH` | Check the current package, the requested version, and the file bytes; do not hand-edit the manifest to make the error disappear |
| `official export requires exactly...` | The source list is missing official IDs or contains extra ones; locate them via the missing / extra entries in the error |
| txt / JSON hashes change unexpectedly | Check whether the editor or Git changed line endings, encoding, BOM, trailing newline, or JSON formatting |
| Evidence slices do not match | Check whether the same frozen full text was used, whether bytes / tokens were mistaken for characters, and whether duplicate content was matched incorrectly |
| `PermissionError` / `WinError 5` appear in tests | Check whether the traceback shows a failure creating, writing, or cleaning up in a temporary directory; retry in an ordinary local terminal with permissions, and do not record it as a pass |
| Seeing `result=failed` | Determine whether it comes from an exception test or an actual validation; rely on the corresponding process exit code and the final result of the whole test group |
| A team member lacks file A after cloning | Check whether the version containing the A artifacts was obtained; B source code or synthetic data alone is not enough to complete this guide |

Frozen files should remain UTF-8 with the established line endings. The repository already has `.gitattributes` rules protecting data bytes; do not batch-convert files just to eliminate hash errors.

## 12. How to report back after testing

Please send the following to A; when the issue involves chunking, the model, or system answers, also record the corresponding B / C run information:

```text
Operating system:
Project path:
Python version:
Code commit (if any) and uncommitted changes:
corpus_version：
gold_version：
corpus validation: exit code / final output
eval validation: exit code / final output
Automated tests: actual item count / OK or FAILED / exit code
Formal package load: document count / main article count
Sample package load: document count / main article count
Regeneration: run or not / byte-identical or not
Source review: reviewer / date / document and question number / findings
Error location: file / document_id / article_id or case_id / [start, end)
Full error text or log location:
```

Verified on this machine so far: five documents, 121 main articles; 30 questions, 24 answerable and 6 refusal; 19 automated tests passed; formal and sample packages load normally; 44 protected files have unchanged hashes after rebuild. See [A final validation ](./artifacts/a_review/a_final_validation.md) for the program check record. The A lead confirmed on 2026-11-19 that manual review and browser visual inspection passed with no issues found; B's formal database build and retrieval and C's question-answering evaluation each record their own results.
