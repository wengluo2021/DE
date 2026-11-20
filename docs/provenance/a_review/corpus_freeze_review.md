# Official corpus freeze and delivery

Record date: 2026-11-19. The review method was a normal import of `formal_loader`, file byte hashes, and standard-library unit tests. This round did not perform a browser visual check, and did not build a vector index or run semantic retrieval.

The acceptance requirements for step 4 have been met: the five documents can be traced from the cleaned body back to the official snapshots, the file hashes can be verified by the loader, and repeated exports produce the same version without creating duplicate documents. B can load this frozen version by treating `data/formal_corpus` as `data_dir`. The official 30 questions and the vector store have still not been started.

Unified `corpus_version`:

`794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795`

The single-document sample version remains `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50`, and no accepted JSON was written.

## Responsibilities of the two manifests

| File | Read by | Path base |
| --- | --- | --- |
| `data/corpus_manifest.json` | A's freeze record | Relative to the project root. For example, the accepted body is `data/processed/eu_consumer_rights_2011_83.txt` and the official package copy is `data/formal_corpus/raw/...` |
| `data/formal_corpus/manifest.json` | B's `formal_loader` | B sets `data_dir` to `data/formal_corpus`. The `data/raw/...` and `data/processed/...` in the manifest have their leading `data/` removed and are then joined to this directory |

`formal_loader` does not read `data/corpus_manifest.json`. The two manifests and the five adaptation JSON files use the same `corpus_version`.

## Version and hash conventions

The calculation follows `app.retrieval.types`'s `canonical`, `digest`, and `formal_loader`:

1. `canonical` is `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`.
2. `digest` is the UTF-8 SHA-256 of this specification JSON.
3. `text_sha256` is the UTF-8 SHA-256 of the adaptation document `text`, equal to the file byte hash of the accepted txt.
4. `structure_sha256` is the `digest` of the `articles` array after adding `label`, `chapter`, and `section`. It is not the file hash of the accepted structure JSON.
5. The file hash of the accepted structure JSON is recorded separately as `accepted.structure_json_sha256`.
6. The version material contains only `parser_version` (`eurlex_html_v1`) and the document list sorted by `document_id`. Each item contains only `document_id`, `title`, `issuer`, `source_url`, `published_at`, `effective_at`, `raw_sha256`, `text_sha256`, `structure_sha256`.
7. First compute `corpus_version`, then write the adaptation document, and finally compute `processed_sha256`. The version material does not contain `corpus_version`, `processed_sha256`, registration time, or export time.

`published_at` takes `publication_date` from the accepted source. `effective_at` takes `entry_into_force_date` from the accepted source. No dates were inferred separately. The effective date of the fifth document remains the registered `1993-04-16`, and the applicable date remains null in `source_fields.dates.application_date`.

The `structure_sha256` of the first document is the same as in the single-document sample, because the provision adaptation rules are the same. The official version differs because the version materials include all five documents.

## Per-document results

The load result is 5 unique documents and 121 main provisions. 121 is obtained by adding 35 + 27 + 27 + 21 + 11. Each provision's `text` equals `clean_text[start:end]`, and `article_id`, `start`, and `end` are the same as in the accepted JSON. `label` is `Article {article_number}`. `chapter` equals `chapter_id`, and `section` equals `section_id`; when there is no chapter or section, it remains null.

| Document | Chapter | Section | Main provisions | published_at | effective_at | text_sha256 | structure_sha256 |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| eu_consumer_rights_2011_83 | 6 | 0 | 35 | 2011-11-22 | 2011-12-12 | 75acf22af53bf1878fe2750757b5ecd5c1230236aaab4fc543c1d029b3bf5689 | 128d842ba9798cf099b4c65d5401ad0a0324f5d5f1efbfe92f139c3fcb82387a |
| eu_digital_content_2019_770 | 0 | 0 | 27 | 2019-05-22 | 2019-06-11 | 6e251e53b94cb4e793d9cd32889a0f70b7e62d7399eacc15197f37bb132ac3bf | 8371031191de166e16027e6b9685cbf88f9dbae32f8a770f15938d56f62ad105 |
| eu_sale_of_goods_2019_771 | 0 | 0 | 27 | 2019-05-22 | 2019-06-11 | d3076ba5236d6e7aad6ba30ae8b8d4b17af14fa148f7abc42cadd96764498ad4 | 3a6ae97d1c9b6e947baa3238299e9848da83d8e502ea9a1c3d97babfbebb0728 |
| eu_unfair_practices_2005_29 | 4 | 2 | 21 | 2005-06-11 | 2005-06-12 | 7bc191bd5b55af42a179d95d98b1e7c2aa603509941065605b4ba175eb54f10b | 2ddf7b21d7f381fcdd1cb4833d864a676c26ba97ddf7b875e0449629d7178ce9 |
| eu_unfair_terms_93_13 | 0 | 0 | 11 | 1993-04-21 | 1993-04-16 | bf518901d6a71d5753ec99ed0b5b13025f5bf136782594a0dbaf8263e376a401 | efb39df04a770128deb0d44a079d3979e912268a8d68dedfbd16c9e9d4ea02ba |

