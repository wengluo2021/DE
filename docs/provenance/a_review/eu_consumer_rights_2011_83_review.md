# eu_consumer_rights_2011_83 source text comparison review

AI-assisted source text review. Review date: 2026-11-19.

This report reads the DOM of the original HTML directly, then compares it with Python character slices of the cleaned full text. No browser visual inspection was performed. The successful output of the cleaning script or validator was not used as the basis for conclusions; all intervals below were re-extracted from this round's txt and checked against the HTML node text. The official snapshot and cleaned artifacts were not modified.

## Bound file versions

| File | SHA-256 |
| --- | --- |
| `data/raw/eu_consumer_rights_2011_83.html` | `7812747113a74ef3a2b2e8d2d3fb067ed416280f415aed76dc255083b54e892e` |
| `data/processed/eu_consumer_rights_2011_83.txt` | `75acf22af53bf1878fe2750757b5ecd5c1230236aaab4fc543c1d029b3bf5689` |
| `data/processed/eu_consumer_rights_2011_83.json` | `f7ed11c4e7817cc58c23498ef1b87b87e885996f8a075a02365782e44b84829a` |

The HTML hash matches the snapshot hash of this document in `data/sources.json`. The txt is 103514 Python characters and 103799 UTF-8 bytes, with LF line endings. The JSON's `cleaning_rule_version` is `eurlex_html_v1`. `character_offsets` states that the unit is Python characters, the interval is `[start, end)`, and the basis is the complete cleaned txt.

In addition, 547 independent slice checks were performed on provisions, chapters, sections, recitals, annexes, tables, footnotes, and their body blocks; `clean_text[start:end]` all match the saved text.

## 1. Article 1

- HTML: `div#art_1`, title `p#d1e663-64-1`, subtitle `div#art_1.tit_1`. The parent chapter is `div#cpt_I` (`p#d1e655-64-1` is CHAPTER I, `div#cpt_I.tit_1` is SUBJECT MATTER, DEFINITIONS AND SCOPE).
- JSON: `eu_consumer_rights_2011_83:article:1`, `chapter_id` is `eu_consumer_rights_2011_83:chapter:I`. Chapter interval `[44937, 53591)`, provision interval `[44986, 45342)`, which falls within the chapter.
- The provision slice begins with `Article 1 / Subject matter / The purpose of this Directive is...`.
- Body block `eu_consumer_rights_2011_83:article:1:block:1`, `[45011, 45342)`. The slice matches the HTML body text:

> The purpose of this Directive is, through the achievement of a high level of consumer protection, to contribute to the proper functioning of the internal market by approximating certain aspects of the laws, regulations and administrative provisions of the Member States concerning contracts concluded between consumers and traders.

- Comparison result: title, subtitle, the single body paragraph, and chapter I attribution are consistent.
- Differences: no content differences. Does not block acceptance.

## 2. Article 18

- HTML: `div#art_18`, title `p#d1e1764-64-1`, subtitle `div#art_18.tit_1` (Delivery). The parent chapter is `div#cpt_IV` (CHAPTER IV, OTHER CONSUMER RIGHTS). The four groups of body text are in `div#018.001` to `div#018.004`. Paragraph 2 has two `p.oj-normal`.
- JSON: `eu_consumer_rights_2011_83:article:18`, chapter `eu_consumer_rights_2011_83:chapter:IV`, chapter interval `[81433, 85295)`. Provision interval `[81963, 83581)`; all five body blocks are within the provision.
- Blocks correspond one-to-one with HTML paragraphs:

| Block | Interval | Key points checked |
| --- | --- | --- |
| `article:18:block:1` | `[81983, 82251)` | Paragraph 1: unless otherwise agreed by the parties; transfer of possession or control; without undue delay; not later than 30 days from the conclusion of the contract |
| `article:18:block:2` | `[82252, 82681)` | Paragraph 2, first subparagraph: where delivery has not been made as agreed or within the period in paragraph 1, the consumer specifies an additional period of time appropriate to the circumstances; if delivery is still not made, the consumer may terminate the contract |
| `article:18:block:3` | `[82682, 83300)` | Exception to the first subparagraph: shall not be applicable; the trader refuses to deliver, or the agreed period is essential, or the consumer informed the trader before conclusion of the contract that delivery by or on a specified date is essential; in these cases the consumer may terminate the contract immediately |
| `article:18:block:4` | `[83301, 83420)` | Paragraph 3: after termination, without undue delay, reimburse all sums paid under the contract |
| `article:18:block:5` | `[83421, 83581)` | Paragraph 4: in addition to the right of termination under paragraph 2, the consumer may also use other remedies provided by national law |

