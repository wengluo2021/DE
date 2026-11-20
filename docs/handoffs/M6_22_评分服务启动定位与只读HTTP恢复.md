# M6 handoff 22: startup issue diagnosis and read-only HTTP recovery

2026-11-20, answer-eval, following ddf299d. No new scores were written in this stage; M6_21's complete scoring of question 1's four groups remains the current progress.

## Diagnosis conclusions and actual evidence

1. A normal standalone process did not start within 45 seconds in the default restricted exec environment; faulthandler recorded the same stack at 20/40 seconds: standard library `socket._fallback_socketpair` waiting in accept, with the call chain coming from asyncio event loop self-communication initialization. The project application had not yet been imported; requests=[].
2. Merely creating a socketpair and setting a 3 second timeout also fails under default execution; in an execution context that permits local communication, the same Python and the same minimal operation succeed within 0.002 seconds. The evidence indicates this round's startup blocking comes from the execution environment's local communication restriction, with no business code change needed. The earlier threaded timeout has no stack from that time; it remains retained as an old failure, and we do not falsely claim to have re-obtained its stack.
3. Using an execution context that permits local communication, with an empty key and offline model environment, a normal app.main standalone process started successfully and completed within 1.533 seconds; only 6 GETs were sent; the scoring page HTTP 200, list/complete run/JSON/CSV match the current SQLite.
4. In health, SQLite/retrieval ready=true, generation configured=false. Overall ready=false is the expected state of the empty-key check; this is not described as a new acceptance of model generation availability.
5. Both our own failed and successful processes were stopped; the database lease was acquired/released successfully again; the complete run was identical before and after the check; no new scoring, Q&A, experiments, or index operations.

Success report `artifacts/c/m6-review-http-readonly-permitted/result.json`, failure report `artifacts/c/m6-review-http-readonly/result.json`, each with server.log and SHA retained. The minimal control is in socketpair-context-check.json, and the final self-check is in the success directory's final-self-check.json. Reading notes: [Scoring service diagnosis and normal read verification ](../M6评分服务启动排查与正常读取验证.md).

## Current scoring and protected items

Original run_id=`eval-20ac108503c44829a96ecca386d4b9de`. Complete paired questions 1/30; human full answers 4/96, 92 remaining; refusals 0/24; supports 8/166, 158 remaining. Review history 8, answers with scores 4, review_complete=false, formal_results=false.

Question 1's four groups' answers and 8 supports are all explicitly confirmed by the user and were saved in M6_21. The latest partial scoring export remains `artifacts/c/m6-human-review/paired-01/grade-confirmation/evaluation.partial-review.json` and CSV. The current SQLite is not overwritten by old backups; A's original 45 file, the original 3 M6 materials, all model generations, and prior scores are unchanged.

This stage involved only local read-only checks and documentation/progress records; no source code changes, and the engineering regression was not repeated. School API 0; cumulative known 191672 tokens unchanged; historical unknown usage retained; no downloads, rebuilds, containers, or new experiments. Committed only locally in answer-eval; no push, no writing to main, no team messages.

## Continue next time

1. Read the root continuation entry, CURRENT, and this report; verify branch/HEAD/worktree; the original AI-assisted pre-review is fully complete; do not create batch-16.
2. Question 1 is fully scored; the next question is 2 gold-crd-withdrawal-refund; the original user confirmation does not extend to other questions. Continue explaining reference points and the four groups' actual answers/citations, then save an explicit decision.
3. If local HTTP reading or subsequent scoring page operations are needed, start a normal process in an execution context with local communication permission. Do not change business code to bypass this environment restriction, and do not re-download models or call the school API.
4. No PATCH was sent this round; when actual confirmation occurs later, still save using the original scoring validation/merge/audit logic, and record field sources separately. The latest CURRENT keeps human-confirmed and AI-suggested items separate.
5. Do not repeat this diagnostic script next time: both outputs already exist and are protected; unless a new issue arises, reuse the conclusions directly. All our own check services are currently stopped; you can shut down and rest.

The latest commit and clean state for this stage are recorded in the root `C任务交接总览.md`.
