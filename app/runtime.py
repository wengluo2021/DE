"""Explicit service composition; one database owner and one persistent task worker."""
from threading import RLock
from app.db.lease import ProcessLease
from app.db.store import SQLiteStore
from app.qa.client import ChatCompletionsClient
from app.qa.errors import QAError
from app.qa.persistent import PersistentQA
from app.qa.service import QAService
from app.tasks.manager import TaskManager
from app.evaluation.repository import EvaluationRepository
from app.evaluation.service import EvaluationService
from app.data import corpus_loader


class Runtime:
    def __init__(self,settings,*,qa_service=None,retrieval_service=None,database_path=None,test_mode=False,gold_loader=None):
        self.settings=settings
        path=database_path or settings.experiment.data_dir/"sqlite/derag.sqlite3"
        self.store=SQLiteStore(path,secret=settings.api_key())
        self.lease=ProcessLease(str(path)+".lock")
        self.injected_qa=qa_service
        self.retrieval=retrieval_service
        self.owns_retrieval=retrieval_service is None
        self.test_mode=test_mode
        self.gold_loader=gold_loader
        self.admission=RLock()
        self.evaluations=EvaluationRepository(self.store)
        self.evaluation=None
        self.tasks=None
        self.qa=None
        self.started=False
        self.retrieval_issue=None

    def open(self):
        self.lease.acquire()
        try:
            self.store.initialize()
            self.evaluations.initialize()
            self.store.recover_interrupted()
            self.evaluations.recover_interrupted()
            self.tasks=TaskManager(self.store)
            self.qa=PersistentQA(self.store,self.get_qa_service,settings=self.settings)
            self.evaluation=EvaluationService(self.settings,self.evaluations,self.tasks,self.get_qa_service,
                                              gold_loader=self.gold_loader,test_mode=self.test_mode,admission=self.admission)
            if self.retrieval is None and self.injected_qa is None:
                self._assemble_retrieval()
            self.started=True
        except Exception:
            if self.tasks:
                self.tasks.close()
            self.lease.release()
            raise

    def _assemble_retrieval(self):
        if not (self.settings.experiment.data_dir/"manifest.json").is_file():
            self.retrieval_issue="OFFICIAL_DATA_NOT_CONFIGURED"
            return
        try:
            loader=corpus_loader(self.settings.experiment.data_dir,formal=self.settings.experiment.mode=="formal")
            loader(self.settings.experiment.corpus_version)
            from app.retrieval import RetrievalService
            from app.retrieval.embedding import LocalEmbedder
            config=self.settings.retrieval_config()
            self.retrieval=RetrievalService(loader,LocalEmbedder(config["embedding"]),config)
        except QAError as error:
            self.retrieval_issue=error.code
        except ImportError:
            self.retrieval_issue="RETRIEVAL_DEPENDENCIES_NOT_INSTALLED"
        except Exception:
            self.retrieval_issue="RETRIEVAL_INITIALIZATION_FAILED"

    def get_retrieval(self):
        if self.retrieval is None:
            if self.retrieval_issue=="INVALID_CORPUS_DATA":
                raise QAError("INVALID_CORPUS_DATA","Frozen corpus validation failed; inspect A's manifests and snapshots",409)
            raise QAError("RETRIEVAL_NOT_CONFIGURED","Official data and retrieval dependencies must be configured",409)
        return self.retrieval

    def get_qa_service(self):
        if self.injected_qa is not None:
            return self.injected_qa
        retrieval=self.get_retrieval()
        try:
            with retrieval.indexes.lock():
                manifest,_=retrieval.indexes.completed(self.settings.experiment.corpus_version)
        except Exception:
            raise QAError("INDEX_NOT_READY","Build all four indexes for the active corpus before asking",409) from None
        return QAService(self.settings,retriever=retrieval.search_result,
                         document_loader=retrieval.documents,generator=ChatCompletionsClient(self.settings),
                         index_version=manifest["index_version"])

    def health(self):
        cfg=self.settings.experiment
        mock_generation=bool(self.test_mode and self.injected_qa is not None
                             and self.injected_qa.settings.experiment.generation.provider=="mock")
        index_ready=self.injected_qa is not None
        if self.retrieval is not None:
            try:
                with self.retrieval.indexes.lock():
                    self.retrieval.indexes.completed(cfg.corpus_version)
                index_ready=True
            except Exception:
                index_ready=False
        return {"status":"ok","phase":"qa_backend","mode":"test" if self.test_mode else cfg.mode,
                "frontend_mode":"api","ready":self.started and self.store.ready() and index_ready
                    and (mock_generation or self.settings.llm_configured),
                "components":{"sqlite":{"ready":self.store.ready()},
                    "retrieval":{"ready":index_ready,"issue":self.retrieval_issue},
                    "generation":{"configured":self.settings.llm_configured,
                                  "mode":"mock" if mock_generation else "api","connectivity_verified":False}},
                "available_conditions":list(cfg.conditions) if index_ready else [],
                "experiment_fingerprint":self.settings.experiment_fingerprint(),
                "configuration":self.settings.public_snapshot()}

    def ensure_no_evaluation(self):
        if self.evaluations.active():
            raise QAError("EVALUATION_ACTIVE","Wait for the evaluation to finish before asking or rebuilding indexes",409)

    def close(self):
        try:
            if self.tasks:
                self.tasks.close()
        finally:
            try:
                if self.owns_retrieval and self.retrieval is not None:
                    try:
                        close=getattr(self.retrieval,"close",None)
                        if close is not None:close()
                    finally:
                        self.retrieval=None
            finally:
                self.started=False
                self.lease.release()


class RetrievalProxy:
    def __init__(self,runtime):
        self.runtime=runtime
    def __getattr__(self,name):
        return getattr(self.runtime.get_retrieval(),name)


class TaskProxy:
    def __init__(self,runtime):
        self.runtime=runtime
    def submit(self,function,background_tasks):
        if self.runtime.tasks is None:
            raise QAError("SERVICE_NOT_READY","Service has not started",503)
        with self.runtime.admission:
            self.runtime.ensure_no_evaluation()
            return self.runtime.tasks.submit(function,background_tasks)
