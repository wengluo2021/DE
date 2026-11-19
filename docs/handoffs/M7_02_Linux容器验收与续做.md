**最新交接：交付工具与 Linux 容器工程验收通过，正式资料/实验仍待 A**

日期2026-11-19。承接answer-eval的2bbb2c8。用户确认GitHub上没有A产物，应是尚未准备好；收尾复查远程仍为4个旧分支和已合并B PR，没有新增交付。没有代A采集法规、编题或生成正式成绩。本报告补充M7独立工程准备，M5正式资料验收、M6及M7最终交付仍未完成。

**本轮完成与实际自检。**

| 内容 | 实测结果 |
| --- | --- |
| 交付准备 | prepare_delivery先校验已有冻结语料/24+6题，再复制原始字节，生成可移植配置、提示词快照和逐文件SHA。只允许新目录，忽略本地dotenv/进程凭据，排除模型、数据库、索引与缓存。明显标记SYNTHETIC的输入不能成为正式候选。 |
| 独立校验 | verify_delivery只用Python标准库；实际python -S运行通过。拒绝篡改、漏文件、额外文件、越界路径和覆盖。公开.env.example和各模块依赖清单在包内，真实Key不在其中。 |
| 迁移演练 | 新SYNTHETIC冻结资料准备包、复制到第二目录，在新目录/新进程校验版本/24+6和实验指纹一致；复用Windows现有venv，未把该步骤称作干净依赖环境。 |
| Windows定向回归 | 最终57 passed in7.54s；此前32/35项阶段检查亦保留；pip check通过。 |
| Linux完整回归 | **369项：368通过、1跳过、0失败/错误，45.558秒**。跳过项只适用于Windows原生长路径保护，已有Windows阶段覆盖；没有删除断言或跳过失败用例。 |
| 镜像 | 独立test与final候选镜像实际构建成功。官方Python3.13.11/Debian12基础，linux/amd64；不复制个人venv、既有索引或模型缓存，依赖从固定清单安装。 |
| CPU与平台依赖 | torch2.15.0+cpu，构建/运行检查cuda=None；Linux补充uvloop0.23.0。预检在Linux同时检查两份锁，Windows不要求uvloop。运行镜像105个Python distribution（含pip）已记录。 |
| 正常应用 | final镜像正常app.main启动，5个页面/设计路由HTTP200；健康存活、ready=false、Key未配置，符合没有正式输入的状态。没有注入QA/检索factory。 |
| 真实Linux检索 | test镜像只读挂载既有固定BGE-M3权重，禁用网络，空/tmp重新建四索引；1024维CPU、12次语义检索、原文/来源/条号、真实token超限拒绝、检索/对照API检查通过，用时67500.965ms。四组块数34/47/18/31。不是正式法规实验。 |
| 当前源码核对 | 镜像内app/config/scripts共58个文件SHA与当前工作树一致；依赖预检通过。镜像没有学校Key或临时构建代理配置。 |
| 费用/清理 | 本轮生成API调用0；既有累计仍6次成功/2085token，价格未知。验收容器与临时回环代理已清理，Windows/Linux代理残留均0。Docker/WSL引擎留作后续使用，未停止其他容器或执行全局prune。 |

最终公开文本检查222个文件（含源码、文档和JSON/XML），未发现实际Key；Markdown编码/围栏与非XML源码空白检查通过。历史失败XML保留原始格式，不为消除空白提示而改写证据。

真实权重版本仍为BAAI/bge-m3的5617a9f61b028005a4858fdac845db406aefb181，模型目录只读挂载并按既有文件manifest核验；没有再次下载约2.3GB权重，也没有做新的收费问答。首次Linux在线模型下载、Linux学校API真实生成尚未验证；不要把离线CPU检索等同这两项。

**可恢复的镜像与证据。**

