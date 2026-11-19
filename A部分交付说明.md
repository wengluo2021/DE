# A 部分交付说明

记录日期：2026-11-19。项目目录：`D:\gitcode\Edit\DE`。解释器：`D:\gitcode\Edit\DE\.venv\Scripts\python.exe`，Python 3.13.11，与 `.python-version` 一致。

## 1. 交付范围和当前状态

A 交付五份 EUR-Lex 英文消费者权益法规的原始公布版快照、清洗全文、章条位置、正式语料包和 30 道英文标准题。B 用正式语料包建库，C 用正式题集做评分对照。

程序校验、重复生成、加载核对、人工复核和浏览器视觉检查已经完成。A 负责人于 2026-11-19 确认通过，未发现问题。详细命令和哈希见 `artifacts/a_review/a_final_validation.md`。正式语料的向量索引、语义检索、LLM 回答和四组评分由 B、C 后续验证。

## 2. 五份文档和版本范围

五份都登记为 `original_publication`。保存的是官方公报原始文本，页面上另外链接的合并修订版没有进入清洗正文。

| document_id | CELEX | 法规 |
| --- | --- | --- |
| eu_consumer_rights_2011_83 | 32011L0083 | Directive 2011/83/EU，消费者权利 |
| eu_sale_of_goods_2019_771 | 32019L0771 | Directive (EU) 2019/771，货物销售 |
| eu_digital_content_2019_770 | 32019L0770 | Directive (EU) 2019/770，数字内容与数字服务 |
| eu_unfair_practices_2005_29 | 32005L0029 | Directive 2005/29/EC，不公平商业行为 |
| eu_unfair_terms_93_13 | 31993L0013 | Council Directive 93/13/EEC，不公平条款 |

快照由浏览器保存。保存时间、HTTP 状态和响应时间在来源清单中为 null，并写明无法从快照核实。

## 3. 目录和文件用途

| 路径 | 用途 |
| --- | --- |
| `data/sources.json` | 五份来源、版本、日期、快照路径和 SHA-256 |
| `data/raw/` | 五份官方 HTML 快照。带空格的文件名按清单读取 |
| `data/processed/*.txt` | 已验收清洗全文，UTF-8、LF、末尾一个换行 |
| `data/processed/*.json` | 已验收结构。区间是 Python `[start, end)`，对应同名 txt |
| `data/corpus_manifest.json` | A 的项目级冻结清单，路径相对于项目根目录 |
| `data/formal_corpus/` | B 的正式语料包。内有 `manifest.json`、`raw/`、`processed/` |
| `data/eval/gold.jsonl` | 30 道正式题，一行一题 |
| `data/eval/manifest.json` | 题集版本、语料版本、题数和覆盖 |
| `data/sample_corpus/` | 只含第一份文档的联调样本，使用自己的语料版本 |
| `data/eval/sample.jsonl` | 三道样题，不是正式 30 题 |
| `scripts/process_documents.py` | 从来源清单清洗 HTML |
| `scripts/export_corpus.py` | 生成正式包。命令行会先核对五份官方文档是否齐全 |
| `scripts/build_gold.py` | 从冻结正文截取证据并生成正式题集 |
| `scripts/validate_data.py` | 只做语料或题集校验 |
| `artifacts/a_review/` | 逐文档复核、冻结、题集和最终校验记录 |

## 4. 版本

| 名称 | 值 | 读取位置 |
| --- | --- | --- |
| corpus_version | `794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795` | `data/formal_corpus/manifest.json` 和 `data/corpus_manifest.json` |
| gold_version | `9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d` | `data/eval/manifest.json`。它等于 `gold.jsonl` 的文件 SHA-256，不写进 jsonl |
| 样本 corpus_version | `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50` | `data/sample_corpus/manifest.json` |

正式包和样本包版本不同。正式问答和正式评分使用第一行的统一语料版本。

## 5. 环境和依赖

在项目根目录运行，使用上面的 `.venv` 解释器。

- 清洗 HTML 使用 `requirements.txt` 中的 `beautifulsoup4==4.15.0` 和 `soupsieve==4.1.2`。
- `formal_loader` 位于 `app.retrieval.types`。导入 `app.retrieval` 会加载检索服务，当前环境还使用 `requirements-b.txt` 里已经安装的 `filelock==4.2.10`。
- 本轮没有新增依赖，也没有执行 `pip install`。

## 6. 从已有快照复现

下面三条命令会重新写文件。本轮实际复跑后，产物字节哈希与运行前一致。

```powershell
Set-Location 'D:\gitcode\Edit\DE'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\process_documents.py' --all
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\export_corpus.py'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\build_gold.py'
```

