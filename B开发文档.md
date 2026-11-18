# DERag：B 开发文档（已实现独立检索模块）

## 1. B 要完成什么

B 负责“清洗后的文档 → 两种分块 → embedding → 四组 Chroma 索引 → 语义检索与对照 API”这条链路。输入输出遵循 [开发文档.md](./开发文档.md)，本文件细化 B 的代码目录、算法、函数、接口、测试和交付方式。

B 可以先用固定测试文档独立开发并完成测试，不需要等待 A 的正式数据和 C 的问答代码。三人完成后，由 C 将 B 的实现接入正式程序；B 负责处理集成中出现的分块、模型、索引和检索问题。

A 一人负责全部官方文档核验和 30 道标准题，C 负责 LLM 回答、引用校验、正式评估、人工评分和页面接入。B 不编写法规题集、不生成法律答案；B 必须给出原文位置准确的检索证据，供 C 引用和评估。

**当前状态：B 独立模块已实现。**分块、四组 Chroma 索引、真实 embedding、检索 API、模型准备脚本和独立验证页已经落地；78 项独立自动测试通过。真实模型与干净虚拟环境验证记录见第 12 节和 `artifacts/b/`。正式入口 `app.main:app` 仍是 C 待集成的前端预览，不能将本次 B 模块测试等同于完整项目或正式 30 题评估。

## 2. B 的代码文件夹和文件职责

项目根目录为 `DERag/`。本机当前位置是 `E:/2027CityU/CS5481 Data Engineering/GroupProject/DERag/`，该绝对路径仅用于找到项目，不能写进代码或交付配置。

**B 的核心代码文件夹固定为 `DERag/app/retrieval/`。**HTTP 路由放 `app/api/`，命令行入口放 `scripts/`，自动测试放 `tests/`。不另建 `B项目/` 或第二套正式应用，不把所有业务塞进 `app/main.py`。

```text
DERag/
  开发文档.md                       # 三人的总契约，已有
  B开发文档.md                      # 本文
  app/
    __init__.py
    main.py                         # C 负责正式装配，B 不覆盖
    contracts.py                    # C 负责统一边界模型，B 独立开发不等待此文件
    config.py                       # C 负责统一配置加载
    retrieval/                      # B 核心代码目录
      __init__.py                   # 对外导出 build_indexes、search 等入口
      types.py                      # B 内部类型与协议；字段遵守总文档
      chunking.py                   # 固定窗口、结构感知、区间覆盖检查
      embedding.py                  # 本地模型加载、token 长度检查、批量编码
      vector_store.py               # Chroma 持久化适配、写入、读取、查询
      indexes.py                    # 四组构建、版本、manifest 和完成标记
      service.py                    # 文档读取、检索与同题对照服务
      errors.py                     # 模块错误，供路由转成统一状态码
    api/
      __init__.py
      documents.py                  # 文档摘要、正文与块预览路由
      indexes.py                    # 建库任务路由，任务管理器通过参数注入
      search.py                     # search 和 compare 路由
    static/                         # C 负责正式页面接入，B 不修改
  scripts/
    __init__.py
    fetch_embedding.py              # 下载固定 revision，校验模型文件
    build_indexes.py                # 读取配置，调用四组建库
  config/
    retrieval.example.json          # B 的独立配置样例，C 最终并入 experiment.json
  requirements-b.txt                # B 验证过的模块运行依赖，最终由 C 合并
  requirements-b-dev.txt            # B 的测试依赖，固定版本
  tests/
    fixtures/b/
      document.json                 # 合成文档，符合 A 的 Document 字段
      long_documents.json           # 长条文、多章节、Unicode 测试样本
      expected_hits.json            # 给 C 的合成 SearchHit 样例
    support/
      b_app.py                      # 仅用于 B 测试的 FastAPI 装配入口
      static/
        b_debug.html                # B 独立检索验证页，普通 HTML/CSS/JS
    test_chunking.py
    test_retrieval.py
    test_retrieval_api.py
  data/
    processed/                      # A 正式文档，B 只读
    chunks/{index_version}/         # B 导出的四组 JSONL
    chroma/{index_version}/          # B 生成的持久化索引
    indexes/{index_version}.json    # 配置、哈希、块统计和建库结果
  models/embedding/                 # 下载的模型文件，支持配置覆盖
  artifacts/b/                     # B 的测试与真实模型冒烟记录
```

上图是职责结构；B 的实现已创建其中自己负责的目录。正式法规原文、`gold.jsonl`、问答和评估模块不由 B 创建。`data/chroma/`、模型权重和临时产物不作为普通源码提交；样例配置、测试数据和重建脚本要提交。

### 2.1 各文件应做到什么

| 文件 | 输入 | 输出与职责 |
| --- | --- | --- |
| `chunking.py` | Document 和字符上限 | Chunk 列表；纯函数，不联网、不调用数据库。 |
| `embedding.py` | 文本列表、模型配置 | 与输入顺序一致的向量；加载一次模型，统一编码规则。 |
| `vector_store.py` | 向量、块 ID、少量标量元数据 | Chroma 存取；不负责切块和构造网页字段。 |
| `indexes.py` | 文档读取函数、四组条件、embedding 配置 | 四组构建、版本 manifest、可校验的 Chunk JSONL。 |
| `service.py` | 问题、条件、语料版本 | SearchHit 列表或两侧同题结果；从权威文档补齐来源字段。 |
| `app/api/*.py` | HTTP 请求、注入的服务 | 验证参数、调用业务函数、返回 JSON；不重复实现检索算法。 |
| `scripts/*.py` | 参数或配置文件 | 调用同一业务函数，打印可读结果和错误，失败返回非零退出码。 |

