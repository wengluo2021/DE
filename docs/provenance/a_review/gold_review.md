# 正式 30 道题复核

记录日期：2026-11-19。题目、参考答案和拒答理由由 AI 对照冻结正文起草。证据 quote 全部由程序从 `formal_loader` 读到的全文按结构区间截取，没有手工抄写。人工复核和浏览器视觉检查已由 A 负责人于 2026-11-19 确认通过，未发现问题。既有 AI 起草和程序截取过程保留。本文件最初的 AI 复核没有打开浏览器，也没有读取四组正式检索结果；浏览器结论以后续人工确认为准。

## 版本

| 项目 | 值 |
| --- | --- |
| corpus_version | `794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795` |
| gold_version | `9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d` |
| gold.jsonl SHA-256 | 与 gold_version 相同 |
| 题数 | 30，其中可答 24、拒答 6 |
| 题型 | single_article 13，multi_evidence 11，unanswerable 6 |

`gold_version` 沿用开发文档中的约定：它是 `data/eval/gold.jsonl` 最终文件字节的 SHA-256。文件使用 UTF-8 和 LF，并保留末尾换行。jsonl 内不含题集版本或时间。连续再生成一次，哈希不变。

加载确认：五份唯一文档、121 条主条文，正式包清单与 `data/corpus_manifest.json` 的版本一致。版本不符时脚本报错，不重建语料。

## 覆盖

| 文档 | 可答题 | 证据段 |
| --- | ---: | ---: |
| eu_consumer_rights_2011_83 | 6 | 11 |
| eu_sale_of_goods_2019_771 | 5 | 9 |
| eu_digital_content_2019_770 | 5 | 10 |
| eu_unfair_practices_2005_29 | 4 | 7 |
| eu_unfair_terms_93_13 | 4 | 5 |

每道可答题的 `key_facts` 逐项等于对应 `evidence.quote`。因此关键事实与证据是同一段冻结原文。参考答案只陈述这些片段中的条件和例外，不把原始公布版写成现行修订法，也不用外部资料补全。

## 可答题

