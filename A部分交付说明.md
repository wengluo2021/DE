# Part A delivery notes

Record date: 2026-11-19. Project directory: `D:\gitcode\Edit\DE`. Interpreter: `D:\gitcode\Edit\DE\.venv\Scripts\python.exe`, Python 3.13.11, consistent with `.python-version`.

## 1. Delivery scope and current status

A delivers the original published-version snapshots, cleaned full text, chapter and article locations, formal corpus package, and 30 English standard questions for five EUR-Lex English consumer rights regulations. B builds the index using the formal corpus package, and C uses the formal question set for scoring comparison.

Programmatic validation, repeated generation, load verification, manual review, and browser visual inspection have been completed. The A lead confirmed acceptance on 2026-11-19, with no issues found. Detailed commands and hashes are in `artifacts/a_review/a_final_validation.md`. The formal corpus's vector index, semantic retrieval, LLM answers, and four-condition scoring will be subsequently verified by B and C.

## 2. Five documents and version scope

All five are registered as `original_publication`. What is saved is the original text of the Official Journal; the consolidated amended versions linked separately on the pages did not enter the cleaned body text.

| document_id | CELEX | Regulation |
| --- | --- | --- |
| eu_consumer_rights_2011_83 | 32011L0083 | Directive 2011/83/EU, consumer rights |
| eu_sale_of_goods_2019_771 | 32019L0771 | Directive (EU) 2019/771, sale of goods |
| eu_digital_content_2019_770 | 32019L0770 | Directive (EU) 2019/770, digital content and digital services |
| eu_unfair_practices_2005_29 | 32005L0029 | Directive 2005/29/EC, unfair business practices |
| eu_unfair_terms_93_13 | 31993L0013 | Council Directive 93/13/EEC, unfair terms |

The snapshot is saved by the browser. The save time, HTTP status, and response time are null in the source manifest, and it is stated that they cannot be verified from the snapshot.

## 3. Directory and file purposes

| Path | Purpose |
| --- | --- |
| `data/sources.json` | Five sources, versions, dates, snapshot paths, and SHA-256 |
| `data/raw/` | Five official HTML snapshots. Filenames containing spaces are read according to the manifest |
| `data/processed/*.txt` | Accepted cleaned full text, UTF-8, LF, one trailing newline |
| `data/processed/*.json` | Accepted structure. Intervals are Python `[start, end)`, corresponding to the txt of the same name |
| `data/corpus_manifest.json` | A's project-level freeze manifest, with paths relative to the project root |
| `data/formal_corpus/` | B's official corpus package. Contains `manifest.json`, `raw/`, `processed/` |
| `data/eval/gold.jsonl` | 30 official questions, one per line |
| `data/eval/manifest.json` | Question set version, corpus version, question count, and coverage |
| `data/sample_corpus/` | Integration sample containing only the first document, using its own corpus version |
| `data/eval/sample.jsonl` | Three sample questions, not the official 30 questions |
| `scripts/process_documents.py` | Clean HTML from the source manifest |
| `scripts/export_corpus.py` | Generate the official package. The command line first checks whether all five official documents are present |
| `scripts/build_gold.py` | Extract evidence from the frozen body text and generate the official question set |
| `scripts/validate_data.py` | Perform corpus or question set validation only |
| `artifacts/a_review/` | Per-document review, freeze, question set, and final validation records |

## 4. Versions

| Name | Value | Read location |
| --- | --- | --- |
| corpus_version | `794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795` | `data/formal_corpus/manifest.json` and `data/corpus_manifest.json` |
| gold_version | `9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d` | `data/eval/manifest.json`. It equals the file SHA-256 of `gold.jsonl` and is not written into the jsonl |
| Sample corpus_version | `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50` | `data/sample_corpus/manifest.json` |

The official package and the sample package have different versions. Official Q&A and official scoring use the unified corpus version in the first row.

## 5. Environment and dependencies

Run in the project root directory, using the `.venv` interpreter above.

- Cleaning HTML uses `beautifulsoup4==4.15.0` and `soupsieve==4.1.2` in `requirements.txt`.
- `formal_loader` is located in `app.retrieval.types`. Importing `app.retrieval` loads the retrieval service; the current environment also uses `filelock==4.2.10` already installed in `requirements-b.txt`.
- No new dependencies were added this round, and `pip install` was not executed.

## 6. Reproducing from existing snapshots

The three commands below rewrite files. After actually rerunning them this round, the artifact byte hashes were identical to those before the run.

```powershell
Set-Location 'D:\gitcode\Edit\DE'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\process_documents.py' --all
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\export_corpus.py'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\build_gold.py'
```

The order is cleaning, official export, question set generation. Export reads the accepted txt and JSON; question set generation reads the official package. Before writing `data/formal_corpus` and `data/corpus_manifest.json`, `export_corpus.py` requires the source manifest to contain exactly the five `document_id` from section 2. If documents are missing or extra, the exit code is 1 and `result=ok` is not printed.

