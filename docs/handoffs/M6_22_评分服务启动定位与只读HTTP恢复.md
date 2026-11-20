# M6第22次交接：启动问题定位与只读HTTP恢复

2026-11-20，answer-eval，承接ddf299d。本阶段没有写新评分；M6_21的第1题四组完整评分仍是当前进度。

## 排查结论与实际证据

1. 正常独立进程在默认受限exec环境中45秒未启动；faulthandler于20/40秒记录到相同栈：标准库`socket._fallback_socketpair`在accept等待，调用链来自asyncio事件循环自通信初始化。尚未导入项目应用，requests=[]。
2. 仅创建socketpair并设置3秒超时，默认执行同样失败；允许本机通信的执行上下文中，同一个Python、同一个最小操作在0.002秒成功。证据表明本轮启动阻塞来自执行环境的本机通信限制，无需业务代码变更。此前线程式超时没有当时栈，继续作为旧失败保留，不假称重新取得其栈。
3. 使用允许本机通信的执行上下文，空Key、离线模型环境启动正常app.main独立进程，1.533秒完成；只发6个GET，评分页面HTTP 200、列表/完整run/JSON/CSV与当前SQLite一致。
4. health中SQLite/retrieval ready=true、generation configured=false。整体ready=false是空Key检查的预期状态，不将此说成模型生成可用性新验收。
5. 自己的失败/成功进程均停止；数据库lease再次获取/释放成功，检查前后完整run相同，没有新评分、问答、实验或索引操作。

成功报告`artifacts/c/m6-review-http-readonly-permitted/result.json`，失败报告`artifacts/c/m6-review-http-readonly/result.json`，各自server.log与SHA保留。最小对照在socketpair-context-check.json，最终自检在成功目录final-self-check.json。阅读说明：[评分服务排查与正常读取验证](../M6评分服务启动排查与正常读取验证.md)。

## 当前评分与保护项

原run_id=`eval-20ac108503c44829a96ecca386d4b9de`。完整配对题1/30；人工整答4/96，剩92；拒答0/24；支持8/166，剩158。review历史8、含评分回答4，review_complete=false、formal_results=false。

第1题四组回答和8条支持均是用户明确确认，已在M6_21保存。最新部分评分导出仍为`artifacts/c/m6-human-review/paired-01/grade-confirmation/evaluation.partial-review.json`及CSV。当前SQLite不被旧备份覆盖；A原45文件、原3份M6材料、全部模型生成和此前评分未改动。

本阶段仅本机只读检查及文档/进度记录；没有源码变更，不重复工程回归。学校API0，累计已知191672 token保持，历史未知usage保留；没有下载、重建、容器或新实验。只在answer-eval本地提交，不push、不写main、不发团队消息。

## 下次继续

1. 读根续做入口、CURRENT与本报告，核对分支/HEAD/工作树；原AI辅助预审全部完成，不创建batch-16。
2. 第1题已全评，下一题第2题gold-crd-withdrawal-refund；原用户确认不顺延其他题。继续解释参考要点、四组实际答案/引用，再保存明确决定。
3. 如需本机HTTP读取或后续评分页操作，在具备本机通信权限的执行上下文启动正常进程。不要改业务代码来绕过本次环境限制，不重新下载模型或调用学校API。
4. 本轮未发送PATCH，后续有实际确认时仍用原评分校验/合并/审计逻辑保存，并单独记录字段来源。最新CURRENT保持人工已确认与AI建议分离。
5. 下次不重复这个诊断脚本：两次输出都已存在并受保护；除非出现新问题，直接复用结论。所有自己的检查服务当前已停止，可以关机休息。

本阶段最新提交与干净状态记录在根`C任务交接总览.md`。
