# A 模块测试指南（组员使用）

记录日期：2026-11-19。本指南参照 [B测试.md](./B测试.md) 的组员操作方式，检查 A 的官方数据、字符位置、正式交付包和标准测试题集。实现原理与字段解释见 [A开发文档.md](./A开发文档.md)。

**建议顺序：确认交付文件 → 准备环境 → 只读校验 → 19 项自动测试 → 正常加载 → 核验证据 → 按需验证重复生成 → 反馈结果。**

主要命令适用于 Windows PowerShell 和 Python 3.13.11。本机验证使用已有项目环境；组员应在自己的环境执行并记录结果。A 的这些检查不需要 GPU、模型权重、Chroma 实例或 LLM API Key。

## 1. 这份指南可以测什么

| 检查 | 验证内容 |
| --- | --- |
| 来源与快照 | 登记的官方 HTML 存在，文件哈希匹配 |
| 清洗和结构 | 五份文档、121 条主条文，章、节、条文、附件等位置有效 |
| 原文追溯 | `text[start:end]` 与条文或证据摘录逐字相同 |
| 正式包 | 五文档范围、文件哈希、适配字段和统一语料版本 |
| 标准题集 | 30 唯一题号、24 可答 / 6 拒答、42 段证据及版本绑定 |
| 异常处理 | 缺文件、哈希失配、版本失配、重复 ID、正式文档缺项 / 多项等明确失败 |
| 可复现性 | 同一快照和规则重新运行后，产物哈希不变 |

通过以上检查说明数据及接口输入可核对。本版本的答案完整性、证据支持关系和拒答条件已由 A 负责人人工复核，未发现问题；真实检索效果及系统回答正确性由 B、C 的后续测试评估。

## 2. 确认项目目录和交付文件

在 PowerShell 中进入项目根目录。本机示例为：

```powershell
Set-Location 'D:\gitcode\Edit\DE'
Get-Location
Get-ChildItem -LiteralPath . -Name
```

其他电脑把第一行路径换成自己的项目目录。后面的相对路径都以此为基准，不要进入 `scripts` 或 `app` 后再运行。

根目录应至少包含：

```text
DE/
  app/retrieval/types.py
  scripts/process_documents.py
  scripts/validate_data.py
  scripts/export_corpus.py
  scripts/build_gold.py
  tests/test_corpus_batch.py
  tests/test_corpus_freeze.py
  tests/test_gold_eval.py
  data/sources.json
  data/raw/                          # 五份官方 HTML
  data/processed/                    # 五对 txt / JSON
  data/corpus_manifest.json
  data/formal_corpus/manifest.json
  data/formal_corpus/raw/             # 五份快照副本
  data/formal_corpus/processed/       # 五份适配 JSON
  data/sample_corpus/                 # 单文档联调包
  data/eval/gold.jsonl
  data/eval/manifest.json
  data/eval/sample.jsonl
  data/eval/sample_manifest.json
  artifacts/a_review/                # 复核报告
  A开发文档.md
  A测试.md
```

如果目录只含 B 的合成测试数据，先取得 A 的交付目录或包含 A 产物的团队版本。不要用其他来源的同名文件补齐，也不要把 `fixture-en-v2` 当作正式五文档版本。

如果这是 Git 工作区，可以只读记录当前代码状态，便于反馈：

```powershell
git status --short
git rev-parse --short HEAD
```

有未提交文件时，commit 号不能单独说明当前全部数据内容，反馈时还应记录语料与题集版本。本指南不要求执行提交、推送或覆盖自己的工作区。

## 3. 建立环境和安装 A 所需依赖

先检查 Python：

```powershell
py -3.13 --version
```