`scripts/export_sample.py` rewrites the single-document sample package and the sample question manifest. It was not run this round. The official delivery does not use the sample version.

## 7. Routine validation and loading

The commands below only check; they do not generate corpus or question sets.

```powershell
Set-Location 'D:\gitcode\Edit\DE'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope corpus
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope eval
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' -m unittest tests.test_corpus_batch tests.test_corpus_freeze tests.test_gold_eval
```

On success, corpus validation prints `documents=5`, `main_articles=121`, `result=ok`. Question set validation prints `questions=30 answerable=24 refusal=6`, `result=ok`.

B's loading method:

```python
from pathlib import Path
from app.retrieval.types import formal_loader

data_dir = Path(r"D:\gitcode\Edit\DE\data\formal_corpus")
corpus_version = "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
documents = formal_loader(data_dir)(corpus_version)
```

`formal_loader` reads `data_dir/manifest.json`. Paths in the manifest that start with `data/` have the first segment removed and are then joined under `data_dir`.

## 8. Final verification and review status

Results for this round:

- The exit codes for corpus validation and question set validation are both 0.
- The three A-part test modules total 19 items, with result `OK`. The failure text printed by exception cases is the expected output being asserted.
- After rerunning cleaning, official export, and question set generation, the hashes of 44 protected files were unchanged.
- Both the official package and the sample package can be loaded according to their respective versions. The loaded full text, article IDs, intervals, `label`, `chapter`, and `section` are consistent with the accepted data.
- 42 segment evidence length is 68–393. The refund question retains Article 13, paragraphs 2 and 3; the two-year liability period question retains the second-hand goods exception in Article 10, paragraph 6.

Review layering:

- The program completes source correspondence, file hashes, structure IDs, citations, character ranges, question counts, evidence slices, and version binding.
- AI wrote five document reviews against the HTML DOM and frozen body text, and a question-set review against the slices. Evidence was captured by the program.
- Human review and browser visual inspection are complete. Lead A confirmed and approved on 2026-11-19, with no issues found.
- The per-document AI reports still retain "no browser visual inspection was performed at the time." Those are records of those rounds; the current conclusion is based on the human confirmation above.
- Slice consistency only shows that the excerpt maps back to the frozen body text; it cannot be treated as answer accuracy.

## 9. Known limitations and unfinished items

- The corpus is the original published version, not a later consolidated revision.
- The snapshot's save time, HTTP status, and response time remain null.
- Browser visual inspection was confirmed and approved by Lead A on 2026-11-19.
- There is no vector index, embedding download, real semantic retrieval, LLM answer, or four-group scoring.
- C's Q&A interface has not yet been tested end-to-end with these 30 formal questions. This document only delivers the question-set fields and does not record that interface as passed.
- This round did not execute `git add`, `commit`, or `push`.

## Handoff to B

- Set `data_dir` to `data/formal_corpus`.
- Use `formal_loader` to read `manifest.json` in the package; use the unified `corpus_version` above as the request version.
- Each document's `text` is the full cleaned body text. The main provisions are in `articles`.
- `article_id` is a stable ID. `label` is `Article {article_number}`.
- `chapter` corresponds to accepted `chapter_id`, and `section` corresponds to `section_id`. It is null when there is no chapter or section.
- Character ranges are Python `[start, end)`, satisfying `text[start:end]` equal to that provision or evidence text.
- The fourth document has two sections. Article 5 belongs directly to Chapter 2, and `section` is null. Articles 6 and 7 belong to Section 1, and Articles 8 and 9 belong to Section 2.
- Sample package `data/sample_corpus` is only for earlier integration testing; its version is `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50`. The formal index uses the unified version of the five documents.

## Handoff to C

- The formal question set is `data/eval/gold.jsonl`, and the manifest is `data/eval/manifest.json`.
- Always use `corpus_version=794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795` and `gold_version=9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d`.
- What is submitted to the system is `question`. `reference_answer`, `key_facts`, and `evidence` are used for scoring comparison, not as system input.
- There are 24 questions with `should_refuse` set to false, and 6 questions with it set to true. For refusal questions, `evidence` and `key_facts` are empty, and the reason is in `refusal_reason`.
- For answerable questions, `key_facts` equals the corresponding `evidence.quote`. The evidence includes `document_id`, `start`, `end`, `quote`, and `article_id` or `structure_id`.
- Question types are `single_article` 13 questions, `multi_evidence` 11 questions, and `unanswerable` 6 questions.
- `data/eval/sample.jsonl` are three integration-test sample questions bound to the sample corpus version; they do not replace the formal question set.
- These 30 questions have not yet been run against C's actual interface. The field descriptions must not be taken as proof that interface compatibility has passed.
