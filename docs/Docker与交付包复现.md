# Docker and delivery package reproduction

This is C's delivery preparation note. A's formal five regulations and frozen 24+6 questions were integrated and validated on 2026-11-20; for formal M5/M6 progress see the latest handover. This note, a synthetic drill, or a page that opens does not represent a formal result. For the latest measured status and limitations see `docs/handoffs/`; do not write preparation completion as completion of all of M7.

## 1. First prepare verifiable source and data packages

In a DERag environment with existing dependencies, first generate a new formal configuration per "Third-Party Integration and Formal Data Access" and validate A data, then run:

```powershell
.venv/Scripts/python.exe -m scripts.prepare_delivery --config config/experiment.formal-a.json --output ../delivery-NEW
```

The output directory must not exist. The tool reads only the selected JSON and ignores process credentials and local dotenv; after validating the corpus and question set it copies the original bytes without re-cleaning or modifying questions. It generates `config/experiment.delivery.json`, a prompt snapshot, and `DELIVERY-MANIFEST.json`, changes data/model/prompt to portable paths within the package, and confirms the experiment fingerprint is unchanged. Under the A layout it retains data/formal_corpus, data/eval, data/processed, and the source manifest; the attachment's complete structure is also packaged as original bytes. Model weights, existing Chroma, SQLite, historical experiments, and private env are not included in this source package. Formally saved per-question results and model weights are retained as separately verified delivery materials and must not mix different versions during packaging.

The raw snapshot, processed documents, both manifests, and gold.jsonl are each recorded file by file with SHA-256; missing materials, hash mismatches, or an existing output cause an explicit failure. Incomplete directories already produced after a failure are retained; inspect them and use a new target directory, without overwriting or automatic recursive deletion.

`--synthetic` is only for explicit development synthetic drills, and its output is marked `synthetic_rehearsal`; the default formal mode rejects development configurations and inputs clearly marked SYNTHETIC. A formal candidate package also does not automatically certify sources: A remains responsible for official materials and standard question verification, and C is responsible for scoring formally generated answers.

## 2. After receiving the package, verify first, then run

In the newly unpacked directory, verify using the Python standard library; `-B` avoids generating extra bytecode:

```bash
python -B -S scripts/verify_delivery.py .
```

This command does not require Pydantic or model libraries to be installed first. It checks manifest format, relative paths, file completeness, and SHA; modifications, missing files, extra files, or path escapes all fail. Run this check on a newly unpacked directory that has not been run; databases/caches added after running belong to the working directory, and it cannot be treated as the original delivery directory to continue claiming bytes are unchanged. The verification manifest guarantees consistency with the saved manifest; source authenticity still requires the team's delivery records and version verification.

The old candidate image 2026-11-19 passed the Linux engineering tests at the time; 2026-11-20 was rebuilt with the new A dependencies/adaptation and passed 401 Windows items, 400 Linux items/1 dedicated skips, formal Linux Q&A/restart, and migration of 120 historical results, see M7_04; the old image is not treated as the current final artifact. Docker no longer forces DERAG_DATA_DIR and uses the data path of the selected configuration; A's formal run directory is /app/data/formal_corpus, and the corresponding SQLite/Chroma/chunks/indexes/runs volumes should also be mounted under that directory, not overriding it with /app/data.

## 3. Build the Linux CPU image

Use Docker Engine, targeting `linux/amd64`. The following commands run in the package directory; the first build requires network access for dependencies and will not download embedding weights or send model requests.

```bash
docker build --platform linux/amd64 --target test -t derag-check .
docker run --rm --network none derag-check
docker build --platform linux/amd64 --target final -t de .
```

The `test` image includes fixed test dependencies, test source, and necessary documentation; the default `final` image keeps only runtime dependencies and code. Choose `de` for formal runs; do not call the test image the formal delivery image. During actual acceptance, record both image IDs, the Python base image digest, the test JUnit, and build logs; missing successful results in the logs cannot be treated as a passing build.

