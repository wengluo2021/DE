# DERag

## 2026-11-20 正式接入更新

A正式五法规/121主条文与冻结24+6题已合入，C只读适配、M5真实索引/学校问答/重启通过。一次正式120项全部完成、0技术失败；人工评分待办，未发布最终准确率。先读[正式实验阅读指南](docs/M6正式实验进度与阅读指南.md)和[M6最新交接](docs/handoffs/M6_02_120项完成与人工评分待办.md)。实际结果在artifacts/c/m6-formal-01，恢复读取已有run_id，不重新提交。

正式配置为config/experiment.formal-a.json；默认开发配置保留。Windows401项通过，Linux新镜像400项通过/1专用跳过；正式Linux建库/学校单题/重启与同一120项历史导出迁移均已通过，详见[M7正式交接](docs/handoffs/M7_04_正式Linux复现与历史恢复.md)；人工评分及最终带评分交付仍待完成。阶段工作只在answer-eval本地保存，无push。


## C 阶段开发入口

C 的 M0–M4已落地：契约配置、引用问答、服务端保存/任务、四组评估/评分/导出、四页真实API接入。M5已接入B生产检索入口、统一依赖、A冻结数据校验、配置生成和预检；当前验收状态见[阶段交接](docs/handoffs)，日期操作见docs/worklogs。2026-11-20已合入A正式5法规/121主条文和24+6题，新配置为config/experiment.formal-a.json；A丰富字段和附件证据已适配，完整401项检查通过。正式建库/问答进度见最新交接，合成联调不代表课程成绩。按[三方对接与正式资料接入](docs/三方对接与正式资料接入.md)继续。

使用Python3.13.11和项目`.venv`。完整运行安装 `requirements.txt`（103个固定运行包）；开发/全部自动检查安装 `requirements-dev.txt`。原 `requirements-b*.txt`、`requirements-c*.txt`仍保留用于独立模块开发；C轻量入口不包含真实Chroma/embedding。已有环境和模型不必重建或重新下载。

Linux另安装`requirements-linux.txt`中的固定平台补充；CPU构建使用同版`torch2.15.0+cpu`。新版容器、源码/冻结数据交付包与SHA校验步骤见[Docker与交付包复现](docs/Docker与交付包复现.md)。当前是否已实际构建和验证，以最新M7阶段交接与证据为准；最新A适配的镜像重验与120项正式评分仍待后续阶段，不能因容器能启动就称最终交付完成。

`config/experiment.json`当前明确是development样例、语料fixture-en-v2、gold_version为空；正式运行需显式选config/experiment.formal-a.json。`DERAG_CONFIG`选择实验JSON，`DERAG_ENV_FILE`选择本地私密env，`DERAG_DATA_DIR`和`DERAG_MODEL_DIR`选择路径，`LLM_TRANSPORT`明确选择curl/httpx。路径从项目根解析，配置不污染全局环境；真实Key不在仓库中。`scripts.prepare_config`只在A输入全部校验后生成新的formal配置；`scripts.validate_data --config config/experiment.formal-a.json`只读C集成校验，A的`--scope corpus/eval`保留；`scripts.preflight`不下载、建库或发模型请求。

无网络问答核心检查：`.venv/Scripts/python.exe -m scripts.ask --fixtures --mock-llm --question "What does Article 2 state?"`。M1另有真实生成与拒答记录；这些使用固定合成证据，不是官方法规或正式检索评估。运行C检查可指定 `tests/test_contracts.py tests/test_config.py tests/test_answer.py tests/test_llm_client.py tests/test_ask_cli.py`，无须先装B的模型。

M2启动仍为 `python -m uvicorn app.main:app --host 127.0.0.1 --port 8765`。只使用一个worker，不加自动reload；数据库在data/sqlite。健康检查区分存活与数据/索引/模型就绪：缺正式资料时API明确返回409，页面能打开不表示知识库已完成。默认读取项目.env，可用DERAG_ENV_FILE显式选择本地环境文件；不自动寻找其他课程的密钥。M2新增检查为 `tests/test_persistence.py tests/test_tasks.py tests/test_qa_api.py`。

