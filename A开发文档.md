# DERag：A 开发文档（官方语料与标准测试题集）

记录日期：2026-11-19。本文说明 A 部分已经实现的数据管线、代码职责、数据契约、版本算法和交接方式。组员实际运行请按 [A测试.md](./A测试.md)；简要交付清单见 [A部分交付说明.md](./A部分交付说明.md)。

## 1. A 要完成什么

A 负责“官方英文 HTML → 来源登记 → 清洗全文 → 章条与字符位置 → 冻结语料包 → 标准测试题集”这条链路。B 接收同一份冻结正文进行分块、embedding、向量入库和语义检索；C 使用对应版本的标准题运行问答、引用校验和正式评估。

**当前状态：五份官方文档、正式语料包、30 道英文标准题及相应脚本已经完成程序校验、AI 辅助原文复核、人工复核和浏览器视觉检查，未发现问题。**A 的三个自动测试模块共 19 项通过；正式包和单文档样本均能通过正常包导入的 `formal_loader` 加载。

人工复核和浏览器视觉检查按 A 负责人 2026-11-19 的确认更新，结论为通过，未发现问题。既有阶段报告保留当时的检查记录。

| 负责人 | 交付范围 | 与其他成员的边界 |
| --- | --- | --- |
| A | 来源、HTML 快照、清洗全文、结构与位置、版本清单、标准题及证据、数据校验与复核记录 | 负责数据问题修订与版本发布 |
| B | 固定窗口与结构感知分块、embedding、四组 Chroma 索引、语义检索及相关 API | 读取 A 的正式包，不改写冻结正文 |
| C | LLM 回答、引用校验、问答页面、四组正式评估、运行答案的人工评分和系统集成 | 使用 A 的题集评分，并调用 B 的检索模块 |

19 项自动测试验证数据管线及异常处理；30 道标准题是评估 RAG 的输入和评分对照。A 的测试通过不能替代 B 的真实检索验证，也不能写成 30 道题的系统回答全部正确。B 独立模块的开发与测试见 [B开发文档.md](./B开发文档.md) 和 [B测试.md](./B测试.md)。

## 2. 代码目录和文件职责

本机项目根目录为 `D:\gitcode\Edit\DE`。下面的目录均相对于项目根目录；组员可以把整个项目放在其他路径。

```text
DE/
  AGENTS.md                          # 当前开发约定
  A部分需求与开发顺序.md              # 需求与第 1–6 步验收要求
  A开发文档.md                       # 本文：实现与数据契约
  A测试.md                           # 组员运行与验收指南
  A部分交付说明.md                   # 当前交付入口与版本
  A部分阶段开发记录.md               # 历史开发与复核记录
  scripts/
    process_documents.py             # 单文档、批量清洗和字符定位
    validate_data.py                 # corpus / eval 校验
    export_sample.py                 # 第一份文档的联调样本导出
    export_corpus.py                 # 正式五文档交付包导出与核对
    build_gold.py                    # 固定题目定义、截取证据、生成题集
  tests/
    test_corpus_batch.py             # 8 项：批处理和全语料校验
    test_corpus_freeze.py            # 6 项：冻结、加载和正式入口完整性
    test_gold_eval.py                # 5 项：题集与证据异常校验
  data/
    sources.json                     # 官方来源与快照登记
    raw/                             # 五份浏览器保存的官方 HTML
    processed/                       # 五对已验收 txt / 结构 JSON
    corpus_manifest.json             # A 的项目级语料冻结清单
    formal_corpus/
      manifest.json                  # B 的正式加载清单
      raw/                           # 官方 HTML 的字节副本
      processed/                     # 补齐 B 字段的适配 JSON，内含完整 text
    sample_corpus/                   # 第一份文档的独立联调包
    eval/
      sample.jsonl                   # 3 道联调样题
      sample_manifest.json           # 样题清单
      gold.jsonl                     # 30 道正式标准题
      manifest.json                  # 正式题集版本和覆盖
  artifacts/a_review/                # 逐文档、批量、冻结、题集与最终复核
```

### 2.1 脚本职责