The fourth document retains two sections. The `chapter` of Article 5 is `eu_unfair_practices_2005_29:chapter:2`, and `section` is null, so it does not enter either section. Articles 6 and 7 belong to Section 1, and Articles 8 and 9 belong to Section 2.

## Official delivery file hashes

| File | SHA-256 |
| --- | --- |
| data/corpus_manifest.json | 3ecdec520cc259b876e65fc2fea492b956deaef941c9a46ba4c08b368b87bd4f |
| data/formal_corpus/manifest.json | 516d0aa17c2674ee57eadfbb73452140e88667a0e3c9c51d7028dd127f1fdb57 |
| data/formal_corpus/processed/eu_consumer_rights_2011_83.json | d1db1b2e0e85b5a9a62b40fc23a0974cd85d597167ccb9a0b654aea22b631e24 |
| data/formal_corpus/processed/eu_digital_content_2019_770.json | 4af53f1647e1eeed535c65d0abcf7802cd50f313e0fef0b98227ccb7cfbf9f79 |
| data/formal_corpus/processed/eu_sale_of_goods_2019_771.json | 3fcd40957992fa8693ecc91cdcad1ce7c23225a92a8809fc1dac20078febea77 |
| data/formal_corpus/processed/eu_unfair_practices_2005_29.json | 1af8f015d0fc8a62cfa40f87074fe3432d54d822b9e3c90f053151638c1fb4c3 |
| data/formal_corpus/processed/eu_unfair_terms_93_13.json | 0eb604ed2dad177ba4d9758607bac8fa691af95c8fac61015f8d925a17011827 |
| data/formal_corpus/raw/eu_consumer_rights_2011_83.html | 7812747113a74ef3a2b2e8d2d3fb067ed416280f415aed76dc255083b54e892e |
| data/formal_corpus/raw/Digital Content and Services.html | 83b8ec2ad8d5a293c278fcffc5add389425bd7c688f92bf110d4ce2b929826f2 |
| data/formal_corpus/raw/Sale of Goods.html | 4869ed74958ae7cc50897e502272cc103502bffd1722f4ed07ca1f7188bb16ac |
| data/formal_corpus/raw/Unfair Commercial Practices.html | 0d678d1bbd988c59b40ff6363f3d9b8370c34da7b3744395eb7147364a19c1cc |
| data/formal_corpus/raw/Unfair Terms.html | 6c700ae54d53f3dc3ece8d226d18471ac905eff42a7cb4d4874e2e56acaff707 |

The five raw copies have the same byte hashes as the official HTML in `data/raw/`. File names containing spaces were copied according to the source manifest; the browser resource directory was not scanned.

## Existing artifacts unchanged

Before and after export, the SHA-256 of the following 28 files are identical item by item: `data/sources.json`, the five official HTML files, the five pairs of accepted txt and JSON, the seven existing review reports, the three files of `data/sample_corpus/`, `data/eval/sample.jsonl`, and `sample_manifest.json`.

The full validation was rerun after freezing, with exit code 0 and output `documents=5`, `main_articles=121`, `result=ok`.

## Actual commands

```powershell
Set-Location 'D:\gitcode\Edit\DE'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\export_corpus.py'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\export_corpus.py'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope corpus
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' -m unittest tests.test_corpus_freeze
```

The `corpus_version` of all three exports are the values above, all exit codes are 0, and the output is `documents=5`, `main_articles=121`, `result=ok`. The byte hashes of the 12 official delivery files are identical in the second and third runs.

`python -m unittest tests.test_corpus_freeze` is `Ran 4 tests`, `OK`. Temporary copy coverage: missing accepted body text, modified raw hash in the official package, requested version inconsistent with the manifest, and manifest version inconsistent with the content fingerprint. When a file is missing, the exit code is 1 and the output does not contain `result=ok`. Official data did not participate in these test cases.

Normal loading uses `formal_loader` after package initialization, without substituting a test stub. The current environment can already import it, and no new dependencies were added in this round. `filelock` was installed previously and is still registered in `requirements-b.txt`.

```python
from pathlib import Path
from app.retrieval.types import formal_loader

data_dir = Path(r"D:\gitcode\Edit\DE\data\formal_corpus")
version = "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
documents = formal_loader(data_dir)(version)
```

## Not yet completed

- The official 30 questions, as well as `data/eval/gold.jsonl` and `data/eval/manifest.json`.
- Vector index, real semantic retrieval, and scoring.
- This round did not execute `git add`, `commit`, or `push`.
