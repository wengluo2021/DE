# Step 3 sample handover notes

The sample questions were generated with AI assistance and reviewed against the accepted cleaned body text. Review date: 2026-11-19. Field compatibility was corrected on the same day.

This is a single-document integration sample, marked as `integration_sample`. It is not a frozen version of the five official corpus documents, and it cannot replace the future `data/eval/gold.jsonl`.

The accepted files were not modified:

| File | SHA-256 |
| --- | --- |
| `data/raw/eu_consumer_rights_2011_83.html` | `7812747113a74ef3a2b2e8d2d3fb067ed416280f415aed76dc255083b54e892e` |
| `data/processed/eu_consumer_rights_2011_83.txt` | `75acf22af53bf1878fe2750757b5ecd5c1230236aaab4fc543c1d029b3bf5689` |
| `data/processed/eu_consumer_rights_2011_83.json` | `f7ed11c4e7817cc58c23498ef1b87b87e885996f8a075a02365782e44b84829a` |
| `artifacts/a_review/eu_consumer_rights_2011_83_review.md` | `0af5fe7c011fb7ddffe21f910cd702c362c4497a890f7a759c70b3604544391f` |

## Sample version

`corpus_version`：

`41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50`

The sample questions, `data/eval/sample_manifest.json`, and `data/sample_corpus/manifest.json` use the same value.

The previous adaptation was missing `label`, `chapter`, and `section` that B needs to read; its version was `c3ebeccff2269286fe939a266a899919fa07b5d3d5300362de8d53be959fc225`. After the fields were added, the `articles` structure hash changed from `fecd18aeec4c9b308331e148e6a801aea18ceb1d8543c858bbee00980565ee00` to `128d842ba9798cf099b4c65d5401ad0a0324f5d5f1efbfe92f139c3fcb82387a`. The file hash of the adaptation JSON is now `1c5c2ae09d58423bc63d084390b25030051495b7b4fb3aeb056e6335f506290f`.

The calculation method follows `app/retrieval/types.py`'s `canonical`, `digest`, and `formal_loader`:

1. `text_sha256` is the SHA-256 of the UTF-8 bytes of the cleaned full text, and still equals the accepted txt.
2. `structure_sha256` is the canonical JSON SHA-256 of the complete `articles` array after the fields were added. The canonical JSON uses `sort_keys=True`, `separators=(",", ":")`, and `ensure_ascii=False`.
3. The version materials contain only `parser_version` (`eurlex_html_v1`) and the document list sorted by `document_id`. Each item takes only `document_id`, `title`, `issuer`, `source_url`, `published_at`, `effective_at`, `raw_sha256`, `text_sha256`, and `structure_sha256`.
4. First obtain `corpus_version`, then write the adaptation document, and finally compute `processed_sha256`.

The materials do not contain `corpus_version` itself, nor the processed JSON file hash, registration time, or review time. `published_at` is the original publication date `2011-11-22`. `effective_at` is the effective date `2011-12-12` of that original text, not the applicable date `2014-06-13` in Article 28. The full date remains in `source_fields.dates` of the adaptation JSON.

Re-running `scripts/export_sample.py` re-exports from the accepted JSON, and the version and the above artifact hashes remain consistent.

## A's JSON and B's loading format

The accepted `data/processed/eu_consumer_rights_2011_83.json` continues to serve as the structural source of truth. B's `formal_loader` reads the adaptation document in the sample directory.

| Field read by B | Adaptation method |
| --- | --- |
| String `title`, `issuer`, `source_url` | Title, institution, and official URL from the accepted source record |
| Top-level `text` | Accepted cleaned full text |
| `raw_path`, `raw_sha256` | Point to the HTML copy in the sample directory; hash is the same as the original snapshot |
| `label` | `Article {article_number}`, e.g. Article 18 is `Article 18` |
| `chapter` | Equal to the original `chapter_id`, e.g. `eu_consumer_rights_2011_83:chapter:IV` |
| `section` | Equal to the original `section_id`; this file has no sections, so it is `null` |
| `chapter_id`, `section_id` | Original fields retained |

For the main provision of Article 35, `article_id`, the body text, body blocks, and `start`, `end` are the same as in the accepted JSON. Mapping example for Article 18:

| Field | Value |
| --- | --- |
| `article_id` | `eu_consumer_rights_2011_83:article:18` |
| `label` | `Article 18` |
| `chapter` / `chapter_id` | `eu_consumer_rights_2011_83:chapter:IV` |
| `section` / `section_id` | `null` |
| `start`、`end` | `[81963, 83581)` |

## Directories for B and C