| 文件 | 输入 | 输出与职责 |
| --- | --- | --- |
| `process_documents.py` | `sources.json` 和其中登记的本地 HTML | 生成规范化 txt、结构 JSON、稳定 ID、字符区间和统计 |
| `validate_data.py` | 来源、快照、处理产物、正式包或题集 | 只读校验；成功返回 0，校验失败返回非零并报告原因 |
| `export_sample.py` | 已验收的第一份文档和原样题 | 生成单文档样本适配包并同步样题版本；会重写样本文件 |
| `export_corpus.py` | 五份已验收 txt / JSON 和官方 HTML | 生成正式包、两份 manifest，计算统一版本并验证加载 |
| `build_gold.py` | 正式包、结构位置和代码中固定的题目定义 | 截取证据，生成 `gold.jsonl` 和题集 manifest |

`build_gold.py` 是固定题集的可复现生成器，运行时不调用 LLM 随机出题。题目和参考答案已写入定义，证据由程序从冻结全文截取。

### 2.2 主要函数

| 模块与函数 | 作用 |
| --- | --- |
| `process_documents.load_catalog` / `run_all` | 清单预检、稳定排序、逐文档处理及成功失败汇总 |
| `process_documents.build_document` | 从一份 HTML 构建清洗全文与结构载荷 |
| `process_documents.parse_chapter` / `parse_section` / `parse_article` | 解析现代 EUR-Lex 章、节、主条文 |
| `process_documents.parse_legacy` | 处理第五份旧式 HTML 的相邻段落、落款、脚注和附件 |
| `process_documents.TextCursor` / `assemble` / `assemble_legacy` | 拼接正文时记录当前位置，绑定各结构区间 |
| `validate_data.validate_corpus` / `validate_all` | 单份及整套语料的区间、结构、哈希与清单校验 |
| `validate_data.check_cases` / `validate_eval` | 题目字段、版本、证据归属、切片、数量及题集哈希检查 |
| `export_corpus.adapt_article` / `prepare_documents` | 保留已验收条文，补齐 B 字段并计算版本材料 |
| `export_corpus.export_official` / `require_official_catalog` | 正式入口在写文件前强制核对五份官方 ID |
| `export_corpus.export_corpus` / `verify_corpus` | 通用导出，以及正常加载后与已验收数据核对 |
| `build_gold.clip` | 在指定结构内用唯一锚点定位并截取证据 |
| `app.retrieval.types.formal_loader` | B 提供的正常加载器，核对包内文件、正文、条文结构和版本 |

正式 CLI 使用 `export_official`。通用 `export_corpus(root)` 仍支持单元测试的小语料；不能因为通用函数可导出一份测试文档，就绕过正式五份文档的完整性检查。

## 3. 固定语料范围

主题为英文欧盟网络购物消费者权益，五份文档均采用 **原始公布版 `original_publication`**。保存网页中链接的合并修订版没有替换本地快照正文。

| 原始文件 | document_id | 主条文 | 章 / 节 | 序言项 | 附件 |
| --- | --- | ---: | --- | ---: | ---: |
| `eu_consumer_rights_2011_83.html` | `eu_consumer_rights_2011_83` | 35 | 6 / 0 | 67 | 2 |
| `Sale of Goods.html` | `eu_sale_of_goods_2019_771` | 27 | 0 / 0 | 72 | 1 |
| `Digital Content and Services.html` | `eu_digital_content_2019_770` | 27 | 0 / 0 | 87 | 0 |
| `Unfair Commercial Practices.html` | `eu_unfair_practices_2005_29` | 21 | 4 / 2 | 25 | 2 |
| `Unfair Terms.html` | `eu_unfair_terms_93_13` | 11 | 0 / 0 | 24 | 1 |

主条文合计 **121**。第五份的 24 项序言没有官方编号，只保存内部顺序 `ordinal`；不能给它们补造官方 recital 编号。

来源核验依据、官方 URL、CELEX、机构、日期和公报信息保存在 `sources.json` 及逐文档复核报告。浏览器快照无法证实的保存时间、下载 HTTP 状态和响应时间使用 `null`，并说明原因。来源核验时访问 Cellar 的 HTTP 200 是另一次请求的结果，不能当作浏览器保存这份 HTML 时的状态。

## 4. 数据处理流程

