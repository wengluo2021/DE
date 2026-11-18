# B 模块测试指南（组员使用）

本指南用于从 GitHub 获取项目后，独立测试 B 的分块、向量索引、检索 API 和浏览器验证页面。主要命令适用于 **Windows PowerShell + Python 3.13.11 + CPU**，这是目前实际验证通过的环境。

**建议顺序：获取代码 → 安装依赖 → 自动测试 → mock 页面 → 准备模型 → 真实模型测试 → real 页面。**

不需要复制开发者的虚拟环境、不需要开发者电脑的 Python 路径，也不需要 API Key。组员在自己的电脑建立环境，由依赖锁文件安装相同版本的软件；模型由脚本准备到项目目录。

## 1. 这份指南可以测什么

| 测试内容 | 具体检查 |
| --- | --- |
| 两种分块 | 固定窗口、法条结构感知；字符完整覆盖、不超长、位置准确 |
| 四组条件 | F400、S400、F800、S800；同一正文、同一模型及检索设置 |
| 向量入库 | 真实 Chroma 持久化、重复建库、失败重试、版本及文件完整性 |
| 单组检索 | 英文问题编码、top-5 命中、文档与条文信息 |
| 同题对照 | 同一个问题分别在两组索引中检索，左右展示结果 |
| 来源追溯 | 返回的片段与冻结正文的 `[start,end)` 切片一致 |
| 模型保护 | 模型缺失明确报错；输入 token 超限时拒绝推理 |
| HTTP 接口 | 请求字段、错误格式、建库任务、文档及检索接口 |

当前入库的是 **英文合成测试规则**，版本为 `fixture-en-v2`，不是官方法规。它们用于验证 B 模块；A 的官方文档和 30 道标准题、C 的答案生成及引用支持性评估尚未在这里完成。

页面能返回证据，不代表已经调用大模型生成法律答案。当前 `DE.tar` 和原 Dockerfile 对应前端预览，测试 B 请按本指南使用 Python 入口。

## 2. 获取代码，确认所在目录

先安装 Git 和 Python 3.13，推荐与验证环境一致的 **Python 3.13.11**。不需要安装 CUDA 或准备 GPU。

第一次获取仓库，在自己选定的父文件夹执行：

```powershell
git -c core.autocrlf=false clone https://github.com/wengluo2021/DE.git DE
cd DE
git config core.autocrlf false
git rev-parse --short HEAD
```

`DE` 是克隆后的文件夹名；本机开发时叫 `DERag`，两者不影响运行。**后续所有命令都在含有 `app`、`tests`、`config` 和 `requirements-b.txt` 的项目根目录执行。** 不要进入 `app` 后再运行。

关闭这个仓库的自动换行转换，是为了保持冻结正文的 LF 换行及字节哈希。不要用编辑器批量转换测试语料的换行，也不要仅修改正文而保留旧坐标和哈希。

已有仓库时，先处理或保存自己的修改，再获取团队约定的分支更新：

```powershell
git status
git pull --ff-only
git rev-parse --short HEAD
```

测试反馈时记录最后输出的 commit，方便确认大家测试的是同一份代码。首次复现如果旧工作区曾被转换换行，优先使用一个按上述方式新克隆的目录测试。

根目录应至少包含：

```text
DE/
├─ app/
│  ├─ api/
│  └─ retrieval/
├─ config/retrieval.example.json
├─ scripts/
│  ├─ build_indexes.py
│  ├─ fetch_embedding.py
│  └─ smoke_embedding.py
├─ tests/
│  ├─ fixtures/b/
│  ├─ support/b_app.py
│  ├─ support/static/b_debug.html
│  ├─ test_chunking.py
│  ├─ test_retrieval.py
│  └─ test_retrieval_api.py
├─ requirements-b.txt
├─ requirements-b-dev.txt
├─ pytest.ini
└─ B测试.md
```

如果这些文件缺失，先确认维护者已提交 B 模块、自己已拉取正确版本，不要用其他项目的同名文件凑齐。

## 3. 建立自己的环境，安装依赖

在 PowerShell 中执行：

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements-b.txt -r requirements-b-dev.txt
.\.venv\Scripts\python.exe -m pip check
```

若 `.venv` 已存在且版本正确，可跳过创建环境这一行。`pip check` 正常应输出：

```text
No broken requirements found.
```

说明：

- `requirements-b.txt` 是 B 的运行依赖，包括 embedding、Chroma、FastAPI 等。
- `requirements-b-dev.txt` 是 pytest 等测试依赖，必须与运行依赖一起安装。
- 仅安装原 `requirements.txt` 不足以测试 B，它主要服务于前端预览。
- 第一次安装需要联网，包含 PyTorch 等较大的软件包，请等命令结束。
- 本指南始终显式调用 `.venv` 中的 Python，无需执行激活命令，也不受 PowerShell 激活脚本限制影响。
- 即使终端前面显示 `(base)`，上面的命令也使用项目自己的 `.venv`。

## 4. 先运行自动测试：不需要下载模型权重

执行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py -q --tb=short --basetemp=.pytest_cache/b-member-tests --junitxml=artifacts/b/local-tests.xml
```

