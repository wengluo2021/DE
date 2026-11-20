# DERag Project Development Conventions

## Project and Tasks

- The project is located at `D:\gitcode\Edit\DE`; its goal is knowledge-base question answering with verifiable citations and chunk comparison experiments.
- The current corpus uses official EUR-Lex English consumer rights documents; questions, reference answers, and evidence excerpts are in English.
- When performing Part A tasks, read the content relevant to the current step in [Part A Requirements and Development Order ](./A部分需求与开发顺序.md). When performing Part B tasks, read [Part B Requirements and Development Order ](./B部分需求与开发顺序.md), and use the data format delivered by A.
- The project's early design and the B document still contain Chinese corpus examples; when processing the current batch of materials, use English models and the `Chapter` and `Article` structural conventions.
- Complete implementation and validation within the task scope specified by the user; stage deliverables include actual artifacts, run commands, and check results.

## Acceptance Requirements from the Assignment Text

The following is organized from the complete topic description provided by the user and serves as the baseline for course functionality acceptance. The implementation focus is the backend data pipeline that prepares and serves knowledge for retrieval, and the mechanism for answering faithfully to sources.

| Item | Required Content |
| --- | --- |
| Data preparation | Collect a set of custom documents, write scripts to complete loading, chunking, and vectorization, using an open-source embedding model or embedding API. Compare at least two chunking strategies and report their impact on retrieval quality. |
| Knowledge base storage | Store document chunks and their corresponding embeddings in a vector database, preserving the mapping between chunks and source documents. |
| Semantic retrieval | Convert user questions into embeddings and retrieve the most relevant document chunks from the vector database based on semantic similarity. |
| Evidence-based generation | Pass the original question and retrieved chunks to the LLM API, instructing the model to answer only based on the provided context and to explicitly cite the source document and chunk for each claim. When the knowledge base lacks sufficient information, clearly state that it cannot answer. |
| Evaluation | Build a test set of at least 20 question-answer pairs, actually run the system, report retrieval hit rate and answer correctness, and also report the impact of chunking strategy on retrieval quality. |

The assignment permits comparing chunking strategies via different chunk sizes, overlap, and no overlap. Given the current corpus, this group chose two methods: fixed window and article-structure-aware. In execution, this section distinguishes the course minimum requirements from the group's experimental design in the next section.

## Current experimental plan of this group

- Use the five currently saved English EU consumer rights documents, preserving their sources, snapshots, cleaned full text, and verifiable locations.
- Chunking uses fixed window / article-structure-aware × 400 / 800 characters, yielding four conditions: F400, S400, F800, S800. The vector store is Chroma, and retrieval uses Top-5.
- All four groups share the frozen corpus, embedding model, question set, and retrieval configuration. In the generation stage, the LLM, prompts, and generation parameters are fixed; each run's configuration is recorded to support paired comparison.
- The test set uses 24 answerable questions and 6 questions that should be refused, 30 questions in total; a full run of the four conditions produces 120 per-question records.
- Additionally check citation accuracy and refusal behavior. The above document count, four conditions, question count, and technology choices belong to this group's plan; the course minimum acceptance is executed per the previous section.

## Python environment

- Use project `.venv`; the Python version aligns with `.python-version`, currently `3.13.11`.
- When running Python commands in the project root directory, use `.\.venv\Scripts\python.exe`. Install dependencies using `-m pip` of the same interpreter.
- Newly added runtime dependencies are registered in the project dependency file so group members can reproduce.

## Part A data processing

- `data/raw/` stores the official HTML snapshots and browser-generated companion resources. The cleaning script reads the HTML paths registered in `data/sources.json`.
- The cleaned UTF-8 full text and structure JSON are written to `data/processed/`, preserving regulation titles, chapters, articles, paragraphs, and preambles, annexes, and footnotes with substantive content.
- Source records include the official URL, the actually saved version, language, file path, and the actually computed SHA-256. Fields that cannot be verified use `null` with the reason noted; registration time is recorded separately.
- Main articles are identified via HTML structure; `Article` numbers in body cross-references and annex comparison tables are attributed to their respective paragraphs or tables.
- First unify newline and whitespace rules across the full text, then generate positions. Character intervals use Python `[start, end)`, ensuring `clean_text[start:end]` matches the saved article or evidence text.
- Documents and articles use stable IDs. When the same input is registered or processed repeatedly, update by ID and verify the results are reproducible.
- When freezing the corpus and question set, record content hashes, processing rules, and versions. After revising content, update the version and re-verify affected evidence locations.
- The formal question set has 30 English questions in total, of which 24 are answerable and 6 should be refused, saved as `data/eval/gold.jsonl`. Each answerable question's evidence comes from the corresponding frozen body text; refusal conditions are based on the entire frozen corpus.

## Implementation conventions for retrieval, citation, and evaluation

- Formal Q&A uses real semantic embeddings, a vector database, and an LLM API. When referencing the `rag.py` workflow, replace the example MD5 vectorization, in-memory retrieval, and extractive answering with the corresponding formal components.
- Document chunks and questions use matching embedding models and configurations. Retrieval results include `document_id`, `chunk_id`, chunk text, corpus version, and original-text location, for reuse in citation and evaluation.
- Each factual claim is bound to the source document and chunk in the current round's retrieval results. The backend verifies that the citation can be located in the corresponding snapshot and saves the evidence text at that time, supporting verification of historical answers.
- When sufficient evidence is lacking, explicitly return insufficient information. When validation fails or model or index calls fail, return the corresponding error status, and the run record saves the failure reason.
- Formal evaluation is based on the frozen question set, saving per-question question, reference answer, standard evidence, retrieval results, final answer, citations, and scores. The hit-rate definition of the interval-coverage method follows the A and B requirements documents; multiple chunks may jointly cover one piece of standard evidence.
- Report each strategy's retrieval hit rate and answer correctness, clearly stating numerator, denominator, Top-k, and scoring rules. This group's answerable-question metrics use the 24 answerable questions as the denominator; the 6 questions that should be refused are counted separately, and call failures and false refusals are recorded.
- Judge answer correctness question by question against reference answers and source text, and check item by item whether citations support the claims. Sample records on the demo page are labeled independently; the formal report reads actual run and review results.

## Validation and delivery

- When changes involve sources, cleaning, article location, or the question set, run the corresponding validation to check file paths, ID uniqueness, hashes, character intervals, and evidence excerpts.
- Scripts provide reproducible entry points; error output includes the specific file, document ID, article, or question number, facilitating location and retry.
- At delivery, state the actual changes, executed commands, validation results, and information still pending confirmation. Experimental numbers and completion status are based on actual run artifacts.