B 独立测试时使用 `tests/support/b_app.py` 装配 router、样本文档读取器和内存任务管理器，并提供 `/b-debug` 页面。验证页代码放在 `tests/support/static/b_debug.html`，与 C 的 `app/static/` 正式前端分开。最终 C 在 `app/main.py` 中注入真实依赖并注册同一组业务 router，正式页面调用相同 API。

## 3. 固定实验条件

| 条件 | 分块方法 | 最大字符数 |
| --- | --- | ---: |
| `f400` | 固定窗口 `fixed` | 400 |
| `s400` | 法条结构感知 `structured` | 400 |
| `f800` | 固定窗口 `fixed` | 800 |
| `s800` | 法条结构感知 `structured` | 800 |

主比较为 F400/S400 和 F800/S800。四组使用相同冻结正文、embedding 模型及 revision、归一化、向量库引擎与参数、cosine 距离和 top-5 检索。所有条件无重叠、不跨文档；不能为了某个条件命中更高而加 rerank、换提示前缀或调整模型。

字符数使用 Python `len(text)`，含条号、标点和换行。B 收到 A 的正文后不做 `strip()`、换行替换或二次清洗，避免原文坐标失效。

## 4. 统一输入与输出

当前活动语料为英文 `fixture-en-v2`，分块规则为 `structure-offset-v2`。旧中文短样例单独保存为 `legacy_zh_document.json`，仅用于 Unicode/旧 ID 回归，不能向当前服务请求旧版本。

### 4.1 输入 Document

B 使用 A 输出的 `data/manifest.json` 和处理后 Document。独立开发期间直接使用以下合成样例，不冒充正式法规：

```json
{
  "schema_version":"1.0",
  "document_id":"fixture",
  "corpus_version":"fixture-en-v2",
  "title":"Synthetic API Contract Fixture (not official legislation)",
  "issuer":"Synthetic test data",
  "source_url":"https://example.org/fixture",
  "published_at":null,
  "effective_at":null,
  "raw_path":"tests/fixtures/b/raw.txt",
  "raw_sha256":"b65e8b1fa799c486a1340e674d420e133eab935dd801757d40991be24dee3b09",
  "text":"Article 1 A.\nArticle 2 B.",
  "articles":[
    {"article_id":"fixture-a001","label":"Article 1","chapter":null,"section":null,"start":0,"end":12},
    {"article_id":"fixture-a002","label":"Article 2","chapter":null,"section":null,"start":13,"end":25}
  ]
}
```

正文 25 字符；Article 2 是 `[13,25)`，其中 `B.` 是 `[23,25)`。上面的原始哈希仅对应正文 UTF-8、LF、无 BOM 字节。

正式读取时校验：语料版本一致、文档 ID 唯一、哈希正确、条文区间在正文范围内、同一文档条文有序且不重叠。解析不合法则报错，不能自己修正文档后继续实验。测试样例使用 `fixture-en-v2`，正式语料使用总文档规定的真实版本哈希。

### 4.2 输出 Chunk

```json
{
  "chunk_id":"ecc55790d61808b33e0ec4cb33471f7e520a6af4dd26c2ebdd083d2ed80a18ac",
  "corpus_version":"fixture-en-v2",
  "condition":"s400",
  "boundary_method":"structured",
  "target_chars":400,
  "document_id":"fixture",
  "article_ids":["fixture-a001","fixture-a002"],
  "start":0,
  "end":25,
  "text":"Article 1 A.\nArticle 2 B."
}
```

`chunk_id` 的原始字符串为：

```text
corpus_version|boundary_method|target_chars|document_id|start|end
```

对这个字符串做 UTF-8 SHA-256，返回完整小写十六进制。例：`fixture-en-v2|structured|400|fixture|0|25` 对应上面的 ID。不使用 Python 内置 `hash()`、随机 UUID 或顺序编号。

`article_ids` 按原文顺序记录与块实际相交的条文，判定为 `max(chunk.start, article.start) < min(chunk.end, article.end)`。只含标题或空白的块允许此数组为空，不能捏造条号。

### 4.3 输出 SearchHit

```json
{
  "rank":1,
  "score":0.9,
  "chunk_id":"ecc55790d61808b33e0ec4cb33471f7e520a6af4dd26c2ebdd083d2ed80a18ac",
  "corpus_version":"fixture-en-v2",
  "condition":"s400",
  "document_id":"fixture",
  "article_ids":["fixture-a001","fixture-a002"],
  "start":0,
  "end":25,
  "text":"Article 1 A.\nArticle 2 B.",
  "title":"Synthetic API Contract Fixture (not official legislation)",
  "source_url":"https://example.org/fixture",
  "article_labels":["Article 1","Article 2"]
}
```

`rank` 从 1 开始。Chroma cosine 距离按升序排列，统一 `score=1-distance`；分数越大越相关，但不是概率。样例分数是测试值。相同距离的已返回候选按 `chunk_id` 排序，查询的并列边界可能受近似索引影响，必须在运行说明中记录。

