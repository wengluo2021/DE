# DERag: B Development Document (Standalone Retrieval Module Implemented)

## 1. What B must accomplish

B is responsible for the chain "cleaned documents → two chunking methods → embedding → four Chroma indexes → semantic retrieval and comparison API". Inputs and outputs follow [开发文档.md](./开发文档.md); this document details B's code directories, algorithms, functions, interfaces, tests, and delivery method.

B may first develop and complete testing independently using fixed test documents, without waiting for A's formal data or C's Q&A code. After all three finish, C will integrate B's implementation into the formal program; B is responsible for handling chunking, model, index, and retrieval issues that arise during integration.

A alone is responsible for verifying all official documents and the 30 standard questions; C is responsible for LLM answers, citation validation, formal evaluation, human scoring, and page integration. B does not write regulatory question sets or generate legal answers; B must provide retrieval evidence with accurate source locations for C to cite and evaluate.

**Current status: B's standalone module is implemented.** Chunking, four Chroma indexes, real embeddings, the retrieval API, model preparation scripts, and a standalone verification page are in place; 78 standalone automated tests pass. Records of real-model and clean virtual-environment verification are in Section 12 and `artifacts/b/`. The formal entry point `app.main:app` is still a frontend preview pending integration by C; this B module test must not be equated with the complete project or the formal 30-question evaluation.

## 2. B's code folders and file responsibilities

The project root is `DERag/`. The current local location is `E:/2027CityU/CS5481 Data Engineering/GroupProject/DERag/`; that absolute path is only for locating the project and must not be written into code or delivery configuration.

**B's core code folder is fixed as `DERag/app/retrieval/`.** HTTP routes go in `app/api/`, the command-line entry point goes in `scripts/`, and automated tests go in `tests/`. Do not create a separate `B项目/` or a second formal application, and do not put all business logic into `app/main.py`.

```text
DERag/
  开发文档.md                       # The three-person overall contract, already exists
  B开发文档.md                      # This document
  app/
    __init__.py
    main.py                         # C is responsible for formal assembly; B does not overwrite
    contracts.py                    # C is responsible for the unified boundary model; B develops independently without waiting for this file
    config.py                       # C is responsible for unified configuration loading
    retrieval/                      # B core code directory
      __init__.py                   # Exports entry points such as build_indexes and search
      types.py                      # B internal types and protocols; fields follow the master document
      chunking.py                   # Fixed window, structure-aware, interval coverage checks
      embedding.py                  # Local model loading, token length checks, batch encoding
      vector_store.py               # Chroma persistence adapter, write, read, query
      indexes.py                    # Four-group build, version, manifest and completion marker
      service.py                    # Document reading, retrieval and same-question comparison service
      errors.py                     # Module errors, for routes to convert into unified status codes
    api/
      __init__.py
      documents.py                  # Document summary, body and chunk preview routes
      indexes.py                    # Index build task routes, task manager injected via parameters
      search.py                     # search and compare routes
    static/                         # C is responsible for production page integration, B does not modify
  scripts/
    __init__.py
    fetch_embedding.py              # Download fixed revision, verify model files
    build_indexes.py                # Read configuration, invoke the four-group index build
  config/
    retrieval.example.json          # B's standalone configuration sample, C ultimately merges into experiment.json
  requirements-b.txt                # Module runtime dependencies verified by B, ultimately merged by C
  requirements-b-dev.txt            # B's test dependencies, pinned versions
  tests/
    fixtures/b/
      document.json                 # Synthetic document, conforms to A's Document fields
      long_documents.json           # Long articles, multi-section, Unicode test samples
      expected_hits.json            # Synthetic SearchHit samples for C
    support/
      b_app.py                      # FastAPI assembly entry point used only for B tests
      static/
        b_debug.html                # B standalone retrieval verification page, plain HTML/CSS/JS
    test_chunking.py
    test_retrieval.py
    test_retrieval_api.py
  data/
    processed/                      # A production documents, B read-only
    chunks/{index_version}/         # Four groups of JSONL exported by B
    chroma/{index_version}/          # Persistent index generated by B
    indexes/{index_version}.json    # Configuration, hashes, chunk statistics and index build results
  models/embedding/                 # Downloaded model files, configuration override supported
  artifacts/b/                     # B's test and real-model smoke records
```

The figure above is the responsibility structure; B's implementation has created the directories it is responsible for. The production regulation text, `gold.jsonl`, Q&A and evaluation modules are not created by B. `data/chroma/`, model weights and temporary artifacts are not committed as ordinary source code; sample configurations, test data and rebuild scripts must be committed.

### 2.1 What each file should do

| File | Input | Output and responsibilities |
| --- | --- | --- |
| `chunking.py` | Document and character limit | Chunk list; pure function, no network, no database calls. |
| `embedding.py` | Text list, model configuration | Vectors in the same order as input; load the model once, unified encoding rules. |
| `vector_store.py` | Vectors, chunk IDs, a small amount of scalar metadata | Chroma storage and retrieval; not responsible for chunking or constructing web page fields. |
| `indexes.py` | Document reading function, four-group conditions, embedding configuration | Four-group build, version manifest, verifiable Chunk JSONL. |
| `service.py` | Question, conditions, corpus version | SearchHit list or same-question results for both sides; fill in source fields from authoritative documents. |
| `app/api/*.py` | HTTP request, injected service | Validate parameters, call business functions, return JSON; do not reimplement retrieval algorithms. |
| `scripts/*.py` | Parameters or configuration file | Call the same business functions, print readable results and errors, return non-zero exit code on failure. |

