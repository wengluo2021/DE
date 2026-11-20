# DERag: Part A development documentation (official corpus and standard test question set)

Record date: 2026-11-19. This document describes the data pipeline already implemented for Part A, code responsibilities, data contracts, version algorithms, and handover methods. For team members running it in practice, follow [A测试.md](./A测试.md); for a brief delivery checklist, see [A部分交付说明.md](./A部分交付说明.md).

## 1. What Part A must accomplish

Part A is responsible for the chain "official English HTML → source registration → cleaned full text → chapter/article and character positions → frozen corpus package → standard test question set". Part B receives the same frozen body text for chunking, embedding, vector database ingestion, and semantic retrieval; Part C uses the corresponding version of the standard questions to run question answering, citation validation, and formal evaluation.

**Current status: The five official documents, the formal corpus package, the 30 English standard questions, and the corresponding scripts have completed programmatic validation, AI-assisted source-text review, human review, and browser visual inspection, with no issues found.** Part A's three automated test modules have 19 items passing; both the formal package and the single-document sample can be loaded through the normal package import's `formal_loader`.

Human review and browser visual inspection were updated according to the confirmation of Part A lead 2026-11-19, with the conclusion being pass and no issues found. Existing stage reports retain the inspection records from that time.

| Lead | Delivery scope | Boundaries with other members |
| --- | --- | --- |
| A | Sources, HTML snapshots, cleaned full text, structure and positions, version manifest, standard questions and evidence, data validation and review records | Responsible for data issue revisions and version releases |
| B | Fixed-window and structure-aware chunking, embedding, four Chroma indexes, semantic retrieval, and related APIs | Reads Part A's formal package, does not rewrite the frozen body text |
| C | LLM answers, citation validation, question-answering page, four formal evaluations, human scoring of run answers, and system integration | Uses Part A's question set for scoring and calls Part B's retrieval module |

19 automated tests validate the data pipeline and exception handling; the 30 standard questions are the input and scoring reference for evaluating RAG. Part A's tests passing cannot replace Part B's real retrieval validation, nor can it be written as all system answers to the 30 questions being correct. Development and testing of Part B's independent module are described in [B开发文档.md](./B开发文档.md) and [B测试.md](./B测试.md).

## 2. Code directory and file responsibilities

The local project root directory is `D:\gitcode\Edit\DE`. The directories below are all relative to the project root directory; team members can place the entire project at another path.

```text
DE/
  AGENTS.md                          # Current development conventions
  A部分需求与开发顺序.md              # Requirements and acceptance criteria for steps 1–6
  A开发文档.md                       # This document: implementation and data contracts
  A测试.md                           # Team member running and acceptance guide
  A部分交付说明.md                   # Current delivery entry point and version
  A部分阶段开发记录.md               # Historical development and review records
  scripts/
    process_documents.py             # Single-document and batch cleaning and character positioning
    validate_data.py                 # corpus / eval validation
    export_sample.py                 # Joint debugging sample export for the first document
    export_corpus.py                 # Formal five-document delivery package export and verification
    build_gold.py                    # Fixed question definitions, evidence extraction, question set generation
  tests/
    test_corpus_batch.py             # 8 items: batch processing and full corpus validation
    test_corpus_freeze.py            # 6 items: freezing, loading, and formal entry point integrity
    test_gold_eval.py                # 5 items: question set and evidence exception validation
  data/
    sources.json                     # Official source and snapshot registration
    raw/                             # Five official HTML files saved from the browser
    processed/                       # Five accepted pairs of txt / structure JSON
    corpus_manifest.json             # Part A's project-level corpus freeze manifest
    formal_corpus/
      manifest.json                  # Part B's formal loading manifest
      raw/                           # Byte copy of the official HTML
      processed/                     # Adapted JSON with B fields filled in, containing the full text
    sample_corpus/                   # Standalone integration-test package for the first document
    eval/
      sample.jsonl                   # 3 integration-test sample questions
      sample_manifest.json           # Sample question manifest
      gold.jsonl                     # 30 formal gold questions
      manifest.json                  # Formal question set version and coverage
  artifacts/a_review/                # Per-document, batch, freeze, question set and final review
```

### 2.1 Script responsibilities

