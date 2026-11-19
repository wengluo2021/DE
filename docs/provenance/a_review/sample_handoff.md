# 第 3 步样本交接说明

样题由 AI 辅助生成，并对照已验收清洗正文复核。复核日期：2026-11-19。字段兼容性于同日修正。

这是单文档联调样本，标记为 `integration_sample`。它不是五份正式语料的冻结版本，也不能代替以后的 `data/eval/gold.jsonl`。

已验收文件没有改动：

| 文件 | SHA-256 |
| --- | --- |
| `data/raw/eu_consumer_rights_2011_83.html` | `7812747113a74ef3a2b2e8d2d3fb067ed416280f415aed76dc255083b54e892e` |
| `data/processed/eu_consumer_rights_2011_83.txt` | `75acf22af53bf1878fe2750757b5ecd5c1230236aaab4fc543c1d029b3bf5689` |
| `data/processed/eu_consumer_rights_2011_83.json` | `f7ed11c4e7817cc58c23498ef1b87b87e885996f8a075a02365782e44b84829a` |
| `artifacts/a_review/eu_consumer_rights_2011_83_review.md` | `0af5fe7c011fb7ddffe21f910cd702c362c4497a890f7a759c70b3604544391f` |

## 样本版本

`corpus_version`：

`41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50`

样题、`data/eval/sample_manifest.json` 和 `data/sample_corpus/manifest.json` 使用同一个值。

上一版适配缺少 B 要读取的 `label`、`chapter`、`section`，版本是 `c3ebeccff2269286fe939a266a899919fa07b5d3d5300362de8d53be959fc225`。补字段后，`articles` 结构哈希从 `fecd18aeec4c9b308331e148e6a801aea18ceb1d8543c858bbee00980565ee00` 变为 `128d842ba9798cf099b4c65d5401ad0a0324f5d5f1efbfe92f139c3fcb82387a`。适配 JSON 的文件哈希现为 `1c5c2ae09d58423bc63d084390b25030051495b7b4fb3aeb056e6335f506290f`。

计算方式沿用 `app/retrieval/types.py` 的 `canonical`、`digest` 和 `formal_loader`：

1. `text_sha256` 是清洗全文 UTF-8 字节的 SHA-256，仍等于已验收 txt。
2. `structure_sha256` 是补完字段后的完整 `articles` 数组的规范 JSON SHA-256。规范 JSON 使用 `sort_keys=True`、`separators=(",", ":")`、`ensure_ascii=False`。
3. 版本材料只有 `parser_version`（`eurlex_html_v1`）和按 `document_id` 排序的文档列表。每项只取 `document_id`、`title`、`issuer`、`source_url`、`published_at`、`effective_at`、`raw_sha256`、`text_sha256`、`structure_sha256`。
4. 先得到 `corpus_version`，再写入适配文档，最后计算 `processed_sha256`。

材料里没有 `corpus_version` 自身，也没有处理后 JSON 文件哈希、登记时间或复核时间。`published_at` 是原始公布日期 `2011-11-22`。`effective_at` 是该原始文本的生效日期 `2011-12-12`，不是第 28 条里的适用日期 `2014-06-13`。完整日期仍放在适配 JSON 的 `source_fields.dates`。

重复运行 `scripts/export_sample.py` 会从已验收 JSON 重新导出，版本和上述产物哈希保持一致。

## A 的 JSON 与 B 的加载格式

已验收的 `data/processed/eu_consumer_rights_2011_83.json` 继续作为结构真源。B 的 `formal_loader` 读取样本目录中的适配文档。

| B 读取的字段 | 适配方式 |
| --- | --- |
| 字符串 `title`、`issuer`、`source_url` | 来自已验收来源记录的标题、机构和官方 URL |
| 顶层 `text` | 已验收清洗全文 |
| `raw_path`、`raw_sha256` | 指向样本目录中的 HTML 副本，哈希与原快照相同 |
| `label` | `Article {条号}`，例如第 18 条是 `Article 18` |
| `chapter` | 等于原有 `chapter_id`，例如 `eu_consumer_rights_2011_83:chapter:IV` |
| `section` | 等于原有 `section_id`；本文件没有节，因此为 `null` |
| `chapter_id`、`section_id` | 原字段保留 |

35 条主条文的 `article_id`、正文、正文块和 `start`、`end` 与已验收 JSON 相同。第 18 条的映射示例：

| 字段 | 值 |
| --- | --- |
| `article_id` | `eu_consumer_rights_2011_83:article:18` |
| `label` | `Article 18` |
| `chapter` / `chapter_id` | `eu_consumer_rights_2011_83:chapter:IV` |
| `section` / `section_id` | `null` |
| `start`、`end` | `[81963, 83581)` |

