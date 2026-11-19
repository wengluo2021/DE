# eu_consumer_rights_2011_83 原文对照复核

AI 辅助原文复核。复核日期：2026-11-19。

本报告直接阅读原始 HTML 的 DOM，再与清洗全文的 Python 字符切片对照。未做浏览器视觉检查。没有把清洗脚本或校验器的成功输出当作结论依据；下列区间均用本次 txt 重新截取，并与 HTML 节点文字核对。正式快照和清洗产物未改。

## 绑定的文件版本

| 文件 | SHA-256 |
| --- | --- |
| `data/raw/eu_consumer_rights_2011_83.html` | `7812747113a74ef3a2b2e8d2d3fb067ed416280f415aed76dc255083b54e892e` |
| `data/processed/eu_consumer_rights_2011_83.txt` | `75acf22af53bf1878fe2750757b5ecd5c1230236aaab4fc543c1d029b3bf5689` |
| `data/processed/eu_consumer_rights_2011_83.json` | `f7ed11c4e7817cc58c23498ef1b87b87e885996f8a075a02365782e44b84829a` |

HTML 哈希与 `data/sources.json` 中该文档的快照哈希一致。txt 为 103514 个 Python 字符、103799 个 UTF-8 字节，换行是 LF。JSON 的 `cleaning_rule_version` 为 `eurlex_html_v1`。`character_offsets` 标明单位是 Python 字符，区间是 `[start, end)`，基准是完整清洗 txt。

另外对条文、章节、recital、附件、表格、脚注及其正文块做了 547 次独立切片核对，`clean_text[start:end]` 与保存文本全部一致。

## 1. Article 1

- HTML：`div#art_1`，标题 `p#d1e663-64-1`，副标题 `div#art_1.tit_1`。父章节是 `div#cpt_I`（`p#d1e655-64-1` 为 CHAPTER I，`div#cpt_I.tit_1` 为 SUBJECT MATTER, DEFINITIONS AND SCOPE）。
- JSON：`eu_consumer_rights_2011_83:article:1`，`chapter_id` 为 `eu_consumer_rights_2011_83:chapter:I`。章节区间 `[44937, 53591)`，条文区间 `[44986, 45342)`，落在章节内。
- 条文切片以 `Article 1 / Subject matter / The purpose of this Directive is...` 开头。
- 正文块 `eu_consumer_rights_2011_83:article:1:block:1`，`[45011, 45342)`。切片与 HTML 正文一致：

> The purpose of this Directive is, through the achievement of a high level of consumer protection, to contribute to the proper functioning of the internal market by approximating certain aspects of the laws, regulations and administrative provisions of the Member States concerning contracts concluded between consumers and traders.

- 对照结果：标题、副标题、唯一一段正文和第一章归属一致。
- 差异：无内容差异。不阻碍验收。

## 2. Article 18

- HTML：`div#art_18`，标题 `p#d1e1764-64-1`，副标题 `div#art_18.tit_1`（Delivery）。父章节是 `div#cpt_IV`（CHAPTER IV, OTHER CONSUMER RIGHTS）。四组正文在 `div#018.001` 至 `div#018.004`。第 2 款有两个 `p.oj-normal`。
- JSON：`eu_consumer_rights_2011_83:article:18`，章节 `eu_consumer_rights_2011_83:chapter:IV`，章节区间 `[81433, 85295)`。条文区间 `[81963, 83581)`，五个正文块都在条文内。
- 块与 HTML 段落一一对应：

| 块 | 区间 | 核对要点 |
| --- | --- | --- |
| `article:18:block:1` | `[81983, 82251)` | 第 1 款：当事人另有约定的除外；转移占有或控制；without undue delay；not later than 30 days from the conclusion of the contract |
| `article:18:block:2` | `[82252, 82681)` | 第 2 款第一段：未按约定或第 1 款期限交付时，消费者指定 additional period of time appropriate to the circumstances；仍未交付则可 terminate the contract |
| `article:18:block:3` | `[82682, 83300)` | 第一子款的例外：shall not be applicable；商人拒绝交付，或约定期限属于 essential，或消费者在缔约前告知 delivery by or on a specified date is essential；这些情况下可 terminate the contract immediately |
| `article:18:block:4` | `[83301, 83420)` | 第 3 款：解除后 without undue delay，reimburse all sums paid under the contract |
| `article:18:block:5` | `[83421, 83581)` | 第 4 款：除第 2 款解除权外，还可使用 national law 规定的 other remedies |

