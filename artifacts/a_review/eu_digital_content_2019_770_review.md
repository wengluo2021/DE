# Digital Content and Services Source-Text Cross-Check Review

Review method: AI-assisted source-text review. Date: 2026-11-19.

This review reads the original HTML directly, uses `html.parser` to count the main articles and recital nodes in `#document1`, then slices the body back using the Python ranges `[start, end)` from the cleaned JSON. No browser was opened for a visual page check.

## Inputs and Artifacts

| File | SHA-256 | Bytes |
| --- | --- | --- |
| `data/raw/Digital Content and Services.html` | `83b8ec2ad8d5a293c278fcffc5add389425bd7c688f92bf110d4ce2b929826f2` | 520093 |
| `data/processed/eu_digital_content_2019_770.txt` | `6e251e53b94cb4e793d9cd32889a0f70b7e62d7399eacc15197f37bb132ac3bf` | 118158 |
| `data/processed/eu_digital_content_2019_770.json` | `3d7b88ac3b35365986c18970dfc24cdf6b1574f701c13c350efe7466e5e366ab` | 409690 |
| `data/sources.json` | `d9edf17d3bf6748b66cdfa20a8ae9f6b2e45091d6fa88e826d28f5c5ff890aac` | 21962 |

The body is 118079 Python characters, contains only LF, and the file ends with a single newline.

## Main Articles and DOM

The `div.eli-subdivision` main articles in `#document1` are `art_1` through `art_27`, 27 in total. There are no `cpt_` chapter sections and no `anx_` annexes. The recital nodes are `rct_1` through `rct_87`, 87 in total. The body has 23 footnotes. The cleaned result's article numbering, `chapter_id=null`, empty chapters, empty annexes, 87 recital items, and 23 footnotes match this count.

## Spot Checks

| Location | Range | Sliced Result |
| --- | --- | --- |
| Article 1 | `[78438, 79082)` | `Article 1` / `Subject matter and purpose` |
| Article 14 | `[99518, 102616)` | `Article 14` / `Remedies for lack of conformity` |
| Article 27 | `[113198, 113269)` | `Article 27` / `Addressees` |
| List | `[100102, 100206)` | `(a) the value the digital content or digital service would have if there were no lack of conformity; and` |
| Footnote | `[113395, 113426)` | `(1) OJ C 264, 20.7.2016, p. 57.` |
| Footnote reference | `[516, 595)` | `Having regard to the opinion of the European Economic and Social Committee (1),` |

Article 14 retains 7 list items. The `referenced_by` of footnote `act:1` points to the recital block above.

## Deadlines, Exceptions, and Limitations

- Article 11 `[94633, 96386)` provides that if a Member State makes only the trader liable for a lack of conformity that appears within a period after delivery, that period may not be shorter than two years after delivery. The phrase starts at character 95202.
- Article 14 allows the consumer to require restoration of conformity unless this is impossible or disproportionate. This limitation starts at character 99949 and is located within Article 14.
- Article 24(1) requires transposition by 2021 7 1, with the measures applying from 2022 1 1.
- Article 24(2) provides that the Directive applies to supplies occurring from 2022 1 1, but Articles 19 and 20 apply only to contracts concluded from that date. This sentence starts at character 112467 and is located within Article 24 `[111670, 112565)`.
- Article 26 `[113029, 113196)` provides only that it enters into force on the 20 day after publication; it does not state 2022 1 1 as a second entry into force.

## Full-Text Coverage

Of the 27 main articles, 24 match the DOM text after whitespace folding. The differences in Articles 3, 23, and 26 come from the comparator inserting spaces on both sides of tags: footnote `(21)`, the Official Journal link `(OJ L 136, 22.5.2019, p. 1)`, and `Union</span>.`. After removing these tag-boundary spaces, the three texts match. This file has no annexes, and the body ends at the last footnote.

## Duplicate Handling and Anomaly Detection

After the final source record was written, cleaning was run twice consecutively; the txt and JSON byte hashes are both the values in the table above.

After deleting Article 27 in a temporary copy, validation exited with code 1, because the main articles became 1–26. After deleting all main articles, validation exited with code 1, because the main article list was empty. The formal artifacts were not modified by these two failed checks.

## Issues Not Covered in This File

This review did not perform a browser visual check. The merged text `02019L0770-20190522` of the page links is not the body of this snapshot.
