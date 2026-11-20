# M7 handover 6: latest scoring database Linux recovery passed, continue final packaging

2026-11-20, answer-eval. The user asked for continuous completion, so work does not stop at this stage.

The first attempt failed before the container started; subsequently, cleaning up a mistakenly copied runtime-source-sha.json that had not yet been generated lost the original exception; the failure report has been retained and the missing item explicitly noted. A separate check confirmed the Docker daemon was not running; after starting the existing engine, a retry with a new directory/new nonce passed, with no installation or download.

Success evidence artifacts/c/m7-scored-restore-retry/result.json: image c9fd363…, 68 runtime source/config files identical to the current files; the original Chroma was copied read-only to a new dedicated volume, the original chunks/indexes/runs were mounted read-only, and the new SQLite volume was restored from a consistent backup. The container has networking disabled and an empty Key; normal app.main reads 120 items/124 audit history, and restart and JSON/CSV are byte-for-byte identical to the Windows final results. 21 human/99 AI source labels are preserved, external model calls 0, indexes not rebuilt. My own check container has been deleted, the Windows database/original volume logic is unchanged, and the two new volumes for this task are retained for recovery.

Updated the README current entry point, the C report, and the delivery/recovery instructions. Old instructions were moved into the history record or retained by Git; the original A inputs, the original unscored experiment, and all old archives are unchanged. The final self-check for this M7 stage is in the success directory final-self-check.json.

Next, create the new final package deliveries/20261120-C-final-mixed-review: prepare_delivery/verify_delivery generate and verify the source frozen data, and separately package the complete scoring/evidence/SQLite backup ZIP; reuse the verified runtime image and fixed weights to generate DE.tar and the weights package, with SHA/CRC/per-member/key-isolation verification, and generate the final manifest and reading instructions. Do not overwrite the old DE.tar or candidate packages, and do not publish/push.

The scoring fields 30/30 are complete, with mixed sources 21 human/99 authorized AI, so they can no longer be labeled all-human; from now on do not repeat question 31, batch-16, 120 item generation, model downloads, or regression on the unchanged 401 items. Cumulative known school 191672 tokens and historical unknown usage remain unchanged.

To resume after an interruption, first read the root resume entry, CURRENT, and this report, and check answer-eval/HEAD/working tree. For the latest commit see the root overview; the only remaining work is final packaging and global delivery verification, and do not restore old databases to overwrite completed scores.

Supplement: the newly generated runtime-source-sha.json showed a CRLF normalization warning during Git commit; it has been converted to LF and the integrity proof updated; this is only new metadata line endings, and the 68 source SHAs, original A/M6/SQLite/exports are all unchanged, so recovery acceptance does not need to be rerun.