| File | Input | Output and responsibilities |
| --- | --- | --- |
| `process_documents.py` | `sources.json` and the local HTML registered therein | Generate normalized txt, structure JSON, stable IDs, character ranges and statistics |
| `validate_data.py` | Source, snapshot, processed artifacts, formal package or question set | Read-only validation; returns 0 on success, non-zero on validation failure with the reason reported |
| `export_sample.py` | The accepted first document and the as-is questions | Generate the single-document sample adaptation package and sync the sample question version; rewrites sample files |
| `export_corpus.py` | The five accepted txt / JSON files and the official HTML | Generate the formal package and two manifests, compute the unified version and verify loading |
| `build_gold.py` | Formal package, structural positions and question definitions fixed in code | Extract evidence, generate `gold.jsonl` and the question set manifest |

`build_gold.py` is a reproducible generator for a fixed question set; it does not call an LLM to generate random questions at runtime. Questions and reference answers are written into the definitions, and evidence is extracted by the program from the frozen full text.

### 2.2 Main functions

| Module and function | Purpose |
| --- | --- |
| `process_documents.load_catalog` / `run_all` | Manifest pre-check, stable sorting, per-document processing and success/failure summary |
| `process_documents.build_document` | Build the cleaned full text and structure payload from one HTML file |
| `process_documents.parse_chapter` / `parse_section` / `parse_article` | Parse chapters, sections and main articles of modern EUR-Lex |
| `process_documents.parse_legacy` | Handle adjacent paragraphs, sign-off, footnotes and annexes of the fifth legacy HTML |
| `process_documents.TextCursor` / `assemble` / `assemble_legacy` | Record the current position when concatenating body text and bind each structural range |
| `validate_data.validate_corpus` / `validate_all` | Validate ranges, structure, hashes and manifests for a single document and the whole corpus |
| `validate_data.check_cases` / `validate_eval` | Check question fields, version, evidence attribution, slices, counts and question set hash |
| `export_corpus.adapt_article` / `prepare_documents` | Preserve accepted articles, fill in B fields and compute version material |
| `export_corpus.export_official` / `require_official_catalog` | The formal entry point enforces verification of the five official IDs before writing files |
| `export_corpus.export_corpus` / `verify_corpus` | General export, and cross-check against accepted data after normal loading |
| `build_gold.clip` | Locate and extract evidence within a specified structure using a unique anchor |
| `app.retrieval.types.formal_loader` | The normal loader provided by B, verifying package files, body text, article structure and version |

The formal CLI uses `export_official`. The general `export_corpus(root)` still supports small corpora for unit tests; the fact that a general function can export one test document must not be used to bypass the integrity check for the five formal documents.

## 3. Fixed corpus scope

The topic is EU online shopping consumer rights in English, and all five documents use the **original published version `original_publication`**. The consolidated revised versions linked from the web pages did not replace the body text of the local snapshots.

| Original file | document_id | Main articles | Chapters / sections | Recitals | Annexes |
| --- | --- | ---: | --- | ---: | ---: |
| `eu_consumer_rights_2011_83.html` | `eu_consumer_rights_2011_83` | 35 | 6 / 0 | 67 | 2 |
| `Sale of Goods.html` | `eu_sale_of_goods_2019_771` | 27 | 0 / 0 | 72 | 1 |
| `Digital Content and Services.html` | `eu_digital_content_2019_770` | 27 | 0 / 0 | 87 | 0 |
| `Unfair Commercial Practices.html` | `eu_unfair_practices_2005_29` | 21 | 4 / 2 | 25 | 2 |
| `Unfair Terms.html` | `eu_unfair_terms_93_13` | 11 | 0 / 0 | 24 | 1 |

Main articles total **121**. The 24 recitals of the fifth document have no official numbering, so only the internal order `ordinal` is stored; official recital numbers must not be fabricated for them.

The basis for source verification, official URLs, CELEX, institutions, dates and gazette information are stored in `sources.json` and the per-document review reports. For save time, download HTTP status and response time that browser snapshots cannot substantiate, `null` is used, with the reason stated. The HTTP 200 from accessing Cellar during source verification is the result of a separate request and must not be treated as the status when the browser saved this HTML.

## 4. Data processing flow

```text
sources.json + raw HTML
           |
           v
process_documents.py
           |
           +--> processed/*.txt: the single normalized full text
           +--> processed/*.json: metadata, structure, IDs, ranges and hashes
           |
           v
validate_data.py --scope corpus
           |
           v
export_corpus.py --> formal_corpus + corpus_manifest.json --> B chunking and indexing
           |
           v
build_gold.py --> gold.jsonl + eval/manifest.json --> C question answering evaluation
           |
           v
validate_data.py --scope eval
```

### 4.1 Reading and cleaning

