# Docker 与交付包复现

这是 C 的交付准备说明。A 的正式五法规与冻结 24+6 题已于 2026-11-20 接入校验，正式 M5/M6 进度见最新交接；本说明、合成演练或一个能打开的页面均不代表正式成绩。最新实测状态与限制见 `docs/handoffs/`，不要把准备完成写成整个 M7 完成。

## 1. 先准备可校验的源码与数据包

在已有依赖的 DERag 环境中，先按《三方对接与正式资料接入》生成新的正式配置并验证 A 数据，然后执行：

```powershell
.venv/Scripts/python.exe -m scripts.prepare_delivery --config config/experiment.formal-a.json --output ../delivery-NEW
```

输出目录必须不存在。工具只读取选定 JSON，忽略进程凭据和本地 dotenv；校验语料与题集后复制原始字节，不重新清洗、不改题。它生成 `config/experiment.delivery.json`、提示词快照及 `DELIVERY-MANIFEST.json`，把数据/模型/提示词改成包内可移植路径，确认实验指纹没有改变。A 布局下保留 data/formal_corpus、data/eval、data/processed 及来源清单；附件完整结构也按原字节打包。模型权重、已有 Chroma、SQLite、历史实验与私密 env 不装入此源码包。正式保存的逐题结果与模型权重作为另行校验的交付材料保留，不能在打包时混用不同版本。

原始快照、处理文档、两个 manifest 与 gold.jsonl 都逐文件记录 SHA-256；缺资料、哈希不符、输出已存在时明确失败。失败后已经产生的不完整目录会保留，先检查并使用新目标目录，不覆盖或自动递归删除。

`--synthetic` 只用于明确的 development 合成演练，输出标记 `synthetic_rehearsal`；默认正式模式拒绝 development 配置和明显标注 SYNTHETIC 的输入。正式候选包也不会自动认证来源：A 仍负责官方资料与标准题核验，C 负责正式生成答案的评分。

## 2. 收到包后先核验，再运行

在新解包目录，使用 Python 标准库校验；`-B` 避免生成额外字节码：

```bash
python -B -S scripts/verify_delivery.py .
```

此命令无需先装 Pydantic 或模型库。它检查清单格式、相对路径、文件齐全和 SHA；修改、漏文件、额外文件或路径逃逸都会失败。请对未运行的新解包目录做此检查；运行后新增的数据库/缓存属于工作目录，不能把它当成原始交付目录继续声称字节未变。校验清单保证与保存的清单一致，来源真实性仍需团队的交付记录与版本核验。

2026-11-19 的旧候选镜像已通过当时的 Linux 工程测试；2026-11-20 新 A 依赖/适配已重建并通过Windows401项、Linux400项/1专用跳过、正式Linux问答/重启和120项历史结果迁移，见M7_04，不把旧镜像当当前最终产物。Docker 不再强设 DERAG_DATA_DIR，采用选定配置的数据路径；A 正式运行目录为 /app/data/formal_corpus，相应 SQLite/Chroma/chunks/indexes/runs 卷也应挂载到该目录下，不能以 /app/data 覆盖它。

## 3. 构建 Linux CPU 镜像

使用 Docker Engine，目标为 `linux/amd64`。以下命令在包目录运行，首次构建需要依赖网络；不会下载 embedding 权重或发送模型请求。

```bash
docker build --platform linux/amd64 --target test -t derag-check .
docker run --rm --network none derag-check
docker build --platform linux/amd64 --target final -t de .
```

`test` 镜像包含固定测试依赖、测试源码和必要文档；默认 `final` 镜像只保留运行依赖与代码。正式运行选 `de`，不要把测试镜像称为正式交付镜像。实际验收时记录两镜像 ID、Python 基础镜像 digest、测试 JUnit 和构建日志；日志里缺少成功结果不能当作构建通过。

