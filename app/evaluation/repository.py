from contextlib import closing
import hashlib
import json
import sqlite3
from uuid import uuid4

from app.db.store import now
from app.qa.errors import QAError
from .metrics import case_metrics,summarize,paired_cases
from .review import merge_review


class EvaluationRepository:
    def __init__(self,store):
        self.store=store

    def initialize(self):
        with closing(self.store._connect()) as db,db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,task_id TEXT NOT NULL REFERENCES tasks(id),
                    corpus_version TEXT NOT NULL,gold_version TEXT NOT NULL,index_version TEXT NOT NULL,
                    synthetic INTEGER NOT NULL,state TEXT NOT NULL,config_json TEXT NOT NULL,
                    gold_json TEXT NOT NULL,created_at TEXT NOT NULL,finished_at TEXT);
                CREATE TABLE IF NOT EXISTS evaluation_cases (
                    run_id TEXT NOT NULL REFERENCES evaluations(id),condition TEXT NOT NULL,case_id TEXT NOT NULL,
                    gold_json TEXT NOT NULL,state TEXT NOT NULL,ask_id TEXT,conversation_id TEXT,
                    result_json TEXT,trace_json TEXT,metrics_json TEXT,error_json TEXT,review_json TEXT,
                    updated_at TEXT NOT NULL,PRIMARY KEY(run_id,condition,case_id));
                CREATE TABLE IF NOT EXISTS evaluation_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL,condition TEXT NOT NULL,
                    case_id TEXT NOT NULL,review_json TEXT NOT NULL,created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id,condition,case_id) REFERENCES evaluation_cases(run_id,condition,case_id));
            """)

    def create(self,settings,dataset,index_version,conditions=None):
        run_id,task_id,stamp="eval-"+uuid4().hex,"task-"+uuid4().hex,now()
        conditions=tuple(conditions or settings.experiment.conditions)
        config=settings.public_snapshot()
        config["experiment_fingerprint"]=settings.experiment_fingerprint()
        config["conditions"]=list(conditions)
        if conditions != tuple(settings.experiment.conditions):
            config["extension"]="p800" if conditions == ("p800",) else "custom"
        key=hashlib.sha256((config["experiment_fingerprint"]+"|"+dataset.gold_version+"|"+index_version+"|"+",".join(conditions)).encode()).hexdigest()
        total=len(dataset.cases)*len(conditions)
        encode=self.store._json
        try:
            with closing(self.store._connect()) as db,db:
                db.execute("INSERT INTO tasks VALUES (?,?,?,'queued',0,?,NULL,NULL,?,?)",
                           (task_id,"evaluation",key,total,stamp,stamp))
                db.execute("INSERT INTO evaluations VALUES (?,?,?,?,?,?,'queued',?,?,?,NULL)",
                           (run_id,task_id,dataset.corpus_version,dataset.gold_version,index_version,
                            int(dataset.synthetic),encode(config),encode(dataset.snapshot()),stamp))
                for condition in conditions:
                    for case in dataset.cases:
                        db.execute("INSERT INTO evaluation_cases VALUES (?,?,?,?,'queued',NULL,NULL,NULL,NULL,NULL,NULL,NULL,?)",
                                   (run_id,condition,case.case_id,encode(case.model_dump(mode="json")),stamp))
        except sqlite3.IntegrityError:
            raise QAError("EVALUATION_ALREADY_RUNNING","An equivalent evaluation is already active",409) from None
        return {"run_id":run_id,"task_id":task_id,"state":"queued"}

    def list_runs(self):
        with closing(self.store._connect()) as db:
            rows=[dict(row) for row in db.execute("SELECT id AS run_id,task_id,state,synthetic,corpus_version,gold_version,index_version,created_at,finished_at,config_json FROM evaluations ORDER BY created_at DESC,id")]
        for row in rows:
            config=json.loads(row.pop("config_json"))
            row["conditions"]=config.get("conditions") or ["f400","s400","f800","s800"]
            row["extension"]=config.get("extension")
        return rows

    def _case(self,row):
        result=dict(row)
        for column,key in (("gold_json","gold"),("result_json","result"),("trace_json","trace"),
                           ("metrics_json","metrics"),("error_json","error"),("review_json","review")):
            value=result.pop(column)
            result[key]=json.loads(value) if value is not None else None
        return result

    def get_case(self,run_id,condition,case_id):
        with closing(self.store._connect()) as db:
            row=db.execute("SELECT * FROM evaluation_cases WHERE run_id=? AND condition=? AND case_id=?",
                           (run_id,condition,case_id)).fetchone()
        if not row:
            raise QAError("NOT_FOUND","Evaluation case does not exist",404)
        return self._case(row)

    def get(self,run_id):
        with closing(self.store._connect()) as db:
            row=db.execute("SELECT * FROM evaluations WHERE id=?",(run_id,)).fetchone()
            if not row:
                raise QAError("NOT_FOUND","Evaluation does not exist",404)
            result=dict(row);result["run_id"]=result.pop("id")
            result["config"]=json.loads(result.pop("config_json"))
            result["gold_cases"]=json.loads(result.pop("gold_json"))
            result["synthetic"]=bool(result["synthetic"])
            result["cases"]=[self._case(item) for item in db.execute("SELECT * FROM evaluation_cases WHERE run_id=? ORDER BY rowid",(run_id,))]
            result["review_history"]=[dict(id=r["id"],condition=r["condition"],case_id=r["case_id"],
                                            review=json.loads(r["review_json"]),created_at=r["created_at"])
                                       for r in db.execute("SELECT * FROM evaluation_reviews WHERE run_id=? ORDER BY id",(run_id,))]
        conditions=tuple(result["config"].get("conditions") or ("f400","s400","f800","s800"))
        result["summary"]=summarize(result["gold_cases"],result["cases"],conditions=conditions)
        result["paired_cases"]=paired_cases(result["gold_cases"],result["cases"],conditions=conditions)
        result["review_complete"]=all(not s["processing"] and not s["answer_accuracy"]["pending"]
             and not s["refusal_accuracy"]["pending"] and not s["citation_accuracy"]["pending"] for s in result["summary"].values())
        result["finalizable"]=result["state"]=="completed" and result["review_complete"]
        result["formal_results"]=(result["finalizable"] and not result["synthetic"]
                                  and result["config"].get("mode")=="formal"
                                  and not result["config"].get("extension"))
        result["actual_generation_models"]=sorted({a["model"] for r in result["cases"] for a in (r["trace"] or {}).get("attempts",[])
                                                    if isinstance(a.get("model"),str)})
        if len(result["actual_generation_models"])>1:
            result["finalizable"]=False
            result["formal_results"]=False
            result["configuration_warning"]="GENERATION_MODEL_CHANGED"
        return result

    def start_run(self,run_id):
        with closing(self.store._connect()) as db,db:
            if not db.execute("UPDATE evaluations SET state='running' WHERE id=? AND state='queued'",(run_id,)).rowcount:
                raise QAError("EVALUATION_NOT_QUEUED","Evaluation is no longer queued",409)

    def begin_case(self,run_id,condition,case_id,request):
        case=self.get_case(run_id,condition,case_id)
        run=self._run_identity(run_id)
        if (case["state"]!="queued" or run["state"]!="running" or request.question!=case["gold"]["question"]
                or request.condition!=condition or request.corpus_version!=run["corpus_version"] or request.conversation_id is not None):
            raise QAError("EVALUATION_CASE_MISMATCH","Case input differs from its frozen plan",409)
        ask_id,conversation="ask-"+uuid4().hex,"eval-chat-"+uuid4().hex
        with closing(self.store._connect()) as db,db:
            if not db.execute("UPDATE evaluation_cases SET state='running',ask_id=?,conversation_id=?,updated_at=? WHERE run_id=? AND condition=? AND case_id=? AND state='queued'",
                 (ask_id,conversation,now(),run_id,condition,case_id)).rowcount:
                raise QAError("EVALUATION_CASE_NOT_QUEUED","Case has already started",409)
        return ask_id,conversation

    def _run_identity(self,run_id):
        with closing(self.store._connect()) as db:
            row=db.execute("SELECT * FROM evaluations WHERE id=?",(run_id,)).fetchone()
        if not row:
            raise QAError("NOT_FOUND","Evaluation does not exist",404)
        return dict(row)

    def _validate_trace(self,run_id,case,trace):
        if not trace:
            return
        run=self._run_identity(run_id)
        if (trace.get("ask_id")!=case["ask_id"] or trace.get("conversation_id")!=case["conversation_id"]
                or trace.get("condition")!=case["condition"] or trace.get("question")!=case["gold"]["question"]
                or trace.get("corpus_version")!=run["corpus_version"]):
            raise QAError("EVALUATION_TRACE_MISMATCH","Trace differs from the frozen case",409)
        previous=(case["trace"] or {}).get("retrieval")
        current=trace.get("retrieval")
        if previous is not None and previous!=current:
            raise QAError("EVIDENCE_CONFLICT","Evaluation evidence cannot be replaced",409)

    def progress(self,run_id,condition,case_id,trace):
        case=self.get_case(run_id,condition,case_id)
        if case["state"]!="running":
            raise QAError("EVALUATION_CASE_NOT_RUNNING","Case is not running",409)
        self._validate_trace(run_id,case,trace)
        with closing(self.store._connect()) as db,db:
            db.execute("UPDATE evaluation_cases SET trace_json=?,updated_at=? WHERE run_id=? AND condition=? AND case_id=? AND state='running'",
                       (self.store._json(trace),now(),run_id,condition,case_id))

    def finish_case(self,run_id,condition,case_id,result,trace,error=None):
        case=self.get_case(run_id,condition,case_id)
        if case["state"] not in {"queued","running"}:
            raise QAError("EVALUATION_CASE_FINISHED","Case is already finished",409)
        run=self._run_identity(run_id)
        self._validate_trace(run_id,case,trace)
        if result is not None and (result.ask_id!=case["ask_id"] or result.condition!=condition
                or result.conversation_id!=case["conversation_id"] or result.corpus_version!=run["corpus_version"]
                or result.index_version!=run["index_version"]):
            raise QAError("EVALUATION_RESULT_MISMATCH","Answer does not belong to this case",409)
        if result is None and error is None:
            raise QAError("EVALUATION_RESULT_MISSING","A finished case needs an answer or an error",409)
        metrics=case_metrics(case["gold"],trace)
        encode=self.store._json
        with closing(self.store._connect()) as db,db:
            changed=db.execute("UPDATE evaluation_cases SET state=?,result_json=?,trace_json=?,metrics_json=?,error_json=?,updated_at=? WHERE run_id=? AND condition=? AND case_id=? AND state IN ('queued','running')",
                       ("error" if error else "completed",encode(result.model_dump(mode="json") if result else None),
                        encode(trace),encode(metrics),encode(error),now(),run_id,condition,case_id))
            if not changed.rowcount:
                raise QAError("EVALUATION_CASE_FINISHED","Case is already finished",409)

    def complete_run(self,run_id):
        with closing(self.store._connect()) as db,db:
            pending=db.execute("SELECT count(*) FROM evaluation_cases WHERE run_id=? AND state IN ('queued','running')",(run_id,)).fetchone()[0]
            if pending:
                raise QAError("EVALUATION_INCOMPLETE","Some cases are still unprocessed",409)
            db.execute("UPDATE evaluations SET state='completed',finished_at=? WHERE id=?",(now(),run_id))

    def review(self,run_id,condition,case_id,patch):
        with closing(self.store._connect()) as db,db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM evaluation_cases WHERE run_id=? AND condition=? AND case_id=?",(run_id,condition,case_id)).fetchone()
            if not row:
                raise QAError("NOT_FOUND","Evaluation case does not exist",404)
            case=self._case(row)
            if case["state"]!="completed" or not case["result"]:
                raise QAError("CASE_NOT_REVIEWABLE","Only a completed generated result can be scored",409)
            try:
                review=merge_review(case["review"],patch,case["gold"],case["result"])
            except ValueError:
                raise QAError("INVALID_REVIEW","Review fields do not match this question or its claims",422) from None
            review["reviewed_at"]=now()
            encoded=self.store._json(review)
            db.execute("UPDATE evaluation_cases SET review_json=?,updated_at=? WHERE run_id=? AND condition=? AND case_id=?",
                       (encoded,review["reviewed_at"],run_id,condition,case_id))
            db.execute("INSERT INTO evaluation_reviews(run_id,condition,case_id,review_json,created_at) VALUES(?,?,?,?,?)",
                       (run_id,condition,case_id,encoded,review["reviewed_at"]))
        return json.loads(encoded)

    def fail_run(self,run_id,error):
        with closing(self.store._connect()) as db,db:
            rows=db.execute("SELECT * FROM evaluation_cases WHERE run_id=? AND state IN ('queued','running')",(run_id,)).fetchall()
            for row in rows:
                case=self._case(row)
                metrics=case_metrics(case["gold"],case["trace"])
                db.execute("UPDATE evaluation_cases SET state='error',error_json=?,metrics_json=?,updated_at=? WHERE run_id=? AND condition=? AND case_id=?",
                           (self.store._json(error),self.store._json(metrics),now(),run_id,case["condition"],case["case_id"]))
            db.execute("UPDATE evaluations SET state='failed',finished_at=? WHERE id=? AND state IN ('queued','running')",(now(),run_id))

    def recover_interrupted(self):
        with closing(self.store._connect()) as db:
            ids=[r[0] for r in db.execute("SELECT id FROM evaluations WHERE state IN ('queued','running')")]
        for run_id in ids:
            self.fail_run(run_id,{"code":"PROCESS_INTERRUPTED","message":"Evaluation stopped before completion; start a new run"})

    def active(self):
        with closing(self.store._connect()) as db:
            return bool(db.execute("SELECT 1 FROM evaluations WHERE state IN ('queued','running') LIMIT 1").fetchone())


class EvaluationAskStore:
    """Reuse PersistentQA without adding 120 evaluation chats to normal user history."""
    def __init__(self,repository,run_id,condition,case_id):
        self.repo,self.run_id,self.condition,self.case_id=repository,run_id,condition,case_id
    def start_ask(self,request):
        return self.repo.begin_case(self.run_id,self.condition,self.case_id,request)
    def save_progress(self,ask_id,trace):
        self.repo.progress(self.run_id,self.condition,self.case_id,trace)
    def finish_ask(self,result,trace):
        self.repo.finish_case(self.run_id,self.condition,self.case_id,result,trace)
    def fail_ask(self,ask_id,error,trace=None):
        self.repo.finish_case(self.run_id,self.condition,self.case_id,None,trace,error)