The Dockerfile pins Python 3.13.11, first installs `torch==2.15.0+cpu` from the official PyTorch CPU index, then installs the unified lock; the build checks `torch.version.cuda is None`. The precheck allows only the `+cpu` build suffix for that pinned torch version and still rejects other release versions or CUDA suffixes; other packages continue to be strictly compared against pinned versions. See [official CPU installation instructions ](https://pytorch.org/get-started/locally/); the actual CPU index version has separate read-only verification evidence.

Actual Linux resolution also found that uvicorn[standard] requires the Linux-only uvloop, so `requirements-linux.txt` was added to lock uvloop 0.23.0. Docker installs the unified lock first, then this supplementary lock; the precheck checks both locks on Linux, and Windows does not install uvloop. Final software versions are based on actual installation records and image IDs; the Windows dependency count cannot be directly treated as all Linux dependencies.

`.dockerignore` explicitly excludes the root/formal_corpus runtime directory and all *.lock after directory exceptions, preventing reads of in-use locks, databases, or native indexes. It uses an allowlist permitting program/config, tests, and frozen raw/processed/eval/manifest; it continues to exclude models, credential files, databases, indexes, results, and caches. `data/.gitkeep` only makes the directory exist when there is no formal input; it is not a regulation or question set. For Docker context rules see [official documentation ](https://docs.docker.com/build/concepts/context/).

The current computer's Windows PATH has no Docker; the existing WSL `ubuntu20` Docker 24.0.6 engine was found and started. `wsl.exe -d ubuntu20 -u root -- docker ...` is available on this machine, and mounted Windows paths are first converted via the same WSL's `wslpath -a`. Do not reinstall Docker just because the Windows command is not found. Independent acceptance images use random suffixes and do not overwrite the old `de`; do not stop containers that do not belong to this task.

## 4. Configuration, read-only model, and persistent output

On the Docker host, prepare the complete `models/embedding` and its `derag-model-manifest.json`, verified by fixed revision/file SHA. Mount the model directory read-only into `/app/models/embedding`. The formal candidate package's frozen data is already copied into the image; do not mount the entire `/app/data` with an empty host directory, or it will hide the inputs in the image, see [Docker mount documentation ](https://docs.docker.com/engine/storage/bind-mounts/).

The private connection file can be mounted read-only at `/run/secrets/llm.env` with `DERAG_ENV_FILE` set, suitable for an existing quoted dotenv file on this machine. Docker's own `--env-file` and python-dotenv interpret quotes differently; if choosing `--env-file`, use an unquoted KEY=value format like `.env.example`, and do not directly assume the existing private file format is fully equivalent. The original Key file need not be rewritten, and the key does not enter the image.

The endpoint/model/transport in the private env should match the selected experiment JSON; overriding these fields changes the actual experiment fingerprint, while the Key itself does not enter the experiment fingerprint.

The following examples run in a Linux/WSL shell; replace the two paths with actual absolute paths:

```bash
docker run --name DE -d -p 127.0.0.1:8766:8000 \
  -e DERAG_CONFIG=config/experiment.delivery.json \
  -e DERAG_ENV_FILE=/run/secrets/llm.env \
  --mount type=bind,source=/ABS/PATH/private.env,target=/run/secrets/llm.env,readonly \
  --mount type=bind,source=/ABS/PATH/models/embedding,target=/app/models/embedding,readonly \
  --mount type=volume,source=derag-sqlite,target=/app/data/formal_corpus/sqlite \
  --mount type=volume,source=derag-chroma,target=/app/data/formal_corpus/chroma \
  --mount type=volume,source=derag-chunks,target=/app/data/formal_corpus/chunks \
  --mount type=volume,source=derag-indexes,target=/app/data/formal_corpus/indexes \
  --mount type=volume,source=derag-runs,target=/app/data/formal_corpus/runs \
  de
```

Only one worker; no reload. The Dockerfile does not force-override the generated transport; the formal configuration should explicitly select the verified curl/httpx; the image has curl and CA installed. Encoding is offline by default, using only the local model; the first model download uses an explicit download script in a networked environment, and automatic pulling at startup cannot be treated as a reproduction step.

## 5. Formal container acceptance order

```bash
docker exec DE python -m scripts.validate_data --config config/experiment.delivery.json
docker exec DE python -m scripts.build_indexes
docker exec DE python -m scripts.preflight
```

The health check only determines whether the HTTP service is alive; `/api/health`'s `ready` and preflight's `formal_ready` indicate whether the required components match. A container without data/Key can open the page but is explicitly not ready. After confirming official sources, formal single questions, complete citations, and restart persistence, follow the "Evaluation Usage Instructions" to do M6's 120 items and actual human scoring; synthetic offline scoring cannot substitute.

Final M7 must install from a new environment, verify inputs and model, rebuild the four groups, do real Q&A, check the formal experiment and export, then record image/data/model/result SHA and package. The old DE.tar is a frontend preview; overwriting it does not mean the new version is complete. Export a new image package only after final acceptance passes, and retain the filename, image ID/digest, and package SHA; external release/push still follows user authorization.
