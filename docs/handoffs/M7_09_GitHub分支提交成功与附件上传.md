# M7 handover 9: GitHub branch committed, attachments uploading

2026-11-20. After the user provided the Authentication Succeeded page, it was verified that local Git saved the bcj6 login. The previous login blocker is resolved; no need to log in again or send a password/Token.

Ordinary proxy connections still show TLS handshake failure; only after disabling the forced old proxy for this command and using HTTP/1.1, the 76 accumulated local commits were successfully fast-forward pushed, with server answer-eval=`c9595b556325b373c634077b2b7c2e57fe206c8f`. main remains 66dbada9ed7c2339216d80bcc456ee5b00342fac, not merged or force-pushed.

Draft PR: https://github.com/wengluo2021/DE/pull/2，供组长审阅，未合并。连接器创建请求传输失败后，先用REST检查避免重复，再创建PR #2.

Independent C delivery Release draft ID=452404260, tag planned c-delivery-20261120. The source/frozen-data ZIP and the complete scoring/SQLite backup ZIP have been uploaded, and server-side size and SHA-256 match local. DE.tar and the 3 weight shards are uploading in parallel, and the guide/manifest/merge script will also be uploaded. Publish only after all 10 attachments pass; do not claim the full package is online early.

The upload tool is located at .bootstrap/Upload-C-GitHub-Release.py in the workspace, and progress is in .bootstrap/github-release-progress.json. On resume, release_id is reused; attachments that are already complete and have the same server-side SHA are skipped; only unfinished starter items from this release are cleaned up, and formal experiments/weights or indexes are not rebuilt. The token is read only by standard Git credentials into process memory and is not written to reports or command arguments.

All business code, frozen A materials, original results for 120 items, and 21 human / 99 authorized AI scores from this round are retained. The school API adds 0. The source package remains pinned at 16a8e82; subsequent commits only deliver documentation/upload bookkeeping. Going forward, the upload completion status of M7_10 or the latest CURRENT is authoritative.
