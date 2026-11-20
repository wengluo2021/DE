# M7 Independent Engineering Re-verification: Linux Version After A Adaptation

2026-11-20. The current A new dependencies and C adaptation have rebuilt an independent candidate image; the old 11 month 19 image conclusions were not mixed in.

- test：derag-c-m7-check:90f59e7032，sha256:d6615d52edc0f8fcae6b02f66154a19e3b072154d5131a2616a23e3e022c2234。
- runtime：derag-c-m7-runtime:90f59e7032，sha256:c9fd36327ffa6d676a1fe45c4a6369cc91ad11d643168523448185b1ab1a89de。
- Linux 401 items: 400 passed, 1 Windows native path protection-only skip, 0 failed/errors, 66.856 seconds. m7-a-linux-tests.xml.
- runtime normal app.main HTTP check passed; actually no formal_corpus run directory and *.lock. The image did not inject the school Key.
- Read-only reuse of the local fixed weights, rebuilding the synthetic four indexes in an empty temporary directory, 12 real CPU retrieval/original text/API/overlong token rejection checks passed, 91.839 seconds. m7-a-linux-real-smoke.json. This is not formal regulation retrieval or real Linux generation.
- First-round failure m7-a-docker-check.json: the Docker directory exception mistakenly brought in the sqlite lock in use by Windows, and the read lock caused EOF. After explicitly excluding all run directories and *.lock at the end, the actual re-verification passed, without deleting locks or interrupting the formal database build.
- Full record m7-a-docker-final-check.json; the temporary loopback relay has been stopped, and its own three acceptance containers have been cleaned up. Other containers are not stopped, and no prune is done.

The formal A source/data candidate package delivery-20261120-A has 181 files; standard library verification and new-directory/new-process verification passed, and the version and fingerprint are retained. m7-a-portable-delivery.json. The existing Windows venv is reused; this step is not called a clean dependency environment; the package does not contain models/indexes/SQLite/formal results, nor is it the final course delivery. It is a source snapshot at that time; subsequent handover/results should generate a new candidate and not overwrite it.

M5 formal Windows acceptance passed, see M5_07. M6 real 120 items are still pending running/actual human scoring. M7 still requires formal Linux indexes, real generation, formal history export-restore, and final image/weights/results archive acceptance; this report does not treat the synthetic CPU smoke test as formally complete.