C 使用此对象加上本轮 `n` 构造引用；B 不自行生成回答或会话引用号。`article_labels` 从 A 的条文表取，不凭块正文猜测。

## 5. 两种分块方法如何实现

### 5.1 固定窗口

1. 校验上限为正整数；空正文返回空列表并记录空文档状态。
2. 从 `start=0` 开始，每次取 `end=min(start+max_chars, len(text))`。
3. 块文本必须直接用 `text[start:end]`，计算 ID 与覆盖条文后保存。
4. 下一块从前一块的 `end` 开始，不重叠、不去空白。最后一块允许小于上限。

英文样例用 16 字符上限测试时必须得到 `[0,16)`、`[16,25)`，再拼接得到原文。正式实验仍只用 400/800。

### 5.2 法条结构感知

优先使用 A 提供的条文位置。章节识别只在标题行或条文间隙中进行，不能把正文里的“依照第十条”误认为新条文边界。

1. 在原文上建立结构单元，不复制清洗过的句子。单元保留 `start/end`、章/节身份和条文 ID。
2. 章/节标题归入其后内容；普通条间空白归入前一单元。遇新章/节前结束上一单元，不能让前一条吞掉下一章标题。
3. 在同章同节内按原文顺序贪心合并：加入下一完整单元后不超上限就合并，超上限则先输出当前块。无章/节信息按同一组处理。
4. 单条本身超上限时，优先在 `。！？；` 和明确段落边界处按原文坐标拆分；保留标点和换行，不做 `join()` 重建文本。
5. 单句超过上限则硬切，并记录 `long_sentence_fallback` 次数。标题加首条超长时允许标题单独成块，但仍不得超上限或漏字。
6. 无条文标注时按段落/句子边界构造单元再打包，记录 `no_article_fallback`，不能静默转用另一份正文。

为避免不同实现产生不一致结果，先把“正文完整覆盖、块长上限、章/节边界”写成测试断言，再写打包循环。英文样例在 16 字符测试上限下应为 `[0,13)`、`[13,25)`；400 上限下两条能装进一个 `[0,25)` 块。

### 5.3 两种方法都必须满足的断言

- 每个块 `0 <= start < end <= len(text)`，`end-start <= max_chars`，`chunk.text == text[start:end]`。
- 同条件、同文档按位置排序后，第一块从 0 开始，后一块从前一块 `end` 开始，最后到正文末尾。
- 所有块文本拼接必须等于原文；空文本单独处理，不制造空块。
- 输入相同，块列表、位置和 ID 稳定；换语料版本后 ID 跟着变化。
- 结构法尽量保留完整条文，但不预设检索一定优于固定窗口。实际优势由最终评估验证。

## 6. embedding 模型与可复现环境

### 6.1 模型选择原则

本次采用并实测 `BAAI/bge-m3`：支持中英文、可使用稠密向量，其公开规格为 1024 维、较长输入窗口，适合避免 800 字文本块被短窗口模型截断。它在 CPU 上的下载和编码成本高于小模型，本次已在 Windows / Python 3.13.11 / CPU 上完成真实安装、加载、四组建库与检索验证；模型 revision 固定为 `5617a9f61b028005a4858fdac845db406aefb181`，权重约 2.27 GB。

可通过 `sentence-transformers` 加载候选模型，Chroma 使用本地持久化客户端。B 必须确认 Python 3.13/Linux CPU 的依赖可以安装，再填写具体锁定版本。本次安装版本已锁在 `requirements-b.txt` 与 `requirements-b-dev.txt`；原 `requirements.txt` 仍是预览入口依赖。Linux CPU / Docker 尚未实测，不将 Windows 验证写成跨平台验证。

最终模型 ID、不可变 revision、模型文件哈希、维度、最大输入 token 数、归一化、查询/文档前缀和池化策略全部写进配置和索引 manifest。仅使用稠密向量，不额外引入模型的稀疏检索或多向量能力。

### 6.2 不能忽略的输入截断

400/800 的单位是 Python 字符，模型输入上限的单位是 tokenizer token，两者不同。下载模型后，对所有块加实际前缀进行分词，检查特殊 token 加上正文是否超过模型有效上限。

**禁止静默 truncation。**超限时直接报告文档 ID、块 ID、token 数和模型上限，要求在正式实验前修正统一模型配置；不能只给某组截掉后半段，也不能悄悄改变那组块长。问题本身也要检查长度并给出可读错误。若最终换模型，四组全部重建并使用同一新配置。

### 6.3 下载、缓存与依赖

- `scripts/fetch_embedding.py` 显式下载固定 revision 到配置路径，完成后生成文件清单及哈希；正式加载优先读取这个路径。
- 支持 `DERAG_MODEL_DIR` 覆盖目录；源码和容器使用同一规则，不依赖 `C:/Users/某人/.cache/` 已有权重。
- 独立模块依赖写入 `requirements-b.txt`，包括经过测试的直接与间接运行版本；测试依赖写入 `requirements-b-dev.txt`，与运行依赖一起验证。C 最终解决三个模块依赖冲突并合并到项目锁定清单。
- 模型首次下载通常需要联网。离线复现要提供权重或可访问的固定模型包及其校验信息，并遵守模型许可；只有源码和空模型目录不能离线运行 embedding。
- 测试不要求 GPU。编码批次可配置以适应内存，不能因换批次顺序弄乱文本与向量对应关系。