```text
data/sample_corpus/manifest.json
data/sample_corpus/raw/eu_consumer_rights_2011_83.html
data/sample_corpus/processed/eu_consumer_rights_2011_83.json
data/eval/sample.jsonl
data/eval/sample_manifest.json
scripts/export_sample.py
```

When `formal_loader` sees a relative path starting with `data/`, it removes the first segment and appends the rest to the passed data directory. Therefore, when the data directory is set to `data/sample_corpus`, it reads the copy in the sample directory, not the accepted file in `data/processed/`.

B's loading entry point:

```python
from pathlib import Path
from app.retrieval.types import formal_loader

data_dir = Path(r"D:\gitcode\Edit\DE\data\sample_corpus")
version = "41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50"
documents = formal_loader(data_dir)(version)
```

`from app.retrieval.types import formal_loader` and `from app.retrieval.service import RetrievalService` execute normally in the current environment. The earlier issue of the missing `filelock` has been resolved.

The returned document contains `document_id`, `corpus_version`, `title`, `text`, `articles`, and `chapters`. Provision ranges are in Python characters `[start, end)`. Structural splitting reads `chapter` and `section` to determine chapter boundaries. Retrieval result assembly reads `label` to generate `article_labels`.

The four chunking groups were actually run in memory; the full text was covered contiguously, chunk lengths did not exceed their respective limits, chunk text equals the original slice, and provision association was computed by range intersection:

| Condition | Chunk count |
| --- | ---: |
| f400 | 259 |
| s400 | 365 |
| f800 | 130 |
| s800 | 163 |

No embeddings were downloaded this round, and no real vector index was built. When `RetrievalService._search` was called with a test stub, it returned one hit for Article 18, with `article_labels` as `["Article 18"]`, and no `KeyError` occurred. This result only verifies interface compatibility; it is not a semantic retrieval result.

When C reads the original text, it uses `text` from the loading result, or the accepted txt; the two have identical content:

```python
quote = document["text"][evidence["start"]:evidence["end"]]
```

`document_id` must be `eu_consumer_rights_2011_83`, and `quote` must equal `quote` in the evidence.

## Sample question fields

`data/eval/sample.jsonl` has 3 rows in total. The file SHA-256 is `63f14226611fc7fbda5d2996c37ebe5f97f9ee237e7cbdc476fb14f7dfbc1126`. The questions, reference answers, key facts, refusal reasons, and evidence content were not changed; only `corpus_version` was synchronized.

Each row contains `case_id`, `corpus_version`, `question`, `question_type`, `should_refuse`, `reference_answer`, `key_facts`, `evidence`, `refusal_reason`.

Each evidence segment of an answerable question contains `document_id`, `article_id`, `start`, `end`, `quote`. `quote` is excerpted from the cleaned txt, and all lengths are less than 400 Python characters. For refusal questions, `evidence` is an empty list.

| case_id | Type | Provision | Range |
| --- | --- | --- | --- |
| `sample-2011-83-delivery-deadline` | Answerable from a single article | `article:18` | `[81983, 82251)` |
| `sample-2011-83-digital-withdrawal` | Answerable from two evidence segments | `article:9`, `article:16` | `[69452, 69734)`, `[81214, 81431)` |
| `sample-2011-83-flight-compensation` | Should refuse | None | None |

The evidence for Article 16 (m) falls within Article 16's own span. The attachment also contains numeric content statements, but this excerpt does not switch to the attachment location.

## Verification

Complete using `D:\gitcode\Edit\DE\.venv\Scripts\python.exe`:

```powershell
.\.venv\Scripts\python.exe scripts\export_sample.py
```

Then call `formal_loader` and `RetrievalService` via a normal package import, and run the export script again.

- The three-line JSONL is readable, question numbers are unique, and the version matches both manifests.
- All 35 items have `label`, `chapter`, and `section`; the original `chapter_id`, `section_id`, body text, and spans are unchanged.
- Evidence spans fall within the declared articles, and the slices equal `quote`.
- `formal_loader` loads successfully with the new version.
- The f400, s400, f800, and s800 chunks pass coverage, length, slice, and article-association checks.
- The `article_labels` read path returns `Article 18`.
- Two consecutive exports produce identical versions and artifact hashes.
- The hashes of the accepted HTML, txt, structure JSON, source records, and source-text review report remain unchanged.

## Unresolved

- The remaining four documents and the formal 30 questions have not been done yet. The formal corpus version still awaits freezing in steps 4 and 5.
- No Chroma index was built this round, and no real semantic retrieval, hit rate, or answer scoring was run.

The sample is now ready to hand to B and C for joint debugging of loading, chunking, and evidence mapping. Real vector retrieval still requires a database to be built later.
