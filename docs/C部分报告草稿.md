# C Section Experiment Results and Implementation Report

2026-11-20. Real 30 questions × 4 groups, 120 items in total, completed, with all scoring fields complete and 0 technical errors. **The scoring method uses mixed sources: 21 answers were specifically human-confirmed, and 99 were scored with Codex AI assistance under explicit C authorization; this is not described as all purely human verification, nor as an independent human gold standard.** The latest scoring database has passed network-disabled Linux recovery, restart, and export-consistency verification; the delivery package and SHA are in the separate final manifest, and the original unscored baseline is retained.

## Project and what C is responsible for

This project compares two regulation chunking methods and two sizes. The system first retrieves given regulation snippets, then has the LLM answer based on the snippets, and retains sentence-level citations for checking. It did not retrain an LLM, nor send standard answers to the generation model.

A is responsible for freezing the five official regulations, article structure, and 30 standard questions; B is responsible for chunking, BGE-M3, and Chroma retrieval; C is responsible for the LLM client, cited Q&A, source/location verification, session and evidence persistence, background tasks, four-page integration, evaluation/scoring/export, and integrated delivery. Ordinary Q&A and experiments share the backend pipeline.

## Frozen settings and comparability

Five EUR-Lex English original published versions, 121 main articles, 391777 characters; 24 answerable questions, 6 refusal questions, 42 standard evidence passages. The four groups are F400/S400/F800/S800, with 400/800 counted by characters; the structural method prioritizes chapters/articles and splits overlong text by sentence segments, but may still hard-cut. Top5, cosine metric, prompts, and generation parameters are identical across the four groups.

BGE-M3 revision `5617a9f61b028005a4858fdac845db406aefb181`, 1024 dimensions, CPU; generation model `CS5351/DeepSeek-V4-Flash`, temperature=0. Original run_id=`eval-20ac108503c44829a96ecca386d4b9de`, experiment fingerprint `cf8e68e0c8a71de07c8917f96bb8304843f64bbfb8e4b4bbbbfb2b192698047a`. Only this one formal 120-item run was done; no reruns or changes to questions/parameters were made to improve scores.

## Results: under this mixed-source scoring basis

| Condition | correct/24 | partial | wrong | of which incorrect refusals | refusal correct/6 | citation support/claims |
| --- | --- | --- | --- | --- | --- | --- |
| F400 | 6/24（25.00%） | 11 | 7 | 5 | 6/6（100.00%） | 27/36（75.00%） |
| S400 | 9/24（37.50%） | 9 | 6 | 6 | 6/6（100.00%） | 33/35（94.29%） |
| F800 | 10/24（41.67%） | 7 | 7 | 6 | 6/6（100.00%） | 42/45（93.33%） |
| S800 | 13/24（54.17%） | 8 | 3 | 3 | 6/6（100.00%） | 50/50（100.00%） |

Answerable questions total 38 correct, 35 partial, 23 wrong; 20 wrong cases are incorrect refusals of answerable questions. 6 should-refuse questions were correctly refused in all four groups, but this does not offset incorrect refusals of answerable questions. Of all 166 claims, 152 supported, 14 unsupported; none pending, no claims without citations. The citation denominator is the actual number of output claims, which differs by group and excludes refusal outputs with no claims.

| Condition | Chunks | Hit@1 any | Hit@1 all | Hit@5 any | Hit@5 all |
| --- | --- | --- | --- | --- | --- |
| F400 | 982 | 5/24 | 1/24 | 9/24 | 4/24 |
| S400 | 1415 | 7/24 | 4/24 | 14/24 | 6/24 |
| F800 | 493 | 10/24 | 4/24 | 17/24 | 10/24 |
| S800 | 625 | 14/24 | 8/24 | 21/24 | 13/24 |

Hit strictly requires the union of character intervals in the same document to fully cover the standard evidence; any means at least one passage, all means all, with a fixed denominator of 24, including frozen characters such as numbering. It is a different metric from whether the claim semantics are supported; numbering was not removed or evidence relabeled to boost scores.

## What can be concluded