## 7. 四组索引如何构建与检索

### 7.1 build_indexes 构建流程

1. 读取传入的文档加载函数，校验 A 的数据版本和 manifest。独立测试中注入 fixture 加载函数。
2. 读取有效 embedding/检索配置，构造索引版本材料，使用规范 JSON 的 SHA-256 得到 `index_version`。
3. 为四个条件各生成完整 Chunk 列表，验证覆盖断言，保存 JSONL 与统计。
4. 使用同一 embedding 实例编码四组块；若文本相同可在同版本、同模型内复用编码缓存，但各自保留条件与块 ID。
5. 在 `data/chroma/{index_version}/` 建立四个 collection：`kb_f400`、`kb_s400`、`kb_f800`、`kb_s800`，明确配置 cosine 度量。
6. 以 `chunk_id` 写入向量和最小元数据；使用该版本 Chroma 支持的 create/upsert/query API，并写测试验证。不要假设 Python 列表能直接作为 collection metadata，`article_ids` 等权威内容保留在 Chunk JSONL 中。
7. 四组全部写入并核对数量后，索引 manifest 标为 `completed`。中途失败记录 `failed`，服务不得把半成品索引用于正式查询。

`index_version` 至少覆盖 `corpus_version`、分块实现版本、条件列表、模型 ID/revision/文件哈希、维度、归一化、前缀、截断策略和向量库有效配置。规范 JSON 用 `ensure_ascii=False, sort_keys=True, separators=(',', ':')` 编码。与运行机器相关的缓存绝对路径、创建时间和耗时不进入版本哈希，但保留在诊断记录中。

相同版本重复构建时，已完成且校验正常可直接复用；失败版本重试必须清理本次未完成状态或幂等覆盖，不能重复插入。新版本写到新目录，旧索引不被静默覆盖。查询与建库加适当锁，避免同一索引在写入中被读取。

### 7.2 search 检索流程

1. 校验问题非空、条件合法、`top_k` 为 1–5；核对请求语料与激活索引版本。
2. 对问题按固定 query 前缀编码，使用与文档相同模型、revision 和归一化规则。
3. 查询对应 collection，结果不足 5 个时原样返回实际数量，不补样例块。
4. 从 Chunk 和 Document 中补齐权威文本、区间、标题、官方来源及条号，检查块与冻结原文切片一致。
5. 转成第 4.3 节 SearchHit，记录实际查询耗时。索引未准备好和检索无命中必须区分。

只有已完成索引可被激活。检索不能调用 LLM、使用标准答案筛选结果或读取 `gold.jsonl` 帮助排名。30 题的正式 hit@k 和答案指标由 C 计算，B 只提供可验证证据与运行统计。

### 7.3 compare 对照流程

同一问题、同一 `corpus_version`、同一 `index_version` 下依次查询两侧条件，各返回最多 5 个块。左侧或右侧出错时返回明确错误，不用另一侧结果补齐。每侧同时返回 `context_chars=sum(len(hit.text))` 和检索耗时，便于解释块数相同但实际上下文长度不同。

## 8. 对外函数与 API 样例

### 8.1 C 调用 B 的函数

```python
build_indexes(corpus_version) -> IndexManifest
search(question, condition, corpus_version, top_k=5) -> list[SearchHit]
```

服务初始化时注入 `document_loader`、`embedder`、`vector_store_factory` 和配置。B 独立测试提供假实现，C 集成时替换成 A 的加载器与真实组件，不要求 C 改动检索内部代码。

路由通过工厂接收服务与任务管理器，例如 `create_retrieval_routers(service, task_manager)`；返回的 router 由 C 注册。不要在导入 Python 模块时直接下载模型或建索引。

### 8.2 B 负责的 HTTP 接口

| 路径 | 行为 |
| --- | --- |
| `GET /api/documents?corpus_version=...` | 返回 `{"items":[...]}`，摘要字段固定为 `document_id`、`title`、`source_url`、`corpus_version`、`article_count`、`char_count`。 |
| `GET /api/documents/{id}?corpus_version=...` | 返回完整 Document。 |
| `GET /api/documents/{id}/chunks?condition=s400&corpus_version=...` | 返回 `{"items":[Chunk...]}`，不得重新运行另一套浏览器切分逻辑。 |
| `POST /api/indexes/build` | 输入语料版本，提交四组建库任务，返回 202 和任务 ID。 |
| `POST /api/search` | 返回一个条件的语义检索结果。 |
| `POST /api/compare` | 返回两个条件的同题 top-5 对照。 |

建库请求与响应：

```json
{"corpus_version":"fixture-en-v2"}
```

```json
{"task_id":"index-task-1","state":"queued"}
```

C 提供正式的 `GET /api/tasks/{id}`。B 在独立 API 测试中提供内存任务适配器，状态采用 `queued|running|completed|failed`，不为了等待 C 而放弃接口测试。正式 `build_indexes()` 本身可同步返回 manifest，HTTP 层负责把它提交为后台任务。

检索请求：

```json
{"question":"What does Article 2 say?","corpus_version":"fixture-en-v2","condition":"s400","top_k":5}
```

完整合成响应，分数与耗时只用于接口测试：

