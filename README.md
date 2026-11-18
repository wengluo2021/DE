# DERag

## C 阶段开发入口

C 的 M0（共享契约、统一配置）、M1（证据问答核心）、M2（持久会话、任务及后台API）与M3（四组评估、评分、导出）已落地，交接见 `docs/handoffs/`；日期工作记录见 `docs/worklogs/`。正式入口已有问答/历史/任务/评估API，四个页面仍待M4接入；原B验证入口继续保留。

使用Python3.13.11创建项目`.venv`后，可安装 `requirements-c-dev.txt`，运行 `tests/test_contracts.py tests/test_config.py`。B的模型/向量库依赖继续按下方B说明准备，最终统一依赖在集成阶段完成。

`config/experiment.json`当前明确是development样例、语料fixture-en-v2、gold_version为空；正式数据由A交付。配置从项目根解析路径，读取项目`.env`或显式env_file，不污染全局环境；真实Key不在仓库中。

无网络问答核心检查：`.venv/Scripts/python.exe -m scripts.ask --fixtures --mock-llm --question "What does Article 2 state?"`。M1另有真实生成与拒答记录；这些使用固定合成证据，不是官方法规或正式检索评估。运行C检查可指定 `tests/test_contracts.py tests/test_config.py tests/test_answer.py tests/test_llm_client.py tests/test_ask_cli.py`，无须先装B的模型。

M2启动仍为 `python -m uvicorn app.main:app --host 127.0.0.1 --port 8765`。只使用一个worker，不加自动reload；数据库在data/sqlite。健康检查区分存活与数据/索引/模型就绪：缺正式资料时API明确返回409，页面能打开不表示知识库已完成。默认读取项目.env，可用DERAG_ENV_FILE显式选择本地环境文件；不自动寻找其他课程的密钥。M2新增检查为 `tests/test_persistence.py tests/test_tasks.py tests/test_qa_api.py`。

M3用法见 [评估使用说明](docs/评估使用说明.md)。配置正式数据/题集/索引后，在另一个终端执行 `python -m scripts.run_eval --config config/experiment.json --base-url http://127.0.0.1:8765`；默认导出到新的data/runs/client-随机目录。`--run-id`读取已有实验，不重新生成。M3检查为 `tests/test_evaluation.py tests/test_evaluation_api.py tests/test_eval_cli.py`；M0–M3组合227项通过，实际合成HTTP流程120项通过，均不代表正式成绩。

---

下方“运行方式/当前可操作内容”保留原预览版说明，尤其requirements.txt和DE.tar仅对应旧预览。当前C后台启动需要requirements-c.txt（开发检查用requirements-c-dev.txt）；尚未完成新版Docker集成，不以旧镜像验证新后台。B的真实embedding与Chroma按后续B说明安装。官方数据及30题正式评估仍待A交付后集成。

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


## B 独立检索模块（已实现）

组员从 GitHub 获取代码后，请先阅读 [B测试.md](./B测试.md)：包含依赖安装、自动测试、模型准备、浏览器验收及常见问题。

详细接口、目录和集成约定见 [B开发文档.md](./B开发文档.md) 第 12 节。
Python 3.13.11 / Windows CPU 在空虚拟环境中已验证安装、测试和真实模型运行。
B 依赖必须安装 `requirements-b.txt`；上方原 `requirements.txt` 和 `DE.tar` 仍只对应前端预览。

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