| case_id | 题型 | 主题 | 证据位置 | 复核结论 |
| --- | --- | --- | --- | --- |
| gold-crd-delivery-time | single_article | 未约定时的交付期限 | 2011/83 第 18 条第 1 款 `[81983,82251)` | 支持“无不当迟延且不晚于合同订立后 30 日” |
| gold-crd-withdrawal-refund | multi_evidence | 撤回后退款及同条例外 | 2011/83 第 13 条第 1 至第 3 款 `[73780,74083)`、`[74390,74631)`、`[74632,74908)` | 第 1 款支持 14 日内退还已付款和可适用的交付费用；第 2 款排除消费者另选更贵配送时的附加费用；第 3 款允许在买卖合同中暂扣退款直到收回货物或收到寄回证明 |
| gold-crd-payment-fee-cap | single_article | 支付方式费用 | 2011/83 第 19 条 `[83631,83816)` | 支持费用不得超过交易者承担的成本 |
| gold-crd-withdrawal-information-omission | single_article | 未告知撤回权 | 2011/83 第 10 条第 1 款 `[71568,71843)` | 支持撤回期在初始期间结束后 12 个月届满 |
| gold-crd-withdrawal-digital-content | multi_evidence | 数字内容撤回例外 | 2011/83 第 9 条第 1 款 `[69452,69734)`；第 16 条 (m) `[81214,81431)` | 两段合起来才能说明 14 日权利受第 16 条例外限制 |
| gold-crd-late-delivery-termination | multi_evidence | 迟延交付后的解除和退款 | 2011/83 第 18 条 `[82252,82543)`、`[82544,82681)`、`[83301,83420)` | 三段分别支持额外期限、仍不交付则可解除、解除后立即退还全部已付款 |
| gold-sgd-two-year-liability | multi_evidence | 货物不符的责任期 | 2019/771 第 10 条第 1、3、6 款 `[69752,70036)`、`[70749,70856)`、`[71762,72066)` | 支持两年责任和成员国可以规定更长期间；二手商品可由双方约定更短期间，但不得短于一年 |
| gold-sgd-one-year-presumption | single_article | 不符存在时间的推定 | 2019/771 第 11 条第 1 款 `[72095,72484)` | 支持一年推定及其两项例外 |
| gold-sgd-repair-or-replacement | multi_evidence | 修理或更换 | 2019/771 第 13 条第 2 款 `[73709,74013)`；第 14 条第 1 款 `[76165,76529)` | 支持消费者选择，以及免费、合理期限和无明显不便 |
| gold-sgd-minor-lack-no-termination | single_article | 轻微不符不得解除 | 2019/771 第 13 条第 5 款 `[75446,75649)` | 支持不得解除，并由出卖人证明轻微 |
| gold-sgd-price-reduction | single_article | 减价幅度 | 2019/771 第 15 条 `[77337,77531)` | 支持按价值减少比例减价 |
| gold-dcd-supply-without-delay | single_article | 数字内容交付时间 | 2019/770 第 5 条第 1 款 `[87988,88233)` | 支持未另有约定时在缔约后无不当迟延提供 |
| gold-dcd-burden-of-supply | single_article | 是否已提供的举证责任 | 2019/770 第 12 条第 1 款 `[96415,96565)` | 支持举证责任在交易者 |
| gold-dcd-conformity-remedies | multi_evidence | 数字内容救济和轻微缺陷 | 2019/770 第 14 条第 1、6 款 `[99561,99830)`、`[102316,102616)` | 支持三种救济，以及付费合同仅在非轻微不符时才能解除 |
| gold-dcd-reimbursement-time | single_article | 数字内容退款期限 | 2019/770 第 18 条第 1 款 `[106220,106613)` | 支持无不当迟延且不晚于被告知后 14 日 |
| gold-dcd-modification-conditions | multi_evidence | 持续提供时的修改条件 | 2019/770 第 19 条第 1 款 (a) 至 (d) `[107059,108042)` 分成五段 | 五段合起来覆盖允许修改的全部四项条件 |
| gold-ucpd-two-part-unfairness-test | single_article | 不公平商业行为的一般检验 | 2005/29 第 5 条第 2 款 (a)、(b) 及中间的 and `[26303,26665)` | 同一段包含两个要件和连接词 and |
| gold-ucpd-aggressive-practice | multi_evidence | 侵略性商业行为 | 2005/29 第 8 条 `[33078,33295)`、`[33296,33558)` | 原句长于 399 字符，按句内两段保留手段和结果两个条件 |
| gold-ucpd-invitation-price-information | multi_evidence | 购买邀请中的价格信息 | 2005/29 第 7 条第 4 款引导语 `[31679,31822)` 和 (c) `[32119,32501)` | 两段合起来说明价格信息在购买邀请中属于重要信息 |
| gold-ucpd-pyramid-scheme | multi_evidence | 金字塔促销 | 2005/29 第 5 条第 5 款 `[27416,27640)`；附件 I 第 14 点 `[51682,51969)` | 附件描述行为，第 5 条第 5 款说明附件行为在任何情况下都不公平 |
| gold-utd-unfair-term-test | multi_evidence | 不公平条款的定义 | 93/13 第 3 条第 1、2 款 `[9854,10128)`、`[10129,10383)` | 分别支持显著不平衡和未经个别协商的认定 |
| gold-utd-plain-language | single_article | 明白语言和有利解释 | 93/13 第 5 条 `[11684,12064)` | 支持明白语言、对消费者有利的解释，以及该解释规则不适用于第 7 条第 2 款程序 |
| gold-utd-unfair-term-not-binding | single_article | 不公平条款不约束消费者 | 93/13 第 6 条第 1 款 `[12076,12418)` | 支持按国内法不约束消费者，合同在能够存续时继续有效 |
| gold-utd-negotiation-burden | single_article | 个别协商的举证责任 | 93/13 第 3 条 `[10666,10819)` | 支持主张标准条款已经个别协商的出卖人或供应商承担举证责任 |