当前验证版本为 Python 3.13.11。没有 `.venv` 时创建；已有正确版本的环境可跳过创建命令：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe --version
```

A 的命令行数据处理和正常包导入直接使用以下依赖，版本来自仓库现有依赖声明：

```powershell
.\.venv\Scripts\python.exe -m pip install beautifulsoup4==4.15.0 soupsieve==4.1.2 filelock==4.2.10
.\.venv\Scripts\python.exe -m pip check
```

| 依赖 | 用途 | 已登记位置 |
| --- | --- | --- |
| `beautifulsoup4` | 解析已保存的 HTML | `requirements.txt` |
| `soupsieve` | Beautiful Soup 的选择器支持 | `requirements.txt` |
| `filelock` | 正常导入 `app.retrieval` 时所加载的索引服务依赖 | `requirements-b.txt` |

`pip check` 正常输出 `No broken requirements found.`。首次安装依赖需要访问软件包源；安装后，A 的清洗、校验、加载与题集生成使用本地文件。

这里运行 `unittest`，不要求额外安装 pytest。测试 B 的 Chroma 和真实 embedding 时，再按 `B测试.md` 安装 B 的完整运行与测试依赖；A 的这组检查不会下载模型权重。已经安装 B 环境的组员仍需确认 HTML 解析依赖存在。

所有命令显式使用项目解释器，无需激活虚拟环境。终端即使显示其他环境名称，也以命令里的 `.venv` 为准。

## 4. 先做只读校验

### 4.1 整套语料

```powershell
.\.venv\Scripts\python.exe scripts\validate_data.py --scope corpus
$LASTEXITCODE
```

当前版本的最终汇总应包含：

```text
documents=5
main_articles=121
result=ok
0
```

程序还会打印各文档的结构与区间检查数量。121 来自 35、27、27、21、11 条相加，不是硬凑题数。

### 4.2 正式题集

```powershell
.\.venv\Scripts\python.exe scripts\validate_data.py --scope eval
$LASTEXITCODE
```

预期汇总为：

```text
scope=eval
corpus_version=794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795
questions=30 answerable=24 refusal=6
result=ok
0
```

这两条命令不生成或改写语料和题集。`result=ok` 应与进程退出码 0 一起出现；失败时保留错误中的文件、文档或题号及区间。

只检查一份语料时可执行：

```powershell
.\.venv\Scripts\python.exe scripts\validate_data.py --scope corpus --document-id eu_unfair_terms_93_13
```

`--scope eval` 检查整套题集，不与 `--document-id` 同用。

## 5. 运行 A 的 19 项自动测试

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_corpus_batch tests.test_corpus_freeze tests.test_gold_eval
$LASTEXITCODE
```

当前预期结果为：

```text
Ran 19 tests in ...s

OK
0
```

| 模块 | 项数 | 主要异常与行为 |
| --- | ---: | --- |
| `tests.test_corpus_batch` | 8 | 参数互斥、空清单、重复 ID、缺快照、哈希失配、部分失败、缺产物 / 未登记文件、节镜像 |
| `tests.test_corpus_freeze` | 6 | 缺处理文件、正式快照被改、版本不符、重复导出、正式清单缺项及多项拒绝 |
| `tests.test_gold_eval` | 5 | 证据归属及失配、附件重复条号、拒答证据、重复题号、版本、哈希、CRLF 和参数 |

一项测试可能检查多个相关异常，因此不能把上表每个异常名称都计成单独测试项。后续新增测试后，以实际用例数为准，不要为了维持 19 项删测试。

这些用例使用内存对象或临时目录中的副本制造异常，正式文件保持不变。输出中的参数错误或 `result=failed` 可以来自故意触发的反例；整组仍必须以 `OK` 和退出码 0 结束。出现 `FAILED`、`ERROR` 或 traceback 时不能因为看到过某一行预期失败文本就忽略。

如需保留本机运行日志，可写到独立目录，避免覆盖已验收复核报告：

```powershell
New-Item -ItemType Directory -Path .\artifacts\a_local_tests -Force | Out-Null
.\.venv\Scripts\python.exe -m unittest tests.test_corpus_batch tests.test_corpus_freeze tests.test_gold_eval 2>&1 | Tee-Object -FilePath .\artifacts\a_local_tests\unittest.txt
$LASTEXITCODE
```

## 6. 正常导入并加载正式包与样本包

下面整段在 PowerShell 执行。它通过正常包导入加载器，核对正式五文档和独立样本，并检查条文内容与已验收产物一致：