The cleaning script reads paths from the source manifest and does not scan the entire browser resource directory. HTML file names containing spaces are handled as-is from the manifest; a `_files` folder with the same name is not treated as another regulation.

The body text retains the regulation title, recitals, chapters, sections, main articles, paragraphs, lists, substantive tables, sign-off, annexes and footnotes. Ancillary content such as navigation, language menus, page buttons and repeated gazette headers is excluded. Tables are converted to text in row and cell order, and empty cells still preserve column relationships, for example `Article 1 | | Article 3 ...`.

The cleaning rule version is `eurlex_html_v1`. Whitespace and LF line breaks are normalized first, then all character positions are generated. Wording, negations, exceptions, numbers and cross-references in the original text are not rewritten by the cleaner.

### 4.2 Modern structure and legacy HTML

Modern pages identify chapters, sections, and main articles by the actual structural containers under `#document1`. The `Article` occurrences in in-text cross-references, amending quotations, and annex tables remain within their original parent structure and are not treated as new main articles.

The legacy parsing branch is entered only when `p.ti-art` exists and `div.eli-subdivision` does not. The fifth document is split by 11 main article headings; Article 11 ends before the signature block, and subsequent footnotes and annexes are assigned independently. Footnote continuation paragraphs without anchors are merged into the preceding footnote.

Both parsing branches ultimately output the same full-text and structure contract; B receives the processed data and does not need to parse the raw HTML separately.

### 4.3 Character ranges and duplicate text

Positions are recorded by the body-assembly cursor and are not backfilled from the position of the first `find()` occurrence in the full text. Identical article numbers, identical paragraphs, and footnotes with the same number each retain their own ranges.

Ranges are uniformly Python character indices `[start, end)`:

```python
assert clean_text[item["start"]:item["end"]] == item["text"]
```

Indices refer to the complete cleaned full text, including spaces, punctuation, and line breaks; they are not UTF-8 bytes, English word counts, or tokens. After reading, B and C must not `strip()` again, replace line breaks, or reorder paragraphs.

The sections of the fourth document are both stored within chapters and mirrored at the top level. The validator distinguishes "structure definitions" from "structure references," and mirrors count as a definition only once. Article 5 belongs directly to Chapter 2; Articles 6 and 7 belong to its Section 1; Articles 8 and 9 belong to its Section 2.

## 5. Three data formats

### 5.1 Source records

The top-level `sources` array of `data/sources.json` registers five documents. Each record contains `document_id`, `title`, `institution`, `language`, `official_url`, `eli`, `celex`, `version_type`, `source_format`, dates, gazette information, `snapshot`, null-value reasons, and verification basis.

`snapshot.path` and `snapshot.sha256` correspond to the stored HTML. Date fields distinguish meanings such as file date, publication, entry into force, transposition, and application; file modification times must not be used in place of official dates, and later consolidation points must not be treated as the revision date of the current original published version.

### 5.2 Accepted full text and structure JSON

`data/processed/<document_id>.txt` stores the complete body text. The paired JSON stores `clean_text_path`, `clean_text_sha256`, `character_offsets`, sources, cleaning rules, statistics, and the various structures. Here `title` is the structure object, while the full text is in a separate txt file.

Main articles retain fields such as `article_id`, `number`, `chapter_id`, `section_id`, `start`, `end`, `text`, and `blocks`. When there are no chapters or sections, the corresponding field is `null`.

### 5.3 B's adapted Document

The formal delivery JSON is located at `data/formal_corpus/processed/`, embeds the accepted full text in the top-level `text`, and fills in the fields required by B.

| Field | Source and purpose |
| --- | --- |
| `document_id` | Existing stable document ID |
| `corpus_version` | Content version shared by the five documents |
| `title`, `issuer`, `source_url` | Verified title string, institution, and official URL |
| `published_at`, `effective_at` | Publication date and entry-into-force date from the source; dates are not re-inferred |
| `raw_path`, `raw_sha256` | In-package snapshot path and file byte hash |
| `text` | Full text identical to the accepted txt |
| `articles` | Retains the original articles and adds `label`, `chapter`, `section` |
| `chapters`, `sections` | Chapter and section boundaries and membership information used for chunking |
| `source_fields` | Traceability information such as language, CELEX, version type, dates, and the hash of the accepted structure file |

For example, some fields of Article 18 in the first adapted document are as follows; this is an excerpt of the article object, not a complete Document:

