# C任务最终交付：先读我

2026-11-20。本目录包含可离线交付的源码/冻结数据、完整评分/备份、Linux CPU镜像和固定模型权重。旧DE.tar及此前candidate/unreviewed包未覆盖。

## 你的项目和C任务

项目比较两种法规分块方式与两种大小：先查给定法规，再让模型按查到的片段回答并给引用。A提供法规/题集，B负责分块/检索，你负责的C已实现问答、引用核验、保存/恢复、四组实验/评分、页面与集成交付。

真实30题×4组120项全部完成、0技术错误；96整答、24拒答、166引用判断全部齐备。评分来源是21份具体人工确认＋99份按你授权的AI辅助，含45条人工/121条AI主张判断，不称全部纯人工核验。

完整正确数：F400 6/24、S400 9/24、F800 10/24、S800 13/24；引用支持27/36、33/35、42/45、50/50。共20次对可答题误拒答，这些失败未删去。方法、分母、局限见源码中的docs/C部分报告草稿.md及docs/M6评分方式与授权记录.md。

## 文件与校验

| 文件 | 字节数 | SHA-256 |
| --- | --- | --- |
| C-source-data-scored-20261120.zip | 2073716 | `105fa047ed16e17a38edd92c12ed4cc49ab025c3286834d136a673ffeb6b81d7` |
| C-scored-results-20261120.zip | 33513874 | `e9b6726bebad5b4422a728d1514b350e708fc67494f0a2261d3c565661dad2d9` |
| DE.tar | 1870832128 | `0a42af6e5a64e55383b20970b98fff8262e2d746bea26b0f189951aeb79d1c05` |
| BGE-M3-5617a9f6-weights.tar | 2293350400 | `bde9e27a9e758677f035097550944dab26b49fe99ba786dd4fd51b44dc08f958` |

FINAL-MANIFEST.json记录来源与验收范围，SHA256SUMS.txt可用`sha256sum --check SHA256SUMS.txt`核对。source-data是便于阅读的展开源码快照；ZIP用于复制到新的工作目录。源码快照Git提交`16a8e82b62cbe5a76e48bb5715fb7a15a2338a07`，最终打包后的工作日志另在项目仓库保存。

## 当前电脑无需恢复

当前DERag工作库已经保存全部评分，继续用原目录查看即可，不用这些旧/新备份覆盖它，不重跑120题。查看结果使用README顶部的空Key方式，浏览/evaluation；学校API在评分/备份/打包阶段新增0次。

## 新机器先解包、验包

1. 将源码ZIP解压到一个新的DERag目录。先用Python3.13运行`python -B -S scripts/verify_delivery.py .`；它只需标准库。
2. 再将结果ZIP解压到同一个新目录，得到artifacts和sqlite-backup；完整最新结果在artifacts/c/m6-final-scored，所有中间评分、原未评分数据和验收证据保留。
3. 权重TAR在新源码根解压，得到models/embedding。加入运行文件后目录不再是原始解包快照，不再用源码清单声称整目录未变。
4. `docker load --input DE.tar`加载镜像，tag是`de:latest`，镜像ID`sha256:c9fd36327ffa6d676a1fe45c4a6369cc91ad11d643168523448185b1ab1a89de`。镜像无需联网安装依赖，模型权重不在镜像里，作为独立包提供。

## 用Docker先看已有评分

以下在Linux/WSL shell执行，把/ABS/NEW/DERag换成新的解包目录。新卷名用于独立恢复；Python命令会在目标已有数据库时停止，不覆盖已有成绩：

```bash
docker volume create derag-reviewed-sqlite
docker run --rm --network none --mount type=bind,source=/ABS/NEW/DERag/sqlite-backup,target=/snapshot,readonly --mount type=volume,source=derag-reviewed-sqlite,target=/target de:latest python -c "from pathlib import Path; import sqlite3; p=Path('/target/derag.sqlite3'); assert not p.exists(); s=sqlite3.connect('file:/snapshot/derag.sqlite3?mode=ro&immutable=1',uri=True); d=sqlite3.connect(p); s.backup(d); d.close(); s.close()"
docker run --name DE -d -p 127.0.0.1:8766:8000 -e DERAG_CONFIG=config/experiment.formal-a.json -e DERAG_ENV_FILE=/dev/null -e LLM_API_KEY= --mount type=volume,source=derag-reviewed-sqlite,target=/app/data/formal_corpus/sqlite de:latest
```

打开http://127.0.0.1:8766/evaluation，选择`eval-20ac108503c44829a96ecca386d4b9de`。本方式只准备已有结果浏览，不含新问答所需的Key/索引挂载，health整体未ready不代表历史记录丢失。需要新生成时按docs/Docker与交付包复现.md配置私密env、只读模型与独立原生索引卷；原正式120项仍保留，不用重跑。

## 实测与范围

Windows401项及Linux400项通过/1平台跳过、正式索引与真实学校问答/重启在先前阶段验收。最新评分库在禁网/无Key的新Linux卷恢复，124条历史完整保留，启动及重启后的导出逐字节等同Windows，68个运行代码/配置文件与此镜像相同，21/99来源标签保留。原卷未改，自己的检查容器已移除。

源码新目录已通过标准库清单及正式A资料验证；两个ZIP已校验CRC和逐成员SHA，DE.tar配置和17层diff_id已核验，权重包与先前逐11文件验收的固定归档SHA相同。全部公开包扫描无实际Key。没有重新下载模型、建索引或调用学校API。

本机WSL实测不是另一台物理机验收；接收方仍需实际load/运行。评分是已披露的AI辅助混合来源，不是双人独立金标准。老师/组长最终课程提交与展示审阅由团队负责。本轮没有push、main写入或发送团队消息。
