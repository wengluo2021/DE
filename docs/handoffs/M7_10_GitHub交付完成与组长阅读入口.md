# M7第10次交接：GitHub交付已完成

2026-11-20。用户已授权提交及登录，登录成功后完成本阶段；无需再次登录、下载模型或跑实验。

源码/报告/全部评分证据已快进推送answer-eval。草稿PR：https://github.com/wengluo2021/DE/pull/2，供组长审阅，未合并main。

独立C交付页：https://github.com/wengluo2021/DE/releases/tag/c-delivery-20261120。全部10个附件uploaded，官方API的size及sha256逐项对应本地准备清单，已发布为C部分prerelease，不替代全组正式版本或设为仓库latest。具体附件下载链接和实际服务端摘要见delivery/c-20261120/GITHUB-RECEIPT.json。

包含源码冻结资料ZIP、完整评分/SQLite备份ZIP、DE.tar、3权重分片、指南ZIP、附件JSON、SHA清单及合并脚本。先下载并解压指南，权重分片合并后校验原TAR SHA。准备时GITHUB-ASSETS.json的not_uploaded是历史准备快照，当前以上传回执为准。

旧DE.tar、所有旧candidate/unreviewed和正式120项原输出保留。原四包与固定16a8e82源码快照不变，随后提交仅补入口/上传回执。21具体人工确认+99授权AI来源保持，不能称全部人工金标准。Windows/Linux验收及异机未实测的边界不变。

登录凭据仅由标准Git管理器在进程内存使用，公开文件无真实Key/Token。阶段新增学校API0，无新生成、下载模型或索引重建。代理下TLS曾失败，当前成功Git命令采用临时http.proxy为空、HTTP/1.1；未改系统代理/证书验证。

所有阶段均有日期日志和自检。后续由组长审阅PR、整合全组报告和最终提交；本次不合并main、不代发团队消息。实际最终HEAD、远程一致和工作树状态以根交接总览为准。