```json
{
  "corpus_version":"fixture-en-v2",
  "index_version":"fixture-index-v1",
  "condition":"s400",
  "hits":[{
    "rank":1,
    "score":0.9,
    "chunk_id":"ecc55790d61808b33e0ec4cb33471f7e520a6af4dd26c2ebdd083d2ed80a18ac",
    "corpus_version":"fixture-en-v2",
    "condition":"s400",
    "document_id":"fixture",
    "article_ids":["fixture-a001","fixture-a002"],
    "start":0,
    "end":25,
    "text":"Article 1 A.\nArticle 2 B.",
    "title":"Synthetic API Contract Fixture (not official legislation)",
    "source_url":"https://example.org/fixture",
    "article_labels":["Article 1","Article 2"]
  }],
  "timing_ms":10
}
```

对照请求：

```json
{"question":"What does Article 2 say?","corpus_version":"fixture-en-v2","left_condition":"f400","right_condition":"s400"}
```

对照响应顶层为 `question`、`corpus_version`、`index_version`、`left`、`right`。左右各含 `condition`、完整 `hits` 数组、`timing_ms` 和 `context_chars`；样例正文很短，F400/S400 都能返回全文，文本相同是正常结果。用长条文样例才能观察切分差异。

### 8.3 错误规范

| 场景 | HTTP | `code` 示例 |
| --- | ---: | --- |
| 问题为空、非法 condition 或 top_k | 422 | `INVALID_REQUEST` |
| 文档或任务不存在 | 404 | `NOT_FOUND` |
| 未建库、构建未完成、请求版本不一致 | 409 | `INDEX_NOT_READY` / `VERSION_MISMATCH` |
| 模型文件未准备好或外部下载失败 | 503 | `EMBEDDING_UNAVAILABLE` |
| 正文位置损坏、输入超模型上限 | 409 | `SOURCE_MISMATCH` / `MODEL_INPUT_TOO_LONG` |

错误体统一为 `{"code":"...","message":"可读说明"}`。未预期的程序错误返回 500 并写服务器日志，不伪装成“没有找到证据”。API 参数校验错误需要显式转换为总文档的统一错误格式，不能一部分返回 `detail`、另一部分返回 `message`。

## 9. B 如何独立测试

| 测试 | 样例与预期 | 是否需要下载模型 |
| --- | --- | --- |
| 原文覆盖与 ID | 25 字英文样例，以及保留的 13 字中文回归样例；验证完整覆盖与固定哈希。 | 否。 |
| 固定窗口边界 | 刚好 400、401、800、801 字符，含空格、换行、emoji。 | 否。 |
| 结构边界 | 相邻短条、超长条、跨章/节、条文内引用其他条号、无条号文本。 | 否。 |
| 长句回退 | 单句超上限，确保硬切但不漏字符，回退次数被记录。 | 否。 |
| 向量适配 | 注入固定向量，核对写入数量、文本/向量顺序和 cosine 换算。 | 否，可用临时真实 Chroma。 |
| 幂等与版本 | 连续建两次同版本不重复；旧索引拒绝新语料；失败索引不能查询。 | 否。 |
| API | 参数错误、任务状态、文档读取、单侧对照失败、返回字段与区间一致。 | 否。 |
| 真实模型冒烟 | 干净环境下载固定 revision，CPU 编码、四组建库、运行搜索；验证 token 检查和实际维度。 | 是，首次联网或提供固定权重包。 |

真实模型检索测试要验证语义相关内容可返回、向量有效、结构字段正确；不要把某个语义问题的精确浮点数写成跨平台必须相等的断言。模拟测试输出不能作为正式四组实验结果。

为了让 C 能直接验证契约，B 将上面样例存入 `tests/fixtures/b/`，同时附一份 `expected_hits.json`。测试块 ID、文档位置和官方来源字段必须与输入一致；不能只交一张“能检索”的截图。

### 9.1 独立开发命令约定

以下入口已实现。创建自己的项目 `.venv` 后在项目根目录使用该虚拟环境的 Python：

```bash
python -m pip install -r requirements-b.txt -r requirements-b-dev.txt
python -m pip check
python -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py
```

模型准备与四组建库脚本约定支持 `--config` 和测试 fixture 模式：

```bash
python -m scripts.fetch_embedding --config config/retrieval.example.json
python -m scripts.build_indexes --config config/retrieval.example.json --fixtures
```

`--fixtures` 明确选择 `tests/fixtures/b/`，不能写入正式数据目录；不带该参数读取 A 的正式 manifest，找不到时应报错。测试索引与真实索引物理隔离，不能只靠页面标签区分。

独立 API 和检索验证页预览入口：

```bash
python -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

如采用这个模块路径，需要在 `tests/` 和 `tests/support/` 加包标识，保证命令能导入。启动后打开 `http://127.0.0.1:8767/b-debug` 查看 B 的检索验证页，`/docs` 用于 API 自测。该入口已实现并完成网页操作验证；C 最终注册同一组业务 router 到正式 `app.main:app`。

### 9.2 独立测试如何体现在前端

B 实现一个简单的独立验证页即可，无需等待 C 完成完整问答页面。该页用普通 HTML/CSS/JavaScript，由测试服务同源提供，使用 `fetch()` 调用 B 的真实 API；不新增 Node 构建环境，不依赖 CDN。样本输入和结果通过 `textContent` 安全展示。

