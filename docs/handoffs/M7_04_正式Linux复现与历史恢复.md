# M7 Step 4 Handover: Formal Linux Q&A and History Migration Passed

2026-11-20, answer-eval, following 97580e8. M5 formal Windows passed, M6 one 120 items all completed with no human scores. This step completes formal Linux data/model/index/school API and Windows history result migration, without regenerating the 120 questions.

## Actual Passes

- Normal app.main, the same A five regulations/121 main articles/24+6 questions/42 evidence, fixed BGE-M3 CPU weights; an independent empty volume newly built 3515 blocks and four indexes, database build 1307.513 seconds.
- index_version is the same as Windows: e1d9e93d8abeea648bf64a2e7ac215e39f051a3c715dbe2ffa0664dac8b302bf; model/input versions and configuration fingerprints are consistent, and the SHA of 65 app/config/scripts files matches the current source.
- The four groups' Top5 original text/source checks, compare, school single question, save, new-process read, formal_ready/QA/evaluation prechecks all passed. Linux Q&A actually 1 times/1673 tokens, returning the same source-supported claims as the Windows single question. It was not counted into M6 formal scoring.
- Model/env mounted read-only; school TLS retained, temporary WSL loopback relay used the existing local proxy; its own application and relay have been stopped. Reports m7-linux-formal-retry.json and m7-linux-formal-e2e-retry.json.
- Windows completed SQLite generating an independent backup via a read-only connection; another Linux new SQLite volume, network disabled, no Key, read 120 items of the same run_id in the normal application. The JSON/CSV from the two starts are completely identical to the originals, 0 model calls, review_rows=0. m7-formal-result-restore-retry.json.
- Runtime image derag-c-m7-runtime:90f59e7032, sha256:c9fd36327ffa6d676a1fe45c4a6369cc91ad11d643168523448185b1ab1a89de. Python3.13.11/linux-amd64, 107 distributions; inherits the previously layer-by-layer verified official Python base, manifest digest ac76900038d8606cc99b413d4ede77bc7152f1e42b94cf5d50d4b80a999652fe. m7-a-image-provenance.json.

## Offline Candidates

- Image: deliveries/C-runtime-20261120-candidate.tar, 1870832128 bytes, SHA256 03a3be92bc9346aa79bb79ba4b5398e766ca46b7b45976962ae11617b734c003. The config SHA and 17 layer diff_ids have been verified; docker load has not yet been executed on another computer.
- Weights: deliveries/BGE-M3-5617a9f6-weights.tar, 2293350400 bytes, SHA256 bde9e27a9e758677f035097550944dab26b49fe99ba786dd4fd51b44dc08f958; 11 files individually match the fixed manifest. Existing downloads were reused, with no repeated online downloads.
- Streaming scan of the archive found no actual school Key. The old DE.tar is unchanged, with no image tag overwrite/publish. m7-offline-runtime-and-model.json.

## Failures and Corrections Both Retained

In the first round the container helper mistakenly used the Windows interpreter path, generating a call to 0; after changing to sys.executable it passed, without changing the production image. In the first round the history restore backup retained WAL mode, and the source directory being read-only prevented SQLite from creating shared-memory auxiliary files; only after adding immutable=1 to the independently completed stable snapshot did it pass, and this parameter is not used on the active original database. The original failure report is retained; gold, metrics, prompts, or the Windows original database were not changed to pass.

## Continuation and Limitations

Its own formal containers have been removed, and the index/database volumes are retained, see m7-nov20-cleanup.json; no prune, no stopping others' containers. Formal Linux index volumes: {"sqlite": "derag-c-formal-5961513ef7-sqlite", "chroma": "derag-c-formal-5961513ef7-chroma", "chunks": "derag-c-formal-5961513ef7-chunks", "indexes": "derag-c-formal-5961513ef7-indexes", "runs": "derag-c-formal-5961513ef7-runs"}.

Next, organize the source/data and unscored results ZIP, CRC/SHA, full-round self-check, and rest handover. M6 actual human scoring is still pending; the 166 claims with citations were not automatically scored; after scoring is complete, a new scored result should be exported and the final delivery list generated. The current candidate/synthetic old tests are not passed off as the final course grade. The first online model download on Linux was not separately tested; this step built the database offline from the accepted weights; the image archive has been verified layer by layer, and cross-machine load still needs verification on the receiving machine.

This round's actual generation attempts 123 times (M5 1 + M6 121 + Linux 1), known 189587 tokens, including 1 failures without usage; plus the previous 2085, cumulative known 191672 tokens, amount unknown. All subsequent reads/migrations/packaging 0 generation calls.
