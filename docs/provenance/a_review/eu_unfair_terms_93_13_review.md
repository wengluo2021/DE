# Unfair Terms 原文对照复核

复核方式：AI 辅助原文复核。日期：2026-11-19。

本复核直接读取 `data/raw/Unfair Terms.html`，用 `html.parser` 清点 `#document1` 中的标题、序言段落、`p.ti-art`、落款、脚注和附件，再按清洗 JSON 的 Python 区间 `[start, end)` 回切正文。没有打开浏览器做页面视觉检查。

## 输入与产物

| 文件 | SHA-256 | 字节数 |
| --- | --- | --- |
| `data/raw/Unfair Terms.html` | `6c700ae54d53f3dc3ece8d226d18471ac905eff42a7cb4d4874e2e56acaff707` | 312379 |
| `data/processed/eu_unfair_terms_93_13.txt` | `bf518901d6a71d5753ec99ed0b5b13025f5bf136782594a0dbaf8263e376a401` | 20868 |
| `data/processed/eu_unfair_terms_93_13.json` | `c4d387298a543eb545a91cec522662b77473a6c79c7ee27c450818f17df29893` | 86075 |
| `data/sources.json` | `6a7a20ff4c9ea87bb940a066e8fdf08b285458fc9208b6b231dcf8e99fa5bad9` | 37980 |

正文 20839 个 Python 字符，只含 LF，文件以一个换行结束。最后一个附件区间结束于 20838，文件末尾的换行不计入结构区间。

## 旧式结构清点

正文在 `#document1` 内层容器中，是一段相邻的段落和布局表，没有 `art_` 容器，也没有 Chapter 或 Section 容器。

| 结构 | 本地 HTML 清点 |
| --- | --- |
| 法规标题 | 3 个 `p.doc-ti`：`COUNCIL DIRECTIVE 93/13/EEC`、`of 5 April 1993`、`on unfair terms in consumer contracts` |
| 序言 | 24 个以 Whereas 开头的 `p.normal`，没有官方编号；另有制定公式、引用条款和 `HAS ADOPTED THIS DIRECTIVE:` |
| 主条文 | 11 个 `p.ti-art`，文本为 Article 1 至 Article 11 |
| 落款 | `div.final`，含 `Done at Luxembourg, 5 April 1993.` 和 `p.signatory` |
| 脚注 | 6 个 `p.note`，其中 4 个带 `ntr` 锚点；(2) 和 (4) 的续行没有新锚点 |
| 附件 | 1 个 `div#L_1993095EN.01003301`，标题 `ANNEX`，内部有 `ti-grseq-1` |

页眉表含 `hd-date`、`hd-lg`、`hd-ti`、`hd-oj`，对应 `21.4.1993`、`EN`、`Official Journal of the European Communities`、`L 95/29`。这些文字没有进入清洗正文。脚注中的 `OJ No` 引用仍保留。

主条文 HTML id 依次为 `d1e196-29-1`、`d1e210-29-1`、`d1e245-29-1`、`d1e268-29-1`、`d1e282-29-1`、`d1e288-29-1`、`d1e302-29-1`、`d1e321-29-1`、`d1e327-29-1`、`d1e333-29-1`、`d1e360-29-1`。第 2 条里的 “defined in Article 3” 和第 4 条里的 “Without prejudice to Article 7” 位于正文段落或列表，不是 `p.ti-art`，没有成为新的主条文。附件标题 `TERMS REFERRED TO IN ARTICLE 3 (3)` 留在附件。

## 抽查