```text
sources.json + raw HTML
           |
           v
process_documents.py
           |
           +--> processed/*.txt：唯一的规范化全文
           +--> processed/*.json：元数据、结构、ID、区间和哈希
           |
           v
validate_data.py --scope corpus
           |
           v
export_corpus.py --> formal_corpus + corpus_manifest.json --> B 分块与建库
           |
           v
build_gold.py --> gold.jsonl + eval/manifest.json --> C 问答评估
           |
           v
validate_data.py --scope eval
```

### 4.1 读取和清洗

清洗脚本从来源清单读取路径，不扫描整棵浏览器资源目录。带空格的 HTML 文件名按清单原样处理；同名 `_files` 文件夹不作为另一份法规。

正文保留法规标题、序言、章、节、主条文、段落、列表、实质表格、落款、附件及脚注。导航、语言菜单、页面按钮和重复的公报页眉等附属内容被排除。表格按行及单元格顺序转为文本，空单元格仍保留列关系，例如 `Article 1 | | Article 3 ...`。

清洗规则版本为 `eurlex_html_v1`。先规范化空白和 LF 换行，再生成全部字符位置。原文中的用词、否定、例外、数字和交叉引用不由清洗器改写。

### 4.2 现代结构和旧式 HTML

现代页面按 `#document1` 下的实际结构容器识别章、节和主条文。正文交叉引用、修订引文和附件表格中的 `Article` 字样保留在原所属结构内，不作为新的主条文。

只有存在 `p.ti-art` 且没有 `div.eli-subdivision` 时，才进入旧式解析分支。第五份文档按 11 个主条文标题切分；第 11 条在落款前结束，后续脚注和附件独立归属。无锚点的脚注续段并入前一脚注。

两种解析分支最终都输出同一种全文与结构契约；B 接收的是处理后的数据，无需分别解析原始 HTML。

### 4.3 字符区间和重复文本

位置由正文组装游标记录，不依靠全文第一次 `find()` 的位置回填。相同的条号、相同段落和同号脚注各自保留自己的区间。

区间统一为 Python 字符索引 `[start, end)`：

```python
assert clean_text[item["start"]:item["end"]] == item["text"]
```

索引对应完整清洗全文，包含空格、标点和换行；不是 UTF-8 字节、英文单词数或 token。B、C 读取后不得再次 `strip()`、替换换行或重排段落。

第四份的节既在章内保存，也有顶层镜像。校验器区分“结构定义”和“结构引用”，镜像只计一次定义。第 5 条直接属于第二章，第 6、7 条属于其第一节，第 8、9 条属于其第二节。

## 5. 三种数据格式

### 5.1 来源记录

`data/sources.json` 的顶层 `sources` 数组登记五份文档。每条记录包含 `document_id`、`title`、`institution`、`language`、`official_url`、`eli`、`celex`、`version_type`、`source_format`、日期、公报信息、`snapshot`、空值原因与核验依据。

`snapshot.path` 和 `snapshot.sha256` 对应保存的 HTML。日期字段区分文件日期、公布、生效、转化和适用等含义；不能用文件修改时间替代官方日期，也不能把后来的合并点当作当前原始公布版的修订日。

### 5.2 已验收全文和结构 JSON

`data/processed/<document_id>.txt` 保存完整正文。配对 JSON 保存 `clean_text_path`、`clean_text_sha256`、`character_offsets`、来源、清洗规则、统计以及各类结构。这里的 `title` 是结构对象，全文在独立 txt 中。

主条文保留 `article_id`、`number`、`chapter_id`、`section_id`、`start`、`end`、`text` 和 `blocks` 等字段。无章、无节时对应字段为 `null`。

### 5.3 B 的适配 Document

正式交付 JSON 位于 `data/formal_corpus/processed/`，把已验收全文嵌入顶层 `text`，并补齐 B 所需字段。

| 字段 | 来源和用途 |
| --- | --- |
| `document_id` | 原有稳定文档 ID |
| `corpus_version` | 五份文档共用的内容版本 |
| `title`、`issuer`、`source_url` | 已核对的标题字符串、机构和官方 URL |
| `published_at`、`effective_at` | 来源中的公布日和生效日，不重新推断日期 |
| `raw_path`、`raw_sha256` | 包内快照路径和文件字节哈希 |
| `text` | 与已验收 txt 完全相同的全文 |
| `articles` | 保留原有条文，增加 `label`、`chapter`、`section` |
| `chapters`、`sections` | 分块使用的章、节边界与成员信息 |
| `source_fields` | 语言、CELEX、版本类型、日期和已验收结构文件哈希等追溯信息 |

