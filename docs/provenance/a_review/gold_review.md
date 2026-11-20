# Review of the 30 official questions

Record date: 2026-11-19. The questions, reference answers, and refusal reasons were drafted by AI against the frozen body. All evidence quotes were extracted programmatically from the full text read from `formal_loader` according to structural ranges, not copied by hand. Human review and browser visual check were confirmed as passed by lead A on 2026-11-19, with no issues found. The existing AI drafting and programmatic extraction process is retained. The initial AI review in this file did not open a browser and did not read the four sets of official retrieval results; the browser conclusion is subject to the subsequent human confirmation.

## Version

| Item | Value |
| --- | --- |
| corpus_version | `794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795` |
| gold_version | `9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d` |
| gold.jsonl SHA-256 | Same as gold_version |
| Number of questions | 30, of which answerable 24, refused 6 |
| Question type | single_article 13, multi_evidence 11, unanswerable 6 |

`gold_version` follows the convention in the development documentation: it is the SHA-256 of the final file bytes of `data/eval/gold.jsonl`. The file uses UTF-8 and LF, and retains the trailing newline. The jsonl contains no question set version or timestamp. Regenerating once consecutively leaves the hash unchanged.

Load confirmation: five unique documents, 121 main articles, and the formal package manifest matches the version of `data/corpus_manifest.json`. If the version does not match, the script reports an error and does not rebuild the corpus.

## Coverage

| Document | Answerable questions | Evidence segments |
| --- | ---: | ---: |
| eu_consumer_rights_2011_83 | 6 | 11 |
| eu_sale_of_goods_2019_771 | 5 | 9 |
| eu_digital_content_2019_770 | 5 | 10 |
| eu_unfair_practices_2005_29 | 4 | 7 |
| eu_unfair_terms_93_13 | 4 | 5 |

For each answerable question, `key_facts` equals the corresponding `evidence.quote` item by item. Therefore the key facts and the evidence are the same frozen passage of source text. The reference answers state only the conditions and exceptions in these passages; they do not present the original published version as the law currently in force, nor do they supplement it with external materials.

## Answerable questions