```json
{
  "article_id": "eu_consumer_rights_2011_83:article:18",
  "number": "18",
  "label": "Article 18",
  "chapter_id": "eu_consumer_rights_2011_83:chapter:IV",
  "chapter": "eu_consumer_rights_2011_83:chapter:IV",
  "section_id": null,
  "section": null,
  "start": 81963,
  "end": 83581
}
```

Adaptation only adds interface fields and does not change article IDs, body text, chunks, or ranges. The accepted JSON is not passed directly to B's loader; use the adaptation package and its manifest.

## 6. Formal export and the two manifests

### 6.1 Integrity check of the formal entry point

Before creating or writing the delivery package, the command `scripts/export_corpus.py` requires the source manifest to contain exactly five official document IDs. Missing, extra, or duplicate documents all cause failure; a successful export of four documents must not be treated as a formal five-document delivery.

The generic export function first prepares all documents to be exported, then writes the HTML byte copies and adaptation JSON. Only after the corpus version is written into the adaptation JSON is its final file hash computed.

### 6.2 Responsibilities and paths of the two manifests

| File | User | Path basis |
| --- | --- | --- |
| `data/corpus_manifest.json` | A's project-level freeze and traceability record | Relative to the project root; registers both the original artifacts and the in-package copies |
| `data/formal_corpus/manifest.json` | B's `formal_loader` | Relative to the loading directory; supports path forms with the first `data/` segment removed |

B sets `data_dir` to `data/formal_corpus`. The in-package manifest's `data/raw/Sale of Goods.html` resolves to `data/formal_corpus/raw/Sale of Goods.html` and does not read the original snapshot in the project root.

The two manifests have the same `corpus_version`, but their file structures and purposes differ. `formal_loader` does not directly read the project-level `corpus_manifest.json`.

## 7. Versions and hash algorithm

### 7.1 The current three versions

| Name | Value |
| --- | --- |
| Formal `corpus_version` | `794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795` |
| Formal `gold_version` | `9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d` |
| Single-document sample `corpus_version` | `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50` |

The old question set version `444afb6d...` is a historical version from before the corrections to the refund and second-hand goods exceptions; the current formal evaluation uses the new question set version in the table above.

### 7.2 corpus version

Reuse `app.retrieval.types.canonical` and `digest`:

