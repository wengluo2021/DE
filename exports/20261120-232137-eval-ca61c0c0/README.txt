DERag presentation and result export

Open ../../工作文档.md for the Chinese project explanation, B-module analysis,
presentation script, demonstration route, and 35 mock TA questions.
Open results-overview.html for a standalone offline viewer of all 120 records.
The viewer requires no model, API key, Python installation, or external assets.

evaluation.json and evaluation.csv are the existing scored run exported through
the application's read-only export API. The CSV has 120 data records.
The grades are user-authorized AI-assisted assessments, not independent human
verification. Review reasons and history are included without rewriting them.

sqlite-backup/derag.sqlite3 is a consistent SQLite backup. Restore it only into
a separate project copy or an empty target database directory, with that target
service stopped. This export operation did not restore or change the live DB.

The ZIP includes this guide and the export files in the same relative layout.
It is NOT a complete source-code, dependency, or embedding-model distribution.
The guide explains how to prepare those materials separately for reproduction.

Historical runtime configuration may contain paths from the original computer.
Use the project's relative formal configuration when setting up a new machine.
No local .env file, actual API key, or embedding weights are included.
SHA256SUMS.txt paths are relative to the project or extracted package root.

Only the standalone sqlite3 backup is included; transient WAL/SHM sidecars are excluded.
