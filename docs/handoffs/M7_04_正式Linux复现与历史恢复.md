# M7第四步交接：正式Linux问答与历史迁移通过

2026-11-20，answer-eval，承接97580e8。M5正式Windows通过，M6一次120项全完成且无人工分数。本步完成正式Linux数据/模型/索引/学校API及Windows历史结果迁移，不重复生成120题。

## 实际通过

- 正常app.main、同一A五法规/121主条文/24+6题/42证据、固定BGE-M3 CPU权重；独立空卷新建3515块四索引，建库1307.513秒。
- index_version与Windows相同：e1d9e93d8abeea648bf64a2e7ac215e39f051a3c715dbe2ffa0664dac8b302bf；模型/输入版本及配置指纹一致，65个app/config/scripts文件SHA与当前源码相符。
- 四组Top5原文/来源检查、compare、学校单题、保存、新进程读取、formal_ready/QA/evaluation预检全部通过。Linux问答实际1次/1673token，返回与Windows单题相同的受原文支持主张。未把它算入M6正式评分。
- 模型/env只读挂载；学校TLS保留，临时WSL回环转接利用本机既有代理；自己的应用与relay已停。报告m7-linux-formal-retry.json及m7-linux-formal-e2e-retry.json。
- Windows已完成SQLite经只读连接生成独立backup；另一个Linux新SQLite卷、禁网、无Key，在正常应用中读取同一run_id的120项。两次启动的JSON/CSV与原件完全一致，0模型调用，review_rows=0。m7-formal-result-restore-retry.json。
- 运行镜像derag-c-m7-runtime:90f59e7032，sha256:c9fd36327ffa6d676a1fe45c4a6369cc91ad11d643168523448185b1ab1a89de。Python3.13.11/linux-amd64，107个distribution；继承之前逐层核验的官方Python基础，manifest digest ac76900038d8606cc99b413d4ede77bc7152f1e42b94cf5d50d4b80a999652fe。m7-a-image-provenance.json。

## 离线候选

- 镜像：deliveries/C-runtime-20261120-candidate.tar，1870832128字节，SHA256 03a3be92bc9346aa79bb79ba4b5398e766ca46b7b45976962ae11617b734c003。config SHA及17层diff_id已核验，尚未在另一台电脑执行docker load。
- 权重：deliveries/BGE-M3-5617a9f6-weights.tar，2293350400字节，SHA256 bde9e27a9e758677f035097550944dab26b49fe99ba786dd4fd51b44dc08f958；11文件逐项符合固定manifest。复用既有下载，无重复联网下载。
- 归档流式扫描未发现实际学校Key。旧DE.tar不变，无镜像tag覆盖/发布。m7-offline-runtime-and-model.json。

## 失败和修正均保留

首轮容器helper误用Windows解释器路径，生成调用0；改sys.executable后通过，未改生产镜像。首轮历史恢复backup保留WAL模式，源目录只读导致SQLite无法建共享内存辅助文件；仅对独立完成的稳定快照加immutable=1后通过，不对活动原库使用此参数。原失败报告保留；没有为了过关改gold、指标、prompt或Windows原库。

## 继续与限制

自有正式容器已移除，索引/数据库卷保留，见m7-nov20-cleanup.json；不prune、不停止他人容器。正式Linux索引卷：{"sqlite": "derag-c-formal-5961513ef7-sqlite", "chroma": "derag-c-formal-5961513ef7-chroma", "chunks": "derag-c-formal-5961513ef7-chunks", "indexes": "derag-c-formal-5961513ef7-indexes", "runs": "derag-c-formal-5961513ef7-runs"}。

接下来整理源码/数据和未评分结果ZIP、CRC/SHA、全轮自检与休息交接。M6实际人工评分仍待完成，166条带引用主张没有自动填分；完成评分后应导出新带评分结果并生成最终交付清单。当前候选/合成旧测试不冒充最终课程成绩。Linux首次在线下载模型未另测，本步从已验收权重离线新建库；镜像归档已逐层验证，异机load仍需接收机器验证。

本轮实际生成尝试123次（M5 1+M6 121+Linux 1），已知189587token，含1次无usage失败；加此前2085，累计已知191672token，金额未知。所有后续读取/迁移/打包0生成调用。
