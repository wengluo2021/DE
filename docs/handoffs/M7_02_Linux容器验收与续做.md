**Latest handoff: delivery tooling and Linux container engineering acceptance passed, formal materials/experiments still await A**

Date 2026-11-19. Continuing from answer-eval's 2bbb2c8. User confirmed there are no A artifacts on GitHub, likely not yet ready; closing review found the remote still has 4 old branches and a merged B PR, with no new delivery. Did not collect regulations, write questions, or generate formal scores on A's behalf. This report supplements M7 independent engineering preparation; M5 formal material acceptance, M6 and M7 final delivery remain incomplete.

**This round's completion and actual self-check.**

| Item | Measured result |
| --- | --- |
| Delivery preparation | prepare_delivery first validates existing frozen corpus/24+6 questions, then copies original bytes, generating portable config, prompt snapshots and per-file SHA. Only new directories allowed, local dotenv/process credentials ignored, models, databases, indexes and caches excluded. Inputs clearly marked SYNTHETIC cannot become formal candidates. |
| Independent validation | verify_delivery uses only the Python standard library; actual python -S run passed. Rejects tampering, missing files, extra files, out-of-bounds paths and overwrites. Public .env.example and each module's dependency list are in the package; real keys are not. |
| Relocation rehearsal | New SYNTHETIC frozen materials prepared into a package, copied to a second directory, validated in new directory/new process with matching versions/24+6 and experiment fingerprint; reused the existing Windows venv, did not call this step a clean dependency environment. |
| Windows targeted regression | Final 57 passed in 7.54s; earlier 32/35-item phase checks also retained; pip check passed. |
| Linux full regression | **369 items: 368 passed, 1 skipped, 0 failed/errored, 45.558 seconds**. Skipped items apply only to Windows native long-path protection, already covered by the Windows phase; no assertions deleted or failing cases skipped. |
| Image | Independent test and final candidate images actually built successfully. Official Python 3.13.11/Debian 12 base, linux/amd64; does not copy personal venv, existing indexes or model caches, dependencies installed from fixed manifest. |
| CPU and platform dependencies | torch 2.15.0+cpu, build/runtime check cuda=None; Linux additionally uvloop 0.23.0. Preflight checks both locks on Linux, Windows does not require uvloop. Runtime image 105 Python distributions (including pip) recorded. |
| Normal application | final image normal app.main starts, 5 pages/design routes HTTP 200; health liveness, ready=false, keys not configured, consistent with no formal input state. No QA/retrieval factory injected. |
| Real Linux retrieval | test image read-only mounts existing fixed BGE-M3 weights, network disabled, rebuilds four indexes in empty /tmp; 1024-dim CPU, 12 semantic retrievals, original text/source/item number, real token over-limit rejection, retrieval/comparison API checks passed, took 67500.965ms. Four groups chunk counts 34/47/18/31. Not a formal regulation experiment. |
| Current source verification | 58 files' SHA in image app/config/scripts match current working tree; dependency preflight passed. Image has no school keys or temporary build proxy config. |
| Cost/cleanup | This round generated API calls 0; existing cumulative still 6 successes/2085 tokens, price unknown. Acceptance containers and temporary loopback proxy cleaned up, Windows/Linux proxy residue both 0. Docker/WSL engine kept for later use, did not stop other containers or run global prune. |

Final public text check 222 files (including source, docs and JSON/XML), no actual keys found; Markdown encoding/fence and non-XML source whitespace checks passed. Historical failure XML retains original format; evidence not rewritten to eliminate whitespace warnings.

Real weight version remains BAAI/bge-m3's 5617a9f61b028005a4858fdac845db406aefb181, model directory read-only mounted and verified against existing file manifest; did not re-download the ~2.3GB weights, nor perform new paid Q&A. First Linux online model download, Linux school API real generation not yet verified; do not equate offline CPU retrieval with these two.

**Recoverable images and evidence.**

- Runtime candidate: `derag-c-m7-runtime:3713835790`, ID `sha256:9ad991e4775fbb0a8c8c254c742e421574bda3c2dd6668da8afa5eb4b4c78017`.
- Test candidate: `derag-c-m7-check:3713835790`, ID `sha256:acdb76ae35bef808c76443aef22f73b4046cce5d64f42eae7b15c3f38403b80f`.
- Official Python base manifest digest: `sha256:ac76900038d8606cc99b413d4ede77bc7152f1e42b94cf5d50d4b80a999652fe`; after import image ID matches official config digest. Full layer/diff_id verification see m7-python-base-verification.json.
- `artifacts/c/m7-docker-runtime-and-model.json`: last passing runtime/model acceptance; reused the **same-ID** image and JUnit from m7-docker-verified.json that passed 369 tests, not rerun without reason.
- `m7-linux-tests.xml`, `m7-windows-final-tests.xml`: final Linux full and Windows-related regression.
- `m7-linux-runtime.json`, `m7-linux-software.json`, `m7-image-provenance.json`: normal HTTP, actual software/source SHA, image ID and Debian system packages.
- `m7-linux-real/real-smoke.json` and model-manifest.json: real Linux CPU retrieval and weight verification.
- `m7-delivery-final-rehearsal.json`, `m7-self-check.json`, `m7-cleanup.json`: actual relocation, self-check and cleanup.

