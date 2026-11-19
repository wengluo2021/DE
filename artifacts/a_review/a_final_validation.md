# A 部分最终校验

记录日期：2026-11-19。解释器是 `D:\gitcode\Edit\DE\.venv\Scripts\python.exe`，版本 Python 3.13.11。

本轮没有改写正文、结构、题目、答案或证据，没有重新编题，也没有用新结果覆盖冻结版本。没有建立向量索引，没有下载 embedding 模型，没有运行语义检索、LLM 回答或四组评分，没有执行 Git 写入或推送。

## 第 6 步程序校验时的运行前基线

写入任何生成产物之前，记录了 44 个受保护文件的 SHA-256，并另存字节副本。44 个文件都存在，`missing=0`。复跑清洗、正式导出和题集生成之后再次逐字节对照，`compared=44 changed=0`。因此下面的哈希同时是当时运行前和运行后的值。后续人工复核状态更新涉及的 Markdown 哈希变化单列于文末，来源、语料与题集文件均未改变。

| 文件 | SHA-256 |
| --- | --- |
| data/sources.json | `6a7a20ff4c9ea87bb940a066e8fdf08b285458fc9208b6b231dcf8e99fa5bad9` |
| data/raw/eu_consumer_rights_2011_83.html | `7812747113a74ef3a2b2e8d2d3fb067ed416280f415aed76dc255083b54e892e` |
| data/raw/Sale of Goods.html | `4869ed74958ae7cc50897e502272cc103502bffd1722f4ed07ca1f7188bb16ac` |
| data/raw/Digital Content and Services.html | `83b8ec2ad8d5a293c278fcffc5add389425bd7c688f92bf110d4ce2b929826f2` |
| data/raw/Unfair Terms.html | `6c700ae54d53f3dc3ece8d226d18471ac905eff42a7cb4d4874e2e56acaff707` |
| data/raw/Unfair Commercial Practices.html | `0d678d1bbd988c59b40ff6363f3d9b8370c34da7b3744395eb7147364a19c1cc` |
| data/processed/eu_consumer_rights_2011_83.txt | `75acf22af53bf1878fe2750757b5ecd5c1230236aaab4fc543c1d029b3bf5689` |
| data/processed/eu_consumer_rights_2011_83.json | `f7ed11c4e7817cc58c23498ef1b87b87e885996f8a075a02365782e44b84829a` |
| data/processed/eu_digital_content_2019_770.txt | `6e251e53b94cb4e793d9cd32889a0f70b7e62d7399eacc15197f37bb132ac3bf` |
| data/processed/eu_digital_content_2019_770.json | `3d7b88ac3b35365986c18970dfc24cdf6b1574f701c13c350efe7466e5e366ab` |
| data/processed/eu_sale_of_goods_2019_771.txt | `d3076ba5236d6e7aad6ba30ae8b8d4b17af14fa148f7abc42cadd96764498ad4` |
| data/processed/eu_sale_of_goods_2019_771.json | `ec42ea4dbad2a165bfd409f50c21fc10620ef4ca9b17d8028e5c1885570b4d6c` |
| data/processed/eu_unfair_practices_2005_29.txt | `7bc191bd5b55af42a179d95d98b1e7c2aa603509941065605b4ba175eb54f10b` |
| data/processed/eu_unfair_practices_2005_29.json | `1f21061ca7b3f46f8cd2a949c722b86dbcdac0864c95281291cf037fad40c200` |
| data/processed/eu_unfair_terms_93_13.txt | `bf518901d6a71d5753ec99ed0b5b13025f5bf136782594a0dbaf8263e376a401` |
| data/processed/eu_unfair_terms_93_13.json | `c4d387298a543eb545a91cec522662b77473a6c79c7ee27c450818f17df29893` |
| data/corpus_manifest.json | `3ecdec520cc259b876e65fc2fea492b956deaef941c9a46ba4c08b368b87bd4f` |
| data/formal_corpus/manifest.json | `516d0aa17c2674ee57eadfbb73452140e88667a0e3c9c51d7028dd127f1fdb57` |
| data/formal_corpus/raw 五份 HTML | 与上表 `data/raw` 中同名文件哈希相同 |
| data/formal_corpus/processed/eu_consumer_rights_2011_83.json | `d1db1b2e0e85b5a9a62b40fc23a0974cd85d597167ccb9a0b654aea22b631e24` |
| data/formal_corpus/processed/eu_digital_content_2019_770.json | `4af53f1647e1eeed535c65d0abcf7802cd50f313e0fef0b98227ccb7cfbf9f79` |
| data/formal_corpus/processed/eu_sale_of_goods_2019_771.json | `3fcd40957992fa8693ecc91cdcad1ce7c23225a92a8809fc1dac20078febea77` |
| data/formal_corpus/processed/eu_unfair_practices_2005_29.json | `1af8f015d0fc8a62cfa40f87074fe3432d54d822b9e3c90f053151638c1fb4c3` |
| data/formal_corpus/processed/eu_unfair_terms_93_13.json | `0eb604ed2dad177ba4d9758607bac8fa691af95c8fac61015f8d925a17011827` |
| data/eval/gold.jsonl | `9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d` |
| data/eval/manifest.json | `175c8a94d4c638dadc4b3f22f154d539c96649d8553173f1f046ee0c1308a1d3` |
| data/eval/sample.jsonl | `63f14226611fc7fbda5d2996c37ebe5f97f9ee237e7cbdc476fb14f7dfbc1126` |
| data/eval/sample_manifest.json | `f86266512cef7f7385c9e122de488f0a0f6e79d7f5b5a40968043d06c51896c7` |
| data/sample_corpus/manifest.json | `5fa36813a51dde8839b4faafb56f57ba82f9e39f1e669e5463f9842414dbabb1` |
| data/sample_corpus/raw/eu_consumer_rights_2011_83.html | `7812747113a74ef3a2b2e8d2d3fb067ed416280f415aed76dc255083b54e892e` |
| data/sample_corpus/processed/eu_consumer_rights_2011_83.json | `1c5c2ae09d58423bc63d084390b25030051495b7b4fb3aeb056e6335f506290f` |
| artifacts/a_review/eu_consumer_rights_2011_83_review.md | `0af5fe7c011fb7ddffe21f910cd702c362c4497a890f7a759c70b3604544391f` |
| artifacts/a_review/eu_sale_of_goods_2019_771_review.md | `a58c9974e3c205a3aa823a534f2b7e337299d045331b53c4632acd12a1e5c8f0` |
| artifacts/a_review/eu_digital_content_2019_770_review.md | `c89ce047f2e62c5ca9dcef46380536c049b4dad9c647d7f510afa9812e8f23c4` |
| artifacts/a_review/eu_unfair_practices_2005_29_review.md | `f2fa06baa56e403c804188db38cc27cc9bea5bb6beb42d33492b2fa76f10f18e` |
| artifacts/a_review/eu_unfair_terms_93_13_review.md | `b2e320339da6c28a4b3b2ca06ae4458a11a230f5e2c8e0d447a61dde29064e59` |
| artifacts/a_review/corpus_batch_review.md | `ef76a2ca40e444beeec0c1bc7c3a42ed3763408d0d24cafddf0f458d20c6b571` |
| artifacts/a_review/corpus_freeze_review.md | `24b1adf12a48423a6ff04e83544fb2856d12ad7ef60399b3ea599e98b71b16af` |
| artifacts/a_review/gold_review.md | `f25b102165730cce9c3496d4df8634b86bde0812e10e3e13ae5ffc302737ac0f` |
| artifacts/a_review/sample_handoff.md | `b4adf827e6226e4ca480bfac3457b00ac9e3d95652e197467015b52532994684` |