On this batch of frozen questions and this one generation run, S800 has the highest number of complete answers 13/24 and Hit@5-all 13/24. S400 has 3 more questions reaching correct than F400, and 0 in the reverse direction; S800 has 4 more questions reaching correct than F800, and 1 in the reverse direction. This only describes paired results on the same questions and does not claim statistical significance or that it holds for all legal Q&A.

S800 citation support is 50/50, while overall answers are only 13/24: sentences can each be grounded yet still miss required rules, and incorrect refusals produce no scorable factual claims. F400 citation 27/36 reflects some key conditions being truncated at fixed-window boundaries. Larger/more structurally complete chunks improved coverage in this batch but did not eliminate generation omissions or institutional mixing.

## Failure and disputed cases

- Question 2: all four groups missed the refund deferral condition; although F800 additionally answered the delivery price-difference exception, it is still partial; all citations for claims actually written are supported. This shows answer completeness and citation support are separate.
- Question 6: F800 wrongly applied the 14-day refund rule for withdrawn contracts to termination for late delivery, judged wrong; F400's "This rule" reference was read strictly by actual human choice, wrong, and the source and original AI's differing opinion are retained.
- Question 11: the first three groups refused, while S800 found the complete price-reduction rule and answered. Question 12/13/19: all four groups incorrectly refused, showing the evidence supply and generation pipeline still have shortcomings; the 100% on refusal questions cannot be reported alone.
- Question 20: F400 writes can as cannot, reversing the core direction; a valid source span does not guarantee semantic correctness.
- In question 4, the supplementary claim for F400/F800 omits the citation's precondition, so the citation is judged unsupported; in question 16, the end of F800 lacks only the modification word ending, and the actual claimed alternative right is already shown, so it is supported under the adopted standard. The full original text, the actually bound span, and the reasoning are all retained.

## Scoring sources and limitations

The user first confirmed the first 5 questions and question 6 F400 item by item, then explicitly authorized routine questions to skip further confirmation and special disputes to be asked separately. Human confirmation covers 21 answer grades and 45 claims; the AI authorization covers 75 answer grades, 24 refusal judgments, and 121 claims. The database reviewer identifies C and Codex AI respectively, and 124 modification history entries are retained. Method authorization is not proof that the remaining questions were read by a human one by one.

Answers are graded on A's necessary-fact completeness; some references include incidental conditions not separately asked in the question, and applying the same strict standard would increase partial grades. Explicit facts in the question are allowed as context, without supplementing evidence from uncited legal rules; identifiable word endings are handled separately from missing full legal conditions/objects. There is no second independent reviewer, and both AI and human-assisted judgments may be wrong, so these figures are not called a purely human independent quality rate.

Backend `review_complete=true` and `formal_results=true` indicate that scoring fields, formal configuration, and run conditions are complete; they are not proof that "everything has been manually reviewed." For the method and the exact authorization wording, see [M6 scoring method and authorization record ](M6评分方式与授权记录.md); per-question sources are in `artifacts/c/m6-final-scored/review-provenance.json`.

## Engineering verification and cost

Completed: 401 Windows items, 400 Linux items passed / 1 Windows-only skip, the four formal indexes, real school Q&A/save-restart, and cross-platform recovery of unscored experiments. Business code, dependencies, prompts, and frozen inputs were not changed by scoring, so these engineering checks were not repeated. This time, additionally verified read-only HTTP with an empty Key in a normal process; the latest scoring database's consistency backup was restored on a new Linux volume with network disabled/no Key, and JSON/CSV were byte-identical before and after restart, with 124 history entries and human/AI source labels retained. The 68 runtime source/config files in the image are identical to the current source, so unchanged business code does not need to be rebuilt.

The formal 120 items involved 121 actual model attempts, 186241 known tokens, and 1 failures with no usage followed by successful bounded retries, with the actual model consistent. Including earlier smoke tests, the cumulative known total is 191672 tokens, with the amount unknown. All scoring, exports, backups, and this stage's summary added 0 school API calls; there was no new generation, model download, or index rebuild.

The final JSON/CSV, per-question sources, all stage checks, and the SQLite backup hash are in `artifacts/c/m6-final-scored/`. The original unscored JSON/CSV/reading materials were not overwritten; the source code is saved only locally in answer-eval, not pushed, not written to main, and no team message was sent.