| case_id | Question type | Topic | Evidence location | Review conclusion |
| --- | --- | --- | --- | --- |
| gold-crd-delivery-time | single_article | Delivery period when not agreed | 2011/83 Article 18(1) `[81983,82251)` | Supports "without undue delay and no later than 30 days after the conclusion of the contract" |
| gold-crd-withdrawal-refund | multi_evidence | Refund after withdrawal and the exceptions in the same article | 2011/83 Article 13(1) to (3) `[73780,74083)`, `[74390,74631)`, `[74632,74908)` | Paragraph 1 supports reimbursement of payments made and applicable delivery costs within 14 days; paragraph 2 excludes additional costs where the consumer chose a more expensive delivery option; paragraph 3 permits withholding reimbursement in sales contracts until the goods are recovered or proof of return is received |
| gold-crd-payment-fee-cap | single_article | Fees for payment methods | 2011/83 Article 19 `[83631,83816)` | Supports that fees must not exceed the cost borne by the trader |
| gold-crd-withdrawal-information-omission | single_article | Failure to inform of the right of withdrawal | 2011/83 Article 10(1) `[71568,71843)` | Supports that the withdrawal period expires 12 months after the end of the initial period |
| gold-crd-withdrawal-digital-content | multi_evidence | Exception to withdrawal for digital content | 2011/83 Article 9(1) `[69452,69734)`; Article 16 (m) `[81214,81431)` | Only the two passages together show that the 14-day right is subject to the exception in Article 16 |
| gold-crd-late-delivery-termination | multi_evidence | Termination and refund after late delivery | 2011/83 Article 18 `[82252,82543)`, `[82544,82681)`, `[83301,83420)` | The three passages respectively support an additional period, termination if delivery still does not occur, and immediate reimbursement of all payments made after termination |
| gold-sgd-two-year-liability | multi_evidence | Liability period for lack of conformity | 2019/771 Article 10(1), (3), (6) `[69752,70036)`, `[70749,70856)`, `[71762,72066)` | Supports two-year liability and that Member States may provide for a longer period; for second-hand goods the parties may agree a shorter period, but not less than one year |
| gold-sgd-one-year-presumption | single_article | Presumption as to when the lack of conformity existed | 2019/771 Article 11(1) `[72095,72484)` | Supports the one-year presumption and its two exceptions |
| gold-sgd-repair-or-replacement | multi_evidence | Repair or replacement | 2019/771 Article 13(2) `[73709,74013)`; Article 14(1) `[76165,76529)` | Supports the consumer's choice, as well as free of charge, within a reasonable time and without significant inconvenience |
| gold-sgd-minor-lack-no-termination | single_article | Minor lack of conformity does not permit termination | 2019/771 Article 13(5) `[75446,75649)` | Supports that termination is not permitted, and that the seller bears the burden of proving the lack is minor |
| gold-sgd-price-reduction | single_article | Extent of price reduction | 2019/771 Article 15 `[77337,77531)` | Supports reduction in proportion to the decrease in value |
| gold-dcd-supply-without-delay | single_article | Time of supply of digital content | 2019/770 Article 5(1) `[87988,88233)` | Supports supply without undue delay after the conclusion of the contract where not otherwise agreed |
| gold-dcd-burden-of-supply | single_article | Burden of proof as to whether supply occurred | 2019/770 Article 12(1) `[96415,96565)` | Supports that the burden of proof lies with the trader |
| gold-dcd-conformity-remedies | multi_evidence | Remedies for digital content and minor defects | 2019/770 Article 14(1), (6) `[99561,99830)`, `[102316,102616)` | Supports the three remedies, and that in paid contracts termination is available only for a lack of conformity that is not minor |
| gold-dcd-reimbursement-time | single_article | Time limit for refunds for digital content | 2019/770 Article 18(1) `[106220,106613)` | Supports without undue delay and no later than 14 days after being informed |
| gold-dcd-modification-conditions | multi_evidence | Conditions for modification in the case of continuous supply | 2019/770 Article 19(1) (a) to (d) `[107059,108042)` split into five passages | The five passages together cover all four conditions for a permitted modification |
| gold-ucpd-two-part-unfairness-test | single_article | General test for unfair commercial practices | 2005/29 Article 5(2) (a), (b) and the intervening and `[26303,26665)` | The same passage contains the two elements and the connecting word and |
| gold-ucpd-aggressive-practice | multi_evidence | Aggressive commercial practice | 2005/29 Article 8 `[33078,33295)`, `[33296,33558)` | The original sentence is longer than 399 characters, so the two conditions of means and result are kept as two passages within the sentence |
| gold-ucpd-invitation-price-information | multi_evidence | Price information in an invitation to purchase | 2005/29 Article 7(4) introductory wording `[31679,31822)` and (c) `[32119,32501)` | The two passages together show that price information is material information in an invitation to purchase |
| gold-ucpd-pyramid-scheme | multi_evidence | Pyramid promotional scheme | 2005/29 Article 5(5) `[27416,27640)`; Annex I point 14 `[51682,51969)` | The Annex describes the practice, and Article 5(5) states that the practices in the Annex are unfair in all circumstances |
| gold-utd-unfair-term-test | multi_evidence | Definition of an unfair term | 93/13 Article 3(1), (2) `[9854,10128)`, `[10129,10383)` | Respectively support the findings of a significant imbalance and of not being individually negotiated |
| gold-utd-plain-language | single_article | Plain language and favourable interpretation | 93/13 Article 5 `[11684,12064)` | Supports plain language, interpretation in favour of the consumer, and that this interpretation rule does not apply to the procedure under Article 7(2) |
| gold-utd-unfair-term-not-binding | single_article | Unfair terms do not bind the consumer | 93/13 Article 6(1) `[12076,12418)` | Supports that the term does not bind the consumer under national law, and that the contract continues to be binding where it can continue in existence |
| gold-utd-negotiation-burden | single_article | Burden of proof as to individual negotiation | 93/13 Article 3 `[10666,10819)` | Supports that the burden of proving that standard terms were individually negotiated lies with the seller or supplier who asserts it |