- 运行候选：`derag-c-m7-runtime:3713835790`，ID `sha256:9ad991e4775fbb0a8c8c254c742e421574bda3c2dd6668da8afa5eb4b4c78017`。
- 测试候选：`derag-c-m7-check:3713835790`，ID `sha256:acdb76ae35bef808c76443aef22f73b4046cce5d64f42eae7b15c3f38403b80f`。
- 官方Python基础manifest digest：`sha256:ac76900038d8606cc99b413d4ede77bc7152f1e42b94cf5d50d4b80a999652fe`；导入后image ID匹配官方config digest。完整层/diff_id校验见m7-python-base-verification.json。
- `artifacts/c/m7-docker-runtime-and-model.json`：最后通过的运行/模型验收；复用m7-docker-verified.json中已通过369项测试的**相同ID**镜像和JUnit，未无理由重跑。
- `m7-linux-tests.xml`、`m7-windows-final-tests.xml`：最终Linux完整与Windows相关回归。
- `m7-linux-runtime.json`、`m7-linux-software.json`、`m7-image-provenance.json`：正常HTTP、实际软件/源码SHA、镜像ID与Debian系统包。
- `m7-linux-real/real-smoke.json`及model-manifest.json：真实Linux CPU检索和权重校验。
- `m7-delivery-final-rehearsal.json`、`m7-self-check.json`、`m7-cleanup.json`：实际迁移、自检与清理。

以上是本机候选镜像，没有覆盖旧de或DE.tar，也未push/发布。最终正式镜像应在A数据和M6结果齐备后重新构建，记录最终镜像/归档SHA，不把当前候选称为最终课程交付。

**遇到的问题与修正均已保留。**

1. Docker在WSL中而非Windows PATH；原引擎未运行，正常启动现有引擎，没有安装系统组件或读取其他作业/凭据。早期WSL清单混合编码读取失败，正常主机权限/正确解码后定位到ubuntu20、Docker24.0.6。
2. 第一轮Docker Hub直连超时（m7-docker-check.json）。经Windows已有127.0.0.1:7890代理从官方仓库取得基础镜像，校验manifest/config/每层压缩digest及解压diff_id后导入，TLS保留；匿名pull token未写日志或传学校Key。
3. 第二轮直连依赖约120kB/s，由本任务取消自己的构建客户端（m7-docker-check-after-base-import.json）。随后用只绑定WSL127.0.0.1的临时字节转接接入已有Windows代理；不解密TLS，不修改系统代理/监听/防火墙。最终镜像没有构建代理环境变量。
4. 首轮Linux369项中1失败（m7-linux-first-tests.xml）：镜像默认DERAG_DATA_DIR覆盖了该测试的临时语料。仅让该测试隔离此环境变量，保留所有断言与生产的进程环境>JSON优先级，重跑后368通过/1Windows专用跳过。
5. 完整测试与镜像成功后，外层辅助脚本清理代码误插入三引号字符串，导致runtime-http的临时python -c语法错误（m7-docker-verified.json）。修复的是验收helper，生产源码未受影响；核对原镜像ID、复用已通过的测试证据，再完成实际HTTP与模型检查。
6. 日志提取遇WSL前缀导致StopIteration，元数据命令格式转义也曾失败；改按JSON起始解析及dpkg默认输出格式，未改原证据或生产逻辑。相关操作记于当日日志。

外层恢复脚本：`.bootstrap/Check-M7-Docker.py`、Check-M7-Delivery.py、Prepare-M7-Base-Image.py；运行记录在`.bootstrap/m7docker-*`。最新成功复验目录为m7docker-ec3c41df9a，完整构建/测试目录为m7docker-3713835790。官方基础镜像归档位于.bootstrap/m7-python-base，不进业务Git。脚本默认拒绝覆盖证据，不为恢复上下文重复下载/构建/收费。

**下一步仍按原阶段顺序。**

1. 阅读本报告、M5_04及《三方对接与正式资料接入》《Docker与交付包复现》，核对answer-eval和最新本地检查点。不要reset、重建venv、重下模型或重复本轮验收。
2. 等组长/A交付5–8份官方快照与处理Document、corpus manifest、24可答+6拒答gold.jsonl及gold manifest，附版本/来源/目录。用户已确认暂未准备，不反复询问或代填。
3. 接收后生成新formal配置、校验冻结字节、用B代码重建四索引，正式问题核对官方来源/完整引用/保存恢复，结束M5正式验收。Docker运行时用便携配置、只读模型、独立可写输出卷；既有带引号私密dotenv可只读挂载并设DERAG_ENV_FILE。
4. M6按同一冻结30题跑四组120项，保存失败与真实模型用量，再由实际评审人核验答案/引用/拒答并评分，不使用合成测试评分冒充人工结果。
5. M7最终再验证正式数据/配置/模型/结果的完整复现、真实Linux生成与导出，并打包新镜像、权重/数据/结果及哈希。当前工程镜像和工具可复用，但不代替这一步。

源码仍仅answer-eval，本轮不推送、不合并main、不向团队发消息；最新提交与工作树核验在仓库外层《C任务交接总览.md》。
