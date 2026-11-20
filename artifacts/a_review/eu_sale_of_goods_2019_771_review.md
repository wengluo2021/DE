# Sale of Goods Source-Text Cross-Check Review

Review method: AI-assisted source-text review. Date: 2026-11-19.

This review compares the local original HTML with the cleaned body and does not rely on the success status printed by the cleaning script. It uses Python `html.parser` and BeautifulSoup to independently count the main article nodes in `#document1`, then slices the body back using the Python ranges `[start, end)` from the cleaned JSON. No browser was used for a visual page check.

## Inputs and Artifacts

| File | SHA-256 | Bytes |
| --- | --- | --- |
| `data/raw/Sale of Goods.html` | `4869ed74958ae7cc50897e502272cc103502bffd1722f4ed07ca1f7188bb16ac` | 489604 |
| `data/processed/eu_sale_of_goods_2019_771.txt` | `d3076ba5236d6e7aad6ba30ae8b8d4b17af14fa148f7abc42cadd96764498ad4` | 89977 |
| `data/processed/eu_sale_of_goods_2019_771.json` | `ec42ea4dbad2a165bfd409f50c21fc10620ef4ca9b17d8028e5c1885570b4d6c` | 343414 |
| `data/sources.json` | `ae872164524255ec12406c4bf15c78c6ac372ac1c024e6b39c9c0b25aaf1e6e8` | 15284 |

The body is 89878 Python characters, contains only LF, and the file ends with a single newline.

## Main Articles and DOM

The `div.eli-subdivision` main article nodes in `#document1` outside the annexes are `art_1` through `art_27`, 27 in total. There are no `cpt_` chapter nodes. All 27 nodes are direct children of `div#enc_1`, in the same order as `articles` in the JSON. Each `chapter_id` is `null`, and `chapters` is empty.

Cells such as `Article 1` and `Article 13` in the annex comparison table remain in the table rows. The `Article 15` cross-reference in the body of Article 13 did not generate a new main article. The quoted items `‘3.` and `‘7.` in the replacement text of Article 22 remain inside Article 22.

## Spot Checks

| Location | Range | Sliced Result |
| --- | --- | --- |
| Article 1 | `[57289, 57797)` | `Article 1` / `Subject matter and purpose` |
| Article 14 | `[76119, 77308)` | `Article 14` / `Repair or replacement of the goods` |
| Article 27 | `[86022, 86093)` | `Article 27` / `Addressees`, body is `This Directive is addressed to the Member States.` |
| List | `[76214, 76233)` | `(a) free of charge;`, located within Article 14 |
| Footnote | `[86219, 86250)` | `(1) OJ C 264, 20.7.2016, p. 57.` |
| Footnote reference | `[580, 659)` | `Having regard to the opinion of the European Economic and Social Committee (1),` |

The `referenced_by` of footnote `eu_sale_of_goods_2019_771:footnote:act:1` points to this recital block. The recitals have 72 items, (1) through (72), numbered consecutively. The body has 10 footnotes; there are no footnotes in the annexes.

## Deadlines, Exceptions, and Limitations

- Article 10 `[69717, 72066)` provides that the seller is liable for a lack of conformity that exists at the time of delivery and appears within two years thereafter: `within two years of that time`.
- The same article allows a shorter liability or limitation period to be agreed for second-hand goods, but `shall not be less than one year`. This phrase starts at character 72034 and remains within Article 10 `[69717, 72066)`.
- Article 13(3) allows the seller to refuse restoration of conformity where repair and replacement are impossible or disproportionate. The sentence starts at character 74245 and falls within Article 13 `[73422, 76117)`.
- Article 24 requires transposition by 2021 7 1, with the measures applying from 2022 1 1, and this Directive does not apply to contracts concluded before that date. The latter sentence is located within Article 24 `[84215, 84951)`.
- Article 26 provides that the Directive enters into force on the 20 day after publication, and also states that Article 22 applies from 2022 1 1. The entry-into-force date and the application date are therefore kept separate.

## Full-Text Coverage

After folding whitespace in the DOM text of the 27 main articles, they were compared with the corresponding cleaned articles. 25 match exactly. The differences in Articles 22 and 26 come from the comparator inserting spaces on both sides of tags:

- The source of Article 22 is `(<a ...>OJ L 136, 22.5.2019, p. 28</a>)`, and the cleaned result is `(OJ L 136, 22.5.2019, p. 28)`.
- The source of Article 26 is `Union</span>.`, and the cleaned result is `Union.`.

These two places were checked against the HTML text nodes, and no characters were deleted. The annex begins with `ANNEX` and `CORRELATION TABLE`, and the first comparison row is `Article 1(1) | Article 1`. The HTML heading is `ANNEX`, not `ANNEX I`; the structure ID uses the HTML id `anx_1`, and the label remains `ANNEX`.

The EUR-Lex document information area contains `OJ L 136, 22.5.2019, pp. 28–50` and procedure number `PE/27/2019/REV/1`. They are outside `#document1` and do not enter the cleaned body text. The body header contains only `L 136/28`, and internal body references give the starting page `p. 28`.

## Duplicate handling

After the final source record was written, `process_documents.py --document-id eu_sale_of_goods_2019_771` was run twice in succession. The byte hashes of the txt and JSON from both runs are the values in the table above.

## Issues Not Covered in This File

This review did not open a browser to check the layout. The subsequent amendments to 2024/1799 and the two consolidated texts are recorded only as source links and did not enter this cleaned body text.
