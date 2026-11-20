# B Module Testing Guide (for team members)

This guide is for independently testing B's chunking, vector index, retrieval API, and browser verification page after obtaining the project from GitHub. The main commands apply to **Windows PowerShell + Python 3.13.11 + CPU**, which is the environment actually verified so far.

**Suggested order: get the code → install dependencies → automated tests → mock page → prepare model → real model tests → real page.**

You do not need to copy the developer's virtual environment, the developer's computer's Python path, or an API Key. Team members set up the environment on their own computers, installing the same software versions from the dependency lock file; the model is prepared into the project directory by a script.

## 1. What this guide can test

| Test content | Specific checks |
| --- | --- |
| Two chunking methods | Fixed window, article-structure-aware; complete character coverage, no over-length, accurate positions |
| Four conditions | F400, S400, F800, S800; same body text, same model and retrieval settings |
| Vector ingestion | Real Chroma persistence, repeated index building, failure retry, version and file integrity |
| Single-group retrieval | English question encoding, top-5 hits, document and article information |
| Same-question comparison | The same question retrieved separately in two group indexes, results shown side by side |
| Source tracing | Returned chunks match the `[start,end)` slice of the frozen body text |
| Model protection | Explicit error when the model is missing; reject inference when input tokens exceed the limit |
| HTTP interface | Request fields, error format, index-building tasks, document and retrieval endpoints |

What is currently ingested is the **English synthetic test rules**, version `fixture-en-v2`, not official regulations. They are used to verify module B; A's official documents and 30 standard questions, C's answer generation, and citation support evaluation have not yet been completed here.

The page returning evidence does not mean an LLM has been called to generate a legal answer. The current `DE.tar` and the original Dockerfile correspond to the frontend preview; to test B, use the Python entry point as described in this guide.

## 2. Get the code and confirm your directory

First install Git and Python 3.13; **Python 3.13.11** is recommended to match the verified environment. No CUDA installation or GPU is needed.

To get the repository for the first time, run this in a parent folder of your choice:

```powershell
git -c core.autocrlf=false clone https://github.com/wengluo2021/DE.git DE
cd DE
git config core.autocrlf false
git rev-parse --short HEAD
```

`DE` is the folder name after cloning; during local development it was called `DERag`, and the name does not affect operation. **All subsequent commands must be run in the project root directory containing `app`, `tests`, `config`, and `requirements-b.txt`.** Do not enter `app` before running them.

Disabling automatic line-ending conversion for this repository is to preserve the LF line endings and byte hashes of the frozen body text. Do not use an editor to batch-convert the line endings of the test corpus, and do not modify only the body text while keeping the old coordinates and hashes.

If you already have the repository, first handle or save your own changes, then fetch the branch update agreed by the team:

```powershell
git status
git pull --ff-only
git rev-parse --short HEAD
```

When reporting test feedback, record the commit of the last output so everyone can confirm they are testing the same code. For the first reproduction, if the old workspace has had its line endings converted, prefer testing in a directory freshly cloned as described above.

The root directory should contain at least:

```text
DE/
├─ app/
│  ├─ api/
│  └─ retrieval/
├─ config/retrieval.example.json
├─ scripts/
│  ├─ build_indexes.py
│  ├─ fetch_embedding.py
│  └─ smoke_embedding.py
├─ tests/
│  ├─ fixtures/b/
│  ├─ support/b_app.py
│  ├─ support/static/b_debug.html
│  ├─ test_chunking.py
│  ├─ test_retrieval.py
│  └─ test_retrieval_api.py
├─ requirements-b.txt
├─ requirements-b-dev.txt
├─ pytest.ini
└─ B测试.md
```

If these files are missing, first confirm that the maintainer has committed module B and that you have pulled the correct version; do not fill the gap with same-named files from other projects.

## 3. Set up your own environment and install dependencies

Run in PowerShell:

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements-b.txt -r requirements-b-dev.txt
.\.venv\Scripts\python.exe -m pip check
```

If `.venv` already exists and is the correct version, you can skip the environment creation line. `pip check` should normally output:

```text
No broken requirements found.
```

Notes:

- `requirements-b.txt` contains B's runtime dependencies, including embedding, Chroma, FastAPI, etc.
- `requirements-b-dev.txt` contains test dependencies such as pytest and must be installed together with the runtime dependencies.
- Installing only the original `requirements.txt` is not enough to test B; it mainly serves frontend preview.
- The first installation requires internet access and includes large packages such as PyTorch; please wait for the command to finish.
- This guide always explicitly invokes the Python in `.venv`, so no activation command is needed and it is not affected by PowerShell activation script restrictions.
- Even if the terminal prompt shows `(base)`, the commands above use the project's own `.venv`.

## 4. First run the automated tests: no model weights need to be downloaded

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py -q --tb=short --basetemp=.pytest_cache/b-member-tests --junitxml=artifacts/b/local-tests.xml
```

