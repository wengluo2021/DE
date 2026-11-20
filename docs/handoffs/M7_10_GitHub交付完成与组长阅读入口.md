# M7 handoff 10: GitHub delivery completed

2026-11-20. The user has authorized the commit and login; this stage is complete after a successful login; no further login, model download, or experiment run is needed.

Source code/reports/all scoring evidence have been fast-forward pushed to answer-eval. Draft PR: https://github.com/wengluo2021/DE/pull/2，供组长审阅，未合并main。

Standalone C delivery page: https://github.com/wengluo2021/DE/releases/tag/c-delivery-20261120。全部10个附件uploaded，官方API的size及sha256逐项对应本地准备清单，已发布为C部分prerelease，不替代全组正式版本或设为仓库latest。具体附件下载链接和实际服务端摘要见delivery/c-20261120/GITHUB-RECEIPT.json。

Includes the source frozen materials ZIP, the full scoring/SQLite backup ZIP, DE.tar, 3 weight shards, the guide ZIP, the attachment JSON, the SHA manifest, and the merge script. First download and extract the guide; after merging the weight shards, verify against the original TAR SHA. At preparation time, not_uploaded in GITHUB-ASSETS.json was a historical preparation snapshot; the upload receipts are now authoritative.

The old DE.tar, all old candidate/unreviewed outputs, and the original outputs for the formal 120 items are retained. The original four packages and the pinned 16a8e82 source snapshot are unchanged; subsequent commits only add entry points/upload receipts. The specific 21 human confirmation + 99 authorized AI sources are retained and cannot be called a fully human gold standard. The Windows/Linux acceptance and the boundary that cross-machine testing has not been performed remain unchanged.

Login credentials are used only by the standard Git manager in process memory; public files contain no real keys/tokens. This stage adds 0 school APIs, with no new generation, model downloads, or index rebuilds. TLS previously failed under the proxy; the currently successful Git commands use a temporary empty http.proxy and HTTP/1.1; system proxy/certificate verification was not changed.

All stages have dated logs and self-checks. Going forward, the team lead will review the PR, consolidate the whole team's report, and make the final submission; this round does not merge into main or send team messages on anyone's behalf. The actual final HEAD, remote consistency, and working tree status are governed by the root handoff overview.