| 位置 | 区间 | 回切结果 |
| --- | --- | --- |
| 序言第 1 项 | `[414, 675)` | 以 `Whereas it is necessary to adopt measures` 开头；`number` 和 `official_number` 都是 null，`ordinal` 为 `1` |
| 序言第 24 项 | `[8592, 8797)` | `Whereas the courts or administrative authorities...unfair terms in consumer contracts,` |
| 第 1 条 | `[8827, 9348)` | `Article 1`，目的条款和第 2 款排除规定；`chapter_id`、`section_id`、`heading` 都是 null |
| 第 2 条列表 | `[9396, 9464)` | `(a) ‘unfair terms’ means the contractual terms defined in Article 3;` |
| 第 6 条 | `[12066, 12727)` | 含 `not be binding on the consumer`，以及消费者不因选择非成员国法律而失去保护 |
| 第 11 条 | `[14865, 14925)` | 只有 `Article 11` 和 `This Directive is addressed to the Member States.` |
| 落款 | `[14927, 15009)` | `Done at Luxembourg, 5 April 1993.`、`For the Council`、`The President`、`N. HELVEG PETERSEN` |
| 脚注 (2) | `[15046, 15112)` | `(2) OJ No C 326, 16. 12. 1991, p. 108 and OJ No C 21, 25. 1. 1993.`，引用块为序言 block 4 |
| 附件 | `[15220, 20838)` | 以 `ANNEX` 开头，不是整部法规的标题 |
| 附件例外标题 | `[19072, 19114)` | `2. Scope of subparagraphs (g), (j) and (1)` |
| 附件例外 | `[20240, 20291)` | `(c) Subparagraphs (g), (j) and (1) do not apply to:` |

第 11 条结束于 14925，落款开始于 14927，脚注 (1) 开始于 15011，附件开始于 15220。中间的空白行不属于任一侧区间。

## 条件、否定和原文措辞

以下表述按 HTML 原文保留：

- 第 4 条第 2 款使用 `shall relate neither`，并保留 `goods supplies`、`plain intelligible language`。
- 第 5 条要求书面条款使用 `plain, intelligible language`，同时写明解释规则 `shall not apply` 于第 7 条第 2 款程序。
- 第 6 条写明不公平条款 `not be binding on the consumer`，合同在去掉该条款后仍可存续时继续约束双方。
- 第 10 条的转化期限是 `no later than 31 December 1994`，措施适用于 `contracts concluded after 31 December 1994`。
- 附件保留字母列表、`without hindrance`，以及标题和例外中的 `(1)`。这处 `(1)` 看起来像 `(l)` 的排版或识别问题，本轮没有按常识改写。
- 脚注日期保留源文中的空格，例如 `24. 3. 1992`。HTML 把脚注 (2) 和 (4) 拆成两个 `p.note`；清洗后续行并入对应锚点，两个 OJ 引用仍属于同一个脚注。

## 覆盖与重复运行

标题、序言、11 条、落款、4 条脚注和附件都进入同一份清洗正文。校验 `result=ok`，并检查了每个结构的 `clean_text[start:end] == item.text`。连续清洗两次，txt 与 JSON 哈希不变。

临时副本上的异常检查均退出码 1，正式快照和产物未改：

- 删除第 6 条：主条文变成 1–5、7–11。
- 删除全部主条文：主条文为空。
- 序言 block 3 改成不存在的脚注引用 `ntr-does-not-exist`。
- 第 1 条区间改成 `[8827, 100521)`，超出 20839 个字符。

## 规则说明修正

修正前的结构 JSON 哈希 `9e57f3f501ec37583d36d273be66aa2ca5cf5d573696ab39ab2ac1523e32e22f` 是历史值。重新生成后，JSON 差异只有 `cleaning_rules.main_articles` 和 `cleaning_rules.footnotes`。正文哈希仍是 `bf518901d6a71d5753ec99ed0b5b13025f5bf136782594a0dbaf8263e376a401`。来源、条文、正文块、ID、区间、统计和脚注引用没有变化。

旧式说明现在写明：主条文从 `p.ti-art` 开始，到下一主条文、落款、脚注或附件边界结束；带 `ntr` 锚点的 `p.note` 开始一条脚注，没有新锚点的续行并入前一条。本文件 6 个 `p.note` 对应 4 条脚注。

## 本复核未包括

没有做浏览器视觉检查。没有运行 `--all`，没有生成正式 `data/corpus_manifest.json`，没有编写 30 道正式题，也没有建立向量库。
