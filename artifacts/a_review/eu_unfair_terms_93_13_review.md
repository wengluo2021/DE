# Unfair Terms source comparison review

Review method: AI-assisted source-text review. Date: 2026-11-19.

This review reads `data/raw/Unfair Terms.html` directly, uses `html.parser` to count the headings, recital paragraphs, `p.ti-art`, sign-off, footnotes and annexes in `#document1`, and then slices the body text back using the Python ranges `[start, end)` from the cleaned JSON. No browser was opened for a visual page check.

## Inputs and Artifacts

| File | SHA-256 | Bytes |
| --- | --- | --- |
| `data/raw/Unfair Terms.html` | `6c700ae54d53f3dc3ece8d226d18471ac905eff42a7cb4d4874e2e56acaff707` | 312379 |
| `data/processed/eu_unfair_terms_93_13.txt` | `bf518901d6a71d5753ec99ed0b5b13025f5bf136782594a0dbaf8263e376a401` | 20868 |
| `data/processed/eu_unfair_terms_93_13.json` | `c4d387298a543eb545a91cec522662b77473a6c79c7ee27c450818f17df29893` | 86075 |
| `data/sources.json` | `6a7a20ff4c9ea87bb940a066e8fdf08b285458fc9208b6b231dcf8e99fa5bad9` | 37980 |

The body text is 20839 Python characters, contains only LF, and the file ends with a single newline. The last annex range ends at 20838; the trailing newline at the end of the file is not counted in the structural range.

## Legacy structure count

The body text is inside the inner container `#document1`, as a contiguous run of paragraphs and layout tables, with no `art_` containers and no Chapter or Section containers.

| Structure | Local HTML count |
| --- | --- |
| Regulation title | 3 `p.doc-ti`: `COUNCIL DIRECTIVE 93/13/EEC`, `of 5 April 1993`, `on unfair terms in consumer contracts` |
| Preamble | 24 `p.normal` beginning with Whereas, with no official numbering; also contains the enacting formula, cited provisions, and `HAS ADOPTED THIS DIRECTIVE:` |
| Main articles | 11 `p.ti-art`, text is Article 1 through Article 11 |
| Signature block | `div.final`, containing `Done at Luxembourg, 5 April 1993.` and `p.signatory` |
| Footnotes | 6 `p.note`, of which 4 have `ntr` anchors; the continuation lines of (2) and (4) have no new anchor |
| Annex | 1 `div#L_1993095EN.01003301`, heading `ANNEX`, containing `ti-grseq-1` |

The header table contains `hd-date`, `hd-lg`, `hd-ti`, `hd-oj`, corresponding to `21.4.1993`, `EN`, `Official Journal of the European Communities`, `L 95/29`. This text did not enter the cleaned body. The `OJ No` references in the footnotes are still retained.

The main article HTML ids are, in order, `d1e196-29-1`, `d1e210-29-1`, `d1e245-29-1`, `d1e268-29-1`, `d1e282-29-1`, `d1e288-29-1`, `d1e302-29-1`, `d1e321-29-1`, `d1e327-29-1`, `d1e333-29-1`, `d1e360-29-1`. "defined in Article 3" in Article 2 and "Without prejudice to Article 7" in Article 4 are in body paragraphs or lists, not `p.ti-art`, and did not become new main articles. The annex heading `TERMS REFERRED TO IN ARTICLE 3 (3)` remains in the annex.

## Spot Checks