正式包 raw 的五个哈希已逐项计入 44 个文件，并与 `data/raw` 同名快照相同。上表把它们合并成一行，避免把同一哈希写两遍。

## 命令和退出码

工作目录均为 `D:\gitcode\Edit\DE`。

| 命令 | 作用 | 退出码 | 结果 |
| --- | --- | ---: | --- |
| `scripts\validate_data.py --scope corpus` | 只校验 | 0 | `documents=5`，`main_articles=121`，`result=ok` |
| `scripts\validate_data.py --scope eval` | 只校验 | 0 | `questions=30 answerable=24 refusal=6`，`result=ok` |
| `python -m unittest tests.test_corpus_batch tests.test_corpus_freeze tests.test_gold_eval` | 只测试临时副本和内存对象 | 0 | `Ran 19 tests`，`OK` |
| `scripts\process_documents.py --all` | 重新生成已验收 txt 和 JSON | 0 | `batch_documents=5`，`succeeded=5`，`failed=0`，`result=ok` |
| `scripts\export_corpus.py` | 重新生成正式包和两份清单 | 0 | `corpus_version=794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795`，`documents=5`，`main_articles=121`，`result=ok` |
| `scripts\build_gold.py` | 重新生成题集和题集 manifest | 0 | `gold_version=9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d`，`result=ok` |