```python
canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

The version materials are `parser_version` and the document list sorted by `document_id`. Each document contains only:

```text
document_id, title, issuer, source_url,
published_at, effective_at, raw_sha256,
text_sha256, structure_sha256
```

| Hash | Object computed |
| --- | --- |
| `raw_sha256` | Raw HTML file bytes |
| `text_sha256` | UTF-8 bytes of the complete `text`, equal to the byte hash of the accepted txt |
| `structure_sha256` | Canonical JSON of the adapted `articles` array, including the filled-in label, chapter, and section |
| `processed_sha256` | Bytes of the entire adapted JSON file after the version is written |
| `accepted.structure_json_sha256` | Bytes of the accepted structure JSON file, recorded separately |

`structure_sha256` is not the file hash of the complete structure JSON. The loader also verifies the hash of the entire adapted file, covering the remaining metadata within it.

The corpus fingerprint does not include the version number itself, the final hash of the adapted file, the registration time, or the export time, to avoid self-reference and version drift caused by runtime.

### 7.3 question set version

`gold_version` equals the SHA-256 of the file bytes of `gold.jsonl`, including the trailing LF; the manifest's `gold_sha256` is identical to it. Each question already contains the formal `corpus_version` but does not contain `gold_version`, so there is no problem of a file writing its own hash into itself.

Modifying a question, reference answer, key fact, evidence, field serialization, or line breaks will change the question set version. After revision, the question set manifest and review record must be regenerated, and members using that question set must be notified.

## 8. Standard test question set

### 8.1 distribution and fields

The formal question set has **30 questions in total: 24 answerable, 6 refusal**. The current types are single-segment evidence `single_article` 13 questions, multi-segment evidence `multi_evidence` 11 questions, and `unanswerable` 6 questions. Multiple pieces of evidence may come from the same provision and do not necessarily span documents.

| Document | Answerable questions | Evidence segments |
| --- | ---: | ---: |
| Consumer rights 2011/83 | 6 | 11 |
| Sale of goods 2019/771 | 5 | 9 |
| Digital content 2019/770 | 5 | 10 |
| Unfair commercial practices 2005/29 | 4 | 7 |
| Unfair terms 93/13 | 4 | 5 |
| Total | 24 | 42 |

The fields of each JSON line follow the existing sample questions:

| Field | Purpose |
| --- | --- |
| `case_id` | Unique and stable question number |
| `corpus_version` | Formal corpus version used by this question |
| `question`, `question_type` | English question and question type |
| `should_refuse` | Whether a refusal is expected |
| `reference_answer` | English scoring reference answer |
| `key_facts` | Key facts; the current implementation takes the corresponding quote item by item |
| `evidence` | Standard evidence list |
| `refusal_reason` | What information the refusal question lacks; null for answerable questions |

Each evidence segment contains `document_id`, `article_id` or `structure_id`, `start`, `end`, and `quote`. The current 42 segment excerpts are 68–393 Python characters long, all satisfy `0 < len(quote) < 400`, and are cut contiguously from the full text.

### 8.2 question authoring and semantic review

`clip` first obtains the range of the specified provision or annex, then checks that the start and end anchors are unique within that range. The first identical phrase in the full text cannot be used in place of the correct position, nor can non-contiguous sentences be joined into a single quote.

That key facts equal the quote can be verified programmatically, but this cannot prove that the answer has retained all necessary conditions. Semantic review still requires reading the other paragraphs of the same article and related provisions to check qualifications, exceptions, negations, dates, and scope.

There have been two actual corrections:

- `gold-crd-withdrawal-refund` added paragraphs 2 and 3 of Article 13, retaining the conditions on additional delivery costs and deferred refunds, as well as the exception where the trader offers to collect the goods itself.
- `gold-sgd-two-year-liability` added paragraph 6 of Article 10, stating that the shorter period for second-hand goods must be permitted by Member States and agreed by both parties, and must not be less than one year.

### 8.3 refusal and evaluation boundaries

The six refusal questions concern the fixed compensation amount for flights, the VAT rate, the statutory annual interest rate for refunds, the upper limit of fines in Germany, the number of days to bring a lawsuit after refusing repair, and the minimum insurance for package travel. The scope of judgment is the complete five frozen texts, including preambles, annexes, and footnotes, not just one document.

For refusal questions, `evidence` and `key_facts` are both empty, and the reason is written in the English `refusal_reason`. The presence of related keywords does not mean the answer is available, nor does the failure to find a certain word alone prove that a refusal is warranted.

The question set was frozen before consulting the four sets of formal retrieval results. C submits `question` to the system, letting the system retrieve and answer on its own; the reference answers, key facts, and reference evidence are retained for scoring comparison. The four runs produced 120 per-question records, which C still needs to actually execute.

## 9. Command-line entry points and error behavior

The following commands are all run from the project root using the Python at `.venv`.

| Command argument | Behavior | Writes artifacts |
| --- | --- | --- |
| `scripts/process_documents.py --document-id <id>` | Process one registered document | Yes |
| `scripts/process_documents.py --all` | Process all documents in the manifest in stable ID order | Yes |
| `scripts/validate_data.py --scope corpus` | Verify the full source set, processed artifacts, structure, and spans | No |
| `scripts/validate_data.py --scope corpus --document-id <id>` | Verify one document | No |
| `scripts/export_corpus.py` | Verify the five official IDs, then export the official package and validate it | Yes |
| `scripts/build_gold.py` | Regenerate the question set and manifest from the fixed question definitions | Yes |
| `scripts/validate_data.py --scope eval` | Validate the question set, official version, evidence, and question set manifest | No |

For cleaning, `--all` and `--document-id` are mutually exclusive and one is required. Full-corpus validation processes by source registration; extra unregistered txt / JSON files are reported; copies in the sample package do not count as duplicate official documents.

`--data-root` is provided by the cleaning and validation scripts to specify an alternative project data root directory; exception tests use temporary copies accordingly. The official export CLI does not have this command-line option; tests inject a temporary root directory via a function parameter. Question set validation does not accept `--document-id`.

If the batch manifest structure is invalid, it fails before processing; a single snapshot hash mismatch or expected parse failure counts toward the failure count, and processing continues for the remaining documents. If any failures exist, it ultimately exits non-zero and reports `result=failed`. Callers should check the final exit code and summary; seeing that one document has been output is not sufficient to conclude the whole batch succeeded.

## 10. Normal loading and handoff

### 10.1 B: Load the official corpus

The code below runs from the project root and does not bypass the package initialization of `app.retrieval`:

```python
from pathlib import Path
from app.retrieval.types import formal_loader

