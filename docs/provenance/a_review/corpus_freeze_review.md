# 正式语料冻结与交付

记录日期：2026-11-19。复核方式是 `formal_loader` 正常导入、文件字节哈希和标准库单元测试。本轮没有做浏览器视觉检查，也没有建立向量索引或运行语义检索。

第 4 步验收要求已经满足：五份文档能从清洗正文追溯到官方快照，文件哈希可由加载器核对，重复导出得到同一版本且不会产生重复文档。B 可以把 `data/formal_corpus` 当作 `data_dir` 加载这个冻结版本。正式 30 道题和向量库仍未开始。

统一 `corpus_version`：

`794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795`

单文档样本版本继续是 `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50`，没有写入已验收 JSON。

## 两份清单的职责

| 文件 | 谁读取 | 路径基准 |
| --- | --- | --- |
| `data/corpus_manifest.json` | A 的冻结记录 | 相对于项目根目录。例如已验收正文是 `data/processed/eu_consumer_rights_2011_83.txt`，正式包副本是 `data/formal_corpus/raw/...` |
| `data/formal_corpus/manifest.json` | B 的 `formal_loader` | B 把 `data_dir` 设为 `data/formal_corpus`。清单里的 `data/raw/...`、`data/processed/...` 会去掉开头的 `data/`，再拼到这个目录 |

`formal_loader` 不读取 `data/corpus_manifest.json`。两份清单和五份适配 JSON 使用同一个 `corpus_version`。

## 版本和哈希口径

计算沿用 `app.retrieval.types` 的 `canonical`、`digest` 和 `formal_loader`：

1. `canonical` 是 `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`。
2. `digest` 是这段规范 JSON 的 UTF-8 SHA-256。
3. `text_sha256` 是适配文档 `text` 的 UTF-8 SHA-256，等于已验收 txt 的文件字节哈希。
4. `structure_sha256` 是补上 `label`、`chapter`、`section` 之后的 `articles` 数组的 `digest`。它不是已验收结构 JSON 的文件哈希。
5. 已验收结构 JSON 的文件哈希单独记为 `accepted.structure_json_sha256`。
6. 版本材料只有 `parser_version`（`eurlex_html_v1`）和按 `document_id` 排序的文档列表。每项只含 `document_id`、`title`、`issuer`、`source_url`、`published_at`、`effective_at`、`raw_sha256`、`text_sha256`、`structure_sha256`。
7. 先算出 `corpus_version`，再写入适配文档，最后计算 `processed_sha256`。版本材料不含 `corpus_version`、`processed_sha256`、登记时间或导出时间。

`published_at` 取已验收来源里的 `publication_date`。`effective_at` 取已验收来源里的 `entry_into_force_date`。日期没有另行推断。第五份的生效日仍是已登记的 `1993-04-16`，适用日在 `source_fields.dates.application_date` 中保持 null。

第一份的 `structure_sha256` 与单文档样本相同，因为条文适配规则相同。正式版本不同，因为版本材料包含全部五份文档。

## 逐文档结果

加载结果是 5 个唯一文档、121 条主条文。121 由 35 + 27 + 27 + 21 + 11 相加得到。每条条文的 `text` 等于 `clean_text[start:end]`，`article_id`、`start`、`end` 与已验收 JSON 相同。`label` 为 `Article {条号}`。`chapter` 等于 `chapter_id`，`section` 等于 `section_id`；没有章或节时保持 null。

| 文档 | 章 | 节 | 主条文 | published_at | effective_at | text_sha256 | structure_sha256 |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| eu_consumer_rights_2011_83 | 6 | 0 | 35 | 2011-11-22 | 2011-12-12 | 75acf22af53bf1878fe2750757b5ecd5c1230236aaab4fc543c1d029b3bf5689 | 128d842ba9798cf099b4c65d5401ad0a0324f5d5f1efbfe92f139c3fcb82387a |
| eu_digital_content_2019_770 | 0 | 0 | 27 | 2019-05-22 | 2019-06-11 | 6e251e53b94cb4e793d9cd32889a0f70b7e62d7399eacc15197f37bb132ac3bf | 8371031191de166e16027e6b9685cbf88f9dbae32f8a770f15938d56f62ad105 |
| eu_sale_of_goods_2019_771 | 0 | 0 | 27 | 2019-05-22 | 2019-06-11 | d3076ba5236d6e7aad6ba30ae8b8d4b17af14fa148f7abc42cadd96764498ad4 | 3a6ae97d1c9b6e947baa3238299e9848da83d8e502ea9a1c3d97babfbebb0728 |
| eu_unfair_practices_2005_29 | 4 | 2 | 21 | 2005-06-11 | 2005-06-12 | 7bc191bd5b55af42a179d95d98b1e7c2aa603509941065605b4ba175eb54f10b | 2ddf7b21d7f381fcdd1cb4833d864a676c26ba97ddf7b875e0449629d7178ce9 |
| eu_unfair_terms_93_13 | 0 | 0 | 11 | 1993-04-21 | 1993-04-16 | bf518901d6a71d5753ec99ed0b5b13025f5bf136782594a0dbaf8263e376a401 | efb39df04a770128deb0d44a079d3979e912268a8d68dedfbd16c9e9d4ea02ba |

第四份保留两个节。第 5 条的 `chapter` 是 `eu_unfair_practices_2005_29:chapter:2`，`section` 为 null，不进入任一节。第 6、7 条属于 Section 1，第 8、9 条属于 Section 2。

## 正式交付文件哈希

| 文件 | SHA-256 |
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

五份 raw 副本与 `data/raw/` 中的官方 HTML 字节哈希相同。含空格的文件名按来源清单复制，没有扫描浏览器资源目录。

## 已有产物未变

导出前后，以下 28 个文件的 SHA-256 逐项相同：`data/sources.json`、五份官方 HTML、五对已验收 txt 和 JSON、七份已有复核报告、`data/sample_corpus/` 的三份文件、`data/eval/sample.jsonl` 和 `sample_manifest.json`。

全量校验在冻结之后重新运行，退出码 0，输出 `documents=5`、`main_articles=121`、`result=ok`。

## 实际命令

```powershell
Set-Location 'D:\gitcode\Edit\DE'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\export_corpus.py'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\export_corpus.py'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope corpus
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' -m unittest tests.test_corpus_freeze
```

三次导出的 `corpus_version` 都是上面的值，退出码都是 0，输出 `documents=5`、`main_articles=121`、`result=ok`。第二次和第三次的 12 个正式交付文件字节哈希一致。

`python -m unittest tests.test_corpus_freeze` 为 `Ran 4 tests`、`OK`。临时副本覆盖：缺少已验收正文、正式包 raw 哈希被改动、请求版本与清单不一致、清单版本与内容指纹不一致。缺文件时退出码为 1，输出不含 `result=ok`。正式数据没有参与这些用例。

正常加载使用包初始化后的 `formal_loader`，没有用测试桩代替。当前环境已能导入，本轮没有新增依赖。`filelock` 此前已安装，仍登记在 `requirements-b.txt`。

```python
from pathlib import Path
from app.retrieval.types import formal_loader

data_dir = Path(r"D:\gitcode\Edit\DE\data\formal_corpus")
version = "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
documents = formal_loader(data_dir)(version)
```

## 尚未完成

- 正式 30 道题，以及 `data/eval/gold.jsonl` 和 `data/eval/manifest.json`。
- 向量索引、真实语义检索和评分。
- 本轮没有执行 `git add`、`commit` 或 `push`。
