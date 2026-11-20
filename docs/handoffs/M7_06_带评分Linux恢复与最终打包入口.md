# M7第6次交接：最新评分库Linux恢复通过，继续最终打包

2026-11-20，answer-eval。用户要求持续完成，不在本阶段停工。

首次尝试在容器启动前失败，随后清理误复制尚未生成的runtime-source-sha.json而丢失原异常；已保留失败报告并明确缺失。单独检查确认Docker daemon未运行，启动已有引擎后，以新目录/新nonce重试通过，没有安装或下载。

成功证据artifacts/c/m7-scored-restore-retry/result.json：镜像c9fd363…、68个运行源码/配置与当前文件相同；原Chroma只读复制到新专属卷，原chunks/indexes/runs只读挂载，新SQLite卷从一致性备份恢复。容器禁网、Key为空；正常app.main读取120条/124审计历史，重启和JSON/CSV逐字节等同Windows最终结果。21人工/99AI来源标签保留，外部模型0次，未重建索引。自己的检查容器已删除，Windows库/原卷逻辑不变，保留两个本任务新卷供恢复。

已更新README当前入口、C报告及交付/恢复说明。旧说明移入历史记录或由Git保留；原A输入、原未评分实验与所有旧归档不改。M7本阶段最终自检位于成功目录final-self-check.json。

下一步创建deliveries/20261120-C-final-mixed-review的新最终包：prepare_delivery/verify_delivery生成并验证源码冻结数据，另打完整评分/证据/SQLite备份ZIP；复用已验证运行镜像与固定权重生成DE.tar及权重包，SHA/CRC/逐成员/密钥隔离核验，生成最终清单和阅读说明。不能覆盖旧DE.tar或候选包，不发布/推送。

评分字段30/30已齐，混合来源21份人工/99份授权AI，不能再标全部人工；此后不重复第31题、batch-16、120项生成、模型下载、未改变的401项回归。累计已知学校191672 token及历史未知usage不变。

中断恢复先读根续做入口、CURRENT、本报告，检查answer-eval/HEAD/工作树。最新提交见根总览；剩余只有最终打包和全局交付核验，不恢复旧库覆盖已完成成绩。

补充：新生成的runtime-source-sha.json在Git提交时出现CRLF规范化提示，已转为LF并更新完整性证明；这仅是新元数据换行，68个源码SHA、原A/M6/SQLite/导出均未改变，恢复验收无需重跑。