例如第一份适配文档中 Article 18 的部分字段如下；这是条文对象摘录，不是完整 Document：

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

适配只补接口字段，不改条文 ID、正文、块或区间。已验收 JSON 不直接交给 B 的加载器；使用适配包及其 manifest。

## 6. 正式导出和两份 manifest

### 6.1 正式入口的完整性检查

命令 `scripts/export_corpus.py` 在创建或写入交付包之前要求来源清单恰好包含五份官方文档 ID。缺少、多出或重复文档都失败，不能把四份文档导出成功当作正式五文档交付。

通用导出函数会先准备全部待导出文档，再写 HTML 字节副本及适配 JSON。适配 JSON 写入语料版本后，才计算其最终文件哈希。

### 6.2 两份清单的职责与路径

| 文件 | 使用者 | 路径基准 |
| --- | --- | --- |
| `data/corpus_manifest.json` | A 的项目级冻结和追溯记录 | 相对于项目根目录，同时登记原产物与包内副本 |
| `data/formal_corpus/manifest.json` | B 的 `formal_loader` | 相对于加载目录；兼容去掉首段 `data/` 的路径写法 |

B 把 `data_dir` 设置为 `data/formal_corpus`。包内清单的 `data/raw/Sale of Goods.html` 会解析为 `data/formal_corpus/raw/Sale of Goods.html`，不会读取项目根目录原始快照。

两份 manifest 的 `corpus_version` 相同，但文件结构和用途不同。`formal_loader` 不直接读取项目级 `corpus_manifest.json`。

## 7. 版本和哈希算法

### 7.1 当前三个版本

| 名称 | 值 |
| --- | --- |
| 正式 `corpus_version` | `794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795` |
| 正式 `gold_version` | `9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d` |
| 单文档样本 `corpus_version` | `41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50` |

旧题集版本 `444afb6d...` 是退款和二手商品例外修正前的历史版本，当前正式评估使用上表的新题集版本。

### 7.2 语料版本

复用 `app.retrieval.types.canonical` 和 `digest`：