```powershell
@'
import json
from pathlib import Path
from app.retrieval.types import formal_loader

root = Path.cwd()
packages = [
    ("formal_corpus", "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795", 5, 121),
    ("sample_corpus", "41404e6e3bd67f2313a8d2bcc4b151d5273f7bd5807a98f5018c0dd98e6c5a50", 1, 35),
]
for name, version, expected_docs, expected_articles in packages:
    docs = formal_loader(root / "data" / name)(version)
    assert len(docs) == expected_docs
    assert sum(len(doc["articles"]) for doc in docs) == expected_articles
    for doc in docs:
        document_id = doc["document_id"]
        accepted = json.loads((root / "data/processed" / f"{document_id}.json").read_text(encoding="utf-8"))
        assert doc["text"].encode("utf-8") == (root / "data/processed" / f"{document_id}.txt").read_bytes()
        for article, original in zip(doc["articles"], accepted["articles"], strict=True):
            for key in ("article_id", "text", "start", "end"):
                assert article[key] == original[key]
            assert article["label"] == f"Article {original['number']}"
            assert article["chapter"] == original["chapter_id"]
            assert article["section"] == original["section_id"]
            assert doc["text"][article["start"]:article["end"]] == article["text"]
    print(f"PASS {name}: documents={len(docs)}, articles={expected_articles}")
'@ | .\.venv\Scripts\python.exe -
$LASTEXITCODE
```

预期输出两行 PASS：正式包 5 份 / 121 条，样本包 1 份 / 35 条，最后退出码为 0。

正式包的加载目录是 `data/formal_corpus`，不能传入 `data/processed`，也不能把项目级 `corpus_manifest.json` 改名来冒充 B 的 manifest。

## 7. 核对标准题、证据和题集版本

下面脚本只读取正式包与题集，验证所有证据切片并重新计算分布：

```powershell
@'
import hashlib
import json
from collections import Counter
from pathlib import Path
from app.retrieval.types import formal_loader

root = Path.cwd()
manifest = json.loads((root / "data/eval/manifest.json").read_text(encoding="utf-8"))
raw = (root / "data/eval/gold.jsonl").read_bytes()
expected_version = "9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d"
assert hashlib.sha256(raw).hexdigest() == manifest["gold_version"] == manifest["gold_sha256"] == expected_version
assert manifest["corpus_version"] == "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
cases = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
assert len(cases) == len({case["case_id"] for case in cases}) == 30
assert sum(case["should_refuse"] is False for case in cases) == 24
assert sum(case["should_refuse"] is True for case in cases) == 6
docs = {doc["document_id"]: doc for doc in formal_loader(root / "data/formal_corpus")(manifest["corpus_version"])}
lengths = []
for case in cases:
    assert case["corpus_version"] == manifest["corpus_version"]
    if case["should_refuse"]:
        assert case["evidence"] == [] and case["key_facts"] == []
        assert case["refusal_reason"].strip()
    for item in case["evidence"]:
        text = docs[item["document_id"]]["text"]
        assert text[item["start"]:item["end"]] == item["quote"]
        assert 0 < len(item["quote"]) < 400
        lengths.append(len(item["quote"]))
types = dict(Counter(case["question_type"] for case in cases))
assert types == manifest["question_types"] == {"single_article": 13, "multi_evidence": 11, "unanswerable": 6}
assert len(lengths) == 42 and min(lengths) == 68 and max(lengths) == 393
print("PASS gold: questions=30, answerable=24, refusal=6, evidence=42, lengths=68..393")
'@ | .\.venv\Scripts\python.exe -
$LASTEXITCODE
```

完整的证据所属结构校验仍由第 4 节的 `--scope eval` 执行。上面的独立脚本用于直观看到题数、哈希和切片关系，不替代该校验器。

也可用 PowerShell 快速查看题集文件哈希：

```powershell
Get-FileHash -LiteralPath .\data\eval\gold.jsonl -Algorithm SHA256
```

PowerShell 显示的大写十六进制与 manifest 的小写值表示同一个 SHA-256。

## 8. 对照原文复核哪些内容