## Refused questions

For the six questions, `evidence` and `key_facts` are both empty arrays. The scope of the assessment is the five full texts, including preambles, annexes and footnotes. Keyword searches were used only to locate passages, after which the relevant provisions were read.

| case_id | Missing information | Why other provisions cannot answer it either |
| --- | --- | --- |
| gold-refuse-air-cancellation-amount | Fixed euro compensation amount for flight cancellation by an air carrier | The full texts contain no air carrier and no amount of compensation for flight cancellation. 2011/83 Article 3 excludes passenger transport from its scope, retaining only Article 8(2), Article 19 and Article 22, and these three do not set an amount for flight cancellation. The preamble mentions the compensation regime for the service part of mixed contracts, but gives no amount. |
| gold-refuse-standard-vat-rate | Percentage of VAT that must be added | The full texts contain no VAT rate. An invitation to purchase requires the price including taxes to be shown, but does not give the rate. |
| gold-refuse-refund-interest-rate | Statutory annual interest rate to be added to refunds under 2011/83 Article 13 | Article 13 sets out the scope of the refund, the 14 days and the prohibition on charging fees, but no interest rate. 2019/770 Article 18 likewise provides only for 14 days and no fees. Annex 93/13 discusses interest rate terms in financial services contracts and does not set a statutory rate for refunds under Article 13. |
| gold-refuse-german-fine | Maximum euro fine that Germany must impose for using an unfair term | The directives only require Member States to lay down effective, proportionate and dissuasive penalties or means of enforcement; they do not name Germany and do not set a euro ceiling. |
| gold-refuse-lawsuit-deadline | Number of days within which a lawsuit must be brought after the seller refuses to repair | 2019/771 Article 10 sets the liability period and allows Member States to set a limitation period within which remedies may still be exercised, but does not set a deadline for bringing proceedings, a court or a number of days. |
| gold-refuse-package-insurance | Minimum insurance that a package travel organiser must hold | 2011/83 excludes package travel contracts from its scope. Annex II to 2005/29 lists it only as a sector-specific information rule and gives no insurance amount. The other three directives do not regulate this insurance either. |

## Commands and protected files

```powershell
Set-Location 'D:\gitcode\Edit\DE'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\build_gold.py'
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope eval
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' 'D:\gitcode\Edit\DE\scripts\validate_data.py' --scope corpus
& 'D:\gitcode\Edit\DE\.venv\Scripts\python.exe' -m unittest tests.test_gold_eval
```

The review comments noted that the refund answer omitted Article 13(2), (3), and that the two-year liability period question did not qualify the second-hand goods exception in Article 10(6). The original text of the same article has been added to both questions. After the correction, `gold_version` generated twice consecutively are both `9ecc1d148c00dacc354a401bdeae7dc019de871919d9ad673a53a9e491e9f07d`, `result=ok`. The formal corpus `corpus_version` is unchanged. The earlier question set version `444afb6d7fb842b1d7333a8cd9388b9d33601ca385c87638136c3d26526a1253` is the historical value before the correction. `--scope eval` is `questions=30 answerable=24 refusal=6`, `result=ok`. `--scope corpus` remains `documents=5`, `main_articles=121`, `result=ok`.

`tests/test_gold_eval.py` ran 5 items, with result `OK`. The temporary copies covered mismatched evidence slices, duplicate Article numbers in annexes being wrongly pointed to the first occurrence in the main text, refused questions carrying evidence, duplicate case_ids, version mismatch, question set hash mismatch and CRLF. The formal question set bytes were unchanged after the tests.

The source manifest, the five official HTML files, the accepted txt and JSON, the formal delivery package, the corpus manifest, the single-document sample and the three sample questions make 27 recorded hashes in total, all matching the values at the time of freezing. The existing review report was not rewritten in this round.

## Manual review conclusion and follow-up items

- Manual review and browser visual inspection were confirmed as passed by owner A on 2026-11-19, with no issues found.
- There is no vector index, real semantic retrieval, LLM answer, or four-group scoring.
- No Git write or push was performed.