For B standalone testing, `tests/support/b_app.py` is used to assemble the router, sample document reader and in-memory task manager, and provide the `/b-debug` page. Verification page code is placed in `tests/support/static/b_debug.html`, separate from C's `app/static/` production frontend. Ultimately C injects real dependencies in `app/main.py` and registers the same set of business routers, and the production page calls the same API.

## 3. Fixed experimental conditions

| Condition | Chunking method | Maximum characters |
| --- | --- | ---: |
| `f400` | Fixed window `fixed` | 400 |
| `s400` | Article structure-aware `structured` | 400 |
| `f800` | Fixed window `fixed` | 800 |
| `s800` | Article structure-aware `structured` | 800 |

The main comparisons are F400/S400 and F800/S800. All four groups use the same frozen body text, embedding model and revision, normalization, vector store engine and parameters, cosine distance and top-5 retrieval. All conditions are non-overlapping and do not cross documents; rerank, prompt prefix changes or model adjustments must not be added to make a particular condition hit more.

Character counts use Python `len(text)`, including article numbers, punctuation, and line breaks. After receiving A's body text, B does not perform `strip()`, line-break replacement, or secondary cleaning, to avoid invalidating the original text coordinates.

## 4. Unified input and output

The current active corpus is English `fixture-en-v2`, and the chunking rule is `structure-offset-v2`. The old Chinese short samples are stored separately as `legacy_zh_document.json` and are used only for Unicode/legacy ID regression; do not request the old version from the current service.

### 4.1 Input Document

B uses the `data/manifest.json` output by A and the processed Document. During independent development, use the following synthetic samples directly; do not present them as official regulations:

```json
{
  "schema_version":"1.0",
  "document_id":"fixture",
  "corpus_version":"fixture-en-v2",
  "title":"Synthetic API Contract Fixture (not official legislation)",
  "issuer":"Synthetic test data",
  "source_url":"https://example.org/fixture",
  "published_at":null,
  "effective_at":null,
  "raw_path":"tests/fixtures/b/raw.txt",
  "raw_sha256":"b65e8b1fa799c486a1340e674d420e133eab935dd801757d40991be24dee3b09",
  "text":"Article 1 A.\nArticle 2 B.",
  "articles":[
    {"article_id":"fixture-a001","label":"Article 1","chapter":null,"section":null,"start":0,"end":12},
    {"article_id":"fixture-a002","label":"Article 2","chapter":null,"section":null,"start":13,"end":25}
  ]
}
```

Body text is 25 characters; Article 2 is `[13,25)`, of which `B.` is `[23,25)`. The raw hash above corresponds only to the body text as UTF-8, LF, no BOM bytes.

Validate on formal read: corpus version matches, document ID is unique, hash is correct, article ranges fall within the body text, and articles within the same document are ordered and non-overlapping. If parsing is invalid, report an error; do not correct the document yourself and continue the experiment. Test samples use `fixture-en-v2`; the formal corpus uses the real version hash specified in the master document.

### 4.2 Output Chunk

```json
{
  "chunk_id":"ecc55790d61808b33e0ec4cb33471f7e520a6af4dd26c2ebdd083d2ed80a18ac",
  "corpus_version":"fixture-en-v2",
  "condition":"s400",
  "boundary_method":"structured",
  "target_chars":400,
  "document_id":"fixture",
  "article_ids":["fixture-a001","fixture-a002"],
  "start":0,
  "end":25,
  "text":"Article 1 A.\nArticle 2 B."
}
```

The raw string of `chunk_id` is:

```text
corpus_version|boundary_method|target_chars|document_id|start|end
```

Compute UTF-8 SHA-256 on this string and return the full lowercase hexadecimal. Example: `fixture-en-v2|structured|400|fixture|0|25` corresponds to the ID above. Do not use Python's built-in `hash()`, random UUIDs, or sequential numbering.

`article_ids` records, in original text order, the articles that actually intersect the chunk, determined as `max(chunk.start, article.start) < min(chunk.end, article.end)`. Chunks containing only headings or whitespace may have an empty array; do not fabricate article numbers.

### 4.3 Output SearchHit

```json
{
  "rank":1,
  "score":0.9,
  "chunk_id":"ecc55790d61808b33e0ec4cb33471f7e520a6af4dd26c2ebdd083d2ed80a18ac",
  "corpus_version":"fixture-en-v2",
  "condition":"s400",
  "document_id":"fixture",
  "article_ids":["fixture-a001","fixture-a002"],
  "start":0,
  "end":25,
  "text":"Article 1 A.\nArticle 2 B.",
  "title":"Synthetic API Contract Fixture (not official legislation)",
  "source_url":"https://example.org/fixture",
  "article_labels":["Article 1","Article 2"]
}
```

`rank` starts from 1. Chroma cosine distances are sorted in ascending order, uniformly `score=1-distance`; a larger score means more relevant, but it is not a probability. Sample scores are test values. Returned candidates with the same distance are sorted by `chunk_id`; tie boundaries for a query may be affected by the approximate index and must be recorded in the run notes.