| 页面区域 | 用户可以操作什么 | 展示哪些验证结果 |
| --- | --- | --- |
| 运行状态 | 查看启动模式、语料和模型状态 | `mock`/`real`、测试语料标识、模型 ID/revision、索引版本、四组就绪状态。 |
| 文档与分块 | 选择测试文档及 F400/S400/F800/S800 | 原文、各块文本、块 ID、覆盖条号、`start/end`、长度和块数。 |
| 建库 | 点击“建立四组测试索引” | 任务进度、各组块数和失败原因；完成前禁止搜索。 |
| 单组搜索 | 输入问题并选择一个条件 | top-5 原文块、相关分数、条号、来源、字符位置和检索耗时。 |
| 同题对照 | 选择左右条件后提交同一个问题 | 两侧检索块并排展示，各自块长、返回字符总数、分数和耗时。 |
| 原文核对 | 点击某个结果的“查看来源片段” | API 返回的原文片段、文档 ID、条号和区间；不在浏览器重新计算 Python 字符位置。 |

**完整演示步骤：**启动 B 测试服务 → 打开 `/b-debug` → 选择合成长文档 → 建立四组索引 → 预览两种切分 → 输入问题 → 查看单组命中 → 查看同题对照 → 打开片段核对位置。使用长条文样本展示边界差异；25 字英文样例主要验证字段和位置，不应强行做出不同效果。

#### 两种启动模式

- `mock`：默认模式。使用 B 自带合成文档和固定测试向量，实际运行切分、索引适配与 API；无需下载 embedding，也不调用 LLM。页面明显标记“模拟 embedding，仅供接口与流程验证”，不能把排序展示成真实语义检索效果。
- `real`：仍使用 B 自带测试文档，但通过固定 revision 的真实 embedding 编码并写入隔离的测试索引。页面明确标记“真实 embedding + 合成测试语料”；不需要 A 的正式文档或 C 的问答服务。这一模式用于证明模型、向量库和检索链路确实运行。

模式通过测试服务专用环境变量 `DERAG_B_DEBUG_MODE=mock|real` 在启动时设置。进入 `real` 前按第 9.1 节准备模型；权重缺失、输入超限或建库失败应显示具体错误，不自动回退到 `mock`。模式切换后清空页面旧结果，索引目录按模式与版本隔离，避免误用另一模式的缓存。

PowerShell 中选择真实模型验证模式的启动约定：

