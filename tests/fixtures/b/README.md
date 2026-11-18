# English B verification fixtures

Active corpus: `fixture-en-v2`. Chunker: `structure-offset-v2`.

These are synthetic test rules translated from the previous Chinese fixtures. They are NOT official legislation, verified translations, or the formal 30-question evaluation set. The example.org source URLs are placeholders. Each long document intentionally repeats a topic paragraph four times in each article to exercise splitting and indexing.

| Document | Frozen source | Python characters |
| --- | --- | ---: |
| API contract | raw.txt | 25 |
| Personal information | privacy_raw.txt | 4318 |
| Public transport | travel_raw.txt | 4414 |
| Library loans | library_raw.txt | 3854 |

Total: 12611 Python Unicode characters, including spaces and LF newlines. Limits of 400/800 still count characters, not English words or tokens. English translations are longer than the previous Chinese fixtures, so these results cannot be used as a controlled Chinese-versus-English quality comparison.

`document.json` and `long_documents.json` contain frozen English text, SHA-256 values and regenerated article intervals. Each raw text file is an exact UTF-8/LF snapshot, without a BOM. Never edit an offset manually without regenerating and verifying the matching source text. Changed content requires a new corpus version and rebuilt indexes.

`search_cases.json` freezes the questions and expected topic document IDs used by the real-model smoke script:

| Question | Expected top document |
| --- | --- |
| How can an individual request deletion of personal information? | privacy |
| Can a reader renew a library book when the loan period expires? | library |
| What should a bus driver do after noticing an abnormal road condition? | travel |

Each question runs under F400/S400/F800/S800: 12 retrieval checks. The first result must match the expected topic. Every returned hit must equal the exact frozen `[start,end)` source slice; article IDs and source URLs are also checked. This proves the covered retrieval behavior and traceability, not generated-answer correctness or legal accuracy. C's answer/citation support evaluation still requires A's official corpus and gold questions.

`expected_hits.json` is an exact API contract fixture with a stub score, not a semantic score target. `legacy_zh_document.json` and `legacy_zh_raw.txt` preserve the original 13-character Chinese contract as a regression test only. The active loader rejects the old `fixture-v1` version.

## Observed English results

Both the project environment and the independently installed `.venv-b-verify` passed 78 pytest cases and 12 real-model retrieval checks. Both generated the same index version:

`a8da4dd4cdd02faf4fcdee672213a458c39f6e811a45c3c3a4f8993a0b50a22f`

| Condition | Chunks | Mean characters | Maximum |
| --- | ---: | ---: | ---: |
| F400 | 34 | 370.91 | 400 |
| S400 | 47 | 268.32 | 394 |
| F800 | 18 | 700.61 | 800 |
| S800 | 31 | 406.81 | 799 |

The English overflow test uses `"law " * 9000`, producing 9002 tokens with the pinned tokenizer. The expected `MODEL_INPUT_TOO_LONG` error occurs before model inference. The warning in this intentional test is expected.

Historical Chinese artifacts are saved in `artifacts/b/archive/zh-v1/`. Current reports are `artifacts/b/tests.xml`, `real-smoke.json` and `clean-real-smoke.json`.