C uses this object plus this round's `n` to construct citations; B does not generate answers or conversation citation numbers itself. `article_labels` is taken from A's article table, not guessed from chunk body text.

## 5. How the two chunking methods are implemented

### 5.1 Fixed window

1. Validate that the limit is a positive integer; empty body text returns an empty list and records the empty-document status.
2. Starting from `start=0`, take `end=min(start+max_chars, len(text))` each time.
3. Chunk text must directly use `text[start:end]`; compute the ID and covered articles, then save.
4. The next chunk starts from the previous chunk's `end`, with no overlap and no whitespace stripping. The last chunk may be smaller than the limit.

When testing the English sample with a 16 character limit, it must produce `[0,16)`, `[16,25)`, and concatenating them must reconstruct the original text. Formal experiments still use only 400/800.

### 5.2 Article-structure-aware

Prefer the article positions provided by A. Chapter detection is performed only on heading lines or in gaps between articles; do not mistake "in accordance with Article 10" in the body text for a new article boundary.

1. Build structural units on the original text; do not copy cleaned sentences. Units retain `start/end`, chapter/section identity, and article ID.
2. Chapter/section headings belong to the content that follows; ordinary whitespace between articles belongs to the preceding unit. End the previous unit before a new chapter/section; the previous article must not swallow the next chapter heading.
3. Within the same chapter and section, greedily merge in original text order: if adding the next complete unit does not exceed the limit, merge; if it exceeds the limit, output the current chunk first. When there is no chapter/section information, treat as one group.
4. When a single article itself exceeds the limit, prefer splitting at `。！？；` and explicit paragraph boundaries using original text coordinates; preserve punctuation and line breaks, and do not do `join()` to rebuild text.
5. If a single sentence exceeds the limit, hard-split it and record the number of `long_sentence_fallback`. If a heading plus the first article is too long, the heading may be a separate chunk, but it still must not exceed the limit or drop characters.
6. When there are no article annotations, build units by paragraph/sentence boundaries and then pack, record `no_article_fallback`, and do not silently switch to another body text.

To avoid inconsistent results across implementations, first write test assertions for "complete body coverage, chunk length limit, chapter/section boundaries", then write the packing loop. The English sample under a 16 character test limit should be `[0,13)`, `[13,25)`; under a 400 limit, the two articles can fit into one `[0,25)` chunk.

### 5.3 Assertions that both methods must satisfy

- Each chunk `0 <= start < end <= len(text)`, `end-start <= max_chars`, `chunk.text == text[start:end]`.
- Under the same conditions and the same document sorted by position, the first chunk starts at 0, each subsequent chunk starts at the previous chunk's `end`, and the last reaches the end of the body text.
- Concatenating all chunk texts must equal the original text; empty text is handled separately and no empty chunks are created.
- Given the same input, the chunk list, positions, and IDs are stable; after changing the corpus version, IDs change accordingly.
- The structural method preserves complete articles as much as possible, but does not assume retrieval is necessarily better than fixed windows. The actual advantage is verified by the final evaluation.

## 6. embedding model and reproducible environment

### 6.1 Model selection principles

This time `BAAI/bge-m3` was adopted and actually tested: it supports Chinese and English and can use dense vectors; its public specifications are 1024 dimensions and a longer input window, suitable for preventing 800-character text chunks from being truncated by short-window models. Its download and encoding cost on CPU is higher than small models; this time real installation, loading, four-group indexing, and retrieval validation have been completed on Windows / Python 3.13.11 / CPU; the model revision is fixed at `5617a9f61b028005a4858fdac845db406aefb181`, and the weights are about 2.27 GB.

Candidate models can be loaded via `sentence-transformers`, and Chroma uses a local persistent client. B must confirm that dependencies for Python 3.13/Linux CPU can be installed before filling in specific locked versions. The installed versions this time are locked in `requirements-b.txt` and `requirements-b-dev.txt`; the original `requirements.txt` remains a preview entry dependency. Linux CPU / Docker has not yet been tested; do not describe Windows validation as cross-platform validation.

The final model ID, immutable revision, model file hash, dimensions, maximum input tokens, normalization, query/document prefixes, and pooling strategy are all written into the configuration and index manifest. Only dense vectors are used; no additional model sparse retrieval or multi-vector capabilities are introduced.

### 6.2 Input truncation that cannot be ignored

400/800 is measured in Python characters, while the model input limit is measured in tokenizer tokens; the two are different. After downloading the model, tokenize all chunks with the actual prefix and check whether special tokens plus the body text exceed the model's effective limit.

**Silent truncation is prohibited.** When over the limit, directly report the document ID, chunk ID, token count, and model limit, and require fixing the unified model configuration before formal experiments; do not truncate only the latter half of one group, and do not quietly change that group's chunk length. The question itself must also be length-checked with a readable error. If the model is ultimately changed, rebuild all four groups and use the same new configuration.

### 6.3 Download, cache, and dependencies

- `scripts/fetch_embedding.py` explicitly downloads a fixed revision to the configured path and, when done, generates a file list and hashes; formal loading reads from this path first.
- Supports a `DERAG_MODEL_DIR` override directory; source code and containers use the same rule and do not rely on existing weights in `C:/Users/某人/.cache/`.
- Write independent module dependencies to `requirements-b.txt`, including tested direct and indirect runtime versions; write test dependencies to `requirements-b-dev.txt` and verify them together with runtime dependencies. C ultimately resolves the dependency conflicts among the three modules and merges them into the project lock file.
- The first model download usually requires network access. Offline reproduction must provide the weights or an accessible fixed model package with its checksum information, and comply with the model license; source code and an empty model directory alone cannot run embedding offline.
- Tests do not require a GPU. Encoding batch size can be configured to fit memory, but changing batch order must not scramble the correspondence between texts and vectors.

