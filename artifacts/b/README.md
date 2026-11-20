# B Verification Record

This directory holds reviewable test and model run records. `.pytest/` is a temporary index directory for independent testing and is not committed.
Model weights are in `models/embedding/`; the four index sets for the synthetic corpus are in `data/b-fixtures/mock|real/`, all rebuilt by script.
These records use synthetic text and cannot serve as evaluation results for the 30 formal questions.


## Current English Version

Active corpus `fixture-en-v2`, rules `structure-offset-v2`. `tests.xml` is the 78-item pass record for the independent verification environment; `real-smoke.json` and `clean-real-smoke.json` are the English real-model verifications for the project environment and the independent environment respectively, each passing 12 retrievals, with the source coordinates of each returned segment checked individually. Both use the same index version.

`frontend-smoke.json` is the browser verification record; `debug-real-english.png` and `debug-mobile-english.png` are desktop/mobile screenshots of the English body text. `archive/zh-v1/` preserves the Chinese corpus and old results from before replacement; the versions and chunk counts in these historical records do not represent the current active corpus.