原文复核按“问题 → 参考答案 → 关键事实 → 证据 → 同条其他款及相关结构”检查，不能只看到 quote 在正文中出现就结束。

| 样本 | 重点检查 |
| --- | --- |
| 每份法规第一条、中间条、最后一条 | 标题、段落、否定和例外是否完整，区间是否对应 |
| 第四份第 5–9 条 | 第 5 条直接属于第二章，第 6/7 条与第 8/9 条分属两节 |
| 第五份第 11 条 | 条文在落款前结束，落款、脚注和附件没有被并入主条文 |
| `gold-crd-withdrawal-refund` | 三段证据分别涵盖第 13(1)、(2)、(3)款；不要漏掉额外配送费用、暂缓退款及经营者自行取货条件 |
| `gold-sgd-two-year-liability` | 两年一般期间、更长期间及二手商品可约定较短但至少一年的条件 |
| `gold-ucpd-pyramid-scheme` | 证据分别来自第 5 条与 `eu_unfair_practices_2005_29:annex:I` |
| 六道拒答题 | 五份全文、序言和附件中是否存在足以作答的规则，不凭单一关键词判断 |

现有五份文档及 30 道题已完成 AI 辅助原文复核和人工复核。A 负责人已确认复核完毕，未发现问题；本次据此更新人工复核状态。后续版本修订或组员复测时，请记录实际检查人、日期、文档或题号、发现的问题和依据。

浏览器视觉检查已由 A 负责人于 2026-11-19 确认通过，未发现问题。各份 AI 报告里的 DOM 对照仍单独保留。附件中的方框样式清洗为普通数字属于已有格式限制，需结合对应填写说明理解。

## 9. 按需验证重复生成

这一节会重新写清洗文件、正式包和题集。日常验收先完成只读校验；需要核对管线可复现性时，再执行以下顺序：

```powershell
.\.venv\Scripts\python.exe scripts\process_documents.py --all
.\.venv\Scripts\python.exe scripts\export_corpus.py
.\.venv\Scripts\python.exe scripts\build_gold.py
.\.venv\Scripts\python.exe scripts\validate_data.py --scope corpus
.\.venv\Scripts\python.exe scripts\validate_data.py --scope eval
```

每条命令都应退出 0。清洗应成功 5、失败 0；正式导出仍是 5 份、121 条和原语料版本；题集仍是原 `gold_version`。命令无须访问实时 EUR-Lex，使用已保存快照。

要一次性核对最终报告中的 44 个受保护文件，可以使用以下脚本。它先验证报告基线，再依次执行重建命令；任何一步失败或任一文件哈希变化都停止。

```powershell
@'
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path.cwd()
report = (root / "artifacts/a_review/a_final_validation.md").read_text(encoding="utf-8")
expected = {
    path.strip(): value
    for path, value in re.findall(r"^\| ((?:data|artifacts)/[^|]+) \| `([a-f0-9]{64})` \|$", report, re.M)
}
sources = json.loads((root / "data/sources.json").read_text(encoding="utf-8"))["sources"]
for source in sources:
    name = Path(source["snapshot"]["path"]).name
    expected[f"data/formal_corpus/raw/{name}"] = source["snapshot"]["sha256"]
assert len(expected) == 44

def check_hashes():
    for relative, value in expected.items():
        path = root / relative
        assert path.is_file(), f"Missing: {relative}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == value, f"Changed: {relative}"

check_hashes()
commands = [
    ["scripts/process_documents.py", "--all"],
    ["scripts/export_corpus.py"],
    ["scripts/build_gold.py"],
    ["scripts/validate_data.py", "--scope", "corpus"],
    ["scripts/validate_data.py", "--scope", "eval"],
]
for args in commands:
    subprocess.run([sys.executable, *args], check=True)
    check_hashes()
print("PASS: 44 protected files match the recorded baseline after regeneration")
'@ | .\.venv\Scripts\python.exe -
$LASTEXITCODE
```

这是当前版本基线的复现脚本。以后正式发布新数据版本时，应同步新的复核记录；不要仅修改报告哈希来让变动通过。