## 7. How the four index groups are built and queried

### 7.1 build_indexes build flow

1. Read the passed-in document loader function and validate A's data version and manifest. Inject a fixture loader function in independent tests.
2. Read the effective embedding/retrieval configuration, construct the index version material, and use the SHA-256 of canonical JSON to obtain `index_version`.
3. Generate a complete Chunk list for each of the four conditions, verify the coverage assertions, and save JSONL and statistics.
4. Encode the four groups of chunks using the same embedding instance; if texts are identical, the encoding cache may be reused within the same version and same model, but each retains its own condition and chunk ID.
5. Create four collections in `data/chroma/{index_version}/`: `kb_f400`, `kb_s400`, `kb_f800`, `kb_s800`, explicitly configuring the cosine metric.
6. Write vectors and minimal metadata with `chunk_id`; use the create/upsert/query API supported by that version of Chroma, and write tests to verify it. Do not assume a Python list can be used directly as collection metadata; authoritative content such as `article_ids` is kept in the Chunk JSONL.
7. After all four groups are written and counts are verified, mark the index manifest as `completed`. Record `failed` on mid-way failure; the service must not use a half-finished index for formal queries.

`index_version` covers at least `corpus_version`, chunking implementation version, condition list, model ID/revision/file hash, dimension, normalization, prefix, truncation policy, and effective vector store configuration. Canonical JSON is encoded with `ensure_ascii=False, sort_keys=True, separators=(',', ':')`. Cache absolute paths, creation time, and elapsed time tied to the runtime machine do not enter the version hash but are retained in diagnostic records.

When rebuilding the same version, a completed and correctly verified build can be reused directly; retrying a failed version must clean up this attempt's incomplete state or overwrite idempotently, and must not insert duplicates. New versions are written to a new directory, and old indexes are not silently overwritten. Add appropriate locks to query and index building to prevent the same index from being read while it is being written.

### 7.2 search retrieval flow

1. Validate that the question is non-empty, the condition is valid, and `top_k` is 1–5; check the request corpus against the active index version.
2. Encode the question with the fixed query prefix, using the same model, revision, and normalization rules as for documents.
3. Query the corresponding collection; when results are fewer than 5, return the actual count as-is without padding with sample chunks.
4. Fill in authoritative text, spans, titles, official sources, and article numbers from Chunk and Document, and check that chunks match the frozen source slices.
5. Convert to the SearchHit from Section 4.3 and record the actual query elapsed time. Index not ready and retrieval with no hits must be distinguished.

Only completed indexes can be activated. Retrieval must not call an LLM, use standard answers to filter results, or read `gold.jsonl` to help ranking. Formal hit@k and answer metrics for the 30 questions are computed by C; B only provides verifiable evidence and runtime statistics.

### 7.3 compare flow

For the same question, same `corpus_version`, and same `index_version`, query the conditions on both sides in sequence, each returning at most 5 chunks. If the left or right side errors, return an explicit error and do not pad with the other side's results. Return `context_chars=sum(len(hit.text))` and retrieval elapsed time for each side, to explain cases where chunk counts are equal but actual context lengths differ.

## 8. Public functions and API examples

### 8.1 Functions C calls on B

```python
build_indexes(corpus_version) -> IndexManifest
search(question, condition, corpus_version, top_k=5) -> list[SearchHit]
```

Inject `document_loader`, `embedder`, `vector_store_factory`, and configuration at service initialization. B's independent tests provide fake implementations; C's integration replaces them with A's loader and real components, without requiring C to modify retrieval internals.

Routes receive the service and task manager through a factory, e.g. `create_retrieval_routers(service, task_manager)`; the returned router is registered by C. Do not download models or build indexes directly at Python module import time.

### 8.2 HTTP endpoints owned by B

| Path | Behavior |
| --- | --- |
| `GET /api/documents?corpus_version=...` | Returns `{"items":[...]}`; summary fields are fixed as `document_id`, `title`, `source_url`, `corpus_version`, `article_count`, `char_count`. |
| `GET /api/documents/{id}?corpus_version=...` | Returns the full Document. |
| `GET /api/documents/{id}/chunks?condition=s400&corpus_version=...` | Returns `{"items":[Chunk...]}`; must not re-run another browser chunking logic. |
| `POST /api/indexes/build` | Takes a corpus version, submits the four-group index build task, and returns 202 and the task ID. |
| `POST /api/search` | Returns semantic retrieval results for one condition. |
| `POST /api/compare` | Returns a same-question top-5 comparison of two conditions. |

Index build request and response:

```json
{"corpus_version":"fixture-en-v2"}
```

```json
{"task_id":"index-task-1","state":"queued"}
```

C provides the formal `GET /api/tasks/{id}`. B provides an in-memory task adapter in independent API tests, with status `queued|running|completed|failed`, rather than giving up API tests while waiting for C. The formal `build_indexes()` itself can return the manifest synchronously; the HTTP layer is responsible for submitting it as a background task.

