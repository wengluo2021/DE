# C部分交付入口（2026-11-20）

此目录供组长在GitHub阅读与验收。代码保留在answer-eval分支，由组长审阅后决定合并；未直接写main。

## 先读这些材料

- [项目、C任务与完成说明](../../docs/C任务完成说明与阅读路线.md)
- [C部分报告与真实指标](../../docs/C部分报告草稿.md)
- [评分方式和授权范围](../../docs/M6评分方式与授权记录.md)
- [最终JSON](../../artifacts/c/m6-final-scored/evaluation.json)、[CSV](../../artifacts/c/m6-final-scored/evaluation.csv)、[来源审计](../../artifacts/c/m6-final-scored/review-provenance.json)
- [离线恢复步骤](OFFLINE-README.md)、[最终包清单](FINAL-MANIFEST.json)、[原包SHA清单](SHA256SUMS.txt)

30题×4组120条正式结果已完成，无技术错误。96整答、24拒答、166引用判断齐备；38 correct、35 partial、23 wrong，20次可答题误拒答保留。评分来源为21份具体人工确认、99份C授权AI辅助，不能称全部逐项人工核验。

Windows401项与Linux400项通过/1平台跳过；最新评分库在禁网无Key的Linux新卷启动并重启，124条审计历史完整、两次导出与Windows逐字节一致。尚未在另一台物理电脑实测，不等于接收方异机已验收。

## 下载运行包

全部10个交付附件已发布并通过服务端大小/SHA核对，详见[实际上传回执](GITHUB-RECEIPT.json)。大型运行包通过[独立C交付附件页](https://github.com/wengluo2021/DE/releases/tag/c-delivery-20261120)提供，实际上传状态以该页附件及[GitHub交付记录](../../docs/handoffs/M7_10_GitHub交付完成与组长阅读入口.md)为准。镜像和模型不放进Git历史，避免将每次代码提交变成数GB下载。

原始四包分别是源码/冻结数据ZIP、完整结果/SQLite备份ZIP、DE.tar、BGE-M3固定权重TAR。权重原包超过GitHub单附件2GiB限制时按附件清单下载全部分片，合并后必须与FINAL-MANIFEST中的原包SHA一致，再按OFFLINE-README操作。原始包不改写，分片只用于传输。

原离线源码快照为`16a8e82b62cbe5a76e48bb5715fb7a15a2338a07`；之后提交补充交付说明和GitHub入口，业务代码不变。GitHub自动生成的Source code ZIP对应发布标签，并非上述已冻结源码ZIP，其SHA不同属于正常情况。

附件准备清单：[GITHUB-ASSETS.json](GITHUB-ASSETS.json)，传输文件校验：[GITHUB-ASSETS-SHA256SUMS.txt](GITHUB-ASSETS-SHA256SUMS.txt)。源码/报告/评分证据已提交answer-eval，草稿[PR #2](https://github.com/wengluo2021/DE/pull/2)供组长审阅；全部大型附件已发布并完成服务端校验。准备清单中的not_uploaded为当时快照，最新状态以GITHUB-RECEIPT.json为准。下载到新目录后，使用[合并脚本](reassemble_weights.py)处理权重分片，再解压C-delivery-guide-20261120.zip得到完整原包校验/恢复说明。

## 验收边界

不需要重新下载模型、重跑120题或覆盖当前本机数据库。公开内容无实际API Key；新问答需接收方自行在本地私密env配置凭据。组长合并、全组报告/展示与课程最终提交由团队后续处理。