`scripts/export_sample.py` 会重新写单文档样本和样题 manifest，不属于上述正式重建流程，日常验收无需运行。

## 10. 文件和版本怎样交给 B、C

### 10.1 B 接收什么

- 完整的 `data/formal_corpus/`，包含包内 manifest、五份 HTML 副本和五份适配 JSON。
- 统一 `corpus_version=794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795`。
- `data/corpus_manifest.json` 及来源、结构、复核记录，供追溯核对。

B 的 `data_dir` 指向正式包目录。四组分块、embedding、索引和检索的验收按 B 的测试指南进行，不能把本指南的 19 项结果作为检索质量结果。

### 10.2 C 接收什么

- `data/eval/gold.jsonl` 与 `data/eval/manifest.json`。
- 对应的正式语料包和两个固定版本。
- 题集与最终复核记录，并说明人工复核已完成、未发现问题的结论。

C 同时固定 `corpus_version` 与 `gold_version`。系统作答时输入问题，自行检索来源；标准答案和证据只作评分对照。四个条件正式运行会产生 120 条逐题记录，尚需实际执行，不能从本指南得出答案正确率。

## 11. 常见问题

| 现象 | 处理 |
| --- | --- |
| `No module named bs4` / `soupsieve` | 用同一 `.venv` 解释器安装第 3 节的 HTML 解析依赖 |
| 正常导入时报 `No module named filelock` | 安装已在 `requirements-b.txt` 登记的 filelock，不绕过包初始化 |
| 找不到 `app`、`scripts` 或数据文件 | 回到包含这些目录的项目根目录，核对交付文件是否齐全 |
| `Missing A corpus manifest` | 核对传给加载器的是正式包目录，包内确有 `manifest.json` |
| `VERSION_MISMATCH` / `SOURCE_MISMATCH` | 核对当前包、请求版本及文件字节；不要手改 manifest 让错误消失 |
| `official export requires exactly...` | 来源清单缺少或多出官方 ID；按错误中的 missing / extra 定位 |
| txt / JSON 哈希突然变化 | 检查编辑器或 Git 是否改变换行、编码、BOM、末尾换行或 JSON 格式 |
| 证据切片不一致 | 检查是否使用同一冻结全文，是否把字节 / token 当成字符，是否错误匹配到重复内容 |
| 测试出现 `PermissionError` / `WinError 5` | 查看 traceback 是否在临时目录创建、写入或清理时失败；在有权限的普通本地终端重试，不将其写成通过 |
| 看到 `result=failed` | 判断它来自某个异常测试还是实际校验；以对应进程退出码及整组测试的最终结果为准 |
| 组员 clone 后缺少 A 文件 | 核对是否取得包含 A 产物的版本；只有 B 源码或合成数据不能完成本指南 |

冻结文件应保持 UTF-8 和既定换行。仓库已有保护数据字节的 `.gitattributes` 规则，不要为消除哈希错误而批量转换文件。

## 12. 测试完成后怎样反馈

请把以下内容发给 A；问题涉及分块、模型或系统回答时，同时记录对应的 B / C 运行信息：

```text
操作系统：
项目路径：
Python 版本：
代码 commit（如有）及未提交修改情况：
corpus_version：
gold_version：
corpus 校验：退出码 / 最终输出
eval 校验：退出码 / 最终输出
自动测试：实际项数 / OK 或 FAILED / 退出码
正式包加载：文档数 / 主条文数
样本包加载：文档数 / 主条文数
重复生成：是否运行 / 是否字节一致
原文复核：检查人 / 日期 / 文档和题号 / 发现
错误定位：文件 / document_id / article_id 或 case_id / [start, end)
完整错误文本或日志位置：
```

当前本机已验证：五份文档、121 条主条文；30 题、24 可答和 6 拒答；19 项自动测试通过；正式与样本包正常加载；44 个受保护文件在重建后哈希不变。程序检查记录见 [A 最终校验](./artifacts/a_review/a_final_validation.md)。A 负责人于 2026-11-19 确认人工复核和浏览器视觉检查通过，未发现问题；B 的正式建库检索及 C 的问答评估分别记录各自结果。
