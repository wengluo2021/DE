# DERag

CS5481 Topic 5 的前端预览版。当前包含问答、文档库、分块对照和评估页面；真实 embedding、向量数据库、LLM 问答与评估 API 尚未接入。界面中的问答与报告样本均明确标记为演示数据。

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