| Location | Range | Sliced Result |
| --- | --- | --- |
| Preamble item 1 | `[414, 675)` | Begins with `Whereas it is necessary to adopt measures`; `number` and `official_number` are both null, `ordinal` is `1` |
| Preamble item 24 | `[8592, 8797)` | `Whereas the courts or administrative authorities...unfair terms in consumer contracts,` |
| Article 1 | `[8827, 9348)` | `Article 1`, purpose clause and paragraph 2 exclusion provision; `chapter_id`, `section_id`, `heading` are all null |
| Article 2 list | `[9396, 9464)` | `(a) ‘unfair terms’ means the contractual terms defined in Article 3;` |
| Article 6 | `[12066, 12727)` | Contains `not be binding on the consumer`, and that consumers do not lose protection by choosing the law of a non-member country |
| Article 11 | `[14865, 14925)` | Only `Article 11` and `This Directive is addressed to the Member States.` |
| Signature block | `[14927, 15009)` | `Done at Luxembourg, 5 April 1993.`, `For the Council`, `The President`, `N. HELVEG PETERSEN` |
| Footnote (2) | `[15046, 15112)` | `(2) OJ No C 326, 16. 12. 1991, p. 108 and OJ No C 21, 25. 1. 1993.`, quoted block is preamble block 4 |
| Annex | `[15220, 20838)` | Begins with `ANNEX`, not the title of the whole regulation |
| Annex exception heading | `[19072, 19114)` | `2. Scope of subparagraphs (g), (j) and (1)` |
| Annex exception | `[20240, 20291)` | `(c) Subparagraphs (g), (j) and (1) do not apply to:` |

Article 11 ends at 14925, the signature block begins at 14927, footnote (1) begins at 15011, and the annex begins at 15220. The blank lines in between belong to neither range.

## Conditions, negations, and source wording

The following wording is preserved as in the HTML source:

- Article 4 paragraph 2 uses `shall relate neither`, and retains `goods supplies`, `plain intelligible language`.
- Article 5 requires written terms to use `plain, intelligible language`, and also states the interpretation rule `shall not apply` in the Article 7 paragraph 2 procedure.
- Article 6 states that an unfair term `not be binding on the consumer`, and the contract continues to bind the parties if it can survive without that term.
- The transposition deadline in Article 10 is `no later than 31 December 1994`, and the measures apply from `contracts concluded after 31 December 1994`.
- The annex retains the lettered list, `without hindrance`, and the `(1)` in the heading and exception. This `(1)` appears to be a typesetting or recognition issue with `(l)`; it was not rewritten based on common sense in this round.
- Footnote dates retain the spaces in the source, e.g. `24. 3. 1992`. The HTML splits footnotes (2) and (4) into two `p.note`; after cleaning, the continuation lines are merged into the corresponding anchor, and the two OJ references still belong to the same footnote.

## Coverage and repeated runs

The title, preamble, 11 articles, signature block, 4 footnotes, and annex all enter the same cleaned body. `result=ok` was validated, and the `clean_text[start:end] == item.text` of each structure was checked. After cleaning twice in a row, the txt and JSON hashes are unchanged.

The anomaly checks on temporary copies all exited with code 1; the official snapshot and outputs were not modified:

- Delete Article 6: the main articles become 1–5, 7–11.
- Delete all main articles: the main articles are empty.
- Change preamble block 3 to a nonexistent footnote reference `ntr-does-not-exist`.
- Change the Article 1 range to `[8827, 100521)`, exceeding 20839 characters.

## Rule description correction

The structure JSON hash `9e57f3f501ec37583d36d273be66aa2ca5cf5d573696ab39ab2ac1523e32e22f` before the correction is a historical value. After regeneration, the only JSON differences are `cleaning_rules.main_articles` and `cleaning_rules.footnotes`. The body hash is still `bf518901d6a71d5753ec99ed0b5b13025f5bf136782594a0dbaf8263e376a401`. The source, articles, body blocks, IDs, ranges, statistics, and footnote references are unchanged.

The legacy description now states: main articles start at `p.ti-art` and end at the next main article, signature block, footnote, or annex boundary; a `p.note` with a `ntr` anchor starts a footnote, and continuation lines without a new anchor are merged into the previous one. The 6 `p.note` in this file correspond to 4 footnotes.

## Not included in this review

No browser visual check was performed. `--all` was not run, no official `data/corpus_manifest.json` was generated, no 30 official questions were written, and no vector store was built.