单元测试输出里出现过 `result=failed` 和参数错误文本。那是异常用例预期捕获的失败信息，测试断言这些失败发生，整组结果是 `OK`。三项分布是 `tests.test_corpus_batch` 8 项、`tests.test_corpus_freeze` 6 项、`tests.test_gold_eval` 5 项。

全语料校验打印的结构计数：

| 文档 | offset_checks |
| --- | --- |
| eu_consumer_rights_2011_83 | annex=2 article=35 block=418 chapter=6 footnote=23 preamble=1 recital=67 signature=1 table=2 table_row=80 title=1 |
| eu_digital_content_2019_770 | article=27 block=261 footnote=23 preamble=1 recital=87 signature=1 title=1 |
| eu_sale_of_goods_2019_771 | annex=1 article=27 block=273 footnote=10 preamble=1 recital=72 signature=1 table=1 table_row=48 title=1 |
| eu_unfair_practices_2005_29 | annex=2 article=21 block=277 chapter=4 footnote=26 preamble=1 recital=25 section=2 signature=1 title=1 |
| eu_unfair_terms_93_13 | annex=1 article=11 block=91 footnote=4 preamble=1 recital=24 signature=1 title=1 |

主条文 35 + 27 + 27 + 21 + 11 = 121。

## 正常加载

通过 `import app.retrieval.types` 使用 `formal_loader`，没有绕过包初始化。

- `formal_loader(data/formal_corpus)(794e3d19...)` 与 `data/corpus_manifest.json` 的版本一致。五份加载全文等于已验收 txt。每条 `article_id`、`start`、`end`、`label`、`chapter`、`section` 与已验收 JSON 一致，`text[start:end]` 等于条文文本。问题数 0。
- `formal_loader(data/sample_corpus)(41404e6e...)` 仍能加载唯一样本文档，并与已验收的第一份 txt 和结构一致。问题数 0。
- 正式包 `data_dir` 记录为 `data/formal_corpus`。

## 题集复查

30 个 `case_id` 唯一。题型为 `single_article` 13、`multi_evidence` 11、`unanswerable` 6。五份文档都有可答题。42 段 quote 长度为 68–393，且由校验器确认 `text[start:end] == quote`。

`gold-crd-withdrawal-refund` 仍有 3 段证据。第 2 段以 “2. Notwithstanding paragraph 1” 开头，第 3 段以 “3. Unless the trader has offered to collect” 开头。参考答案保留附加配送费用可以不退，以及买卖合同中可以暂扣退款。

