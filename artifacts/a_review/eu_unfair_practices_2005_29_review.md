# Unfair Commercial Practices 原文对照复核

复核方式：AI 辅助原文复核。日期：2026-11-19。

本复核直接读取原始 HTML，用 `html.parser` 清点 `#document1` 中的章节容器、节容器、主条文和序言节点，再按清洗 JSON 的 Python 区间 `[start, end)` 回切正文。没有打开浏览器做页面视觉检查。

## 输入与产物

| 文件 | SHA-256 | 字节数 |
| --- | --- | --- |
| `data/raw/Unfair Commercial Practices.html` | `0d678d1bbd988c59b40ff6363f3d9b8370c34da7b3744395eb7147364a19c1cc` | 490851 |
| `data/processed/eu_unfair_practices_2005_29.txt` | `7bc191bd5b55af42a179d95d98b1e7c2aa603509941065605b4ba175eb54f10b` | 59599 |
| `data/processed/eu_unfair_practices_2005_29.json` | `1f21061ca7b3f46f8cd2a949c722b86dbcdac0864c95281291cf037fad40c200` | 270853 |
| `data/sources.json` | `d41adeeff519e4307edd9529bfdeb5df4123e8b73b57c9b8abf17a689fd11e8d` | 30266 |

正文 59467 个 Python 字符，只含 LF，文件以一个换行结束。

## 章节、节与主条文

`#document1` 的正文容器 `enc_1` 下有四个章节容器：`cpt_1`、`cpt_2`、`cpt_3`、`cpt_4`。它们的标题节点是 `cpt_1.tit_1`、`cpt_2.tit_1`、`cpt_3.tit_1`、`cpt_4.tit_1`，类名为 `eli-title`，不是新的章节。

第二章内有两个节容器：`cpt_2.sct_1`、`cpt_2.sct_2`。它们的标题节点是 `cpt_2.sct_1.tit_1`、`cpt_2.sct_2.tit_1`，也没有再算成节。

主条文是 `art_1` 至 `art_21`，共 21 个 `div.eli-subdivision`。序言节点是 `rct_1` 至 `rct_25`，共 25 个。附件容器是 `anx_I`、`anx_II`。

第二章同时包含直接所属的第 5 条，以及两个节内的第 6 至第 9 条。第 1 至第 4 条属于第一章，第 10 条属于第三章，第 11 至第 21 条属于第四章。这些条文没有节。附件和修订引文中的 `Article` 编号没有成为主条文。

## 抽查

| 位置 | 区间 | 回切结果 |
| --- | --- | --- |
| 第一章 | `[20069, 26112)` | `CHAPTER 1` / `GENERAL PROVISIONS` |
| 第 1 条 | `[20099, 20420)` | `Article 1` / `Purpose`，直接属于第一章 |
| 第二章 | `[26114, 34413)` | `CHAPTER 2` / `UNFAIR COMMERCIAL PRACTICES` |
| 第 5 条 | `[26153, 27640)` | `Article 5` / `Prohibition of unfair commercial practices`，直接属于第二章 |
| 第 2 章第 1 节 | `[27642, 32991)` | `Section 1` / `Misleading commercial practices` |
| 第 6 条 | `[27685, 30366)` | `Article 6` / `Misleading actions`，属于第 2 章第 1 节 |
| 第 2 章第 2 节 | `[32993, 34413)` | `Section 2` / `Aggressive commercial practices` |
| 第 8 条 | `[33036, 33558)` | `Article 8` / `Aggressive commercial practices`，属于第 2 章第 2 节 |
| 第 11 条 | `[34994, 38641)` | `Article 11` / `Enforcement` |
| 第 21 条 | `[47654, 47725)` | `Article 21` / `Addressees` |
| 列表 | `[20480, 20658)` | `(a) ‘consumer’ means any natural person who, in commercial practices covered by this Directive, is acting for purposes which are outside his trade, business, craft or profession;` |
| 脚注 | `[42084, 42119)` | `(*1) OJ L 149, 11.6.2005, p. 22.’;"` |
| 附件 I 开头 | 附件文本起始 | `ANNEX I` / `COMMERCIAL PRACTICES WHICH ARE IN ALL CIRCUMSTANCES CONSIDERED UNFAIR` |

第 5 条在第 1 节之前结束，中间是章节内部的空行。第 6 条和第 8 条的区间分别落在两个节内。节 ID 带有所属章：`eu_unfair_practices_2005_29:chapter:2:section:1` 和 `section:2`。

脚注 `act:*1` 的 `referenced_by` 指向第 14 条中引用 `(*1)` 的列表项。脚注文本末尾的引号和分号来自 HTML 脚注段落，该段落包含被修订条文引文的结束符号。

## 条件、例外、否定和限制

- 第 5 条第 1 款写明 `Unfair commercial practices shall be prohibited.`
- 第 5 条随后规定，商业行为同时违反专业注意义务并实质性扭曲平均消费者经济行为时，才构成不公平。
- 第 6 条规定，虚假信息，或者整体展示足以欺骗平均消费者的信息，即使事实正确，只要导致其作出原本不会作出的交易决定，即构成误导。该句位于第 6 条 `[27685, 30366)` 内。
- 第 8 条规定，通过骚扰、胁迫或不当影响严重损害或可能严重损害消费者选择自由，并因此导致交易决定的，构成攻击性商业行为。该句位于第 8 条 `[33036, 33558)` 内。
- 第 3 条第 10 款规定，本指令不适用于贵金属成色认证和标识的成员国规定。
- 第 4 条规定，成员国不得以本指令已协调的事由限制服务提供自由或货物自由流动。
- 第 19 条保留 `by 12 June 2007` 和 `by 12 December 2007`。前者是转化期限，后者是措施适用日。
- 第 20 条只规定在官方公报公布后的次日生效。
- 附件 I 收录在任何情况下都被视为不公平的商业行为。附件 II 中的 `Article 3`、`Articles 4 and 5` 是其他法令的对照条目，不是本文件的主条文。

## 全文覆盖和标题顺序

清洗正文按 HTML 顺序写出四章标题、第二章的两个节标题、21 条主条文、序言、落款、脚注和两个附件。第 14 条修订引文中的 `‘Article 1`、`‘Article 3a`，以及两处 `‘Article 9`，保留为引文标题。

第 15 条一处引文在原始 HTML 中写作 `11 May 2005of`，清洗后仍是 `2005of`。这是快照原文缺少空格，不是清洗时删字。

正文在附件 II 最后一条脚注结束。

## 重复处理与异常检测

最终来源记录写入后连续两次清洗，txt 与 JSON 字节哈希都是上表中的值。

在临时副本上做了三次失败检查，正式文件没有被改写：

- 删除第 21 条后退出码为 1，主条文变为 1–20，期望 1–21。
- 把第 6 条的 `section_id` 改成不存在的 `chapter:2:section:9` 后退出码为 1。
- 把第 1 节的结束位置伸到第二章之外后退出码为 1，原因是节区间超出父章。

## 未纳入本文件的问题

本复核没有做浏览器视觉检查。页面状态写明本法令已被修改，并链接合并文本 `02005L0029-20260927`、`02005L0029-20220528` 和 `02005L0029-20050612`。这些都不是本快照保存的正文。