Retrieval request:

```json
{"question":"What does Article 2 say?","corpus_version":"fixture-en-v2","condition":"s400","top_k":5}
```

Full synthetic response; scores and elapsed time are for API tests only:

```json
{
  "corpus_version":"fixture-en-v2",
  "index_version":"fixture-index-v1",
  "condition":"s400",
  "hits":[{
    "rank":1,
    "score":0.9,
    "chunk_id":"ecc55790d61808b33e0ec4cb33471f7e520a6af4dd26c2ebdd083d2ed80a18ac",
    "corpus_version":"fixture-en-v2",
    "condition":"s400",
    "document_id":"fixture",
    "article_ids":["fixture-a001","fixture-a002"],
    "start":0,
    "end":25,
    "text":"Article 1 A.\nArticle 2 B.",
    "title":"Synthetic API Contract Fixture (not official legislation)",
    "source_url":"https://example.org/fixture",
    "article_labels":["Article 1","Article 2"]
  }],
  "timing_ms":10
}
```

Comparison request:

```json
{"question":"What does Article 2 say?","corpus_version":"fixture-en-v2","left_condition":"f400","right_condition":"s400"}
```

The comparison response top level is `question`, `corpus_version`, `index_version`, `left`, `right`. Left and right each contain `condition`, the full `hits` array, `timing_ms`, and `context_chars`; the sample text is very short, so both F400/S400 return the full text, and identical text is a normal result. Only long article samples reveal chunking differences.

### 8.3 Error specification

| Scenario | HTTP | `code` example |
| --- | ---: | --- |
| Empty question, invalid condition, or top_k | 422 | `INVALID_REQUEST` |
| Document or task not found | 404 | `NOT_FOUND` |
| Database not built, build not completed, requested version mismatch | 409 | `INDEX_NOT_READY` / `VERSION_MISMATCH` |
| Model files not ready or external download failed | 503 | `EMBEDDING_UNAVAILABLE` |
| Body text position corrupted, input exceeds model limit | 409 | `SOURCE_MISMATCH` / `MODEL_INPUT_TOO_LONG` |

Error bodies are unified as `{"code":"...","message":"Human-readable description"}`. Unexpected program errors return 500 and write to the server log; they are not disguised as "no evidence found". API parameter validation errors must be explicitly converted to the overall document's unified error format; it cannot be that some return `detail` while others return `message`.

## 9. How B is tested independently

| Test | Sample and expectation | Requires model download |
| --- | --- | --- |
| Source coverage and IDs | A 25-character English sample, plus the retained 13-character Chinese regression sample; verify complete coverage and fixed hashes. | No. |
| Fixed window boundaries | Exactly 400, 401, 800, 801 characters, including spaces, newlines, and emoji. | No. |
| Structure boundaries | Adjacent short articles, overlong articles, cross-chapter/section, references to other article numbers within an article, text without article numbers. | No. |
| Long-sentence fallback | A single sentence exceeds the limit; ensure hard splitting does not drop characters and fallback counts are recorded. | No. |
| Vector adaptation | Inject fixed vectors; verify write counts, text/vector ordering, and cosine conversion. | No; a temporary real Chroma can be used. |
| Idempotency and versioning | Building the same version twice consecutively does not duplicate; old indexes reject new corpora; failed indexes cannot be queried. | No. |
| API | Parameter errors, task status, document reading, one-sided comparison failure, returned fields consistent with ranges. | No. |
| Real-model smoke test | In a clean environment, download a fixed revision, encode on CPU, build the four groups, and run searches; verify token checks and actual dimensions. | Yes; first-time network access or provide a fixed weights package. |

Real-model retrieval tests must verify that semantically relevant content can be returned, vectors are valid, and structure fields are correct; do not write the exact floating-point values of a particular semantic question as assertions that must be equal across platforms. Mock test output cannot be used as formal four-group experiment results.

So that C can directly verify the contract, B stores the above samples in `tests/fixtures/b/`, along with a copy of `expected_hits.json`. Test block IDs, document positions, and official source fields must match the input; submitting only a "search works" screenshot is not acceptable.

### 9.1 Independent development command conventions

The following entry points are implemented. After creating your own project `.venv`, use that virtual environment's Python from the project root:

```bash
python -m pip install -r requirements-b.txt -r requirements-b-dev.txt
python -m pip check
python -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py
```

The model preparation and four-group build scripts are agreed to support `--config` and a test fixture mode:

```bash
python -m scripts.fetch_embedding --config config/retrieval.example.json
python -m scripts.build_indexes --config config/retrieval.example.json --fixtures
```

`--fixtures` explicitly selects `tests/fixtures/b/` and must not write to the formal data directory; without this parameter it reads A's formal manifest and should error if not found. Test indexes and real indexes are physically isolated and cannot be distinguished only by page labels.

Independent API and retrieval verification page preview entry point:

```bash
python -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

If this module path is used, package markers must be added to `tests/` and `tests/support/` so the command can import them. After startup, open `http://127.0.0.1:8767/b-debug` to view B's retrieval verification page; `/docs` is for API self-testing. This entry point is implemented and has been verified through web operations; C ultimately registers the same set of business routers into the formal `app.main:app`.

### 9.2 How independent testing is reflected in the frontend