- Comparison result: after whitespace folding, the five paragraphs match the HTML verbatim. The 30-day limit, the additional period, the three cases of immediate termination, reimbursement, and other remedies under national law are all preserved. Consecutive non-breaking spaces after paragraph numbers in the HTML are collapsed into a single ordinary space.
- Differences: only whitespace formatting changes; the original meaning is unchanged. Does not block acceptance.

## 3. Article 35

- HTML: `div#art_35`, title `p#d1e2075-64-1`, subtitle `div#art_35.tit_1` (Addressees). The parent chapter is `div#cpt_VI`. It is the last `div.eli-subdivision` in `art_1` to `art_35`.
- JSON: `eu_consumer_rights_2011_83:article:35`, chapter `eu_consumer_rights_2011_83:chapter:VI`, chapter interval `[89541, 91903)`. Provision interval `[91832, 91903)`. The main provision numbers remain 1 to 35, 35 provisions in total.
- Slices:

> Article 35
> Addressees
> This Directive is addressed to the Member States.

- Body block `eu_consumer_rights_2011_83:article:35:block:1`, `[91854, 91903)`; the text is the final sentence.
- Comparison result: title, body text, and interval are consistent. Does not block acceptance.

## 4. Article 16

- HTML: `div#art_16`, title `p#d1e1652-64-1`, subtitle `div#art_16.tit_1`. The parent chapter is `div#cpt_III`. The lead-in is one `p.oj-normal`; (a) to (m) are each a two-column layout table, with the marker in the left column and the condition in the right column.
- JSON: `eu_consumer_rights_2011_83:article:16`, chapter `eu_consumer_rights_2011_83:chapter:III`, provision range `[78815, 81431)`. The introductory block is `article:16:block:1`, `[78866, 79029)`; (a) through (m) are `block:2` through `block:14`, with the range running continuously from `[79030, 79295)` to `[81214, 81431)`.
- After concatenating the two HTML columns into `"(marker) condition"`, the 14 blocks match the HTML in order and text. Negations and limitations are all present:
  - Introductory paragraph: Member States shall not provide for the right of withdrawal set out in Articles 9 to 15.
  - (e)：not suitable for return due to health protection or hygiene reasons and were unsealed after delivery。
  - The sentence after (h) retains the reverse condition: for goods other than additional services or replacement parts, the right of withdrawal shall apply.
  - (j)：with the exception of subscription contracts。
  - (l): accommodation other than for residential purpose, and if the contract provides for a specific date or period of performance.
  - (m): digital content which is not supplied on a tangible medium, retaining prior express consent and thereby loses his right of withdrawal.
- Difference: the layout table is condensed to one entry per line; markers and conditions are all present. Does not block acceptance.

## 5. Annex II

- HTML: `div#anx_II`. The header of the first `table.oj-table` table has three columns: Directive 85/577/EEC, Directive 97/7/EC, This Directive. The three `td` of the first data row are, in order, `Article 1`, an empty cell containing only `&nbsp;`, and `Article 3 read in conjunction with Article 2, points 8 and 9, and Article 16, point (h)`.
- JSON: `eu_consumer_rights_2011_83:annex:II`. Table `eu_consumer_rights_2011_83:annex:II:table:1`, range `[99214, 103146)`, 78 rows, of which 77 cells are empty. Empty cells are kept in their column positions, written as consecutive ` | `.
- Spot-checked rows: `eu_consumer_rights_2011_83:annex:II:block:4`, `[99272, 99374)`. The slices are:

> Article 1 |  | Article 3 read in conjunction with Article 2, points 8 and 9, and Article 16, point (h)

- The entire table was compared cell by cell in HTML row order; all 78 rows match. The next row is an empty cell, Article 1, Article 1 read in conjunction with Article 2, point 7; the column relationships are not swapped left-to-right.
- The Article numbers inside the table did not enter the main provisions. The main provisions remain `art_1` through `art_35`, with no `art_8a`. The structure type of this row is a table row, not `article`. The actual Article 1 is in `[44986, 45342)`, which is not the same location as this row.
- Difference: the `&nbsp;` of empty cells is condensed into an empty column. Column order and source order are preserved. Does not block acceptance.

## 6. Duplicate content and footnotes

### ‘Article 8a

The snapshot contains two `div id="008A"` with duplicate IDs; ownership cannot be distinguished by this ID alone.