The expected result for the version this guide corresponds to is:

```text
78 passed in ...s
```

Runtime depends on the computer. **The pass criterion is that all tests pass and the process exits normally**; the count may change as the team adds tests in the future, and test cases should not be deleted just to make the count 78.

This step does not read real model weights; most encoding uses test vectors, but it does actually execute chunking, temporary Chroma ingestion, API calls, and exception checks. It is not "all 78 regulation questions answered correctly".

The test report is in `artifacts/b/local-tests.xml`. `--basetemp` specifies the temporary directory for tests, which is managed by pytest; do not put business data in it. If the old temporary directory was created by another account and cannot be cleaned up, use a new directory, for example `.pytest_cache/b-member-tests-2`.

## 5. First look at the mock page: check the flow and chunking

Run:

```powershell
$env:DERAG_B_DEBUG_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

After `Uvicorn running on http://127.0.0.1:8767` appears in the terminal, keep it running and open in a browser:

- Verification page: [http://127.0.0.1:8767/b-debug](http://127.0.0.1:8767/b-debug)
- API docs: [http://127.0.0.1:8767/docs](http://127.0.0.1:8767/docs)

The page should show **MOCK** and `fixture-en-v2`. Click "Build four test index groups" and wait for the task status to become `completed`.

The mock uses test vectors and is suitable for first confirming that the program, buttons, indexes, and APIs work; **mock rankings are not used to judge whether semantic retrieval is correct**. To judge "whether the question finds the right document", continue with the real model tests below.

You can also skip the page and run the mock index-building command separately; for the first test, either one is fine:

```powershell
.\.venv\Scripts\python.exe -m scripts.build_indexes --config config/retrieval.example.json --fixtures --mock
```

This command should output JSON with `state` as `completed` and containing four condition groups.

## 6. Prepare the real model, then run retrieval tests

### 6.1 Prepare fixed-version weights

If the mock service is running, first stop it in its terminal with **Ctrl+C**, then run:

```powershell
.\.venv\Scripts\python.exe -m scripts.fetch_embedding --config config/retrieval.example.json
```

The current unified model is:

| Configuration | Value |
| --- | --- |
| Model | `BAAI/bge-m3` |
| Fixed revision | `5617a9f61b028005a4858fdac845db406aefb181` |
| Output dimension | 1024 |
| Inference device | CPU |
| Model directory | `models/embedding/` |
| File checksum manifest | `models/embedding/derag-model-manifest.json` |

The first model file download is about 2.3 GB and requires access to Hugging Face. **Team members use the same set of weights; each person does not switch to a different model.** The script downloads the files into the current project and records and verifies file hashes.

If a developer has already given you the complete `models/embedding/` folder by other means, you can copy it to the same location; be sure to include the checksum manifest and all subdirectories. If the files are complete and the version matches, you can skip the download and run the real tests directly. Do not copy only a single weight file or a personal virtual environment.

Ordinary GitHub code repositories do not contain these weights, so a freshly cloned project cannot immediately perform real retrieval. Once the model is prepared, the current module B encoding and retrieval do not require the network or an external model API.

### 6.2 Run the real model tests

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke_embedding --config config/retrieval.example.json --output artifacts/b/local-real-smoke.json
```

The script automatically builds or reuses the four real index groups for the current version; there is no need to start uvicorn in advance. The first import, weight loading, and index building require waiting, and the time depends on the CPU and disk.

Expected final output:

```text
PASS: 12 real retrieval checks, tokenizer overflow and HTTP APIs; record: ...
```

What it actually checks:

1. The real model loads successfully and outputs a 1024-dimensional vector.
2. Three English questions are retrieved under four condition sets, 12 retrievals in total; each time the top-ranked document has the correct topic.
3. Every returned chunk exactly matches the frozen text's `[start,end)`, and the article ID and source URL correspond correctly.
4. Deliberately oversized input is blocked and returns `MODEL_INPUT_TOO_LONG`.
5. The real service's status, search, and comparison HTTP endpoints work correctly.

The test may show:

```text
Token indices sequence length is longer ... (9002 > 8192)
```

This is the script deliberately using `"law " * 9000` to test the over-limit protection. **Only in this deliberate over-limit test, and only when PASS appears at the end, is this an expected result.** If a normal question or index build unexpectedly exceeds the limit and FAILED is shown at the end, it needs investigation.

This run is recorded in `artifacts/b/local-real-smoke.json`; the repository's `real-smoke.json` and `clean-real-smoke.json` are the developer's existing verification records. Seeing someone else's report does not mean your own computer has passed the test; rely on the results of the command you just ran.

## 7. Item-by-item acceptance on the real page

Start:

```powershell
$env:DERAG_B_DEBUG_MODE = 'real'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

Reopen or refresh [B verification page ](http://127.0.0.1:8767/b-debug). The page must show **REAL**. Changing environment variables does not affect an already-started old process; when switching from mock to real, be sure to stop the old service before running the start command.

### 7.1 Check run status and index

The corpus should be `fixture-en-v2`. If the real test has already built the index successfully, the page should directly show all four index sets ready; if no index has been built yet, click "Build four test index sets" and wait `completed`.

The expected total chunk counts for the same current synthetic corpus are as follows, **these are totals across all four documents, not the chunk count of the currently selected document**:

| Condition | Method | Max characters per chunk | Total chunks | Actual longest chunk |
| --- | --- | ---: | ---: | ---: |
| F400 | Fixed window | 400 | 34 | 400 |
| S400 | Structure-aware | 400 | 47 | 394 |
| F800 | Fixed window | 800 | 18 | 800 |
| S800 | Structure-aware | 800 | 31 | 799 |

Counting here is by Python characters, including spaces, newlines, and punctuation; 400/800 is not an English word count, nor a token count. There are still only two algorithms; the four sets are "two methods × two lengths".

Clicking build again for the same version should reuse the already-validated index, and chunk counts should not double. The four sets share the same experiment version, but mock and real use different models, so it is normal for their index versions to differ.

### 7.2 How to test "01 / Documents and chunks"

Select `Synthetic Personal Information Rules (not official legislation)`, and switch between F400, S400, F800, and S800.

Correct behavior:

- The left side is the frozen English source text, containing `Chapter` and `Article`; switching chunking conditions does not rewrite the left-side text.
- The right-side chunks come from the server; when the condition changes, chunk counts and boundaries may change.
- The previous chunk's `end` equals the next chunk's `start`, the first chunk starts at 0, and the last covers through the end of the full text.
- Clicking "View source chunk" should show a chunk, position, and full text that correspond to each other.
- The structure-aware method can produce chunks below the limit; overlong articles continue to be split by sentence/paragraph, rather than always being "one article, one chunk".

The short document `Synthetic API Contract Fixture (not official legislation)` has only 25 characters, so it is correct that all four sets produce only one chunk. It is suitable for checking fields, not for showing chunking differences on long documents.

### 7.3 How to test "02 / Single-set retrieval"

Enter the following questions in order, select a condition, and click "Retrieve top-5":

| English question | Expected top result in real mode `document_id` |
| --- | --- |
| `How can an individual request deletion of personal information?` | `privacy` |
| `Can a reader renew a library book when the loan period expires?` | `library` |
| `What should a bus driver do after noticing an abnormal road condition?` | `travel` |

You can switch through the four conditions one by one to check; the automated real test already covers these 12 combinations. The text, document titles, and Article labels in the results should be in English.

The correct result is not "the score must equal some decimal", but that the topic, source, and source-text slice correspond correctly. A higher `score` means more relevant under that metric; it is not a probability, nor a legal accuracy rate. Different machines may show differences in the order of tied chunks, so you should not require every ranking and timing in a screenshot to match exactly.

### 7.4 How to test "03 / Same-question comparison"

Enter the same English question, first compare F400 on the left with S400 on the right, then compare F800 with S800, and click "Compare using the question above".

Correct behavior:

- Each side returns the top-5 evidence for its own condition.
- Both sides share the same question, corpus version, and index version; the left-side results are not copied to the right side.
- The chunk boundaries and total returned characters on the two sides may differ, and may also be partly the same; the structure-aware method is not required to score higher.
- After the question is modified, old results are cleared, to avoid mistaking the previous question's answer for the new question's result.

This page is for observing differences in retrieval evidence. You cannot declare which method is more accurate on real regulations based on just three synthetic questions.

### 7.5 How to verify source citations

For any hit, click "View source chunk" and check the document ID, article ID, `chunk_id`, `start/end`, source URL, and full text.

For example, `[100,180)` means starting from the 100-th Python character and ending before the 180-th, with a length of 80. The backend must satisfy:

```python
hit["text"] == document["text"][hit["start"]:hit["end"]]
```

Do not treat this index directly as a byte position; browser JavaScript counts some Unicode characters differently from Python, so the backend validation is authoritative. The current English samples are ASCII, but automated regression tests for Chinese and emoji are retained.

"Can locate the original text" is B's acceptance goal; "whether this evidence is sufficient to support every claim in the large model's answer" is the subsequent evaluation goal for C. `example.org` is a placeholder link for the sample source; opening a real regulation webpage is not required.

## 8. Check the API without the page

Keep the real service running and open another PowerShell window. The requests below use the service that is already started:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8767/b-debug/status' | ConvertTo-Json -Depth 20

$body = @{
    question = 'Can a reader renew a library book when the loan period expires?'
    corpus_version = 'fixture-en-v2'
    condition = 's400'
    top_k = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri 'http://127.0.0.1:8767/api/search' -Method Post -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 20
```

The status should include `mode: real`, `ready: true`, and the current corpus version; the search response includes `corpus_version`, `index_version`, `condition`, `hits`, `timing_ms`, and the top document should be `library`.

You can also expand the endpoints in `/docs` and click `Try it out`. Example same-question comparison request:

```json
{
  "question": "Can a reader renew a library book when the loan period expires?",
  "corpus_version": "fixture-en-v2",
  "left_condition": "f400",
  "right_condition": "s400"
}
```

Send to `POST /api/compare`. Note that compare does not accept `top_k`; both sides are fixed at top-5.

## 9. Where files are saved and which ones need to be obtained from GitHub

| Path | Purpose | How to obtain |
| --- | --- | --- |
| `app/retrieval/`, `app/api/` | B implementation | GitHub source |
| `scripts/`, `tests/`, `config/` | Model/index-building scripts, tests, configuration, and frozen corpus | GitHub source |
| `requirements-b*.txt`, `pytest.ini` | Dependency lock and test configuration | GitHub source |
| `.venv/` | Interpreter environment on the current computer | Created by each member; not uploaded |
| `models/embedding/` | Fixed-version model and verification manifest | Download via script or copy the complete folder; not uploaded to regular Git |
| `data/b-fixtures/mock/` | mock four index sets | Generated automatically on the member's computer |
| `data/b-fixtures/real/` | real four index sets | Generated automatically on the member's computer |
| `artifacts/b/local-tests.xml` | This run's automated test report from the member | Generated by local testing |
| `artifacts/b/local-real-smoke.json` | This run's real-model report from the member | Generated by local testing |
| `.pytest_cache/` | Temporary test directory | Generated automatically on the local machine |

There is no need to copy the Chroma index from the developer's computer. **Rebuilding the index in your own directory from the same source code, corpus, configuration, and model is what tests reproduction.** Personal reports can be sent to other members for comparison and do not need to be repeatedly committed with the business code. Existing reports and historical Chinese reports are in `artifacts/b/`; do not treat historical results as results for the current English version.

## 10. FAQ

| Problem | How to handle |
| --- | --- |
| `py` not found or no Python 3.13 | Install Python 3.13; if using an installation path, the path is determined by your own computer—do not enter the developer's disk path |
| `No module named chromadb`, `sentence_transformers`, or `pytest` | Reinstall both B dependencies using the Python in `.venv`; check whether only the original `requirements.txt` is installed |
| `No module named scripts` or `tests.support.b_app` | Switch back to the project root directory and run; confirm that `scripts/` and `tests/` have been pulled from the repository |
| real mode reports the model is missing | First run `scripts.fetch_embedding`, or copy the complete model directory and manifest |
| Model download fails | Check whether the local network can access Hugging Face; alternatively, a member who can download it can provide the complete directory for the same fixed revision |
| Model or corpus verification fails | Check the version, file integrity, LF line endings, and whether files were manually edited; restore the complete files of the same version and do not bypass hash verification |
| `INDEX_NOT_READY` or the button is unavailable | First build the four index sets and wait for `completed`; if the task fails, check the page error and the service terminal logs |
| `VERSION_MISMATCH` | Use `fixture-en-v2`, update the code and configuration, and restart the service; the old Chinese `fixture-v1` cannot be used for the current active corpus |
| The page still shows Chinese text, old questions, or an old version | Confirm you are in `/b-debug`, stop the old service, restart in the updated directory, and then force-refresh the browser |
| The page shows MOCK, but the environment variable has already been changed | Environment variables only affect new processes; press Ctrl+C to stop the old process, then set real and start again |
| Port 8767 is in use | Use the original service, or stop the old service you started; you can also change to `--port 8768` and update the browser and API addresses accordingly |
| `127.0.0.1` cannot be opened on another computer | Each member runs it on their own computer and accesses their own localhost; the commands here do not expose a LAN service |
| No permission to clean up the test temporary directory | Change `--basetemp` to a new dedicated directory; do not use administrator commands to delete other people's working directories |
| All automated tests pass, but the mock top result has the wrong topic | mock is not used for semantic ranking judgments; complete the real test before checking the three English questions |
| The page has no complete large-model answer | This is normal; B currently only provides retrieval evidence, and the complete answer will be integrated later by C |

## 11. How macOS / Linux members run it

The source code does not contain personal Windows paths. macOS / Linux can create the environment on the same principle, with commands in the following form; **the current B dependency lock and execution flow have only been tested on Windows CPU, and the following are ways to run on other systems that have not yet been accepted across platforms.**

First clone the repository as described in section 2 and enter the project root directory, install Python 3.13, and then run:

```bash
python3.13 -m venv .venv
./.venv/bin/python -m pip install -r requirements-b.txt -r requirements-b-dev.txt
./.venv/bin/python -m pip check
./.venv/bin/python -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py -q --tb=short --basetemp=.pytest_cache/b-member-tests --junitxml=artifacts/b/local-tests.xml
./.venv/bin/python -m scripts.fetch_embedding --config config/retrieval.example.json
./.venv/bin/python -m scripts.smoke_embedding --config config/retrieval.example.json --output artifacts/b/local-real-smoke.json
DERAG_B_DEBUG_MODE=real ./.venv/bin/python -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

Likewise, open `/b-debug`. When not using Docker, Python and dependencies must be installed locally; this is not a double-click, installation-free run. If a locked package has no installation package for the corresponding system or chip architecture, record the package name, Python version, and full error, and let the team uniformly verify a compatible solution; do not each arbitrarily change versions and then mix experimental results.

## 12. How to report back after testing

Members can provide feedback in the following format to help locate problems:

```text
Git commit：
Operating system / CPU architecture:
Python version:
pip check: pass / fail
Automated tests: e.g. 78 passed
Real test: PASS / FAILED / model not yet prepared
Page mode: REAL / MOCK
Corpus version: fixture-en-v2
Total chunks for the four groups: F400=34, S400=47, F800=18, S800=31
Top result for the three English questions: privacy / library / travel
Source snippet verification: passed / failed
If failed: the full command executed, the full error, and the service terminal logs
Attachments: local-tests.xml, local-real-smoke.json, or page screenshots
```

Do not just send "it won't open" or the last line of an error; distinguish between the dependency installation, model download, index building, retrieval, and page stages. Windows and other systems are not required to have the same timings, and tied snippets within the same topic are not required to be in identical order.

## 13. Maintainer pre-commit checklist

When committing the documentation, also commit the current B implementation, dependencies, and English test corpus. **Committing only this file means team members cannot run the B module that has not yet been uploaded.** In particular, confirm that the following new files are included in this commit rather than still sitting untracked on the local machine:

- `app/api/`、`app/retrieval/`。
- `scripts/`、`config/retrieval.example.json`。
- `tests/`, containing the English source text `.txt`, JSON metadata, question files, legacy Chinese regression samples, and the verification page.
- `requirements-b.txt`、`requirements-b-dev.txt`、`pytest.ini`。
- `.gitignore`, `README.md`, `B开发文档.md`, `B测试.md`; keep `.python-version` at the correct version.

Before pushing, you can do a read-only check:

```powershell
git status --short
git diff --cached --stat
git ls-files app/api app/retrieval scripts config tests requirements-b.txt requirements-b-dev.txt pytest.ini B测试.md
```

The first command shows what is still uncommitted; the second checks what has been staged; the third confirms whether the files are already tracked by Git. If the output is empty or a directory is missing, check whether files were left out. Do not upload `.venv/`, model weights, indexes, test temporary directories, or personal IDE configurations.

After pushing, it is best to have a team member clone into a new directory and follow this guide from the beginning. This checks for missing files rather than relying on the environment and data that already exist on the maintainer's computer.
