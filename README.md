# DERag

CS5481 Topic 5 项目。正式入口目前包含问答、文档库、分块对照和评估的前端预览；B 的真实 embedding、Chroma、两种切分与检索 API 已独立实现，使用下方 B 验证入口。完整 LLM 问答、官方数据和 30 题正式评估仍待 A/C 集成。

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

Docker 镜像名必须小写，所以镜像标签是 `de:latest`，容器名是 `DE`。打开 http://127.0.0.1:8766 。如端口被占用，请同时更改启动命令与访问地址。首次安装依赖或构建镜像需要联网；Docker 镜像建好后可离线启动。当前版本没有调用外部模型服务，不需要 API Key。

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