```python
canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

版本材料为 `parser_version` 和按 `document_id` 排序的文档列表。每份文档只包含：

```text
document_id, title, issuer, source_url,
published_at, effective_at, raw_sha256,
text_sha256, structure_sha256
```

| 哈希 | 计算对象 |
| --- | --- |
| `raw_sha256` | 原始 HTML 文件字节 |
| `text_sha256` | 完整 `text` 的 UTF-8 字节，等于已验收 txt 的字节哈希 |
| `structure_sha256` | 适配后 `articles` 数组的规范化 JSON，包含补齐的 label、chapter、section |
| `processed_sha256` | 写入版本之后的整个适配 JSON 文件字节 |
| `accepted.structure_json_sha256` | 已验收结构 JSON 文件字节，单独记录 |

`structure_sha256` 不是完整结构 JSON 的文件哈希。加载器同时核对整个适配文件的哈希，覆盖其中其余元数据。

语料指纹不包含版本号自身、适配文件最终哈希、登记时间或导出时间，避免自引用和运行时间造成版本漂移。

### 7.3 题集版本

`gold_version` 等于 `gold.jsonl` 的文件字节 SHA-256，包括末尾 LF；manifest 的 `gold_sha256` 与它相同。每道题已含正式 `corpus_version`，但不含 `gold_version`，因此不存在文件把自身哈希写入自身的问题。

修改问题、参考答案、关键事实、证据、字段序列化或换行，都会改变题集版本。修订后必须重新生成题集 manifest 和复核记录，并通知使用该题集的成员。

## 8. 标准测试题集

### 8.1 分布和字段

正式题集共 **30 题：24 可答、6 拒答**。当前类型为单段证据 `single_article` 13 题、多段证据 `multi_evidence` 11 题、`unanswerable` 6 题。多证据可以来自同一条文，不表示一定跨文档。

| 文档 | 可答题 | 证据段 |
| --- | ---: | ---: |
| 消费者权利 2011/83 | 6 | 11 |
| 货物销售 2019/771 | 5 | 9 |
| 数字内容 2019/770 | 5 | 10 |
| 不公平商业行为 2005/29 | 4 | 7 |
| 不公平条款 93/13 | 4 | 5 |
| 合计 | 24 | 42 |

每行 JSON 的字段沿用现有样题：

| 字段 | 用途 |
| --- | --- |
| `case_id` | 唯一且稳定的题号 |
| `corpus_version` | 本题使用的正式语料版本 |
| `question`、`question_type` | 英文问题和题型 |
| `should_refuse` | 预期是否拒答 |
| `reference_answer` | 英文评分参考答案 |
| `key_facts` | 关键事实；当前实现逐项取对应 quote |
| `evidence` | 标准证据列表 |
| `refusal_reason` | 拒答题缺少什么信息；可答题为 null |

每段证据包含 `document_id`、`article_id` 或 `structure_id`、`start`、`end` 和 `quote`。当前 42 段摘录长度为 68–393 个 Python 字符，全部满足 `0 < len(quote) < 400`，并从全文连续切出。

### 8.2 编题与语义复核

`clip` 先取得指定条文或附件的区间，再检查起止锚点在该范围内唯一。不能用全文第一个相同词句替代正确位置，也不能把不连续句子拼成一段 quote。

关键事实等于 quote 可由程序验证，但不能证明答案已经保留所有必要条件。语义复核仍需阅读同条其他款及相关条文，检查限定、例外、否定、日期和范围。

已有两项实际修正：

- `gold-crd-withdrawal-refund` 补齐第 13 条第 2、3 款，保留额外配送费用与暂缓退款条件，以及经营者提出自行取货的例外。
- `gold-sgd-two-year-liability` 补齐第 10 条第 6 款，说明二手商品较短期间需由成员国允许并由双方约定，且不能少于一年。

### 8.3 拒答与评估边界

六道拒答题涉及航班固定赔偿额、增值税税率、退款法定年利率、德国罚款上限、拒绝修理后的起诉天数和一揽子旅游最低保险。判断范围是完整五份冻结正文，包括序言、附件和脚注，不只检查某一份文档。

拒答题的 `evidence`、`key_facts` 均为空，原因写入英文 `refusal_reason`。出现相关关键词不等于具备答案，未找到某个词也不能单独证明应拒答。

题集在查阅四组正式检索结果之前冻结。C 向系统提交 `question`，让系统自行检索和回答；标准答案、关键事实和标准证据保留用于评分对照。四组运行时得到 120 条逐题记录，尚需 C 实际执行。

## 9. 命令行入口与错误行为

以下命令均在项目根目录用 `.venv` 的 Python 执行。

| 命令参数 | 行为 | 是否写入产物 |
| --- | --- | --- |
| `scripts/process_documents.py --document-id <id>` | 处理一份登记文档 | 是 |
| `scripts/process_documents.py --all` | 按 ID 稳定排序处理清单中的所有文档 | 是 |
| `scripts/validate_data.py --scope corpus` | 核对整套来源、处理产物、结构与区间 | 否 |
| `scripts/validate_data.py --scope corpus --document-id <id>` | 核对一份文档 | 否 |
| `scripts/export_corpus.py` | 核对五份官方 ID 后导出正式包并验证 | 是 |
| `scripts/build_gold.py` | 按固定题目定义重新生成题集及 manifest | 是 |
| `scripts/validate_data.py --scope eval` | 题集、正式版本、证据及题集 manifest 校验 | 否 |

清洗的 `--all` 与 `--document-id` 必选其一、互斥。全语料校验按来源登记处理，额外的未登记 txt / JSON 会报告；样本包里的副本不算重复正式文档。

`--data-root` 由清洗和校验脚本提供，用于指定另一套项目数据根目录，异常测试据此使用临时副本。正式导出 CLI 没有这个命令行选项；测试通过函数参数注入临时根目录。题集校验不接受 `--document-id`。

批处理清单结构错误时在处理前失败；单份快照哈希不符或预期解析失败计入失败数，继续处理其余文档。只要存在失败，最终退出非零并报告 `result=failed`。调用方应检查最终退出码和汇总，不能只看到某一份文档已输出就判断整批成功。

## 10. 正常加载与交接

### 10.1 B：加载正式语料

下面代码在项目根目录运行，不绕过 `app.retrieval` 的包初始化：

```python
from pathlib import Path
from app.retrieval.types import formal_loader

