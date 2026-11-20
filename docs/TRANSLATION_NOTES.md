# English interface and documentation

Updated: 2026-11-20.

The application interface is in English. The 239 existing Markdown documents other than `开发文档.md` and `项目设计.md` are covered by the English documentation pass; one of these documents was already entirely in English. The two excluded documents remain byte-for-byte unchanged at the user's request. File names and link destinations are retained, including Chinese file names, so existing references and the project-design endpoint keep working.

A later user request adds the intentionally Chinese [presentation preparation guide](../工作文档.md). That guide is outside the earlier English translation scope and explains the project, the B module, the current result export, and mock TA questions.

The standalone B retrieval verification page is also in English. Navigation, controls, loading and error states, chunk comparison, evaluation metrics, review forms, accessibility labels, and the insufficient-evidence message displayed by the interface are in English. The interface translates the fixed refusal message for display; it does not rewrite saved answers or alter the backend response contract. User-authored questions, reviewer names, and existing review notes remain as recorded.

## Historical records and provenance

Historical reports, handoffs, worklogs, and review documents have been translated without updating their dates, experimental numbers, approvals, or completion claims to describe the current checkout. Chinese statements quoted in those documents are English renderings of the original statements, not new confirmations. Technical identifiers, paths, hashes, and original-source references retain their original meaning.

The archive [original-markdown-20261120.zip](provenance/original-markdown-20261120.zip) preserves the exact original bytes of all 241 tracked Markdown files and the original frontend source files. This includes the original review and provenance documents. Historical SHA-256 values referring to those original Markdown snapshots can be checked against their archived entries; they are not hashes of the English translations.

The [translation manifest](translation-manifest.json) records original and translated hashes, the exclusions, and the archive checksum. The archive contains tracked public project documents and frontend sources only; it contains no local environment file, credentials, model weights, or runtime database.

The frozen legal corpus, source snapshots, question set, reference evidence, model configuration, generation prompt, saved experiment, and review history were not changed by the translation pass. Existing release archives and their historical receipts remain historical delivery artifacts; a new package should be built from this checkout when distributing the English version.