```powershell
$env:DERAG_B_DEBUG_MODE = 'real'
python -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

上述命令已可使用；模型配置读取 `config/retrieval.example.json`，路径仍支持项目环境变量覆盖。测试服务导入时不自动下载权重或开始建库。

#### 页面与 API 的对应关系

页面文档与分块区域调用 `/api/documents` 及 `/api/documents/{id}/chunks`；建库调用 `/api/indexes/build`，用测试任务管理器提供的 `/api/tasks/{id}` 查询状态；单组搜索调用 `/api/search`；左右对照调用 `/api/compare`。所有业务均使用 B 的同一套服务函数，不为展示另写一套切分或排序逻辑。

测试服务可增加只读 `/b-debug/status`，返回模式、合成语料版本、模型配置和索引状态，仅用于验证页引导，不属于生产 API 契约。完整原文片段来自已有文档/检索响应；页面没有独立的生成答案或正式指标入口。

#### 页面验收

1. `mock` 模式在空模型缓存环境可启动，能实际切块、建测试索引并展示结果。
2. `real` 模式使用真实模型完成同一流程，明确保留模型版本和运行记录；API 测试仍是自动化验收依据，页面补充可视化验证。
3. 建库状态、无结果、加载中和错误均可见；切换文档/条件或提交新问题时不继续展示旧结果冒充新结果。
4. 截图或录屏标明模式、测试语料与条件；合成文档和模拟向量产生的结果不进入最终法规实验报告。
5. C 集成时复用 B 的 API 和服务，将交互接到正式文档库/对照页面；独立验证页保留在测试目录，B 的正式交付不要求 C 复制这张页面。

## 10. 配置与给老师复现

B 使用 `config/retrieval.example.json` 独立开发，集成后由 C 将同名配置键合入 `config/experiment.json`。

| 配置键 | 要求 |
| --- | --- |
| `corpus_version`、`conditions`、`top_k` | 正式为 A 冻结版本、四组条件和 5。 |
| `embedding.model_id`、`embedding.revision` | 实际模型 ID 和不可变 revision；不使用 `main/latest` 作为最终版本。 |
| `embedding.model_dir`、`embedding.device` | 项目相对路径或容器挂载路径，基线 CPU；支持 `DERAG_MODEL_DIR`。 |
| `embedding.dimension`、`embedding.normalize` | 与真实输出一致；索引和查询保持相同。 |
| `embedding.query_prefix`、`embedding.document_prefix` | 按模型要求固定，空前缀也显式记录。 |
| `embedding.max_input_tokens` | 实际验证的有效输入上限，tokenizer 检查包括特殊 token。 |
| `retrieval.metric`、`retrieval.chunker_version` | `cosine` 和分块实现版本，不能凭时间自动生成算法版本。 |

不得依赖个人全局 Python 包、私人在线 embedding 服务或个人下载缓存。数据根目录支持 `DERAG_DATA_DIR`；配置优先级与总文档一致：显式参数 → 环境变量 → 配置文件，实际生效值写入记录。

B 完成前至少在空虚拟环境或干净 Linux CPU 容器中验证一次安装、模型加载、四组建库和检索。最终 C 负责完整 Docker 镜像，但 B 需提供准确依赖和模型准备脚本，保证容器不需要访问 B 的本机服务。当前预览版 `DE.tar` 不包含这些能力。

## 11. 交给 C 的内容与验收

B 独立完成后提交一个可审阅 PR，至少包含：

1. `app/retrieval/` 全部核心代码、三个 API 模块、模型下载和建库脚本，以及 `tests/support/b_app.py` 和 `tests/support/static/b_debug.html` 独立验证页。
2. 锁定依赖、配置样例、模型 ID/revision/文件清单及 CPU 运行说明。
3. 通过总文档字段校验的 Document/Chunk/SearchHit 样例。
4. 自动测试结果，以及真实 embedding + Chroma 冒烟命令与输出。
5. 四组索引 manifest 示例：版本材料、块数、最小/平均/最大块长、回退次数、建库耗时、模型和向量库配置、完成状态。
6. 已知限制，例如模型体积、CPU 内存占用、下载是否联网和近似检索排序差异；不能把未验证环境写成已支持。

C 合并后只需注入 A 的真实文档加载器、项目配置和任务管理器，注册 B 的 router，再用真实语料重建索引；问答与评估统一调用 B 的 `search()`。C 不重写 B 的算法，B 不为了集成改动 A 的标准答案。

**B 的最终完成标准：在不使用 A/C 实现的情况下通过独立测试与真实模型冒烟；在集成时按同一契约读取 A 的正式文档，并为 C 返回原文可定位的四组检索证据。**


## 12. 本次实现与可复制的验收步骤

### 12.1 已落地的文件

- 核心逻辑：`app/retrieval/` 的 `types.py`、`chunking.py`、`embedding.py`、`vector_store.py`、`indexes.py`、`service.py`、`errors.py`。
- 路由工厂：`app/api/`，包含文档、建库、检索与对照。生产入口尚未注册，C 集成后复用。
- 独立验证入口：`tests/support/b_app.py`，验证页 `tests/support/static/b_debug.html`。
- 命令行：`scripts/fetch_embedding.py`、`scripts/build_indexes.py`、`scripts/smoke_embedding.py`。
- 冻结样例：`tests/fixtures/b/`；合成文本明确标记为测试，未创建正式标准题。
- 依赖锁：`requirements-b.txt` 与 `requirements-b-dev.txt`。原 `requirements.txt` 保留给现有预览应用，C 合并时再统一。

没有在导入模块时下载模型或建库；没有依赖全局 Python 包、私人模型服务、LLM Key 或个人 Hugging Face 缓存。
`DERAG_DATA_DIR`、`DERAG_MODEL_DIR`、`DERAG_RETRIEVAL_CONFIG` 支持覆盖；CLI 的 `--data-dir` / `--model-dir` / `--config` 优先。
`.env` 不自动读取，PowerShell 请使用 `$env:变量名` 注入。

### 12.2 第一次安装（Windows PowerShell）

先安装 Python 3.13.11，在 `DERag` 项目根目录执行。已有项目 `.venv` 可跳过第一行。

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-b.txt -r requirements-b-dev.txt
.\.venv\Scripts\python.exe -m pip check
```

安装需要网络和磁盘空间；这些都是公开依赖，无需复制开发者的虚拟环境。
已创建独立的 `.venv-b-verify` 并安装两份依赖锁；原安装曾通过 `pip check`，英文迁移后再次执行自动测试与真实模型脚本，结果见当前记录。
已验证环境是 Windows / Python 3.13.11 / CPU。Linux 容器尚未实测；原 `DE.tar` 仍是前端预览包。

### 12.3 自动测试（不下载 embedding）

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py -q
```

预期 `78 passed`。测试使用真实临时 Chroma 和测试向量，覆盖分块区间、Unicode、章节、长句回退、幂等建库、失败重试、索引/原文损坏、模型缺失、token 超限、API 字段和错误格式。结果是模块正确性测试，不是法规问答准确率。
`pytest.ini` 将测试临时目录放在项目内 `artifacts/b/.pytest/`，避免依赖个人临时目录权限；该目录会由 pytest 清理，勿放个人文件。

### 12.4 先用网页验收（默认 mock，无需模型）

```powershell
$env:DERAG_B_DEBUG_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

打开 <http://127.0.0.1:8767/b-debug>，API 文档为 <http://127.0.0.1:8767/docs>。
按以下顺序操作：选择“合成数据保护规则” → 点击“建立四组测试索引” → 选择 F400/S400 查看边界 → 检索默认问题 → 左右对照 → 点击“查看来源片段”。所有块来自服务端，不在浏览器重新切分或按 JavaScript 字符串下标截取原文。

API 也可以在另一个 PowerShell 窗口调用：