M3用法见 [评估使用说明](docs/评估使用说明.md)。生成并启用正式配置、资料和索引后，在另一个终端执行 `python -m scripts.run_eval --config config/experiment.formal-a.json --base-url http://127.0.0.1:8765`；必须与服务端使用同一正式配置，默认导出到新的data/runs/client-随机目录。`--run-id`读取已有实验，不重新生成。M3检查为 `tests/test_evaluation.py tests/test_evaluation_api.py tests/test_eval_cli.py`；M0–M3组合227项通过，实际合成HTTP流程120项通过，均不代表正式成绩。

当前源码启动（已有.venv不必重建）：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

页面分别为/、/documents、/compare、/evaluation；会话、引用、实验与评分以后台SQLite为准。无正式资料显示未就绪、禁用生成，不回退演示。Windows原生索引目录超过200字符时会报INDEX_PATH_TOO_LONG，请选择短数据目录；全套测试的临时目录也应保持短。新版Docker已完成Linux工程检查：368通过/1Windows专用跳过、正常HTTP及12次真实CPU检索通过；该旧镜像不包含11月20日新A适配，当前源码的完整M7验收仍待后续阶段，见[M7最新交接](docs/handoffs/M7_02_Linux容器验收与续做.md)。

页面操作与证据见 [M4交接](docs/handoffs/M4_页面接入与真实问答.md)。Windows学校API验收显式使用generation.transport=curl；默认配置仍为httpx，不能把curl结果等同HTTPX/Linux已验证。正式部署先选定适用传输、配置本地env与冻结数据；参数改变会改变实验指纹，旧run保留。

---

下方“运行方式/当前可操作内容”保留原预览版历史；其中对requirements.txt的描述属于当时状态，当前以顶部统一依赖说明为准。DE.tar仍为旧预览镜像；新的Docker工程验证另见M7交接，正式镜像归档未导出。官方数据已交付并适配，正式30×4实验另见最新M5/M6交接。

<details>
<summary>旧预览运行及镜像说明（不适用于当前C后台安装）</summary>

## 运行方式

项目要求 Python 3.13（`.python-version` 指定 3.13.11）。只使用项目自己的 `.venv`，不依赖开发者电脑上的 Python 安装路径。`requirements.txt` 固定了当前前端预览服务的全部直接和间接 Python 依赖。

Windows PowerShell（先安装 Python 3.13；`py -3.13` 应能找到解释器）：

```powershell
py -3.13 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

macOS / Linux：

```bash
python3.13 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

也可以使用 Docker，无需在宿主机安装 Python。需提前安装 Docker，并在项目目录执行：

```bash
docker build -t de .
docker run -d --name DE -p 127.0.0.1:8766:8000 de
```

Docker 镜像名必须小写，所以镜像标签是 `de:latest`，容器名是 `DE`。打开 http://127.0.0.1:8766 。如端口被占用，请同时更改启动命令与访问地址。首次安装依赖或构建镜像需要联网；原预览镜像不调用外部模型。当前C后台真实问答需要配置API Key，密钥仅放在本地env；旧镜像不包含这些新功能。

需要在另一台已安装 Docker Desktop 的电脑上离线运行时，传送项目目录里的 `DE.tar`，然后执行：

```powershell
docker load -i DE.tar
docker run -d --name DE -p 127.0.0.1:8766:8000 de:latest
```

`DE.tar` 是当前前端预览版的完整镜像，不包含以后新增的真实 RAG 后端。代码更新后需要重新构建并导出镜像。
容器创建后，在 Docker Desktop 的 Containers 页面可对 `DE` 点击 Start/Stop；命令行对应 `docker start DE` 和 `docker stop DE`。