The above are local candidate images, did not overwrite old de or DE.tar, and were not pushed/published. The final formal image should be rebuilt after A's data and M6 results are complete, recording final image/archive SHA, and the current candidate must not be called the final course delivery.

**Problems encountered and corrections are both retained.**

1. Docker is in WSL rather than the Windows PATH; the original engine was not running, so the existing engine was started normally, without installing system components or reading other jobs/credentials. An early WSL inventory failed to read due to mixed encodings; after normal host permissions/correct decoding, ubuntu20 and Docker24 were located.0.6.
2. The first round of direct Docker Hub connection timed out (m7-docker-check.json). The base image was obtained from the official repository via the existing Windows 127.0.0.1:7890 proxy; after verifying the manifest/config/per-layer compressed digests and the decompressed diff_id, it was imported, with TLS retained; the anonymous pull token was not written to logs or passed to the school Key.
3. The second round of direct connection depended on about 120kB/s, so this task cancelled its own build client (m7-docker-check-after-base-import.json). A temporary byte relay bound only to WSL 127.0.0.1 was then used to connect to the existing Windows proxy; TLS was not decrypted, and the system proxy/listeners/firewall were not modified. The final image has no build proxy environment variables.
4. In the first round of 369 Linux items, 1 failed (m7-linux-first-tests.xml): the image's default DERAG_DATA_DIR overrode the temporary corpus of that test. Only that test was made to isolate this environment variable, retaining all assertions and the production process environment > JSON priority; after rerunning, 368 passed / 1 Windows-only skip.
5. After the full tests and image succeeded, the outer helper script's cleanup code was mistakenly inserted into a triple-quoted string, causing a syntax error in runtime-http's temporary python -c (m7-docker-verified.json). What was fixed was the acceptance helper; production source was unaffected; the original image ID was checked, the already-passed test evidence was reused, and then the actual HTTP and model checks were completed.
6. Log extraction hit a StopIteration due to the WSL prefix, and metadata command format escaping also failed at one point; parsing was changed to start from the JSON start and to use dpkg's default output format, without changing the original evidence or production logic. The related operations are recorded in that day's log.

Outer recovery scripts: `.bootstrap/Check-M7-Docker.py`, Check-M7-Delivery.py, Prepare-M7-Base-Image.py; run records are in `.bootstrap/m7docker-*`. The latest successful re-verification directory is m7docker-ec3c41df9a, and the full build/test directory is m7docker-3713835790. The official base image archive is located at .bootstrap/m7-python-base and does not enter the business Git. The scripts refuse to overwrite evidence by default and do not re-download/build/charge for recovery context.

**Next steps still follow the original phase order.**

1. Read this report, M5_04, and "Third-Party Integration and Formal Data Access" and "Docker and Delivery Package Reproduction", and check answer-eval and the latest local checkpoint. Do not reset, rebuild the venv, re-download models, or repeat this round's acceptance.
2. Wait for the team lead/A to deliver 5–8 official snapshots and processed Document, corpus manifest, 24 answerable + 6 refusal gold.jsonl and gold manifest, with version/source/directory. The user has confirmed they are not yet prepared; do not repeatedly ask or fill in on their behalf.
3. After receipt, generate a new formal configuration, verify the frozen bytes, rebuild the four indexes with B code, check formal questions against official sources/complete citations/save-restore, and finish M5 formal acceptance. For the Docker runtime, use a portable configuration, read-only model, and an independent writable output volume; the existing quoted private dotenv can be mounted read-only and DERAG_ENV_FILE set.
4. M6 runs four groups of 120 items on the same frozen 30 questions, saving failures and actual model usage, and then actual reviewers verify answers/citations/refusals and score them; synthetic test scores are not used to pass off as human results.
5. M7 finally re-verifies the complete reproduction of formal data/configuration/models/results, real Linux generation and export, and packages the new image, weights/data/results and hashes. The current engineering image and tools can be reused, but do not replace this step.

The source is still only answer-eval; this round does not push, merge main, or send messages to the team; the latest commit and working tree verification are in the repository-outer "C任务交接总览.md".
