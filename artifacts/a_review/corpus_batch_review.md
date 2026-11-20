# Batch cleaning and full validation of the five corpora

Record date: 2026-11-19. The review method was command output, byte hashes, and standard-library unit tests. No browser visual check was performed this round.

Current status: the five documents and batch validation are complete; freezing the official corpus version is pending.

This round did not generate `data/corpus_manifest.json`, did not write a new corpus version into accepted artifacts, did not write the official 30 questions, and did not process the vector store. `git add`, `commit`, and `push` were not executed.

## Batch cleaning

`scripts/process_documents.py` now requires choosing one of `--document-id` and `--all`; the two parameters are mutually exclusive. `--all` reads only `data/sources.json`, sorts by `document_id`, and does not scan `data/raw`. Paths use the relative paths in the manifest directly.

Preflight covers manifest structure, document ID format and uniqueness, snapshot paths, and the SHA-256 field. An empty manifest, duplicate IDs, invalid IDs, missing files, or hash mismatches all report the file and the reason. Manifest structure errors terminate before processing. A snapshot or cleaning failure for a single document counts toward the failure count, and the remaining documents continue processing. As long as the failure count is greater than 0, the batch prints `result=failed` and exits non-zero without printing `result=ok`.

The optional `--data-root` is used only to point exception tests at a temporary copy; the default remains the project root. This parameter was not passed in the official run.

## Full-corpus validation

Without `--document-id`, `scripts/validate_data.py --scope corpus` validates all documents in the manifest. With `--document-id`, it still validates only one. `--data-root` is retained.

Full mode reuses the per-document range checks and verifies:

- Every document in the manifest has `data/processed/<id>.txt` and `data/processed/<id>.json`.
- Unregistered txt or json files of the same kind in `data/processed` are reported.
- `data/sample_corpus` is not included in duplicate-document detection.
- The source record, the document ID in the structure JSON, the snapshot path, and the snapshot hash are consistent.
- `clean_text_path` points to that document's own body text.
- Structure definition IDs are unique across the entire corpus, and references among chapters, sections, and articles can be resolved.
- A section that is stored both within a chapter and at the top level in `sections` is counted as a definition only once.

## Per-document results

The order follows `document_id`. The main article total is the sum of the actual `article` counts for each document, which is 35 + 27 + 27 + 21 + 11 = 121.

| Order | Document ID | Chapters | Main articles | Preamble | Attachments | Footnotes | Validation offset_checks |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | eu_consumer_rights_2011_83 | 6 | 35 | 67 | 2 | 23 | annex=2 article=35 block=418 chapter=6 footnote=23 preamble=1 recital=67 signature=1 table=2 table_row=80 title=1 |
| 2 | eu_digital_content_2019_770 | 0 | 27 | 87 | 0 | 23 | article=27 block=261 footnote=23 preamble=1 recital=87 signature=1 title=1 |
| 3 | eu_sale_of_goods_2019_771 | 0 | 27 | 72 | 1 | 10 | annex=1 article=27 block=273 footnote=10 preamble=1 recital=72 signature=1 table=1 table_row=48 title=1 |
| 4 | eu_unfair_practices_2005_29 | 4 | 21 | 25 | 2 | 26 | annex=2 article=21 block=277 chapter=4 footnote=26 preamble=1 recital=25 section=2 signature=1 title=1 |
| 5 | eu_unfair_terms_93_13 | 0 | 11 | 24 | 1 | 4 | annex=1 article=11 block=91 footnote=4 preamble=1 recital=24 signature=1 title=1 |

The first `process_documents.py --all` exited with code 0 and output `batch_documents=5`, `succeeded=5`, `failed=0`, `result=ok`.

`validate_data.py --scope corpus` exited with code 0 and output `documents=5`, `main_articles=121`, `result=ok`. Standard error was empty.

## Baseline and post-run hashes