- Article 32: parent node `div#art_32`, heading node `p#d1e2006-64-1`. In JSON block `eu_consumer_rights_2011_83:article:32:block`, `quoted_heading` range `[90156, 90167)`, slice is `‘Article 8a`. The following paragraphs 1 through 3 and the two dash conditions remain within Article 32. There is no separate subtitle, consistent with the HTML.
- Article 33: parent node `div#art_33`, heading node `p#d1e2043-64-1`, subtitle is Reporting requirements. In JSON, `quoted_heading` is `[91026, 91037)`, the subtitle block is `[91038, 91060)`, and paragraphs 1 through 3 continue to `[91480, 91674)`. The text matches the HTML, including Article 8(2), Article 5(1) to (3) and Article 7(1).
- Neither is a main provision. The main provision list has no 8a.

### Footnotes with the same number

The body footnote (1) and the Annex II footnote (1) use different nodes, different ranges and different quotations.

| Location | HTML definition node | HTML reference anchor | JSON | Range | Slice | Blocks referencing it |
| --- | --- | --- | --- | --- | --- | --- |
| Body | `a#ntr1-L_2011304EN.01006401-E0001` | `a#ntc1-L_2011304EN.01006401-E0001`, href points to that definition | `eu_consumer_rights_2011_83:footnote:act:1` | `[92040, 92072)` | `(1) OJ C 317, 23.12.2009, p. 54.` | `preamble:block:4`, `[584, 663)`, text contains Committee (1) |
| Annex II | `a#ntr1-L_2011304EN.01008601-E0001` | `a#ntc1-L_2011304EN.01008601-E0001` | `eu_consumer_rights_2011_83:footnote:annex-II:1` | `[103483, 103513)` | `(1) OJ L 364, 9.12.2004, p. 1.` | `annex:II:block:81`, header contains cooperation) (1) |

The href fragments of the two anchors point to their own definition IDs. The body `(1)` first appears in the preamble, not at the location of the footnote text.

Also checked the body footnote (21): definition `ntr21-L_2011304EN.01006401-E0021`, referenced by Article 31 `article:31:block:1`, quotation is OJ L 271, 9.10.2002, p. 16, which differs from both (1) instances.

- Difference: HTML places the number inside `span`, so taking the text directly yields `( 1 )`; on the page it is still `(1)`. The cleaned result matches the visible text. Does not block acceptance.

## 7. Box numbers in Annex I

- HTML: `div#anx_I`. The placeholder in the model sentence is `div.oj-box`, and the left column of the completion instructions is also `div.oj-box`, with content `1.` through `6.`.
- JSON：`eu_consumer_rights_2011_83:annex:I`。

Correspondence between placeholders and instructions:

| HTML box | Cleaned position | Corresponding instruction |
| --- | --- | --- |
| Box in the sentence 1, immediately next to `.To` | `annex:I:block:6`, `[93050, 93370)`, as `day 1. To exercise` | Instruction 1, `[94283, 94344)`, containing five quotations (a) through (e) |
| Box in parentheses 2 | `us (2)` in the same block | Instruction 2, insert name, address and contact details |
| Box at end of sentence 3 | `obligatory. 3` at the end of the same block | Instruction 3, optional statement for electronic submission via website |
| Consecutive boxes after the refund paragraph 4, 5, 6 | `annex:I:block:9`, `[93572, 94253)`, ending with `reimbursement. 4 5 6` | Instructions 4, 5, 6 kept in original order; instruction 5 still contains (a)(b)(c) |

Pure formatting changes:

- The box borders disappear; the numbers remain at their original insertion points.
- In the HTML source, after box 1 comes `.To` with no space in between. Cleaning adds `1. To`. No words are added or removed, and the sentence is easier to read.
- The conditions in instructions 1 through 6, the model sentences in quotation marks, `not put up for sale`, `whichever is the earliest` and the cost-bearing statements are all still present.

Places that may affect understanding but do not change the legal wording:

- Box 3 is now a single number `3` at the end of the sentence.
- Boxes 4, 5, 6 are now joined as `4 5 6`, no longer three separate empty boxes. Readers can still map back via the following instructions `4.`, `5.`, `6.`, but it is visually less clear than the original boxes.

This does not constitute an omitted sentence or a rewrite. The currently accepted `eurlex_html_v1` does not need its body text rewritten for this. If a question later specifically asks about a particular placeholder box, the evidence should cite both the sentence containing the placeholder number and the corresponding numbered instruction.

## Acceptance judgment

All seven items can be traced from HTML nodes to stable structure IDs and sliced back to the same text using `[start, end)`. The exception list in Article 16, the time limits and exceptions in Article 18, the empty columns in the annex table, and the different ownership of footnotes with the same number all preserve the original meaning.

The boxes in Annex I become plain numbers; this is a documented formatting limitation and does not block acceptance of this sample.

This sample meets the conditions to proceed to step 3 and write the sample questions. Step 3 will handle the other four documents and the formal question set.
