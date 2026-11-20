# Unfair Commercial Practices source comparison review

Review method: AI-assisted source-text review. Date: 2026-11-19.

This review reads the original HTML directly, uses `html.parser` to count the chapter containers, section containers, main articles and recital nodes in `#document1`, and then slices the body text back using the Python ranges `[start, end)` from the cleaned JSON. No browser was opened for a visual page check.

## Inputs and Artifacts

| File | SHA-256 | Bytes |
| --- | --- | --- |
| `data/raw/Unfair Commercial Practices.html` | `0d678d1bbd988c59b40ff6363f3d9b8370c34da7b3744395eb7147364a19c1cc` | 490851 |
| `data/processed/eu_unfair_practices_2005_29.txt` | `7bc191bd5b55af42a179d95d98b1e7c2aa603509941065605b4ba175eb54f10b` | 59599 |
| `data/processed/eu_unfair_practices_2005_29.json` | `1f21061ca7b3f46f8cd2a949c722b86dbcdac0864c95281291cf037fad40c200` | 270853 |
| `data/sources.json` | `d41adeeff519e4307edd9529bfdeb5df4123e8b73b57c9b8abf17a689fd11e8d` | 30266 |

The body is 59467 Python characters, contains only LF, and the file ends with a single newline.

## Chapters, sections and main articles

Under the body container `enc_1` of `#document1` there are four chapter containers: `cpt_1`, `cpt_2`, `cpt_3`, `cpt_4`. Their heading nodes are `cpt_1.tit_1`, `cpt_2.tit_1`, `cpt_3.tit_1`, `cpt_4.tit_1`, with class name `eli-title`; they are not new chapters.

Chapter II contains two section containers: `cpt_2.sct_1`, `cpt_2.sct_2`. Their heading nodes are `cpt_2.sct_1.tit_1`, `cpt_2.sct_2.tit_1`, and these are likewise not counted as sections again.

The main articles are `art_1` to `art_21`, 21 `div.eli-subdivision` in total. The recital nodes are `rct_1` to `rct_25`, 25 in total. The annex containers are `anx_I`, `anx_II`.

Chapter II contains both Article 5, which belongs to it directly, and Articles 6 to 9 within the two sections. Articles 1 to 4 belong to Chapter I, Article 10 belongs to Chapter III, and Articles 11 to 21 belong to Chapter IV. These articles have no sections. The `Article` numbers in the annexes and in the amending quotations did not become main articles.

## Spot Checks

| Location | Range | Sliced Result |
| --- | --- | --- |
| Chapter I | `[20069, 26112)` | `CHAPTER 1` / `GENERAL PROVISIONS` |
| Article 1 | `[20099, 20420)` | `Article 1` / `Purpose`, directly under Chapter I |
| Chapter II | `[26114, 34413)` | `CHAPTER 2` / `UNFAIR COMMERCIAL PRACTICES` |
| Article 5 | `[26153, 27640)` | `Article 5` / `Prohibition of unfair commercial practices`, directly under Chapter II |
| Chapter 2, Section 1 | `[27642, 32991)` | `Section 1` / `Misleading commercial practices` |
| Article 6 | `[27685, 30366)` | `Article 6` / `Misleading actions`, under Chapter 2, Section 1 |
| Chapter 2, Section 2 | `[32993, 34413)` | `Section 2` / `Aggressive commercial practices` |
| Article 8 | `[33036, 33558)` | `Article 8` / `Aggressive commercial practices`, under Chapter 2, Section 2 |
| Article 11 | `[34994, 38641)` | `Article 11` / `Enforcement` |
| Article 21 | `[47654, 47725)` | `Article 21` / `Addressees` |
| List | `[20480, 20658)` | `(a) ‘consumer’ means any natural person who, in commercial practices covered by this Directive, is acting for purposes which are outside his trade, business, craft or profession;` |
| Footnote | `[42084, 42119)` | `(*1) OJ L 149, 11.6.2005, p. 22.’;"` |
| Start of Annex I | Start of annex text | `ANNEX I` / `COMMERCIAL PRACTICES WHICH ARE IN ALL CIRCUMSTANCES CONSIDERED UNFAIR` |

Article 5 ends before Section 1; between them are blank lines within the chapter. The ranges of Article 6 and Article 8 fall within the two sections respectively. The section IDs carry their parent chapter: `eu_unfair_practices_2005_29:chapter:2:section:1` and `section:2`.

The `referenced_by` of footnote `act:*1` points to the list item in Article 14 that cites `(*1)`. The quotation mark and semicolon at the end of the footnote text come from the HTML footnote paragraph, which contains the closing punctuation of the quoted amended article.

## Conditions, exceptions, negations and limitations

- Article 5(1) states `Unfair commercial practices shall be prohibited.`
- Article 5 then provides that a commercial practice is unfair only when it simultaneously contravenes the requirements of professional diligence and materially distorts the economic behaviour of the average consumer.
- Article 6 provides that false information, or information whose overall presentation is likely to deceive the average consumer, even if factually correct, constitutes a misleading practice if it causes the consumer to take a transactional decision that they would not have taken otherwise. This sentence is in Article 6 `[27685, 30366)`.
- Article 8 provides that a commercial practice is aggressive if, through harassment, coercion or undue influence, it significantly impairs or is likely to significantly impair the consumer's freedom of choice and thereby causes a transactional decision. This sentence is in Article 8 `[33036, 33558)`.
- Article 3(10) provides that this Directive does not apply to Member State provisions on the certification and marking of the fineness of precious metals.
- Article 4 provides that Member States may not restrict the freedom to provide services or the free movement of goods on grounds relating to matters coordinated by this Directive.
- Article 19 retains `by 12 June 2007` and `by 12 December 2007`. The former is the transposition deadline, the latter the date of application of the measures.
- Article 20 provides only that it enters into force on the day following its publication in the Official Journal.
- Annex I lists commercial practices that are in all circumstances considered unfair. `Article 3` and `Articles 4 and 5` in Annex II are cross-reference entries to other enactments, not main articles of this document.

## Full-text coverage and heading order

The cleaned body text sets out, in HTML order, the four chapter headings, the two section headings of Chapter II, the main articles of 21, the recitals, the sign-off, the footnotes and the two annexes. `‘Article 1` and `‘Article 3a` in the amending quotation of Article 14, as well as the two occurrences of `‘Article 9`, are retained as quotation headings.

One quotation in Article 15 is written as `11 May 2005of` in the original HTML and remains `2005of` after cleaning. This is a missing space in the snapshot source text, not a character deleted during cleaning.

The body text ends at the last footnote of Annex II.

## Duplicate Handling and Anomaly Detection

After the final source record was written, cleaning was run twice consecutively; the txt and JSON byte hashes are both the values in the table above.

Three failure checks were run on temporary copies; the official file was not rewritten:

- After deleting Article 21, the exit code was 1, the main articles became 1–20, and the expected value was 1–21.
- After changing `section_id` of Article 6 to the nonexistent `chapter:2:section:9`, the exit code was 1.
- After extending the end position of Section 1 beyond Chapter II, the exit code was 1, because the section range exceeded its parent chapter.

## Issues Not Covered in This File

This review did not perform a browser visual check. The page status states that this act has been amended and links to consolidated texts `02005L0029-20260927`, `02005L0029-20220528` and `02005L0029-20050612`. None of these are the body text saved in this snapshot.