```powershell
$body = @{ question='How can an individual request deletion of personal information?'; corpus_version='fixture-en-v2'; condition='s400'; top_k=5 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8767/api/search' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

默认服务必须先从网页建库。也可提前执行：

```powershell
.\.venv\Scripts\python.exe -m scripts.build_indexes --config config/retrieval.example.json --fixtures --mock
```

### 12.5 真实模型验收

先停止 mock 服务（Ctrl+C），首次执行模型准备。权重约 2.27 GB，连同分词器约 2.3 GB，首次需联网；文件哈希保存在模型目录的 `derag-model-manifest.json`，复核副本在 `artifacts/b/model-manifest.json`。

```powershell
.\.venv\Scripts\python.exe -m scripts.fetch_embedding --config config/retrieval.example.json
.\.venv\Scripts\python.exe -m scripts.build_indexes --config config/retrieval.example.json --fixtures
.\.venv\Scripts\python.exe -m scripts.smoke_embedding --config config/retrieval.example.json
$env:DERAG_B_DEBUG_MODE = 'real'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

`smoke_embedding` 会复用校验通过的完整索引，并运行四条件 × 三问题共 12 次真实检索检查、实际 1024 维向量检查、真实 tokenizer 超限拒绝、HTTP 检索及对照检查。成功输出 `PASS`，详见 `artifacts/b/real-smoke.json`。
合成文本有重复内容，精确浮点数不作为跨平台断言；只检查主题相关证据及字段契约，不将此处的成功比例写成正式评估指标。
第一次 CPU 模型导入、加载和编码较慢，应等待命令返回；没有自动降级为 mock 的逻辑。

若要让干净环境从空索引完整重建，可指定独立数据根目录：

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke_embedding --config config/retrieval.example.json --data-dir data/b-clean-verification --output artifacts/b/clean-real-smoke.json
```

本次实现使用相同固定 revision、CLS 池化、空前缀、1024 维、归一化、8192 token 上限、CPU、4 条批次与 4 CPU 线程。四条件一律相同。Chroma 1.5.9 使用 cosine、`ef_construction=100`、`ef_search=100`、`max_neighbors=16`、`num_threads=1`、`batch_size=2`、`sync_threshold=2`、`resize_factor=1.2`，有效设置写入索引版本材料。较低同步阈值确保小样本建库后的索引能被后续 HTTP 请求读取，代价是正式语料建库写盘较频繁；若统一改参数，四组必须重新构建。

### 12.6 C 的最小接入方法

```python
from app.api import create_retrieval_routers, install_retrieval_error_handlers
from app.retrieval import RetrievalService
from app.retrieval.embedding import LocalEmbedder
from app.retrieval.types import load_config

config = load_config()  # C 换为统一配置适配；传入相同字段即可
service = RetrievalService(
    document_loader=A_load_documents,  # A 的函数，签名 (corpus_version) -> list[dict]
    embedder=LocalEmbedder(config['embedding']),
    config=config,
)
install_retrieval_error_handlers(app)
app.include_router(create_retrieval_routers(service, task_manager))
# C 问答直接使用 service.search(question, condition, corpus_version, top_k=5)
```

`A_load_documents`、`task_manager` 是 C 装配时注入的变量，不是 B 自行实现的正式模块。A 若返回 Pydantic Document，适配器用 `model_dump()` 转为字典。B 内置 `formal_loader(Path(config['data_dir']))` 也可读取按总文档生成的正式 manifest；会验证原始文件、处理文件、正文、条文和语料版本哈希。

任务管理器需实现 `submit(function, background_tasks) -> {'task_id': ..., 'state': 'queued'}`：接收无参数同步建库函数，把任务交给自己的后台执行器，记录结果/失败原因，立即返回 queued；C 提供生产版 `/api/tasks/{id}`。B 的 `MemoryTaskManager` 展示了完整适配器行为，但仅供单进程测试，重启会丢任务，不作为生产任务持久化。

正式数据不能带 `--fixtures`；将配置 `corpus_version` 换为 A 的真实版本，再执行不带该标志的建库命令。缺少 A 的 manifest 会明确报错，禁止自动使用样例补齐。
实际索引由当前 corpus + 配置的确定性版本定位，不自动选择“最近一次”索引；仅四组完成的同一版本可查询。B 当前采用数据根目录文件锁串行化建库与检索，适用于课程实验；高并发服务需另行设计。

### 12.7 已保存证据与当前边界

- `artifacts/b/tests.xml`：干净虚拟环境的 78 项 pytest 结果。
- `artifacts/b/real-smoke.json`：真实 CPU 模型、四组 manifest、检索快照和 API 输出。
- `artifacts/b/clean-real-smoke.json`：干净环境从隔离索引目录完整重建的记录。
- `artifacts/b/model-manifest.json`：模型 commit 与逐文件 SHA-256。
- `artifacts/b/frontend-smoke.json`、`debug-mock.png`、`debug-mobile.png`：浏览器完成建库、搜索、对照、原文弹窗与输入变更清空旧结果的记录。验证页在桌面与 390px 窄屏检查，无 JavaScript 错误、无横向溢出。

当前未接入 A 的官方文档、C 的 LLM 回答和 30 道标准题正式评估。合成数据来源使用 `example.org`，只验证引用字段和原文区间，不能充当官方法条。Chroma 是近似检索，同距离已返回候选按 chunk_id 排序，top-k 并列边界可能随平台略有差异。
模型权重与生成的索引已被 Git 忽略；上传 GitHub 后组员按本节依赖安装与模型准备命令复现。离线交付需另带固定权重目录及依赖包或最终镜像，C 负责最后 Docker 集成。