## 给 B、C 的目录

```text
data/sample_corpus/manifest.json
data/sample_corpus/raw/eu_consumer_rights_2011_83.html
data/sample_corpus/processed/eu_consumer_rights_2011_83.json
data/eval/sample.jsonl
data/eval/sample_manifest.json
scripts/export_sample.py
```

`formal_loader` 看到以 `data/` 开头的相对路径时，会去掉第一段，再拼到传入的数据目录。因此把数据目录设为 `data/sample_corpus` 时，读到的是样本目录里的副本，不是 `data/processed/` 里那份已验收文件。

B 的加载入口：

```python
from pathlib import Path
from app.retrieval.types import formal_loader

data_dir = Path(r"D:\gitcode\Edit\DE\data\sample_corpus")
version = "41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50"
documents = formal_loader(data_dir)(version)
```

当前环境可以正常执行 `from app.retrieval.types import formal_loader` 和 `from app.retrieval.service import RetrievalService`。此前缺少 `filelock` 的问题已经解决。

返回的文档含 `document_id`、`corpus_version`、`title`、`text`、`articles` 和 `chapters`。条文区间是 Python 字符 `[start, end)`。结构切分会读取 `chapter` 和 `section` 决定章界。检索结果组装会读取 `label` 生成 `article_labels`。

四组分块已在内存中实际运行，全文被连续覆盖，块长不超过各自上限，块文本等于原文切片，条文关联按区间相交计算：

| 条件 | 块数 |
| --- | ---: |
| f400 | 259 |
| s400 | 365 |
| f800 | 130 |
| s800 | 163 |

本轮没有下载 embedding，也没有建立真实向量索引。用测试桩调用 `RetrievalService._search` 时，返回了一块第 18 条的命中，`article_labels` 为 `["Article 18"]`，没有发生 `KeyError`。该结果只验证接口兼容，不是语义检索结果。

C 读取原文时，用加载结果里的 `text`，或已验收 txt，二者内容相同：

```python
quote = document["text"][evidence["start"]:evidence["end"]]
```

`document_id` 必须是 `eu_consumer_rights_2011_83`，并且 `quote` 必须等于证据里的 `quote`。

## 样题字段

`data/eval/sample.jsonl` 共 3 行。文件 SHA-256 是 `63f14226611fc7fbda5d2996c37ebe5f97f9ee237e7cbdc476fb14f7dfbc1126`。题目、参考答案、关键事实、拒答原因和证据内容未改，只同步了 `corpus_version`。

每行包含 `case_id`、`corpus_version`、`question`、`question_type`、`should_refuse`、`reference_answer`、`key_facts`、`evidence`、`refusal_reason`。

可答题的每段证据包含 `document_id`、`article_id`、`start`、`end`、`quote`。`quote` 从清洗 txt 截取，长度都小于 400 个 Python 字符。拒答题的 `evidence` 是空列表。

| case_id | 类型 | 条文 | 区间 |
| --- | --- | --- | --- |
| `sample-2011-83-delivery-deadline` | 单条文可答 | `article:18` | `[81983, 82251)` |
| `sample-2011-83-digital-withdrawal` | 两段证据可答 | `article:9`、`article:16` | `[69452, 69734)`、`[81214, 81431)` |
| `sample-2011-83-flight-compensation` | 应拒答 | 无 | 无 |

第 16 条 (m) 的证据落在 Article 16 自己的区间内。附件里另有数字内容表述，但这段摘录没有改用附件位置。

## 校验

使用 `D:\gitcode\Edit\DE\.venv\Scripts\python.exe` 完成：

```powershell
.\.venv\Scripts\python.exe scripts\export_sample.py
```

随后通过正常包导入调用 `formal_loader` 和 `RetrievalService`，并再次运行导出脚本。

- 三行 JSONL 可读，题号唯一，版本与两份 manifest 一致。
- 35 条都有 `label`、`chapter`、`section`，原 `chapter_id`、`section_id`、正文和区间未变。
- 证据区间落在声明的条文内，切片等于 `quote`。
- `formal_loader` 用新版本成功加载。
- f400、s400、f800、s800 分块通过覆盖、长度、切片和条文关联检查。
- `article_labels` 读取路径返回 `Article 18`。
- 连续两次导出的版本和产物哈希一致。
- 已验收 HTML、txt、结构 JSON、来源记录和原文复核报告的哈希保持不变。

## 尚未解决

- 其余四份文档和正式 30 道题还没有做。正式语料版本仍待第 4、5 步冻结。
- 本轮没有建 Chroma 索引，也没有跑真实语义检索、命中率或答案评分。

样本已经具备交给 B、C 做加载、分块和证据回切联调的条件。真实向量检索仍需后续建库。