data_dir = Path("data/formal_corpus")
version = "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
documents = formal_loader(data_dir)(version)
assert len(documents) == 5
assert sum(len(doc["articles"]) for doc in documents) == 121
```

B 按同一版本建立 F400、S400、F800、S800 四组索引。400/800 是 Python 字符数。A 提供冻结输入和可回查的位置；正式索引、模型和检索质量由 B 的实现及验证负责。

### 10.2 C：加载评分对照

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

C 同时固定语料和题集版本。可答题命中与答案指标按 24 题统计，6 道拒答题单独统计；具体逐题评分和正式结果由 C 实际运行后记录。字段已交付不等于 C 的端到端接口已经验收。

### 10.3 联调样本

`data/sample_corpus` 只含第一份文档，`data/eval/sample.jsonl` 有三道联调题，绑定样本版本。它们保留用于早期联调和回归，不改成正式五文档版本。正式评估使用 `gold.jsonl`。

## 11. 环境、测试和已有证据

本机验证环境为 Windows PowerShell、Python 3.13.11，显式调用 `.venv/Scripts/python.exe`。A 命令行使用 Beautiful Soup；正常包导入的检索服务还会导入 `filelock`。版本分别登记在 `requirements.txt` 与 `requirements-b.txt`，安装步骤见 [A测试.md](./A测试.md)。

| 测试模块 | 当前项数 | 主要覆盖 |
| --- | ---: | --- |
| `tests.test_corpus_batch` | 8 | 参数、空清单、重复 ID、缺快照、哈希失配、部分失败、产物清点、节镜像 |
| `tests.test_corpus_freeze` | 6 | 缺处理产物、正式快照被改、版本失配、重复导出、小语料兼容、正式缺项 / 多项拒绝 |
| `tests.test_gold_eval` | 5 | 证据归属、附件重复条号、摘录失配、拒答证据、重复题号、版本 / 哈希、CRLF、参数 |
| 合计 | 19 | 测试在临时副本或内存对象中制造异常 |

本机已实际复跑清洗、正式导出、题集生成、两类校验及上述 19 项测试。最终记录的 44 个受保护文件哈希保持一致，正式包和样本包加载均通过。详细字节哈希与命令见 [最终校验记录](./artifacts/a_review/a_final_validation.md)。

组员应以自己执行的退出码和输出为准；查看本机已有报告不能代替在另一台电脑运行测试。

## 12. 复核状态和维护规则

| 范围 | 当前状态 | 后续负责人 |
| --- | --- | --- |
| 来源、全文、结构、版本与证据位置 | 程序检查通过，有 AI 辅助原文复核 | A 维护与修订 |
| 官方原文、标准答案和浏览器视觉检查 | 2026-11-19 由 A 负责人确认通过，未发现问题 | A 维护复核结论，修订后重新核对 |
| 正式语料的 embedding、索引及语义检索 | 不属于 A 数据校验的通过结论 | B 正式联调 |
| 生成答案、引用支持性、四组评分和页面集成 | 不属于本次 A 的测试结果 | C 正式联调与评分 |

既有 AI 辅助复核采用 HTML DOM、冻结正文和切片对照。人工复核和五份本地 HTML 的浏览器视觉检查已由 A 负责人于 2026-11-19 确认通过，未发现问题。各份 AI 报告中“当时未做浏览器视觉检查”保留为历史记录。附件 I 的方框样式在清洗后是普通数字，相关填写说明仍保留；引用占位信息时需同时查看说明。语料是保存的原始公布版，不能按后续合并文本补写规则。

维护数据时遵循以下顺序：定位问题并记录文档 ID / 条文或题号 → 修改相应来源或固定定义 → 重新生成受影响数据 → 校验 → 更新内容版本与复核记录 → 向 B、C 提供明确的新旧版本关系。不能只改题集 JSONL 而保留旧生成脚本，也不能只更新 manifest 哈希来掩盖正文、区间或证据错误。

本文和 `A测试.md` 是实现及组员操作入口；[需求文档](./A部分需求与开发顺序.md)保留验收要求，[阶段记录](./A部分阶段开发记录.md)保留历史过程，[交付说明](./A部分交付说明.md)汇总当前交付物。各文档中的当前版本以正式 manifest 与实际文件为准。
