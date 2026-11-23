# DERag

GitHub delivery is complete (separate answer-eval branch, not merged into main). [Draft PR #2](https://github.com/wengluo2021/DE/pull/2) · [all offline attachments](https://github.com/wengluo2021/DE/releases/tag/c-delivery-20261120).

GitHub delivery reading entry point: [Part C delivery navigation and download instructions](delivery/c-20261120/README.md).

## 2026-11-20 Current completion status

The formal five regulations, the frozen 30 questions, the four groups of 120 items, and all scoring fields are complete, with 0 technical errors. Scoring sources are 21 specific manual confirmations and 99 C-authorized AI-assisted ones; this is not described as entirely manual human review. The complete correct counts for F400/S400/F800/S800 are 6/24, 9/24, 10/24, and 13/24 respectively; for the method, denominators, and failure analysis, see the [Part C report](docs/C部分报告草稿.md) and [scoring method](docs/M6评分方式与授权记录.md). The original model outputs and unscored baselines are retained.

Windows passed 401 items and Linux passed 400 items, with 1 platform-specific skips; there is evidence for real CPU retrieval, school Q&A, restart, and the four formal index groups. The latest scored SQLite has been restored on a new Linux volume with networking disabled and no key, and 124 records plus the JSON/CSV before and after restart are byte-for-byte identical; the 68 code/config files inside the runtime image match the current source. Only existing results are read; the 120 questions are not regenerated for scoring.

Formal configuration `config/experiment.formal-a.json`; the default configuration is still the development sample. The latest export is in `artifacts/c/m6-final-scored/`. The current computer continues to use the existing working database and does not overwrite it from an old backup. For delivery and restoration, see [this round's delivery checklist](docs/本轮交付清单与恢复.md); all stage reports and dated logs are retained. The source is on the answer-eval branch; for GitHub commit and attachment status, see the delivery navigation and the latest M7_10 record; main will be merged after the team lead reviews it.

The final offline package is complete: [Part C task completion notes and reading path](docs/C任务完成说明与阅读路线.md). The final directory is the workspace deliveries/20261120-C-final-mixed-review; read README_先读我.md in it first.

## Viewing existing results on the current computer

The existing venv/model does not need to be reinstalled. In a normal PowerShell at the project root, run the following key-free method, then open `http://127.0.0.1:8765/evaluation` and select an existing run; this will not start a new experiment for restoration:

```powershell
$env:DERAG_CONFIG='config/experiment.formal-a.json'
$env:DERAG_ENV_FILE='NUL'
$env:LLM_API_KEY=''
& '.venv/Scripts/python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Newly generated Q&A requires a private key configured per the local API integration documentation; the key is not in the delivery package. Viewing/scoring/exporting existing results does not require model calls. If Codex's default restricted execution environment gets stuck on Python's local socketpair, use an execution context that already permits local communication; see [startup troubleshooting](docs/M6评分服务启动排查与正常读取验证.md).

<details>
<summary>Earlier C development stage records (current status is governed by the above)</summary>

## C stage development entry point

C's M0–M4 are in place: contract configuration, citation Q&A, server-side saving/tasks, four-group evaluation/scoring/export, and real API integration on four pages. M5 has integrated B's production retrieval entry point, unified dependencies, A's frozen data validation, configuration generation, and preflight; for current acceptance status, see [stage handover](docs/handoffs); for dated operations, see docs/worklogs. 2026-11-20 has been merged into A's formal 5 regulations/121 main articles and 24+6 questions; the new configuration is config/experiment.formal-a.json; A's enriched fields and attachment evidence have been adapted, and the full 401-item check passes. For formal index building/Q&A progress, see the latest handover; synthetic integration testing does not represent a course grade. Continue per [three-party integration and formal material onboarding](docs/三方对接与正式资料接入.md).

Use Python 3.13.11 and the project `.venv`. For a full run, install `requirements.txt` (103 pinned runtime packages); for development/all automated checks, install `requirements-dev.txt`. The original `requirements-b*.txt` and `requirements-c*.txt` are still retained for independent module development; the C lightweight entry point does not include real Chroma/embedding. Existing environments and models do not need to be rebuilt or re-downloaded.

On Linux, additionally install the pinned platform supplements in `requirements-linux.txt`; the CPU build uses the same version of `torch2.15.0+cpu`. For the new container, source/frozen data delivery package, and SHA verification steps, see [Docker and delivery package reproduction](docs/Docker与交付包复现.md). Whether it has actually been built and verified so far is governed by the latest M7 stage handover and evidence; the image re-verification for the latest A adaptation and the 120-item formal scoring are still pending in later stages, and final delivery cannot be called complete just because the container starts.

`config/experiment.json` is currently explicitly a development sample, corpus fixture-en-v2, with gold_version empty; formal runs require explicitly selecting config/experiment.formal-a.json. `DERAG_CONFIG` selects the experiment JSON, `DERAG_ENV_FILE` selects the local private env, `DERAG_DATA_DIR` and `DERAG_MODEL_DIR` select paths, and `LLM_TRANSPORT` explicitly selects curl/httpx. Paths are resolved from the project root, and the configuration does not pollute the global environment; real keys are not in the repository. `scripts.prepare_config` generates a new formal configuration only after all A inputs are validated; `scripts.validate_data --config config/experiment.formal-a.json` is a read-only C integration check, and A's `--scope corpus/eval` is retained; `scripts.preflight` does not download, build an index, or send model requests.

Offline Q&A core check: `.venv/Scripts/python.exe -m scripts.ask --fixtures --mock-llm --question "What does Article 2 state?"`. M1 also has real generation and refusal records; these use fixed synthetic evidence and are not official regulations or a formal retrieval evaluation. Running the C check can specify `tests/test_contracts.py tests/test_config.py tests/test_answer.py tests/test_llm_client.py tests/test_ask_cli.py`, without first installing B's model.

M2 startup remains `python -m uvicorn app.main:app --host 127.0.0.1 --port 8765`. Only one worker is used, with no automatic reload; the database is in data/sqlite. The health check distinguishes liveness from data/index/model readiness: when formal materials are missing, the API explicitly returns 409; the page opening does not mean the knowledge base is complete. By default it reads the project .env, and DERAG_ENV_FILE can be used to explicitly select a local environment file; it does not automatically look for keys from other courses. The new M2 check is `tests/test_persistence.py tests/test_tasks.py tests/test_qa_api.py`.

For M3 usage, see [evaluation usage instructions](docs/评估使用说明.md). After generating and enabling the formal configuration, materials, and index, run `python -m scripts.run_eval --config config/experiment.formal-a.json --base-url http://127.0.0.1:8765` in another terminal; it must use the same formal configuration as the server, and by default it exports to a new data/runs/client-random directory. `--run-id` reads an existing experiment and does not regenerate it. The M3 check is `tests/test_evaluation.py tests/test_evaluation_api.py tests/test_eval_cli.py`; the combined M0–M3 227 items pass, and the actual synthetic HTTP flow 120 items pass; neither represents a formal grade.

Start from the current source (an existing .venv does not need to be rebuilt):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

The pages are /, /documents, /compare, and /evaluation respectively; sessions, citations, experiments, and scoring are governed by the backend SQLite. Without formal materials, it shows not ready and disables generation, without falling back to a demo. On Windows, a native index directory exceeding 200 characters reports INDEX_PATH_TOO_LONG; choose a short data directory, and keep the temporary directories for the full test suite short as well. The new Docker has completed the Linux engineering check: 368 passed/1 Windows-specific skip, normal HTTP and 12 real CPU retrievals passed; that old image does not include the new A adaptation from 11 month 20 day, and the full M7 acceptance of the current source is still pending in later stages; see [latest M7 handover](docs/handoffs/M7_02_Linux容器验收与续做.md).

For page operations and evidence, see [M4 handover](docs/handoffs/M4_页面接入与真实问答.md). The Windows school API acceptance explicitly uses generation.transport=curl; the default configuration remains httpx, and curl results cannot be equated with HTTPX/Linux verification. For formal deployment, first select the applicable transport and configure the local env and frozen data; changing parameters changes the experiment fingerprint, and old runs are retained.

</details>

---

The "How to run / currently operable content" below retains the original preview version history; its description of requirements.txt reflects the state at that time, and the unified dependency notes at the top now govern. DE.tar is still the old preview image; for the new Docker engineering verification, see the M7 handover separately; the formal image archive has not been exported. The official data has been delivered and adapted; for the formal 30×4 experiment, see the latest M5/M6 handover separately.

<details>
<summary>Old preview run and image notes (not applicable to the current C backend installation)</summary>

## How to run

The project requires Python 3.13 (`.python-version` specifies 3.13.11). Use only the project's own `.venv`, and do not depend on the Python installation path on the developer's computer. `requirements.txt` pins all direct and indirect Python dependencies of the current frontend preview service.

Windows PowerShell (install Python 3.13 first; `py -3.13` should be able to find the interpreter):

```powershell
py -3.13 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

macOS / Linux：

```bash
python3.13 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

You can also use Docker, without installing Python on the host. Install Docker in advance, and run in the project directory:

```bash
docker build -t de .
docker run -d --name DE -p 127.0.0.1:8766:8000 de
```

Docker image names must be lowercase, so the image tag is `de:latest` and the container name is `DE`. Open http://127.0.0.1:8766. If the port is in use, change both the startup command and the access address. The first dependency installation or image build requires network access; the original preview image does not call external models. The current C backend real Q&A requires an API key configured, with the key kept only in the local env; the old image does not include these new features.

To run offline on another computer with Docker Desktop installed, transfer `DE.tar` from the project directory, then run:

```powershell
docker load -i DE.tar
docker run -d --name DE -p 127.0.0.1:8766:8000 de:latest
```

`DE.tar` is the complete image of the current frontend preview version and does not include the real RAG backend to be added later. After code updates, the image must be rebuilt and re-exported.
After the container is created, you can click Start/Stop for `DE` on the Containers page of Docker Desktop; the command-line equivalents are `docker start DE` and `docker stop DE`.

When subsequently integrating a vector store, embeddings, and model APIs, the dependency files, containers, and reproduction instructions must be updated in sync, and installation must be re-verified in a clean environment.

## Currently Available Actions

- Switch between the four views, create and switch local sessions, and view demo answers with sources.
- Import local `.md`/`.txt` files, view document details, and preview chunking results for fixed windows and article-structure-aware chunking.
- On the Chunk comparison page, select a document, method, and chunk size to compare chunk counts, lengths, and boundaries.
- View and export evaluation reports explicitly marked as demo data; real experiment runs must wait for backend integration.

Browser local storage is used only for the frontend preview and is not the final data storage for the course project. For the requirements on actual data collection, two or more independent vector indexes, and human evaluation, see [项目设计.md](./项目设计.md).


</details>

## Module B Independent Retrieval (Implemented)

After team members get the code from GitHub, please first read [B测试.md](./B测试.md): includes dependency installation, automated tests, model preparation, browser acceptance, and FAQ.

For detailed interfaces, directories, and integration conventions, see [B开发文档.md](./B开发文档.md), Section 12.
Python 3.13.11 / Windows CPU has been verified for installation, testing, and real model runs in an empty virtual environment.
B can be installed independently for independent development with `requirements-b.txt`; the current unified `requirements.txt` already includes B, so the full environment does not need to install it again. `DE.tar` is still the frontend preview image.

```powershell
# In the DERag project root; if the environment has not been created yet, first run py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-b.txt -r requirements-b-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py -q
$env:DERAG_B_DEBUG_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

Open <http://127.0.0.1:8767/b-debug>, click "Build four test indexes", then preview chunking, retrieval, and side-by-side comparison.
The default mock uses fixed test vectors and real Chroma and does not represent semantic retrieval performance. The first download of the formal semantic model is about 2.3 GB:

```powershell
.\.venv\Scripts\python.exe -m scripts.fetch_embedding --config config/retrieval.example.json
.\.venv\Scripts\python.exe -m scripts.smoke_embedding --config config/retrieval.example.json
# Stop the original verification service, switch modes, then start
$env:DERAG_B_DEBUG_MODE = 'real'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

The downloaded weights are in `models/embedding/`, and the model file hashes are in `derag-model-manifest.json`; weights and indexes are not uploaded to regular Git.
Dependency installation and the first model download require network access; after model preparation is complete, encoding and retrieval use only files within the project.
Test indexes are stored separately in `data/b-fixtures/mock/` and `data/b-fixtures/real/` and are not mixed with A's formal data.
`artifacts/b/` stores verification records for real models, automated tests, and web operations.


## English Test Corpus (2026-11-18)

The default questions, three suggested questions, indexed body text, document titles, and article labels on the B verification page have been switched to English. The active version is `fixture-en-v2`, and the chunking rule is `structure-offset-v2`; English Chapter/Section and sentence-ending punctuation are supported, and Chinese regression tests are retained. The four groups are still split by Python character count 400/800; the limit must not be understood as English word count.

Current verification: 78 automated tests passed; the project environment and the independent `.venv-b-verify` environment each passed 12 real-model retrievals, as well as over-limit protection, HTTP API, and source-slice verification. The four group chunk counts are F400=34, S400=47, F800=18, S800=31.

You can enter:

- `How can an individual request deletion of personal information?`
- `Can a reader renew a library book when the loan period expires?`
- `What should a bus driver do after noticing an abnormal road condition?`

This English body text is still a synthetic test rule and must not be regarded as official regulations or a formal 30 question evaluation. For the complete examples and test explanations, see [English corpus notes](tests/fixtures/b/README.md). The old Chinese results are retained in `artifacts/b/archive/zh-v1/`; after updating, restart the original B service and refresh the browser. Use the `real` mode startup command above to view real semantic retrieval.
