# C Task Completion Notes and Reading Path

2026-11-20. **Under this authorization, C's local implementation, formal experiments, mixed-source scoring, cross-platform recovery, and offline delivery are complete.** The source remains in answer-eval; after local delivery was completed, the user separately authorized organizing and committing to GitHub, and the latest upload status is in [M7_10 ](handoffs/M7_10_GitHub交付完成与组长阅读入口.md). I did not directly modify main or submit the course assignment on the team's behalf.

## Project and your task

The project studies how chunking regulations first affects retrieval and answering. The system first finds the given regulation snippets, then has an off-the-shelf LLM answer based on the snippets with citations; no LLM was retrained. A handles regulation/standard questions, B handles chunking/vector retrieval, and your C is responsible for connecting answering, citation verification, persistence, pages, experiments/scoring, and the final run package into one complete system.

The C module can now perform cited answering/refusal, verbatim source verification, Q&A and task persistence, four-group batch experiments, scoring history, JSON/CSV export, and four-page API integration. It is connected to A's formal five regulations and B's real BGE-M3/Chroma; the formal experiments are not simulated data.

## What has been delivered

1. Formal 30 questions × 4 groups, 120 results in total, 0 technical errors; original model answers, retrieval evidence, and all failure/retry records are retained.
2. 96 overall-answer grades, 24 refusal judgments, and 166 citation judgments are all complete; sources are 21 specific human confirmations and 99 C-authorized AI-assisted, and are not described as all purely human-reviewed.
3. Windows 401 items and Linux 400 items passed/1 platform skips; the latest scoring database was also restored on a new Linux volume with network disabled/no key, and 124 scoring-history records, startup, and post-restart export bytes were all identical.
4. The final offline package, SHA manifest, per-member/layer verification, and no-key check have passed. The old DE.tar and all old candidate/unreviewed archives are retained.

Complete correct counts are F400 6/24, S400 9/24, F800 10/24, S800 13/24; citation support 27/36, 33/35, 42/45, 50/50. S800 is best in this batch but still not fully correct, and the 20 incorrect refusals of answerable questions are not hidden. For specific methods, denominators, cases, and limitations, read the [C section report ](C部分报告草稿.md).

## Reading order and file locations

First read [Scoring method and authorization record ](M6评分方式与授权记录.md), then the [C section report ](C部分报告草稿.md), and for reproduction read [Delivery and recovery ](本轮交付清单与恢复.md). The original per-question Chinese/English notes, stage handovers, and date logs are all retained.

The final files are in workspace `deliveries/20261120-C-final-mixed-review/`; first open README_先读我.md in it. It contains the source/frozen-data ZIP, full scoring/evidence/SQLite-backup ZIP, DE.tar, fixed model weights TAR, and FINAL-MANIFEST/SHA256SUMS.

| File | Bytes | SHA-256 |
| --- | --- | --- |
| C-source-data-scored-20261120.zip | 2073716 | `105fa047ed16e17a38edd92c12ed4cc49ab025c3286834d136a673ffeb6b81d7` |
| C-scored-results-20261120.zip | 33513874 | `e9b6726bebad5b4422a728d1514b350e708fc67494f0a2261d3c565661dad2d9` |
| DE.tar | 1870832128 | `0a42af6e5a64e55383b20970b98fff8262e2d746bea26b0f189951aeb79d1c05` |
| BGE-M3-5617a9f6-weights.tar | 2293350400 | `bde9e27a9e758677f035097550944dab26b49fe99ba786dd4fd51b44dc08f958` |

The offline source snapshot is `16a8e82b62cbe5a76e48bb5715fb7a15a2338a07`; subsequent local commits only add the delivery manifest, source notes, and wrap-up records, with no change to business code. The README in the package already has independent complete recovery steps; the original key is not distributed with the package.

For GitHub reading and downloads, start from the [repository delivery navigation ](../delivery/c-20261120/README.md).

## What you hand to the team lead next

Provide the final directory, C report, and scoring method notes for the team lead to review and integrate. Git still keeps a separate branch; team lead merging, whole-team course report/presentation, and final submission are handled by the team; C delivery attachments were published under subsequent user authorization, and no team messages were sent on the team's behalf. The complete materials are ready; there is no need to run the 120 questions again or re-download models for handover.

The current working database already has all results. On reopening the computer, just look at the root continuation entry and the latest M7_07; do not restore an old backup over the current database. If new features or new experiments are needed in the future, record a new version and keep this baseline.