`gold-sgd-two-year-liability` 仍有 3 段证据。第 3 段以 “6. Member States may provide that, in the case of second-hand goods” 开头。参考答案保留二手商品可以约定更短期间，但不得短于一年。

`gold-ucpd-pyramid-scheme` 的两段归属分别是第 5 条和 `eu_unfair_practices_2005_29:annex:I`。附件中的重复条号没有被记到主条文。六道拒答题的空证据和拒答理由由 `--scope eval` 检查。

`gold.jsonl` 的文件哈希等于 manifest 里的 `gold_version` 和 `gold_sha256`，绑定的 `corpus_version` 与正式包一致。

## 正式导出缺文档问题

修复前，`scripts/export_corpus.py` 的命令行直接调用通用导出。来源清单只有四份官方文档时，仍会写出交付包并打印 `documents=4`、`result=ok`。

本轮在正式命令写入交付包之前增加集合核对。五份官方 ID 必须正好是：

`eu_consumer_rights_2011_83`、`eu_digital_content_2019_770`、`eu_sale_of_goods_2019_771`、`eu_unfair_practices_2005_29`、`eu_unfair_terms_93_13`。

少一份时错误含 `missing:`，多一份时含 `extra:`，退出码为 1，且临时目录中不会出现 `data/formal_corpus` 或 `data/corpus_manifest.json`。通用 `export_corpus` 继续供现有小语料测试使用，原有 4 项冻结测试仍然通过。新增 2 项测试只作用在临时目录。当前完整清单重新导出后，正式包哈希没有变化。

## 复核状态

| 范围 | 程序检查 | AI 辅助原文复核 | 人工复核（A 负责人确认） | 浏览器视觉检查 |
| --- | --- | --- | --- | --- |
| 五份来源、快照、清洗和区间 | 本轮 `--scope corpus` 通过 | 五份文档各有一份复核报告，对照 HTML DOM 和正文切片 | 2026-11-19 由 A 负责人确认通过，未发现问题 | 同次确认已在浏览器查看五份本地 HTML，通过 |
| 正式包和版本 | `formal_loader`、重复导出和冻结测试通过 | `corpus_freeze_review.md` 记录哈希和加载核对，不是逐条阅读正文 | 2026-11-19 由 A 负责人确认通过，未发现问题 | 同次确认覆盖五份快照页面 |
| 30 道标准题 | `--scope eval` 和题集测试通过 | `gold_review.md` 对照冻结片段起草答案和拒答理由 | 2026-11-19 由 A 负责人确认通过，未发现问题 | 同次确认对照页面复查标准题 |

程序切片匹配只说明 quote 与冻结正文一致。它不是答案正确率，也不能写成 100% 正确。答案、拒答理由和五份本地 HTML 的浏览器视觉检查，已由 A 负责人于 2026-11-19 确认通过，未发现问题。该状态依据负责人确认更新，不改变既有程序检查和 AI 复核的执行记录。

## 人工复核状态更新与当前报告哈希

A 负责人于 2026-11-19 确认五份文档、30 道标准题和五份本地 HTML 的浏览器视觉检查通过，未发现问题。本次只同步 Markdown 中的复核状态，未修改冻结数据、题目、答案、证据或两个内容版本。

第 6 步历史基线表保留程序校验时的原值。其中 `gold_review.md` 因本次人工复核状态更新而改变文件字节，当前对照值如下；同一路径以本节的最新值为准。此更新仅适用于文档状态，不替代来源或语料内容变更时应做的版本更新。

| 文件 | SHA-256 |
| --- | --- |
| artifacts/a_review/gold_review.md | `d30d13fba966fcb3f6e429f251e0955e718bb947d634dfce701a5b36904ecab1` |

`A测试.md` 的 44 文件复现脚本读取本报告的表格，同一路径使用最后登记的值，因此可以继续核对当前交付文件；其余原有受保护文件哈希保持不变。