本指南对应版本的预期结果为：

```text
78 passed in ...s
```

运行时间由电脑决定。**通过标准是所有测试通过、进程正常结束**；未来团队增加测试后数量可以变化，不应为了凑成 78 去删用例。

这一步不读取真实模型权重，大部分编码使用测试向量，但真的执行分块、临时 Chroma 入库、API 调用及异常检查。它不是“78 道法规题全部答对”。

测试报告在 `artifacts/b/local-tests.xml`。`--basetemp` 指定测试用的临时目录，该目录会由 pytest 管理；不要把业务数据放进去。如果旧临时目录因其他账户创建而无权清理，改用一个新的目录，例如 `.pytest_cache/b-member-tests-2`。

## 5. 先看 mock 页面：检查流程和分块

执行：

```powershell
$env:DERAG_B_DEBUG_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

终端出现 `Uvicorn running on http://127.0.0.1:8767` 后，保持它运行，在浏览器打开：

- 验证页面：[http://127.0.0.1:8767/b-debug](http://127.0.0.1:8767/b-debug)
- 接口文档：[http://127.0.0.1:8767/docs](http://127.0.0.1:8767/docs)

页面应显示 **MOCK** 和 `fixture-en-v2`。点击“建立四组测试索引”，等待任务状态变成 `completed`。

mock 使用测试向量，适合先确认程序、按钮、索引和接口能工作；**mock 排名不用于判断语义检索是否正确**。判断“问题是否找对文档”，需要继续完成下面的真实模型测试。

也可以不打开页面，单独执行 mock 建库命令；首次测试时二选一即可：

```powershell
.\.venv\Scripts\python.exe -m scripts.build_indexes --config config/retrieval.example.json --fixtures --mock
```

这个命令应该输出 `state` 为 `completed`、含四组条件的 JSON。

## 6. 准备真实模型，再做检索测试

### 6.1 准备固定版本权重

如果 mock 服务正在运行，先在它的终端按 **Ctrl+C** 停止，然后执行：

```powershell
.\.venv\Scripts\python.exe -m scripts.fetch_embedding --config config/retrieval.example.json
```

当前统一模型为：

| 配置 | 值 |
| --- | --- |
| 模型 | `BAAI/bge-m3` |
| 固定 revision | `5617a9f61b028005a4858fdac845db406aefb181` |
| 输出维度 | 1024 |
| 推理设备 | CPU |
| 模型目录 | `models/embedding/` |
| 文件校验清单 | `models/embedding/derag-model-manifest.json` |

首次模型文件下载约 2.3 GB，需要能访问 Hugging Face。**组员使用同一套权重，不是每个人换一个模型。** 脚本将文件下载到当前项目，并记录、校验文件哈希。

如果开发者已经把完整的 `models/embedding/` 文件夹通过其他方式交给你，可复制到相同位置，务必包含校验清单及所有子目录。文件完整且版本一致时可跳过下载，直接执行真实测试。不要只复制某一个权重文件或个人虚拟环境。

GitHub 普通代码仓库不包含这些权重，因此刚 clone 的项目还不能立即进行 real 检索。模型准备完成后，当前 B 模块的编码和检索不需要网络或外部模型 API。

### 6.2 运行真实模型测试

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke_embedding --config config/retrieval.example.json --output artifacts/b/local-real-smoke.json
```

脚本会自动构建或复用当前版本的四组 real 索引，不需要提前启动 uvicorn。第一次导入、加载权重和建库需要等待，耗时取决于 CPU 和磁盘。

预期最终输出：

```text
PASS: 12 real retrieval checks, tokenizer overflow and HTTP APIs; record: ...
```

它实际检查：

1. 真实模型成功加载，并输出 1024 维向量。
2. 三个英文问题分别在四组条件下检索，共 12 次；每次第一名的文档主题正确。
3. 每个返回片段与冻结正文的 `[start,end)` 完全一致，条文 ID 和来源 URL 对应正确。
4. 故意超长的输入被拦截，返回 `MODEL_INPUT_TOO_LONG`。
5. 真实服务的状态、搜索和对照 HTTP 接口能正常工作。

测试中可能出现：

```text
Token indices sequence length is longer ... (9002 > 8192)
```

这是脚本故意用 `"law " * 9000` 测试超限保护。**仅在这项故意超限测试中，且最后出现 PASS 时，属于预期结果。** 正常问题或建库意外超限、最后显示 FAILED，都需要排查。

本次运行记录在 `artifacts/b/local-real-smoke.json`；仓库内的 `real-smoke.json` 和 `clean-real-smoke.json` 是开发者已有的验证记录。看到别人的报告不等于自己这台电脑已通过测试，应以刚执行的命令结果为准。

## 7. 在 real 页面逐项验收

启动：

```powershell
$env:DERAG_B_DEBUG_MODE = 'real'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

重新打开或刷新 [B 验证页](http://127.0.0.1:8767/b-debug)。页面必须显示 **REAL**。修改环境变量不会改变已经启动的旧进程，mock 切 real 时一定要停止旧服务，再执行启动命令。

### 7.1 检查运行状态和索引

语料应为 `fixture-en-v2`。真实测试已经建库成功时，页面应直接显示四组索引就绪；首次未建库时点击“建立四组测试索引”，等待 `completed`。

同一份当前合成语料的预期总块数如下，**是四份文档合计，不是当前选中文档的块数**：

| 条件 | 方法 | 每块字符上限 | 总块数 | 实际最长块 |
| --- | --- | ---: | ---: | ---: |
| F400 | 固定窗口 | 400 | 34 | 400 |
| S400 | 结构感知 | 400 | 47 | 394 |
| F800 | 固定窗口 | 800 | 18 | 800 |
| S800 | 结构感知 | 800 | 31 | 799 |

这里按 Python 字符计数，包括空格、换行和标点，400/800 不是英文单词数，也不是 token 数。算法仍然只有两种，四组是“两种方法 × 两个长度”。

同一版本重复点击建库应复用已校验的索引，块数不应翻倍。四组共享同一实验版本，但 mock 和 real 的模型不同，因此二者索引版本不同是正常的。

### 7.2 “01 / 文档与分块”怎么测

选择 `Synthetic Personal Information Rules (not official legislation)`，分别切换 F400、S400、F800、S800。

正确现象：

- 左侧是英文冻结原文，包含 `Chapter`、`Article`；切换分块条件不会改写左侧正文。
- 右侧切块来自服务器，条件变化时块数、边界可能变化。
- 相邻块的前一个 `end` 等于后一个 `start`，第一块从 0 开始，最后覆盖到全文末尾。
- 点击“查看来源片段”，看到的片段、位置及完整正文应相互对应。
- 结构法可以产生不足上限的块；超长条文会继续按句子/段落拆分，并非永远“一条一块”。

短文档 `Synthetic API Contract Fixture (not official legislation)` 只有 25 个字符，四组都只切出一块是正确的。它适合核对字段，不适合展示长文档切分差异。

### 7.3 “02 / 单组检索”怎么测

依次输入以下问题，选择条件后点击“检索 top-5”：

| 英文问题 | real 模式下预期第一名 `document_id` |
| --- | --- |
| `How can an individual request deletion of personal information?` | `privacy` |
| `Can a reader renew a library book when the loan period expires?` | `library` |
| `What should a bus driver do after noticing an abnormal road condition?` | `travel` |

可以逐一切换四个条件进行检查，自动真实测试已经覆盖这 12 种组合。结果中的正文、文档标题、Article 标签应为英文。

正确结果不是“分数必须等于某个小数”，而是主题、来源和原文切片对应正确。`score` 越高表示该度量下越相关，不是概率，也不是法律正确率。不同机器可能出现并列片段顺序差异，不应要求截图中的每一个排名与耗时完全一致。

### 7.4 “03 / 同题对照”怎么测

输入同一个英文问题，先比较左侧 F400 与右侧 S400，再比较 F800 与 S800，点击“使用上方问题对照”。

正确现象：

- 两侧分别返回各自条件的 top-5 证据。
- 两侧共用同一个问题、语料版本和索引版本，不是把左侧结果复制给右侧。
- 两侧片段边界和返回字符总数可以不同，也可能部分相同；不要求结构法分数必然更高。
- 修改问题后，旧结果会清空，避免把上一道题的答案误当作新题结果。

此页用于观察检索证据差异。不能仅凭三道合成问题宣布哪种方法在真实法规上更准确。

### 7.5 原文引用怎么核验

对任意命中点击“查看来源片段”，检查文档 ID、条文 ID、`chunk_id`、`start/end`、来源 URL 和全文。

例如 `[100,180)` 的意思是从第 100 个 Python 字符开始，到第 180 个之前结束，长度为 80。后端必须满足：

```python
hit["text"] == document["text"][hit["start"]:hit["end"]]
```

不要把这个下标直接当成字节位置；浏览器 JavaScript 对部分 Unicode 字符的计数也与 Python 不同，应以后端校验为准。当前英文样例为 ASCII，但保留了中文和 emoji 的自动回归测试。

“能定位到原文”是 B 的验收目标；“这段证据是否足以支持大模型回答中的每个主张”是后续 C 的评估目标。`example.org` 是样例来源占位链接，不要求打开真实法规网页。

## 8. 不用页面也能检查 API

保持 real 服务运行，另开一个 PowerShell 窗口。下面的请求使用已经启动的服务：

```powershell
Invoke-RestMethod 'http://127.0.0.1:8767/b-debug/status' | ConvertTo-Json -Depth 20

$body = @{
    question = 'Can a reader renew a library book when the loan period expires?'
    corpus_version = 'fixture-en-v2'
    condition = 's400'
    top_k = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri 'http://127.0.0.1:8767/api/search' -Method Post -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 20
```

状态应包含 `mode: real`、`ready: true` 和当前语料版本；搜索响应包含 `corpus_version`、`index_version`、`condition`、`hits`、`timing_ms`，第一名文档应为 `library`。

也可以在 `/docs` 中展开接口，点击 `Try it out`。同题对照请求示例：

```json
{
  "question": "Can a reader renew a library book when the loan period expires?",
  "corpus_version": "fixture-en-v2",
  "left_condition": "f400",
  "right_condition": "s400"
}
```

发送到 `POST /api/compare`。注意 compare 不接收 `top_k`，两侧固定 top-5。

## 9. 文件保存在哪里，哪些需要从 GitHub 获取

| 路径 | 用途 | 获取方式 |
| --- | --- | --- |
| `app/retrieval/`、`app/api/` | B 的实现 | GitHub 源码 |
| `scripts/`、`tests/`、`config/` | 模型/建库脚本、测试、配置与冻结语料 | GitHub 源码 |
| `requirements-b*.txt`、`pytest.ini` | 依赖锁及测试配置 | GitHub 源码 |
| `.venv/` | 当前电脑的解释器环境 | 组员自行创建，不上传 |
| `models/embedding/` | 固定版本模型与校验清单 | 脚本下载或复制完整文件夹，不上传普通 Git |
| `data/b-fixtures/mock/` | mock 四组索引 | 在组员电脑自动生成 |
| `data/b-fixtures/real/` | real 四组索引 | 在组员电脑自动生成 |
| `artifacts/b/local-tests.xml` | 组员本次自动测试报告 | 本机测试生成 |
| `artifacts/b/local-real-smoke.json` | 组员本次真实模型报告 | 本机测试生成 |
| `.pytest_cache/` | 临时测试目录 | 本机自动生成 |

不需要从开发者电脑复制 Chroma 索引。**由相同源码、语料、配置和模型在自己的目录重新建库，才是在检验复现。** 个人报告可以发给组员对照，不必随业务代码反复提交。已有报告与历史中文报告在 `artifacts/b/`，不要把历史结果当作当前英文版本的结果。

## 10. 常见问题

| 问题 | 处理方式 |
| --- | --- |
| `py` 找不到或没有 Python 3.13 | 安装 Python 3.13；若使用安装路径，路径由自己电脑决定，不要填写开发者的磁盘路径 |
| `No module named chromadb`、`sentence_transformers` 或 `pytest` | 使用 `.venv` 中的 Python 重新安装两份 B 依赖；检查是否只装了原 `requirements.txt` |
| `No module named scripts` 或 `tests.support.b_app` | 切回项目根目录执行，确认 `scripts/`、`tests/` 已从仓库拉取 |
| real 模式提示模型缺失 | 先运行 `scripts.fetch_embedding`，或复制完整模型目录和清单 |
| 模型下载失败 | 检查本机网络能否访问 Hugging Face；也可由能下载的组员提供同一固定 revision 的完整目录 |
| 模型或语料校验失败 | 核对版本、文件完整性、LF 换行及是否手工编辑过；恢复同版本完整文件，不要绕过哈希校验 |
| `INDEX_NOT_READY` 或按钮不可用 | 先建立四组索引，等待 `completed`；若任务失败，查看页面错误和服务终端日志 |
| `VERSION_MISMATCH` | 使用 `fixture-en-v2`，更新代码及配置并重启服务；旧中文 `fixture-v1` 不能用于当前活动语料 |
| 页面还是中文正文、旧问题或旧版本 | 确认进入 `/b-debug`，停止旧服务后在更新目录重新启动，再强制刷新浏览器 |
| 页面显示 MOCK，但已经改了环境变量 | 环境变量只影响新进程；Ctrl+C 停止旧进程，再设置 real 并启动 |
| 端口 8767 被占用 | 使用原服务，或停止自己启动的旧服务；也可改为 `--port 8768` 并同步更改浏览器与 API 地址 |
| `127.0.0.1` 在别的电脑打不开 | 每位组员在自己的电脑运行，访问自己的 localhost；这里的命令没有开放局域网服务 |
| 测试临时目录无权清理 | 更换 `--basetemp` 为新的专用目录，不要用管理员命令删除其他人的工作目录 |
| 自动测试全通过，但 mock 第一名主题不对 | mock 不用于语义排序判断，完成 real 测试再检查三道英文题 |
| 页面没有完整大模型回答 | 正常；B 当前只提供检索证据，完整回答由 C 后续接入 |

## 11. macOS / Linux 组员怎么运行

源码不包含 Windows 的个人路径。macOS / Linux 可以按相同原理创建环境，命令形式如下；**当前 B 依赖锁和执行流程只完成了 Windows CPU 实测，以下是其他系统的运行方式，尚未跨平台验收。**

先按第 2 节克隆仓库并进入项目根目录，安装 Python 3.13，然后执行：

```bash
python3.13 -m venv .venv
./.venv/bin/python -m pip install -r requirements-b.txt -r requirements-b-dev.txt
./.venv/bin/python -m pip check
./.venv/bin/python -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py -q --tb=short --basetemp=.pytest_cache/b-member-tests --junitxml=artifacts/b/local-tests.xml
./.venv/bin/python -m scripts.fetch_embedding --config config/retrieval.example.json
./.venv/bin/python -m scripts.smoke_embedding --config config/retrieval.example.json --output artifacts/b/local-real-smoke.json
DERAG_B_DEBUG_MODE=real ./.venv/bin/python -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

同样打开 `/b-debug`。不使用 Docker 时需要在本机安装 Python 和依赖；不是双击即可免安装运行。如果某个锁定包没有对应系统或芯片架构的安装包，记录包名、Python 版本和完整错误，由团队统一验证兼容方案，不要各自随意更换版本后混用实验结果。

## 12. 测试完成后怎样反馈

组员可以按下面格式反馈，便于定位问题：

```text
Git commit：
操作系统 / CPU 架构：
Python 版本：
pip check：通过 / 失败
自动测试：例如 78 passed
真实测试：PASS / FAILED / 尚未准备模型
页面模式：REAL / MOCK
语料版本：fixture-en-v2
四组总块数：F400=34，S400=47，F800=18，S800=31
三道英文问题第一名：privacy / library / travel
来源片段核验：通过 / 失败
如果失败：执行的完整命令、完整错误、服务终端日志
附件：local-tests.xml、local-real-smoke.json 或页面截图
```

不要只发“打不开”或最后一行报错；要区分依赖安装、模型下载、建库、检索和页面阶段。Windows 与其他系统的耗时不要求相同，同主题内并列片段的顺序也不要求逐条一致。

## 13. 维护者提交前检查

提交文档时，要同步提交当前 B 实现、依赖和英文测试语料。**仅提交本文件，组员无法运行尚未上传的 B 模块。** 尤其确认以下新增文件已进入本次提交，而不是仍停留在本机 untracked 状态：

- `app/api/`、`app/retrieval/`。
- `scripts/`、`config/retrieval.example.json`。
- `tests/`，包含英文原文 `.txt`、JSON 元数据、问题文件、旧中文回归样例及验证页面。
- `requirements-b.txt`、`requirements-b-dev.txt`、`pytest.ini`。
- `.gitignore`、`README.md`、`B开发文档.md`、`B测试.md`；`.python-version` 保持正确版本。

推送前可只读检查：

```powershell
git status --short
git diff --cached --stat
git ls-files app/api app/retrieval scripts config tests requirements-b.txt requirements-b-dev.txt pytest.ini B测试.md
```

第一条查看还有什么没有提交；第二条检查已经暂存的内容；第三条确认文件是否已经被 Git 跟踪。空输出或缺少目录时应检查是否漏加文件。不要上传 `.venv/`、模型权重、索引、测试临时目录或个人 IDE 配置。

推送后最好让组员在一个新目录 clone，按本指南从头执行一次。这样能检查是否遗漏文件，而不是依赖维护者电脑上早已存在的环境和数据。