Dockerfile 固定 Python3.13.11，先从 PyTorch 官方 CPU 索引安装 `torch==2.15.0+cpu`，再安装统一锁；构建检查 `torch.version.cuda is None`。预检只允许该固定 torch 版本的 `+cpu` 构建后缀，仍拒绝其他发布版本或 CUDA 后缀；其他包继续严格比对固定版本。参考[官方 CPU 安装说明](https://pytorch.org/get-started/locally/)，实际 CPU 索引版本另有只读核验证据。

实际Linux解析还发现uvicorn[standard]需要Linux专用uvloop，因此补充 `requirements-linux.txt` 锁定uvloop0.23.0。Docker先安装统一锁、再安装该补充锁；预检在Linux同时核对两份锁，Windows不安装uvloop。最终软件版本以实际安装记录和镜像ID为准，不能把Windows的依赖数量直接视作Linux全部依赖。

`.dockerignore` 在目录例外后显式排除 root/formal_corpus 的运行目录与所有 *.lock，防止读取正在使用的锁、数据库或原生索引。它使用白名单，允许程序/配置、测试及冻结的 raw/processed/eval/manifest；继续排除模型、凭据文件、数据库、索引、结果和缓存。`data/.gitkeep` 只让没有正式输入时目录存在，不是法规或题集。Docker 的上下文规则见[官方说明](https://docs.docker.com/build/concepts/context/)。

当前电脑 Windows PATH 没有 Docker，已发现并启动现有 WSL `ubuntu20` 的 Docker24.0.6 引擎。本机可用 `wsl.exe -d ubuntu20 -u root -- docker ...`，挂载的 Windows 路径先通过同一 WSL 的 `wslpath -a` 转换。不要因为 Windows 命令未找到就重复安装 Docker。独立验收镜像使用随机后缀，不覆盖旧 `de`；不要停止不属于本任务的容器。

## 4. 配置、只读模型与持久化输出

在 Docker 主机上准备完整 `models/embedding` 及其 `derag-model-manifest.json`，按固定 revision/文件 SHA 验证。把模型目录以只读方式挂入 `/app/models/embedding`。正式候选包的冻结 data 已复制入镜像；不要用空宿主机目录挂载整个 `/app/data`，否则会遮住镜像里的输入，见[Docker 挂载说明](https://docs.docker.com/engine/storage/bind-mounts/)。

私密连接文件可只读挂载到 `/run/secrets/llm.env` 并设置 `DERAG_ENV_FILE`，适用于本机已有的带引号 dotenv 文件。Docker 自身的 `--env-file` 与 python-dotenv 对引号的解释不同；若选择 `--env-file`，应使用 `.env.example` 那样的无引号 KEY=value 格式，不能直接假设已有私密文件格式完全等价。原 Key 文件不必重写，密钥不进入镜像。

私密env中的endpoint/model/transport应与选定实验JSON一致；覆盖这些字段会改变实际实验指纹，Key本身不进入实验指纹。

下列示例在 Linux/WSL shell 中运行，将两个路径替换为实际绝对路径：

```bash
docker run --name DE -d -p 127.0.0.1:8766:8000 \
  -e DERAG_CONFIG=config/experiment.delivery.json \
  -e DERAG_ENV_FILE=/run/secrets/llm.env \
  --mount type=bind,source=/ABS/PATH/private.env,target=/run/secrets/llm.env,readonly \
  --mount type=bind,source=/ABS/PATH/models/embedding,target=/app/models/embedding,readonly \
  --mount type=volume,source=derag-sqlite,target=/app/data/formal_corpus/sqlite \
  --mount type=volume,source=derag-chroma,target=/app/data/formal_corpus/chroma \
  --mount type=volume,source=derag-chunks,target=/app/data/formal_corpus/chunks \
  --mount type=volume,source=derag-indexes,target=/app/data/formal_corpus/indexes \
  --mount type=volume,source=derag-runs,target=/app/data/formal_corpus/runs \
  de
```

仅一个 worker；不加 reload。Dockerfile 不强制覆盖生成 transport，正式配置应显式选择已验证的 curl/httpx；镜像已安装 curl 与 CA。默认编码离线，只读本地模型；首次模型下载使用显式下载脚本在可联网环境准备，不能把启动时自动拉取当复现步骤。

## 5. 正式容器验收顺序

```bash
docker exec DE python -m scripts.validate_data --config config/experiment.delivery.json
docker exec DE python -m scripts.build_indexes
docker exec DE python -m scripts.preflight
```

健康检查只判断 HTTP 服务存活；`/api/health` 的 `ready` 和 preflight 的 `formal_ready` 才表示所需组件是否匹配。没数据/没Key的容器可以打开页面，但明确未就绪。确认官方来源、正式单题、完整引用与重启保存后，再按《评估使用说明》做 M6 的 120 条和实际人工评分；不能拿合成离线评分替代。

最终 M7 要从新环境安装、校验输入与模型、重建四组、真实问答、核对正式实验和导出，再记录镜像/数据/模型/结果 SHA 并打包。旧 DE.tar 属于前端预览，不能覆盖它后就称新版完成。只有最终验收通过后才导出新的镜像包，并保留文件名、镜像 ID/digest 和包 SHA；对外发布/推送仍按用户授权进行。