## 拒答题

六道题的 `evidence` 和 `key_facts` 都是空数组。判断范围是五份全文，包括序言、附件和脚注。关键词搜索只用来定位，随后阅读了相关条文。

| case_id | 缺少的信息 | 为什么其他条文也不能回答 |
| --- | --- | --- |
| gold-refuse-air-cancellation-amount | 航空承运人取消航班的固定欧元赔偿额 | 全文没有 air carrier，也没有航班取消赔偿金额。2011/83 第 3 条把客运排除出适用范围，只保留第 8 条第 2 款、第 19 条和第 22 条，这三条不规定取消航班的金额。序言提到混合合同服务部分的赔偿制度，但没有金额。 |
| gold-refuse-standard-vat-rate | 必须加收的增值税百分比 | 全文没有增值税税率。购买邀请要求显示含税价格，并不给出税率。 |
| gold-refuse-refund-interest-rate | 2011/83 第 13 条退款应加的法定年利率 | 第 13 条规定退款范围、14 日和不得收费，没有利率。2019/770 第 18 条同样只规定 14 日和无费用。93/13 附件讨论金融服务合同中的利率条款，不规定第 13 条退款的法定利率。 |
| gold-refuse-german-fine | 德国对使用一条不公平条款必须处以的最高欧元罚款 | 各指令只要求成员国规定有效、适度、劝阻性的罚则或执行手段，没有点名德国，也没有欧元上限。 |
| gold-refuse-lawsuit-deadline | 出卖人拒绝修理后必须起诉的天数 | 2019/771 第 10 条规定责任期间，并允许成员国设定仍能行使救济的时效，但没有规定起诉期限、法院或天数。 |
| gold-refuse-package-insurance | 一揽子旅游组织者必须持有的最低保险 | 2011/83 把一揽子旅游合同排除出适用范围。2005/29 附件 II 只把它列为部门信息规则，没有保险金额。其余三份指令也不规定这项保险。 |

## 命令和保护文件

```powershell
Set-Location 'D:\gitcode\Edit\DE'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\build_gold.py'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope eval
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope corpus
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' -m unittest tests.test_gold_eval
```

复核意见指出退款答案遗漏第 13 条第 2、3 款，两年责任期题没有限定第 10 条第 6 款的二手商品例外。这两题已补上同条原文。修正后连续两次生成的 `gold_version` 都是 `9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d`，`result=ok`。正式语料 `corpus_version` 没有变化。此前的题集版本 `444afb6d7fb842b1d7333a8cd9388b9d33601ca385c87638136c3d26526a1253` 是修正前的历史值。`--scope eval` 为 `questions=30 answerable=24 refusal=6`，`result=ok`。`--scope corpus` 仍为 `documents=5`、`main_articles=121`、`result=ok`。

`tests/test_gold_eval.py` 运行 5 项，结果 `OK`。临时副本覆盖证据切片不符、附件中的重复 Article 编号被错误指到正文第一次出现、拒答题带有证据、重复 case_id、版本不一致、题集哈希不符和 CRLF。正式题集字节在测试后不变。

来源清单、五份官方 HTML、已验收 txt 和 JSON、正式交付包、语料清单、单文档样本和三道样题共 27 个已记录哈希，与冻结时的值一致。已有复核报告本轮没有改写。

## 人工复核结论与后续事项

- 人工复核和浏览器视觉检查已于 2026-11-19 由 A 负责人确认通过，未发现问题。
- 没有向量索引、真实语义检索、LLM 回答或四组评分。
- 没有执行 Git 写入或推送。
