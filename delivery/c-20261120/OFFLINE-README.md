# C task final delivery: read me first

2026-11-20. This directory contains the offline-deliverable source/frozen data, complete scoring/backup, Linux CPU image, and fixed model weights. The old DE.tar and the earlier candidate/unreviewed packages are not covered.

## Your project and the C task

The project compares two regulation chunking methods and two sizes: first look up the given regulation, then have the model answer based on the retrieved chunks and provide citations. A provides the regulations/question set, B handles chunking/retrieval, and you are responsible for C, which has implemented question answering, citation verification, save/restore, the four experiment groups/scoring, the page, and integrated delivery.

All real 30 questions × 4 groups × 120 items are complete, with 0 technical errors; 96 full answers, 24 refusals, and 166 citation judgments are all complete. The scoring sources are 21 specific human confirmations + 99 AI-assisted items under your authorization, including 45 human / 121 AI claim judgments; this is not described as all purely human verification.

Fully correct counts: F400 6/24, S400 9/24, F800 10/24, S800 13/24; citation support 27/36, 33/35, 42/45, 50/50. There were 20 incorrect refusals on answerable questions; these failures were not removed. For methods, denominators, and limitations, see docs/C部分报告草稿.md and docs/M6评分方式与授权记录.md in the source.

## Files and verification

| File | Bytes | SHA-256 |
| --- | --- | --- |
| C-source-data-scored-20261120.zip | 2073716 | `105fa047ed16e17a38edd92c12ed4cc49ab025c3286834d136a673ffeb6b81d7` |
| C-scored-results-20261120.zip | 33513874 | `e9b6726bebad5b4422a728d1514b350e708fc67494f0a2261d3c565661dad2d9` |
| DE.tar | 1870832128 | `0a42af6e5a64e55383b20970b98fff8262e2d746bea26b0f189951aeb79d1c05` |
| BGE-M3-5617a9f6-weights.tar | 2293350400 | `bde9e27a9e758677f035097550944dab26b49fe99ba786dd4fd51b44dc08f958` |

FINAL-MANIFEST.json records the source and acceptance scope; SHA256SUMS.txt can be checked with `sha256sum --check SHA256SUMS.txt`. source-data is an expanded source snapshot for easier reading; the ZIP is for copying to a new working directory. The source snapshot Git commit is `16a8e82b62cbe5a76e48bb5715fb7a15a2338a07`; the final packaging work log is kept separately in the project repository.

## No recovery needed on the current computer

The current DERag working repository already stores all scoring; continue viewing it in the original directory. Do not overwrite it with these old/new backups, and do not rerun the 120 questions. To view results, use the empty-Key method at the top of the README and browse /evaluation; the school API was called 0 additional times during scoring/backup/packaging.

## On a new machine, unpack and verify first

1. Extract the source ZIP into a new DERag directory. First run `python -B -S scripts/verify_delivery.py .` with Python 3.13; it only needs the standard library.
2. Then extract the results ZIP into the same new directory to obtain artifacts and sqlite-backup; the complete latest results are in artifacts/c/m6-final-scored, and all intermediate scoring, original unscored data, and acceptance evidence are retained.
3. Extract the weights TAR in the new source root to obtain models/embedding. After adding runtime files, the directory is no longer the original unpacked snapshot, so do not use the source manifest to claim the entire directory is unchanged.
4. `docker load --input DE.tar` loads the image; the tag is `de:latest`, and the image ID is `sha256:c9fd36327ffa6d676a1fe45c4a6369cc91ad11d643168523448185b1ab1a89de`. The image does not need network access to install dependencies; model weights are not in the image and are provided as a separate package.

## View existing scoring with Docker first

Run the following in a Linux/WSL shell, replacing /ABS/NEW/DERag with the new unpacked directory. The new volume name is for independent recovery; the Python command stops if the target already has a database and does not overwrite existing scores:

```bash
docker volume create derag-reviewed-sqlite
docker run --rm --network none --mount type=bind,source=/ABS/NEW/DERag/sqlite-backup,target=/snapshot,readonly --mount type=volume,source=derag-reviewed-sqlite,target=/target de:latest python -c "from pathlib import Path; import sqlite3; p=Path('/target/derag.sqlite3'); assert not p.exists(); s=sqlite3.connect('file:/snapshot/derag.sqlite3?mode=ro&immutable=1',uri=True); d=sqlite3.connect(p); s.backup(d); d.close(); s.close()"
docker run --name DE -d -p 127.0.0.1:8766:8000 -e DERAG_CONFIG=config/experiment.formal-a.json -e DERAG_ENV_FILE=/dev/null -e LLM_API_KEY= --mount type=volume,source=derag-reviewed-sqlite,target=/app/data/formal_corpus/sqlite de:latest
```

Open http://127.0.0.1:8766/evaluation，选择`eval-20ac108503c44829a96ecca386d4b9de`。本方式只准备已有结果浏览，不含新问答所需的Key/索引挂载，health整体未ready不代表历史记录丢失。需要新生成时按docs/Docker与交付包复现.md配置私密env、只读模型与独立原生索引卷；原正式120项仍保留，不用重跑。

## Tested and scope

Windows 401 items and Linux 400 items passed / 1 platform skips; the formal index and real school Q&A/restart were accepted in an earlier stage. The latest scoring database was recovered on a new Linux volume with networking disabled/no Key, 124 audit records were fully retained, and exports at startup and after restart are byte-for-byte identical to Windows; 68 runtime code/config files are identical to this image, and 21/99 source labels are retained. The original volume was not modified, and my own inspection container has been removed.

The new source directory passed the standard-library manifest and formal A material verification; both ZIPs had CRC and per-member SHA verified, the DE.tar configuration and 17 layer diff_id were verified, and the weights package has the same SHA as the fixed archive previously accepted file-by-file for 11 files. All public packages were scanned and contain no actual Keys. No models were re-downloaded, no index was rebuilt, and no school API was called.

The local WSL test is not acceptance on another physical machine; the recipient still needs to actually load/run it. Scoring is a disclosed AI-assisted mixed source, not a two-person independent gold standard. Final course submission and presentation review with the teacher/team lead are the team's responsibility. This round did not push, write to main, or send team messages.