顺序是清洗、正式导出、题集生成。导出读取已验收 txt 和 JSON；题集读取正式包。`export_corpus.py` 在写入 `data/formal_corpus` 和 `data/corpus_manifest.json` 之前，要求来源清单正好包含第 2 节的五个 `document_id`。缺少或多出文档时退出码为 1，不打印 `result=ok`。

`scripts/export_sample.py` 会重写单文档样本包和样题 manifest。本轮没有运行它。正式交付不使用样本版本。

## 7. 日常校验和加载

下面的命令只检查，不生成语料或题集。

```powershell
Set-Location 'D:\gitcode\Edit\DE'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope corpus
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope eval
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' -m unittest tests.test_corpus_batch tests.test_corpus_freeze tests.test_gold_eval
```

成功时语料校验打印 `documents=5`、`main_articles=121`、`result=ok`。题集校验打印 `questions=30 answerable=24 refusal=6`、`result=ok`。

B 的加载方式：

```python
from pathlib import Path
from app.retrieval.types import formal_loader

data_dir = Path(r"D:\gitcode\Edit\DE\data\formal_corpus")
corpus_version = "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
documents = formal_loader(data_dir)(corpus_version)
```

`formal_loader` 读取 `data_dir/manifest.json`。清单里以 `data/` 开头的路径会去掉第一段，再拼到 `data_dir` 里面。

## 8. 最终验证和复核状态

本轮结果：

- 语料校验和题集校验退出码都是 0。
- 三个 A 部分测试模块合计 19 项，结果 `OK`。异常用例打印的失败文本是被断言的预期输出。
- 清洗、正式导出和题集生成复跑后，44 个受保护文件哈希不变。
- 正式包和样本包都能按各自版本加载。加载出的全文、条文 ID、区间、`label`、`chapter`、`section` 与已验收数据一致。
- 42 段证据长度为 68–393。退款题保留第 13 条第 2、3 款，两年责任期题保留第 10 条第 6 款的二手商品例外。

复核分层：

- 程序完成来源对应、文件哈希、结构 ID、引用、字符区间、题数、证据切片和版本绑定。
- AI 对照 HTML DOM 和冻结正文写了五份文档复核，并对照切片写了题集复核。证据由程序截取。
- 人工复核和浏览器视觉检查已完成。A 负责人于 2026-11-19 确认通过，未发现问题。
- 逐文档 AI 报告仍保留“当时未做浏览器视觉检查”。那是那些轮次的记录，当前结论以上述人工确认为准。
- 切片一致只说明摘录回到了冻结正文，不能当成答案正确率。

## 9. 已知限制和未完成事项

- 语料是原始公布版，不是后来的合并修订版。
- 快照的保存时间、HTTP 状态和响应时间仍为 null。
- 浏览器视觉检查已由 A 负责人于 2026-11-19 确认通过。
- 没有向量索引、embedding 下载、真实语义检索、LLM 回答或四组评分。
- C 的问答接口还没有用这 30 道正式题做过端到端实测。本文只交付题集字段，不把该接口记为已通过。
- 本轮没有执行 `git add`、`commit` 或 `push`。

## 交给 B

- 把 `data_dir` 设为 `data/formal_corpus`。
- 用 `formal_loader` 读取包内 `manifest.json`，请求版本使用上面的统一 `corpus_version`。
- 每份文档的 `text` 是完整清洗正文。主条文在 `articles` 中。
- `article_id` 是稳定 ID。`label` 为 `Article {条号}`。
- `chapter` 对应已验收 `chapter_id`，`section` 对应 `section_id`。没有章或节时为 null。
- 字符区间是 Python `[start, end)`，满足 `text[start:end]` 等于该条文或证据文本。
- 第四份有两个节。第 5 条直接属于第 2 章，`section` 为 null。第 6、7 条属于 Section 1，第 8、9 条属于 Section 2。
- 样本包 `data/sample_corpus` 只用于早先联调，版本是 `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50`。正式索引使用五份文档的统一版本。

## 交给 C

- 正式题集是 `data/eval/gold.jsonl`，清单是 `data/eval/manifest.json`。
- 固定使用 `corpus_version=794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795` 和 `gold_version=9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d`。
- 向系统提交的是 `question`。`reference_answer`、`key_facts` 和 `evidence` 用于评分对照，不作为系统输入。
- `should_refuse` 为 false 的有 24 题，为 true 的有 6 题。拒答题的 `evidence` 和 `key_facts` 为空，原因在 `refusal_reason`。
- 可答题的 `key_facts` 等于对应 `evidence.quote`。证据含 `document_id`、`start`、`end`、`quote`，以及 `article_id` 或 `structure_id`。
- 题型是 `single_article` 13 题、`multi_evidence` 11 题、`unanswerable` 6 题。
- `data/eval/sample.jsonl` 是三道联调样题，绑定样本语料版本，不代替正式题集。
- 目前没有用 C 的实际接口跑过这 30 题。字段说明不能视为接口兼容性已经通过。