B only needs to implement a simple independent verification page; there is no need to wait for C to complete the full Q&A page. The page uses plain HTML/CSS/JavaScript, is served same-origin by the test service, and uses `fetch()` to call B's real API; no new Node build environment is added and no CDN is depended on. Sample inputs and results are safely displayed via `textContent`.

| Page area | What the user can do | Which verification results are displayed |
| --- | --- | --- |
| Run status | View startup mode, corpus, and model status | `mock`/`real`, test corpus identifier, model ID/revision, index version, four-group readiness status. |
| Documents and chunks | Select a test document and F400/S400/F800/S800 | Source text, each chunk's text, chunk ID, covered article numbers, `start/end`, length, and chunk count. |
| Build index | Click "Build four test indexes" | Task progress, chunk counts per group, and failure reasons; searching is disabled until completion. |
| Single-group search | Enter a question and select one condition | top-5 source chunks, relevance scores, article numbers, sources, character positions, and retrieval time. |
| Same-question comparison | Select left and right conditions, then submit the same question | Retrieval chunks from both sides displayed side by side, with each side's chunk length, total returned characters, scores, and time. |
| Source verification | Click "View source snippet" on a result | The source snippet, document ID, article number, and range returned by the API; Python character positions are not recomputed in the browser. |

**Full demo steps:** Start B's test service → open `/b-debug` → select the synthetic long document → build the four indexes → preview the two chunking methods → enter a question → view single-group hits → view same-question comparison → open a snippet to verify positions. Use long-article samples to demonstrate boundary differences; the 25-character English sample mainly verifies fields and positions and should not be forced to produce different effects.

#### Two startup modes

- `mock`: default mode. Uses B's built-in synthetic documents and fixed test vectors, and actually runs chunking, index adaptation, and the API; no embedding download is required and no LLM is called. The page clearly marks "simulated embedding, for interface and flow verification only"; ranking must not be presented as real semantic retrieval results.
- `real`: still uses B's built-in test documents, but encodes via real embedding at a fixed revision and writes to an isolated test index. The page clearly marks "real embedding + synthetic test corpus"; A's formal documents or C's Q&A service are not required. This mode is used to prove that the model, vector store, and retrieval chain actually run.

The mode is set at startup via the test-service-specific environment variable `DERAG_B_DEBUG_MODE=mock|real`. Before entering `real`, prepare the model as described in section 9.1; missing weights, input over limit, or index build failure should display a specific error and must not automatically fall back to `mock`. After a mode switch, clear old page results; index directories are isolated by mode and version to avoid mistakenly using another mode's cache.

Startup convention for selecting real-model verification mode in PowerShell:

```powershell
$env:DERAG_B_DEBUG_MODE = 'real'
python -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

The above command is usable; model configuration reads `config/retrieval.example.json`, and paths still support project environment variable overrides. Importing the test service does not automatically download weights or start index building.

#### Correspondence between page and API

The page's documents and chunks area calls `/api/documents` and `/api/documents/{id}/chunks`; index building calls `/api/indexes/build`, with status queried via `/api/tasks/{id}` provided by the test task manager; single-group search calls `/api/search`; left-right comparison calls `/api/compare`. All business logic uses B's same set of service functions; no separate chunking or ranking logic is written for display.

The test service may add a read-only `/b-debug/status` that returns mode, synthetic corpus version, model configuration, and index status, used only for verification page guidance and not part of the production API contract. Full source snippets come from existing document/retrieval responses; the page has no independent generated-answer or formal metrics entry point.

#### Page acceptance

1. `mock` mode can start in an empty model cache environment and can actually chunk, build test indexes, and display results.
2. `real` mode completes the same flow using the real model, explicitly retaining the model version and run records; API tests remain the automated acceptance basis, and the page supplements with visual verification.
3. Index build status, no results, loading, and errors are all visible; when switching documents/conditions or submitting a new question, old results are not continuously displayed as if they were new results.
4. Screenshots or screen recordings must indicate the mode, test corpus, and conditions; results produced from synthetic documents and simulated vectors do not enter the final regulatory experiment report.
5. During C integration, reuse B's API and services and connect the interaction to the formal document library/comparison page; the standalone verification page remains in the test directory, and B's formal delivery does not require C to replicate this page.

## 10. Configuration and reproduction for the teacher

B is developed independently using `config/retrieval.example.json`; after integration, C merges the identically named configuration keys into `config/experiment.json`.

| Configuration key | Requirement |
| --- | --- |
| `corpus_version`, `conditions`, `top_k` | Formally the A frozen version, four groups of conditions, and 5. |
| `embedding.model_id`, `embedding.revision` | Actual model ID and immutable revision; do not use `main/latest` as the final version. |
| `embedding.model_dir`, `embedding.device` | Project-relative path or container mount path, baseline CPU; supports `DERAG_MODEL_DIR`. |
| `embedding.dimension`, `embedding.normalize` | Consistent with real output; indexing and querying remain the same. |
| `embedding.query_prefix`, `embedding.document_prefix` | Fixed per model requirements; an empty prefix is also explicitly recorded. |
| `embedding.max_input_tokens` | The actually verified effective input limit; tokenizer checks include special tokens. |
| `retrieval.metric`, `retrieval.chunker_version` | `cosine` and the chunking implementation version; the algorithm version must not be generated automatically from time. |

Must not depend on personal global Python packages, private online embedding services, or personal download caches. The data root directory supports `DERAG_DATA_DIR`; configuration precedence is consistent with the master document: explicit parameters → environment variables → configuration file, and the actually effective values are written to the record.

Before B is complete, verify installation, model loading, index building for the four groups, and retrieval at least once in an empty virtual environment or a clean Linux CPU container. Final C is responsible for the complete Docker image, but B must provide accurate dependencies and a model preparation script to ensure the container does not need to access B's local services. The current preview version `DE.tar` does not include these capabilities.

## 11. Content handed to C and acceptance

After B is completed independently, submit a reviewable PR containing at least:

1. All core code of `app/retrieval/`, the three API modules, model download and index building scripts, and the standalone verification pages for `tests/support/b_app.py` and `tests/support/static/b_debug.html`.
2. Locked dependencies, configuration samples, model ID/revision/file list, and CPU run instructions.
3. Document/Chunk/SearchHit samples that pass the master document field validation.
4. Automated test results, plus real embedding + Chroma smoke commands and output.
5. Example index manifests for the four groups: version materials, chunk count, minimum/average/maximum chunk length, fallback count, index build time, model and vector store configuration, completion status.
6. Known limitations, such as model size, CPU memory usage, whether downloads require network access, and approximate retrieval ranking differences; unverified environments must not be written as supported.

After merging, C only needs to inject A's real document loader, project configuration, and task manager, register B's router, and rebuild the index with the real corpus; question answering and evaluation uniformly call B's `search()`. C does not rewrite B's algorithms, and B does not modify A's standard answers for integration.

**B's final completion criteria: pass standalone tests and real-model smoke tests without using A/C implementations; during integration, read A's formal documents under the same contract and return to C four groups of retrieval evidence that can be located in the original text.**


## 12. This implementation and reproducible acceptance steps

### 12.1 Files already in place

- Core logic: `types.py`, `chunking.py`, `embedding.py`, `vector_store.py`, `indexes.py`, `service.py`, `errors.py` in `app/retrieval/`.
- Router factory: `app/api/`, including documents, index building, retrieval, and comparison. The production entry point is not yet registered; it will be reused after C integration.
- Standalone verification entry: `tests/support/b_app.py`, verification page `tests/support/static/b_debug.html`.
- Command line: `scripts/fetch_embedding.py`, `scripts/build_indexes.py`, `scripts/smoke_embedding.py`.
- Frozen samples: `tests/fixtures/b/`; synthetic text is explicitly marked as test, and no formal standard questions have been created.
- Dependency locks: `requirements-b.txt` and `requirements-b-dev.txt`. The original `requirements.txt` is retained for the existing preview application and will be unified when C merges.

No models are downloaded or indexes built at module import; there is no dependence on global Python packages, private model services, LLM keys, or personal Hugging Face caches.
`DERAG_DATA_DIR`, `DERAG_MODEL_DIR`, `DERAG_RETRIEVAL_CONFIG` support overrides; the CLI's `--data-dir` / `--model-dir` / `--config` take precedence.
`.env` is not read automatically; in PowerShell, use `$env:VARIABLE_NAME` to inject it.

### 12.2 First installation (Windows PowerShell)

First install Python 3.13.11, then run in the `DERag` project root directory. If the project already has `.venv`, the first line can be skipped.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-b.txt -r requirements-b-dev.txt
.\.venv\Scripts\python.exe -m pip check
```

Installation requires network access and disk space; these are all public dependencies, and there is no need to copy the developer's virtual environment.
A separate `.venv-b-verify` has been created and both dependency locks installed; the original installation once passed through `pip check`, and after the English migration the automated tests and real-model scripts were run again, with results in the current record.
The verified environment is Windows / Python 3.13.11 / CPU. The Linux container has not yet been tested; the original `DE.tar` is still the frontend preview package.

### 12.3 Automated tests (no embedding download)

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py -q
```

Expected `78 passed`. The tests use a real temporary Chroma and test vectors, covering chunking intervals, Unicode, sections, long-sentence fallback, idempotent index building, failure retry, index/original text corruption, missing model, token over-limit, API fields, and error formats. The results are module correctness tests, not regulatory question-answering accuracy.
`pytest.ini` places the test temporary directory in the project's `artifacts/b/.pytest/` to avoid depending on personal temporary directory permissions; this directory is cleaned up by pytest, so do not put personal files in it.

### 12.4 First accept via the web page (default mock, no model required)

```powershell
$env:DERAG_B_DEBUG_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

Open <http://127.0.0.1:8767/b-debug>; the API documentation is at <http://127.0.0.1:8767/docs>.
Follow this order: select "Synthetic Data Protection Rules" → click "Build four test indexes" → select F400/S400 to view boundaries → search the default question → compare side by side → click "View source chunk". All chunks come from the server; the original text is not re-split in the browser or sliced by JavaScript string indices.

The API can also be called from another PowerShell window:

```powershell
$body = @{ question='How can an individual request deletion of personal information?'; corpus_version='fixture-en-v2'; condition='s400'; top_k=5 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8767/api/search' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

The default service must first build the database from the web page. You can also run in advance:

```powershell
.\.venv\Scripts\python.exe -m scripts.build_indexes --config config/retrieval.example.json --fixtures --mock
```

### 12.5 Real model acceptance

First stop the mock service (Ctrl+C), then run model preparation for the first time. The weights are about 2.27 GB, about 2.3 GB including the tokenizer, and the first run requires internet access; file hashes are stored in the model directory's `derag-model-manifest.json`, with a verification copy in `artifacts/b/model-manifest.json`.

```powershell
.\.venv\Scripts\python.exe -m scripts.fetch_embedding --config config/retrieval.example.json
.\.venv\Scripts\python.exe -m scripts.build_indexes --config config/retrieval.example.json --fixtures
.\.venv\Scripts\python.exe -m scripts.smoke_embedding --config config/retrieval.example.json
$env:DERAG_B_DEBUG_MODE = 'real'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

`smoke_embedding` reuses a complete index that passed verification and runs a total of 12 real retrieval checks across four conditions × three questions, an actual 1024-dimensional vector check, real tokenizer over-limit rejection, HTTP retrieval, and comparison checks. On success it outputs `PASS`; see `artifacts/b/real-smoke.json` for details.
The synthetic text contains duplicate content, so exact floating-point numbers are not used as cross-platform assertions; only topic-relevant evidence and field contracts are checked, and the success ratio here is not written up as a formal evaluation metric.
The first CPU model import, load, and encoding are slow; wait for the command to return. There is no logic that automatically falls back to mock.

To have a clean environment fully rebuild from an empty index, specify a separate data root directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke_embedding --config config/retrieval.example.json --data-dir data/b-clean-verification --output artifacts/b/clean-real-smoke.json
```

This implementation uses the same fixed revision, CLS pooling, empty prefix, 1024 dimensions, normalization, 8192 token limit, CPU, batch size of 4, and 4 CPU threads. All four conditions are identical. Chroma 1.5.9 uses cosine, `ef_construction=100`, `ef_search=100`, `max_neighbors=16`, `num_threads=1`, `batch_size=2`, `sync_threshold=2`, `resize_factor=1.2`, and the effective settings are written into the index version materials. The lower sync threshold ensures that an index built from a small sample can be read by subsequent HTTP requests, at the cost of more frequent disk writes when building the formal corpus; if parameters are changed uniformly, all four groups must be rebuilt.

### 12.6 Minimal integration method for C

```python
from app.api import create_retrieval_routers, install_retrieval_error_handlers
from app.retrieval import RetrievalService
from app.retrieval.embedding import LocalEmbedder
from app.retrieval.types import load_config

config = load_config()  # C replaces this with a unified config adapter; pass in the same fields
service = RetrievalService(
    document_loader=A_load_documents,  # A's function, signature (corpus_version) -> list[dict]
    embedder=LocalEmbedder(config['embedding']),
    config=config,
)
install_retrieval_error_handlers(app)
app.include_router(create_retrieval_routers(service, task_manager))
# C's Q&A directly uses service.search(question, condition, corpus_version, top_k=5)
```

`A_load_documents` and `task_manager` are variables injected when C is assembled, not formal modules implemented by B itself. If A returns a Pydantic Document, the adapter uses `model_dump()` to convert it to a dictionary. B's built-in `formal_loader(Path(config['data_dir']))` can also read a formal manifest generated from the total documents; it verifies the original files, processed files, body text, articles, and corpus version hashes.

The task manager must implement `submit(function, background_tasks) -> {'task_id': ..., 'state': 'queued'}`: receive a no-argument synchronous index-building function, hand the task to its own background executor, record the result/failure reason, and immediately return queued; C provides the production version `/api/tasks/{id}`. B's `MemoryTaskManager` demonstrates the full adapter behavior, but it is for single-process testing only; tasks are lost on restart and it is not used as production task persistence.

Formal data must not carry `--fixtures`; change the config `corpus_version` to A's real version, then run the index-building command without that flag. A missing A manifest will raise an explicit error; automatically filling in with samples is prohibited.
The actual index is located by a deterministic version derived from the current corpus + config; it does not automatically select the "most recent" index; only the same version with all four groups completed can be queried. B currently uses a data-root file lock to serialize index building and retrieval, which is suitable for coursework experiments; high-concurrency services require a separate design.

### 12.7 Saved evidence and current boundaries

- `artifacts/b/tests.xml`: 78 pytest results in a clean virtual environment.
- `artifacts/b/real-smoke.json`: real CPU model, four-group manifests, retrieval snapshots, and API output.
- `artifacts/b/clean-real-smoke.json`: record of a full rebuild from an isolated index directory in a clean environment.
- `artifacts/b/model-manifest.json`: model commit and per-file SHA-256.
- `artifacts/b/frontend-smoke.json`, `debug-mock.png`, `debug-mobile.png`: records of building the index, searching, comparing, the source-text popup, and clearing old results on input change in the browser. The verification page was checked on desktop and a 390px narrow screen, with no JavaScript errors and no horizontal overflow.

Currently not integrated: A's official documents, C's LLM answers, and the formal evaluation of 30 standard questions. The synthetic data source uses `example.org`, which only verifies citation fields and source-text spans and cannot serve as official legal articles. Chroma is approximate retrieval; candidates returned at the same distance are sorted by chunk_id, and top-k tie boundaries may differ slightly across platforms.
Model weights and generated indexes are ignored by Git; after uploading to GitHub, team members reproduce them using the dependency installation and model preparation commands in this section. Offline delivery requires a separate fixed weights directory plus dependency packages or a final image; C is responsible for the final Docker integration.
