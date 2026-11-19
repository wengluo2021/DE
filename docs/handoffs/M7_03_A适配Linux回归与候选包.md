# M7 独立工程补验：A适配后的Linux版本

2026-11-20。当前A新依赖与C适配已重建独立候选镜像，旧11月19镜像结论未混用。

- test：derag-c-m7-check:90f59e7032，sha256:d6615d52edc0f8fcae6b02f66154a19e3b072154d5131a2616a23e3e022c2234。
- runtime：derag-c-m7-runtime:90f59e7032，sha256:c9fd36327ffa6d676a1fe45c4a6369cc91ad11d643168523448185b1ab1a89de。
- Linux401项：400通过、1Windows原生路径保护专用跳过，0失败/错误，66.856秒。m7-a-linux-tests.xml。
- runtime正常app.main HTTP检查通过；实际无formal_corpus运行目录与*.lock。镜像未注入学校Key。
- 只读复用本机固定权重，空临时目录重新建合成四索引，12次真实CPU检索/原文/API/超长token拒绝检查通过，91.839秒。m7-a-linux-real-smoke.json。不是正式法规检索或Linux真实生成。
- 首轮失败m7-a-docker-check.json：Docker目录例外误带入Windows正在使用的sqlite锁，读锁导致EOF。末尾显式排除所有运行目录及*.lock后实际复验通过，没有删锁或打断正式建库。
- 完整记录m7-a-docker-final-check.json；临时回环relay已停，自己的三个验收容器已清理。不停止其他容器，不prune。

正式A源码/数据候选包delivery-20261120-A有181文件，标准库校验与新目录/新进程校验通过，版本和指纹保持。m7-a-portable-delivery.json。复用已有Windowsvenv，不称该步干净依赖环境；包不含模型/索引/SQLite/正式结果，也不是最终课程交付。它是当时源码快照，后续交接/结果应再生成新候选，不覆盖。

M5正式Windows验收通过见M5_07。M6真实120项尚待运行/实际人工评分。M7仍需正式Linux索引、真实生成、正式历史导出恢复及最终镜像/权重/结果归档验收；本报告不把合成CPU冒烟当正式完成。