- 对照结果：空白折叠后，五个段落与 HTML 逐字一致。30 日上限、额外期限、三类立即解除情形、退款和国内法其他救济都保留。HTML 中款号后的连续不换行空格收成一个普通空格。
- 差异：只有空白格式变化，原意未改。不阻碍验收。

## 3. Article 35

- HTML：`div#art_35`，标题 `p#d1e2075-64-1`，副标题 `div#art_35.tit_1`（Addressees）。父章节是 `div#cpt_VI`。它是 `art_1` 至 `art_35` 中的最后一个 `div.eli-subdivision`。
- JSON：`eu_consumer_rights_2011_83:article:35`，章节 `eu_consumer_rights_2011_83:chapter:VI`，章节区间 `[89541, 91903)`。条文区间 `[91832, 91903)`。主条文编号仍是 1 至 35，共 35 条。
- 切片：

> Article 35
> Addressees
> This Directive is addressed to the Member States.

- 正文块 `eu_consumer_rights_2011_83:article:35:block:1`，`[91854, 91903)`，文本就是最后一句。
- 对照结果：标题、正文和区间一致。不阻碍验收。

## 4. Article 16

- HTML：`div#art_16`，标题 `p#d1e1652-64-1`，副标题 `div#art_16.tit_1`。父章节是 `div#cpt_III`。导语是一个 `p.oj-normal`，(a) 至 (m) 各是一张两列布局表，左列标记、右列条件。
- JSON：`eu_consumer_rights_2011_83:article:16`，章节 `eu_consumer_rights_2011_83:chapter:III`，条文区间 `[78815, 81431)`。导语块是 `article:16:block:1`，`[78866, 79029)`；(a) 至 (m) 是 `block:2` 至 `block:14`，区间从 `[79030, 79295)` 连续到 `[81214, 81431)`。
- 把 HTML 两列拼接成 `"(标记) 条件"` 后，14 个块与 HTML 顺序和文字一致。否定和限制都在：
  - 导语：Member States shall not provide for the right of withdrawal set out in Articles 9 to 15。
  - (e)：not suitable for return due to health protection or hygiene reasons and were unsealed after delivery。
  - (h) 后句保留反向条件：额外服务或更换零件以外的货物，the right of withdrawal shall apply。
  - (j)：with the exception of subscription contracts。
  - (l)：accommodation other than for residential purpose，且 if the contract provides for a specific date or period of performance。
  - (m)：digital content which is not supplied on a tangible medium，并保留 prior express consent 和 thereby loses his right of withdrawal。
- 差异：布局表被收成一行一条，标记和条件都在。不阻碍验收。

## 5. 附件 II

- HTML：`div#anx_II`。第一张 `table.oj-table` 的表头三列是 Directive 85/577/EEC、Directive 97/7/EC、This Directive。第一条数据行的三个 `td` 依次是 `Article 1`、只含 `&nbsp;` 的空单元格、`Article 3 read in conjunction with Article 2, points 8 and 9, and Article 16, point (h)`。
- JSON：`eu_consumer_rights_2011_83:annex:II`。表 `eu_consumer_rights_2011_83:annex:II:table:1`，区间 `[99214, 103146)`，78 行，其中 77 个单元格为空。空单元格保留在列位上，写成连续的 ` | `。
- 抽查行：`eu_consumer_rights_2011_83:annex:II:block:4`，`[99272, 99374)`。切片为：

> Article 1 |  | Article 3 read in conjunction with Article 2, points 8 and 9, and Article 16, point (h)

- 整张表按 HTML 的行顺序逐格比对，78 行全部一致。下一行是空单元格、Article 1、Article 1 read in conjunction with Article 2, point 7，列关系没有左右对调。
- 表内 Article 编号没有进入主条文。主条文仍是 `art_1` 至 `art_35`，没有 `art_8a`。这一行的结构类型是表格行，不是 `article`。真正的 Article 1 在 `[44986, 45342)`，与本行不是同一位置。
- 差异：空单元格的 `&nbsp;` 收成空列。列顺序和原文顺序保留。不阻碍验收。

## 6. 重复内容与脚注

### ‘Article 8a

快照里有两个 `div id="008A"`，ID 重复，不能靠这个 ID 区分归属。