data_dir = Path("data/formal_corpus")
version = "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
documents = formal_loader(data_dir)(version)
assert len(documents) == 5
assert sum(len(doc["articles"]) for doc in documents) == 121
```

B builds four index groups—F400, S400, F800, S800—from the same version. 400/800 is the Python character count. A provides the frozen input and traceable positions; the official index, model, and retrieval quality are the responsibility of B's implementation and validation.

### 10.2 C: Load the scoring comparison

```python
import hashlib
import json
from pathlib import Path

manifest = json.loads(Path("data/eval/manifest.json").read_text(encoding="utf-8"))
raw = Path("data/eval/gold.jsonl").read_bytes()
assert hashlib.sha256(raw).hexdigest() == manifest["gold_version"]
cases = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
assert len(cases) == 30
```

C fixes both the corpus and the question set version. Answerable hits and answer metrics are counted over 24 questions, and the 6 refusal questions are counted separately; the specific per-question scoring and official results will be recorded after C actually runs. Delivering the fields does not mean C's end-to-end interface has been accepted.

### 10.3 Integration sample

`data/sample_corpus` contains only the first document, and `data/eval/sample.jsonl` has three integration questions bound to the sample version. They are retained for early integration and regression and are not changed to the official five-document version. Formal evaluation uses `gold.jsonl`.

## 11. Environment, tests, and existing evidence

The local verification environment is Windows PowerShell, Python 3.13.11, with `.venv/Scripts/python.exe` invoked explicitly. A's command line uses Beautiful Soup; the retrieval service imported by the normal package also imports `filelock`. Versions are registered in `requirements.txt` and `requirements-b.txt` respectively; installation steps are in [A测试.md](./A测试.md).

| Test module | Current item count | Main coverage |
| --- | ---: | --- |
| `tests.test_corpus_batch` | 8 | Arguments, empty manifest, duplicate IDs, missing snapshots, hash mismatch, partial failure, artifact inventory, section mirroring |
| `tests.test_corpus_freeze` | 6 | Missing processed artifacts, modified official snapshots, version mismatch, duplicate export, small-corpus compatibility, missing / extra official items rejection |
| `tests.test_gold_eval` | 5 | Evidence attribution, duplicate attachment clause numbers, excerpt mismatch, refusal evidence, duplicate question numbers, version / hash, CRLF, arguments |
| Total | 19 | Tests create exceptions in temporary copies or in-memory objects |

Locally, cleaning, official export, question set generation, both types of validation, and the above 19 tests have actually been rerun. The final recorded hashes of the 44 protected files remain consistent, and both the official package and the sample package load successfully. Detailed byte hashes and commands are in [Final validation record](./artifacts/a_review/a_final_validation.md).

Team members should rely on the exit codes and output from their own runs; viewing existing local reports is not a substitute for running the tests on another computer.

## 12. Review status and maintenance rules

| Scope | Current status | Follow-up owner |
| --- | --- | --- |
| Source, full text, structure, version, and evidence positions | Program checks passed, with AI-assisted source review | A maintains and revises |
| Official source text, reference answers, and browser visual inspection | 2026-11-19 confirmed passed by the A lead, no issues found | A maintains the review conclusion and rechecks after revisions |
| Embedding, indexing, and semantic retrieval of the official corpus | Not part of A's data validation pass conclusion | B formal integration |
| Generated answers, citation support, four-group scoring, and page integration | Not part of this A test result | C formal integration and scoring |

The existing AI-assisted review used HTML DOM, frozen body text, and chunk comparison. Manual review and browser visual inspection of the five local HTML files were confirmed passed by the A lead on 2026-11-19, with no issues found. The statement in each AI report that "no browser visual inspection was performed at the time" is retained as a historical record. The box style in Attachment I becomes plain numbers after cleaning, and the related filling instructions are still retained; when citing placeholder information, the instructions must be consulted as well. The corpus is the saved original published version and must not be supplemented according to later merged-text rules.

Follow this order when maintaining data: locate the issue and record the document ID / clause or question number → modify the corresponding source or fixed definition → regenerate the affected data → validate → update the content version and review record → provide B and C with a clear old/new version relationship. Do not change only the question set JSONL while keeping the old generation script, and do not update only the manifest hashes to mask errors in body text, spans, or evidence.

This document and `A测试.md` are the entry points for implementation and team member operations; [Requirements document](./A部分需求与开发顺序.md) retains the acceptance requirements, [Phase record](./A部分阶段开发记录.md) retains the historical process, and [Delivery notes](./A部分交付说明.md) summarizes the current deliverables. The current version in each document is subject to the official manifest and the actual files.
