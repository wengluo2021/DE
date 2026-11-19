# Sale of Goods 原文对照复核

复核方式：AI 辅助原文复核。日期：2026-11-19。

本复核对照本地原始 HTML 与清洗正文，不依赖清洗脚本打印的成功状态。使用 Python `html.parser` 与 BeautifulSoup 独立清点 `#document1` 中的主条文节点，再按清洗 JSON 的 Python 区间 `[start, end)` 回切正文。没有使用浏览器做页面视觉检查。

## 输入与产物

| 文件 | SHA-256 | 字节数 |
| --- | --- | --- |
| `data/raw/Sale of Goods.html` | `4869ed74958ae7cc50897e502272cc103502bffd1722f4ed07ca1f7188bb16ac` | 489604 |
| `data/processed/eu_sale_of_goods_2019_771.txt` | `d3076ba5236d6e7aad6ba30ae8b8d4b17af14fa148f7abc42cadd96764498ad4` | 89977 |
| `data/processed/eu_sale_of_goods_2019_771.json` | `ec42ea4dbad2a165bfd409f50c21fc10620ef4ca9b17d8028e5c1885570b4d6c` | 343414 |
| `data/sources.json` | `ae872164524255ec12406c4bf15c78c6ac372ac1c024e6b39c9c0b25aaf1e6e8` | 15284 |

正文 89878 个 Python 字符，只含 LF，文件以一个换行结束。

## 主条文与 DOM

`#document1` 内、附件外的 `div.eli-subdivision` 主条文节点为 `art_1` 至 `art_27`，共 27 个。没有 `cpt_` 章节节点。27 个节点都是 `div#enc_1` 的直接子节点，顺序与 JSON 的 `articles` 一致。每个 `chapter_id` 为 `null`，`chapters` 为空。

附件对照表中的 `Article 1`、`Article 13` 等单元格仍留在表格行里。第 13 条正文中的 `Article 15` 交叉引用没有生成新的主条文。第 22 条替换文本中的引号项 `‘3.` 与 `‘7.` 留在第 22 条内部。

## 抽查

| 位置 | 区间 | 回切结果 |
| --- | --- | --- |
| 第 1 条 | `[57289, 57797)` | `Article 1` / `Subject matter and purpose` |
| 第 14 条 | `[76119, 77308)` | `Article 14` / `Repair or replacement of the goods` |
| 第 27 条 | `[86022, 86093)` | `Article 27` / `Addressees`，正文为 `This Directive is addressed to the Member States.` |
| 列表 | `[76214, 76233)` | `(a) free of charge;`，位于第 14 条内 |
| 脚注 | `[86219, 86250)` | `(1) OJ C 264, 20.7.2016, p. 57.` |
| 脚注引用 | `[580, 659)` | `Having regard to the opinion of the European Economic and Social Committee (1),` |

脚注 `eu_sale_of_goods_2019_771:footnote:act:1` 的 `referenced_by` 指向该序言块。序言有 (1) 至 (72) 共 72 项，编号连续。正文脚注 10 条，附件内没有脚注。

## 期限、例外与限制

- 第 10 条 `[69717, 72066)` 规定，交付时已经存在并在此后两年内显现的不符，由卖方承担责任：`within two years of that time`。
- 同一条允许二手商品约定更短的责任或时效期间，但 `shall not be less than one year`。该短语从字符 72034 开始，仍在第 10 条 `[69717, 72066)` 内。
- 第 13 条第 3 款允许卖方在修理和更换不可能或费用不成比例时拒绝恢复符合性。句子从字符 74245 开始，落在第 13 条 `[73422, 76117)` 内。
- 第 24 条规定 2021 年 7 月 1 日前完成转化，措施自 2022 年 1 月 1 日起适用，并且本指令不适用于该日前订立的合同。后一句位于第 24 条 `[84215, 84951)` 内。
- 第 26 条规定指令在公布后第 20 日生效，同时写明第 22 条自 2022 年 1 月 1 日起适用。生效日与适用日因此分开保留。

## 全文覆盖

把 27 条主条文的 DOM 文本折叠空白后，与对应清洗条文比较。25 条完全一致。第 22 条和第 26 条的差异来自比较器在标签两侧插入空格：

- 第 22 条源码是 `(<a ...>OJ L 136, 22.5.2019, p. 28</a>)`，清洗结果为 `(OJ L 136, 22.5.2019, p. 28)`。
- 第 26 条源码是 `Union</span>.`，清洗结果为 `Union.`。

这两处按 HTML 文本节点核对，没有删字。附件以 `ANNEX` 和 `CORRELATION TABLE` 开始，首行对照是 `Article 1(1) | Article 1`。HTML 标题就是 `ANNEX`，没有写成 `ANNEX I`；结构 ID 使用 HTML id `anx_1`，标签保持 `ANNEX`。

EUR-Lex 文件信息区写有 `OJ L 136, 22.5.2019, pp. 28–50` 和程序号 `PE/27/2019/REV/1`。它们位于 `#document1` 之外，不进入清洗正文。正文页眉只有 `L 136/28`，正文内部引用写起始页 `p. 28`。

## 重复处理

最终来源记录写入后，连续两次运行 `process_documents.py --document-id eu_sale_of_goods_2019_771`。两次的 txt 与 JSON 字节哈希都是上表中的值。

## 未纳入本文件的问题

本复核没有打开浏览器检查排版。2024/1799 的后续修订和两份合并文本只作为来源链接记录，没有进入本清洗正文。
