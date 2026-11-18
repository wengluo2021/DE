"""SQLite transactions for conversations, immutable evidence snapshots and tasks."""
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.qa.client import redact
from app.qa.errors import QAError


def now():
    return datetime.now(timezone.utc).isoformat()


class SQLiteStore:
    def __init__(self, path, *, secret=""):
        self.path = Path(path)
        self._secret = secret

    def _json(self, value):
        return json.dumps(redact(value, self._secret), ensure_ascii=False, allow_nan=False)

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            row = db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if row and row[0] != "1":
                raise QAError("DATABASE_VERSION_MISMATCH", "Unsupported metadata database version", 503)
            db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS asks (
                    id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    question TEXT NOT NULL, condition TEXT NOT NULL, corpus_version TEXT NOT NULL,
                    state TEXT NOT NULL, result_json TEXT, trace_json TEXT, error_json TEXT,
                    created_at TEXT NOT NULL, finished_at TEXT);
                CREATE TABLE IF NOT EXISTS evidence (
                    ask_id TEXT NOT NULL REFERENCES asks(id), n INTEGER NOT NULL,
                    source_verified INTEGER NOT NULL, payload_json TEXT NOT NULL,
                    PRIMARY KEY(ask_id,n));
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, dedupe_key TEXT,
                    state TEXT NOT NULL, completed INTEGER NOT NULL, total INTEGER NOT NULL,
                    result_json TEXT, error_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS active_task_key ON tasks(dedupe_key)
                    WHERE state IN ('queued','running') AND dedupe_key IS NOT NULL;
            """)
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('schema_version','1')")

    def ready(self):
        try:
            with closing(self._connect()) as db:
                return db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "1"
        except (sqlite3.Error, TypeError):
            return False

    def start_ask(self, request):
        stamp, ask_id = now(), "ask-" + uuid4().hex
        conversation = request.conversation_id or "chat-" + uuid4().hex
        question = redact(request.question, self._secret)
        with closing(self._connect()) as db, db:
            if request.conversation_id:
                if not db.execute("SELECT 1 FROM conversations WHERE id=?", (conversation,)).fetchone():
                    raise QAError("NOT_FOUND", "Conversation does not exist", 404)
            else:
                db.execute("INSERT INTO conversations VALUES (?,?,?,?)", (conversation, question[:60], stamp, stamp))
            db.execute("INSERT INTO asks VALUES (?,?,?,?,?,'running',NULL,NULL,NULL,?,NULL)",
                       (ask_id, conversation, question, request.condition, request.corpus_version, stamp))
            db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (stamp, conversation))
        return ask_id, conversation

    def _write_evidence(self, db, ask_id, trace, result=None):
        if result is not None:
            evidence, verified = result["citations"], True
        else:
            evidence = [dict(hit, n=hit["rank"]) for hit in (trace or {}).get("retrieval", {}).get("hits", [])] if (trace or {}).get("retrieval") else []
            verified = bool((trace or {}).get("sources_verified"))
        for item in evidence:
            # Evidence never gets rewritten after a completed run. Progress may only add the same snapshot.
            existing = db.execute("SELECT payload_json FROM evidence WHERE ask_id=? AND n=?", (ask_id,item["n"])).fetchone()
            encoded = self._json(item)
            if existing and json.loads(existing[0]) != json.loads(encoded):
                raise QAError("EVIDENCE_CONFLICT", "An existing evidence snapshot cannot be replaced", 409)
            db.execute("INSERT INTO evidence VALUES (?,?,?,?) ON CONFLICT(ask_id,n) DO UPDATE SET source_verified=MAX(source_verified,excluded.source_verified)",
                       (ask_id,item["n"],int(verified),encoded))

    def save_progress(self, ask_id, trace):
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT state FROM asks WHERE id=?", (ask_id,)).fetchone()
            if not row or row[0] != "running":
                raise QAError("ASK_NOT_RUNNING", "Cannot update a finished or missing ask", 409)
            self._write_evidence(db, ask_id, trace)
            db.execute("UPDATE asks SET trace_json=? WHERE id=?", (self._json(trace),ask_id))

    def finish_ask(self, result, trace):
        data = result.model_dump(mode="json")
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT state FROM asks WHERE id=?", (result.ask_id,)).fetchone()
            if not row or row[0] != "running":
                raise QAError("ASK_NOT_RUNNING", "Ask is no longer running", 409)
            self._write_evidence(db, result.ask_id, trace, data)
            db.execute("UPDATE asks SET state=?,result_json=?,trace_json=?,finished_at=? WHERE id=?",
                       (result.status,self._json(data),self._json(trace),now(),result.ask_id))

    def fail_ask(self, ask_id, error, trace=None):
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT state FROM asks WHERE id=?", (ask_id,)).fetchone()
            if not row or row[0] != "running":
                raise QAError("ASK_NOT_RUNNING", "Ask is no longer running", 409)
            self._write_evidence(db, ask_id, trace)
            db.execute("UPDATE asks SET state='failed',trace_json=?,error_json=?,finished_at=? WHERE id=?",
                       (self._json(trace),self._json(error),now(),ask_id))

    def conversations(self):
        with closing(self._connect()) as db:
            return [dict(row) for row in db.execute("SELECT * FROM conversations ORDER BY updated_at DESC,id")]

    def conversation(self, conversation_id):
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
            if not row:
                raise QAError("NOT_FOUND", "Conversation does not exist", 404)
            result = dict(row)
            result["asks"] = [self._ask_record(db, row) for row in db.execute(
                "SELECT * FROM asks WHERE conversation_id=? ORDER BY created_at,id", (conversation_id,))]
            return result

    def _ask_record(self, db, row):
        data = dict(row)
        for column, key in (("result_json","result"),("trace_json","trace"),("error_json","error")):
            data[key] = json.loads(data.pop(column)) if row[column] is not None else None
        data["evidence"] = [{"source_verified": bool(e["source_verified"]),
                             "citation": json.loads(e["payload_json"])} for e in db.execute(
                                "SELECT * FROM evidence WHERE ask_id=? ORDER BY n", (row["id"],))]
        return data

    def recover_interrupted(self):
        error = self._json({"code":"PROCESS_INTERRUPTED", "message":"The previous service stopped before completion; start a new run"})
        stamp = now()
        with closing(self._connect()) as db, db:
            asks = db.execute("UPDATE asks SET state='failed',error_json=?,finished_at=? WHERE state='running'", (error,stamp)).rowcount
            tasks = db.execute("UPDATE tasks SET state='failed',error_json=?,updated_at=? WHERE state IN ('queued','running')", (error,stamp)).rowcount
        return {"asks":asks,"tasks":tasks}

    def create_task(self, kind, dedupe_key=None, total=1):
        task_id, stamp = "task-" + uuid4().hex, now()
        try:
            with closing(self._connect()) as db, db:
                db.execute("INSERT INTO tasks VALUES (?,?,?,'queued',0,?,NULL,NULL,?,?)",
                           (task_id,kind,dedupe_key,total,stamp,stamp))
        except sqlite3.IntegrityError:
            raise QAError("TASK_ALREADY_RUNNING", "An equivalent task is already queued or running", 409) from None
        return {"task_id":task_id,"state":"queued"}

    def task(self, task_id):
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                raise QAError("NOT_FOUND", "Task does not exist", 404)
            result = dict(row); result["task_id"] = result.pop("id")
            for column, key in (("result_json","result"),("error_json","error")):
                result[key] = json.loads(result.pop(column)) if row[column] is not None else None
            result["result_id"] = next((result["result"][key] for key in ("run_id","index_version")
                                      if isinstance(result["result"],dict) and key in result["result"]),None)
            return result

    def begin_task(self, task_id):
        with closing(self._connect()) as db, db:
            return bool(db.execute("UPDATE tasks SET state='running',updated_at=? WHERE id=? AND state='queued'", (now(),task_id)).rowcount)

    def progress_task(self, task_id, completed, total):
        if type(completed) is not int or type(total) is not int or not 0 <= completed <= total:
            raise ValueError("Invalid task progress")
        with closing(self._connect()) as db, db:
            db.execute("UPDATE tasks SET completed=?,total=?,updated_at=? WHERE id=? AND state='running'", (completed,total,now(),task_id))

    def finish_task(self, task_id, result=None, error=None):
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT state,total,completed FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row or row["state"] != "running":
                raise QAError("TASK_NOT_RUNNING", "Task is no longer running", 409)
            db.execute("UPDATE tasks SET state=?,completed=?,result_json=?,error_json=?,updated_at=? WHERE id=?",
                       ("failed" if error else "completed",row["completed"] if error else row["total"],
                        self._json(result),self._json(error),now(),task_id))