后续接入向量库、embedding 和模型 API 时，必须同步更新依赖文件、容器和复现说明，并重新在干净环境中安装验证。

## 当前可操作内容

- 切换四个视图、创建和切换本地会话、查看带来源的演示回答。
- 导入本地 `.md`/`.txt` 文件，查看文档详情并预览固定窗口与法条结构感知的切块结果。
- 在分块对照页选择文档、方法和块大小，比较块数、长度与边界。
- 查看与导出明确标记为演示数据的评估报告；真实实验运行要等待后端接入。

浏览器本地存储仅用于前端预览，不是课程项目的最终数据存储。实际数据采集、两组以上独立向量索引和人工评估的要求见 [项目设计.md](./项目设计.md)。


</details>

## B 独立检索模块（已实现）

组员从 GitHub 获取代码后，请先阅读 [B测试.md](./B测试.md)：包含依赖安装、自动测试、模型准备、浏览器验收及常见问题。

详细接口、目录和集成约定见 [B开发文档.md](./B开发文档.md) 第 12 节。
Python 3.13.11 / Windows CPU 在空虚拟环境中已验证安装、测试和真实模型运行。
B独立开发可安装 `requirements-b.txt`；当前统一 `requirements.txt` 已包含B，完整环境无需再重复安装。`DE.tar`仍是前端预览镜像。

```powershell
# 在 DERag 项目根目录；若尚未建环境先执行 py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-b.txt -r requirements-b-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest tests/test_chunking.py tests/test_retrieval.py tests/test_retrieval_api.py -q
$env:DERAG_B_DEBUG_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

打开 <http://127.0.0.1:8767/b-debug>，点击“建立四组测试索引”，然后预览分块、检索和左右对照。
默认 mock 使用固定测试向量和真实 Chroma，不代表语义检索效果。正式语义模型的首次下载约 2.3 GB：

```powershell
.\.venv\Scripts\python.exe -m scripts.fetch_embedding --config config/retrieval.example.json
.\.venv\Scripts\python.exe -m scripts.smoke_embedding --config config/retrieval.example.json
# 停止原验证服务后切换模式，再启动
$env:DERAG_B_DEBUG_MODE = 'real'
.\.venv\Scripts\python.exe -m uvicorn tests.support.b_app:app --host 127.0.0.1 --port 8767
```

下载后的权重在 `models/embedding/`，模型文件哈希在 `derag-model-manifest.json`；权重和索引不上传普通 Git。
依赖安装和首次模型下载需要网络，模型准备完成后编码和检索仅使用项目内文件。
测试索引在 `data/b-fixtures/mock/` 与 `data/b-fixtures/real/` 分别保存，不与 A 的正式数据混用。
`artifacts/b/` 保存真实模型、自动测试和网页操作的验证记录。


## 英文测试语料（2026-11-18）

B 验证页的默认问题、三道问题建议、入库正文、文档标题和条文标签已切换为英文。活动版本为 `fixture-en-v2`，分块规则为 `structure-offset-v2`；支持英文 Chapter/Section 和句末标点，并保留中文回归测试。四组仍按 Python 字符数 400/800 切分，不能把上限理解为英文单词数。

当前验证：78 项自动测试通过；项目环境和独立 `.venv-b-verify` 环境各通过 12 次真实模型检索，以及超限保护、HTTP API 和原文切片核验。四组块数为 F400=34、S400=47、F800=18、S800=31。

可输入：

- `How can an individual request deletion of personal information?`
- `Can a reader renew a library book when the loan period expires?`
- `What should a bus driver do after noticing an abnormal road condition?`

这些英文正文仍是合成测试规则，不能视为官方法规或正式 30 题评估。完整样例与测试解释见 [英文语料说明](tests/fixtures/b/README.md)。旧中文结果已保留在 `artifacts/b/archive/zh-v1/`；更新后请重启原来的 B 服务并刷新浏览器。使用上方 `real` 模式启动命令可查看真实语义检索。