The byte hashes of the 10 artifacts recorded before the run are the same as the hashes after the first batch cleaning, the second batch cleaning, and the two subsequent single-document cleanings.

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| eu_consumer_rights_2011_83.txt | 75acf22af53bf1878fe2750757b5ecd5c1230236aaab4fc543c1d029b3bf5689 | 103799 |
| eu_consumer_rights_2011_83.json | f7ed11c4e7817cc58c23498ef1b87b87e885996f8a075a02365782e44b84829a | 464555 |
| eu_digital_content_2019_770.txt | 6e251e53b94cb4e793d9cd32889a0f70b7e62d7399eacc15197f37bb132ac3bf | 118158 |
| eu_digital_content_2019_770.json | 3d7b88ac3b35365986c18970dfc24cdf6b1574f701c13c350efe7466e5e366ab | 409690 |
| eu_sale_of_goods_2019_771.txt | d3076ba5236d6e7aad6ba30ae8b8d4b17af14fa148f7abc42cadd96764498ad4 | 89977 |
| eu_sale_of_goods_2019_771.json | ec42ea4dbad2a165bfd409f50c21fc10620ef4ca9b17d8028e5c1885570b4d6c | 343414 |
| eu_unfair_practices_2005_29.txt | 7bc191bd5b55af42a179d95d98b1e7c2aa603509941065605b4ba175eb54f10b | 59599 |
| eu_unfair_practices_2005_29.json | 1f21061ca7b3f46f8cd2a949c722b86dbcdac0864c95281291cf037fad40c200 | 270853 |
| eu_unfair_terms_93_13.txt | bf518901d6a71d5753ec99ed0b5b13025f5bf136782594a0dbaf8263e376a401 | 20868 |
| eu_unfair_terms_93_13.json | c4d387298a543eb545a91cec522662b77473a6c79c7ee27c450818f17df29893 | 86075 |

The historical hash `9e57f3f501ec37583d36d273be66aa2ca5cf5d573696ab39ab2ac1523e32e22f` of the fifth JSON predates the correction to the rule description, and this round did not roll it back.

Hashes of unchanged files:

| File | SHA-256 |
| --- | --- |
| data/sources.json | 6a7a20ff4c9ea87bb940a066e8fdf08b285458fc9208b6b231dcf8e99fa5bad9 |
| data/raw/Unfair Terms.html | 6c700ae54d53f3dc3ece8d226d18471ac905eff42a7cb4d4874e2e56acaff707 |
| data/eval/sample.jsonl | 63f14226611fc7fbda5d2996c37ebe5f97f9ee237e7cbdc476fb14f7dfbc1126 |
| data/eval/sample_manifest.json | f86266512cef7f7385c9e122de488f0a0f6e79d7f5b5a40968043d06c51896c7 |
| data/sample_corpus/manifest.json | 5fa36813a51dde8839b4faafb56f57ba82f9e39f1e669e5463f9842414dbabb1 |
| data/sample_corpus/processed/eu_consumer_rights_2011_83.json | 1c5c2ae09d58423bc63d084390b25030051495b7b4fb3aeb056e6335f506290f |

The sample version is still `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50`.

## Actual commands

```powershell
Set-Location 'D:\gitcode\Edit\DE'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\process_documents.py' --all
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope corpus
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\process_documents.py' --all
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\process_documents.py' --document-id eu_unfair_terms_93_13
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope corpus --document-id eu_unfair_terms_93_13
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\process_documents.py' --document-id eu_consumer_rights_2011_83
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope corpus --document-id eu_consumer_rights_2011_83
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' -m unittest tests.test_corpus_batch
```

Both `--all` runs used `succeeded=5`, `failed=0`, `result=ok`, with exit code 0. The two single-document cleanings and validations both exited with code 0, and the single-document validation output `result=ok`. The ten artifact hashes are unchanged after repeated runs.

## Exception tests

`tests/test_corpus_batch.py` uses the standard library `unittest`. The exception cases only read and write to a temporary directory; the official `data/` is not involved in these cases. The `python -m unittest tests.test_corpus_batch` result is `Ran 8 tests`, `OK`.

Cases covered:

- When `--all` and `--document-id` are both given, and when both sides lack required parameters, argument parsing exits immediately.
- An empty source manifest reports `sources list is empty`, exits with code 1, and the output does not contain `result=ok`.
- A duplicate document ID reports `document_id eu_one is duplicated` and exits with code 1.
- When the original file referenced by the manifest does not exist, it reports `does not exist` and exits with code 1.
- When one snapshot hash does not match, it reports `snapshot sha256 mismatch`, exits with code 1, and the batch is not `result=ok`.
- When both snapshots are valid and cleaning one of them throws a failure, it outputs `succeeded=1`, `failed=1`, `result=failed`, and does not include `result=ok`.
- When a registered body is missing, while `data/processed` contains an unregistered json and `data/sample_corpus` contains a copy with the same name, it reports the missing file and the unregistered file, and does not count the sample copy as a duplicate document.
- A section within a chapter and the top-level `sections` mirror form only one structure definition; an article ID that is both a definition and a reference is not therefore treated as a duplicate definition.