- 第 32 条：父节点 `div#art_32`，标题节点 `p#d1e2006-64-1`。JSON 块 `eu_consumer_rights_2011_83:article:32:block` 中的 `quoted_heading` 区间 `[90156, 90167)`，切片是 `‘Article 8a`。其后的第 1 至 3 款及两个破折号条件留在第 32 条内。没有单独的副标题，与 HTML 一致。
- 第 33 条：父节点 `div#art_33`，标题节点 `p#d1e2043-64-1`，副标题是 Reporting requirements。JSON 中 `quoted_heading` 为 `[91026, 91037)`，副标题块为 `[91038, 91060)`，第 1 至 3 款继续到 `[91480, 91674)`。文字与 HTML 一致，包括 Article 8(2)、Article 5(1) to (3) 和 Article 7(1)。
- 两处都不是主条文。主条文列表没有 8a。

### 同号脚注

正文脚注 (1) 与附件 II 脚注 (1) 使用不同节点、不同区间和不同引文。

| 位置 | HTML 定义节点 | HTML 引用锚点 | JSON | 区间 | 切片 | 引用它的块 |
| --- | --- | --- | --- | --- | --- | --- |
| 正文 | `a#ntr1-L_2011304EN.01006401-E0001` | `a#ntc1-L_2011304EN.01006401-E0001`，href 指向该定义 | `eu_consumer_rights_2011_83:footnote:act:1` | `[92040, 92072)` | `(1) OJ C 317, 23.12.2009, p. 54.` | `preamble:block:4`，`[584, 663)`，文本含 Committee (1) |
| 附件 II | `a#ntr1-L_2011304EN.01008601-E0001` | `a#ntc1-L_2011304EN.01008601-E0001` | `eu_consumer_rights_2011_83:footnote:annex-II:1` | `[103483, 103513)` | `(1) OJ L 364, 9.12.2004, p. 1.` | `annex:II:block:81`，表头含 cooperation) (1) |

两个锚点的 href 片段分别指向自己的定义 ID。正文 `(1)` 第一次出现在序言，不是脚注正文的位置。

另核了正文脚注 (21)：定义 `ntr21-L_2011304EN.01006401-E0021`，由第 31 条 `article:31:block:1` 引用，引文是 OJ L 271, 9.10.2002, p. 16，与两处 (1) 都不同。

- 差异：HTML 把数字放在 `span` 里，直接取文本会得到 `( 1 )`；页面上仍是 `(1)`。清洗结果与可见文字一致。不阻碍验收。

## 7. 附件 I 方框数字

- HTML：`div#anx_I`。示范文句中的占位是 `div.oj-box`，填写说明左列也是 `div.oj-box`，内容为 `1.` 至 `6.`。
- JSON：`eu_consumer_rights_2011_83:annex:I`。

占位与说明的对应关系：

| HTML 方框 | 清洗后的位置 | 对应说明 |
| --- | --- | --- |
| 文句中的方框 1，紧挨 `.To` | `annex:I:block:6`，`[93050, 93370)`，作 `day 1. To exercise` | 说明 1，`[94283, 94344)`，含 (a) 至 (e) 五段引文 |
| 圆括号中的方框 2 | 同一块中的 `us (2)` | 说明 2，插入姓名、地址和联系方式 |
| 句末方框 3 | 同一块末尾的 `obligatory. 3` | 说明 3，网站电子提交的可选语句 |
| 退款段落后连续的方框 4、5、6 | `annex:I:block:9`，`[93572, 94253)`，句末为 `reimbursement. 4 5 6` | 说明 4、5、6 按原顺序保留，说明 5 仍包含 (a)(b)(c) |

纯格式变化：

- 方框边框消失，数字留在原来的插入点。
- HTML 源码在方框 1 后是 `.To`，中间没有空格。清洗时补成 `1. To`。单词没有增删，句子更容易读。
- 说明 1 至 6 的条件、引号内示范文句、`not put up for sale`、`whichever is the earliest` 和费用承担语句都还在。

可能影响理解、但不改变法律措辞的地方：

- 方框 3 现在是句末的一个数字 `3`。
- 方框 4、5、6 现在连成 `4 5 6`，不再是三个分开的空框。读者仍能靠后面的 `4.`、`5.`、`6.` 说明对回去，但视觉上不如原方框清楚。

这不构成漏句或改写。当前已验收的 `eurlex_html_v1` 不需要为此改写正文。若以后有题目专门问某个占位框，证据应同时引用占位数字所在句和对应的编号说明。

## 验收判断

七项都能从 HTML 节点追到稳定结构 ID，并用 `[start, end)` 切回同一段文字。第 16 条的例外列表、第 18 条的期限和例外、附件表的空列，以及同号脚注的不同归属都保持原意。

附件 I 的方框变成普通数字，属于已记录的格式限制，不阻碍本样本验收。

本样本具备进入第 3 步编写样题的条件。第 3 步再处理其他四份文档和正式题集。
