# 五份语料批量清洗与全量校验

记录日期：2026-11-19。复核方式是命令输出、字节哈希和标准库单元测试。本轮没有做浏览器视觉检查。

当前状态：五份文档及批量校验完成，正式语料版本冻结待完成。

本轮没有生成 `data/corpus_manifest.json`，没有给已验收产物写入新的语料版本，没有编写正式 30 道题，也没有处理向量库。没有执行 `git add`、`commit` 或 `push`。

## 批量清洗

`scripts/process_documents.py` 现在要求在 `--document-id` 和 `--all` 中选择一个，两个参数互斥。`--all` 只读取 `data/sources.json`，按 `document_id` 排序，不扫描 `data/raw`。路径直接使用清单中的相对路径。

预检覆盖清单结构、文档 ID 格式与唯一性、快照路径和 SHA-256 字段。空清单、重复 ID、无效 ID、缺文件或哈希不一致都会报出文件和原因。清单结构错误在处理前终止。单个文档的快照或清洗失败会计入失败数，其余文档继续处理。只要失败数大于 0，批次打印 `result=failed` 并以非零退出，不打印 `result=ok`。

可选 `--data-root` 只用于把异常测试指向临时副本，默认仍是项目根目录。正式运行没有传这个参数。

## 全语料校验

`scripts/validate_data.py --scope corpus` 在不带 `--document-id` 时校验清单中的全部文档。带 `--document-id` 时仍只校验一份。`--data-root` 保留。

全量模式复用逐文档区间检查，并核对：

- 清单中的每份文档都有 `data/processed/<id>.txt` 和 `data/processed/<id>.json`。
- `data/processed` 中未登记的同类 txt 或 json 会被报告。
- `data/sample_corpus` 不参与重复文档判断。
- 来源记录、结构 JSON 的文档 ID、快照路径和快照哈希一致。
- `clean_text_path` 指向该文档自己的正文。
- 结构定义 ID 在全语料中唯一，章节、节、条文之间的引用可以解析。
- 第四份同时保存在章节内和顶层 `sections` 的节只计一次定义。

## 逐文档结果

顺序按 `document_id`。主条文合计由各份实际 `article` 计数相加，为 35 + 27 + 27 + 21 + 11 = 121。

| 顺序 | 文档 ID | 章节 | 主条文 | 序言 | 附件 | 脚注 | 校验 offset_checks |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | eu_consumer_rights_2011_83 | 6 | 35 | 67 | 2 | 23 | annex=2 article=35 block=418 chapter=6 footnote=23 preamble=1 recital=67 signature=1 table=2 table_row=80 title=1 |
| 2 | eu_digital_content_2019_770 | 0 | 27 | 87 | 0 | 23 | article=27 block=261 footnote=23 preamble=1 recital=87 signature=1 title=1 |
| 3 | eu_sale_of_goods_2019_771 | 0 | 27 | 72 | 1 | 10 | annex=1 article=27 block=273 footnote=10 preamble=1 recital=72 signature=1 table=1 table_row=48 title=1 |
| 4 | eu_unfair_practices_2005_29 | 4 | 21 | 25 | 2 | 26 | annex=2 article=21 block=277 chapter=4 footnote=26 preamble=1 recital=25 section=2 signature=1 title=1 |
| 5 | eu_unfair_terms_93_13 | 0 | 11 | 24 | 1 | 4 | annex=1 article=11 block=91 footnote=4 preamble=1 recital=24 signature=1 title=1 |

第一次 `process_documents.py --all` 退出码 0，输出 `batch_documents=5`、`succeeded=5`、`failed=0`、`result=ok`。

`validate_data.py --scope corpus` 退出码 0，输出 `documents=5`、`main_articles=121`、`result=ok`。标准错误为空。

## 基线与运行后哈希

运行前记录的 10 个产物字节哈希，与第一次批量清洗、第二次批量清洗、以及随后两次单文档清洗之后的哈希相同。

| 文件 | SHA-256 | 字节 |
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

第五份 JSON 的历史哈希 `9e57f3f501ec37583d36d273be66aa2ca5cf5d573696ab39ab2ac1523e32e22f` 属于规则说明修正之前，本轮没有回退。

未改动文件的哈希：

| 文件 | SHA-256 |
| --- | --- |
| data/sources.json | 6a7a20ff4c9ea87bb940a066e8fdf08b285458fc9208b6b231dcf8e99fa5bad9 |
| data/raw/Unfair Terms.html | 6c700ae54d53f3dc3ece8d226d18471ac905eff42a7cb4d4874e2e56acaff707 |
| data/eval/sample.jsonl | 63f14226611fc7fbda5d2996c37ebe5f97f9ee237e7cbdc476fb14f7dfbc1126 |
| data/eval/sample_manifest.json | f86266512cef7f7385c9e122de488f0a0f6e79d7f5b5a40968043d06c51896c7 |
| data/sample_corpus/manifest.json | 5fa36813a51dde8839b4faafb56f57ba82f9e39f1e669e5463f9842414dbabb1 |
| data/sample_corpus/processed/eu_consumer_rights_2011_83.json | 1c5c2ae09d58423bc63d084390b25030051495b7b4fb3aeb056e6335f506290f |

样本版本仍是 `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50`。

## 实际命令

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

两次 `--all` 都是 `succeeded=5`、`failed=0`、`result=ok`，退出码 0。两次单文档清洗和校验的退出码都是 0，单文档校验输出 `result=ok`。十个产物哈希在重复运行后不变。

## 异常测试

`tests/test_corpus_batch.py` 使用标准库 `unittest`。异常用例只读写临时目录，正式 `data/` 不参与这些用例。`python -m unittest tests.test_corpus_batch` 结果是 `Ran 8 tests`，`OK`。

覆盖的情况：

- 同时给出 `--all` 与 `--document-id`，以及两边都缺少必要参数，参数解析直接退出。
- 空来源清单报 `sources list is empty`，退出码 1，输出不含 `result=ok`。
- 重复文档 ID 报 `document_id eu_one is duplicated`，退出码 1。
- 清单指向的原始文件不存在时报 `does not exist`，退出码 1。
- 一份快照哈希失配时报 `snapshot sha256 mismatch`，退出码 1，批次不是 `result=ok`。
- 两份快照都有效、其中一份清洗抛出失败时，输出 `succeeded=1`、`failed=1`、`result=failed`，不含 `result=ok`。
- 已登记正文缺失，同时 `data/processed` 有未登记 json、`data/sample_corpus` 有同名副本时，报告缺失和未登记文件，不把样本副本算成重复文档。
- 章节内的节与顶层 `sections` 镜像只形成一条结构定义；条文 ID 同时是定义和引用，不因此被当成重复定义。
