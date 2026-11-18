"""Explicit service composition; one database owner and one persistent task worker."""
from app.db.lease import ProcessLease
from app.db.store import SQLiteStore
from app.qa.client import ChatCompletionsClient
from app.qa.errors import QAError
from app.qa.persistent import PersistentQA
from app.qa.service import QAService
from app.tasks.manager import TaskManager


class Runtime:
    def __init__(self,settings,*,qa_service=None,retrieval_service=None,database_path=None,test_mode=False):
        self.settings=settings
        path=database_path or settings.experiment.data_dir/"sqlite/derag.sqlite3"
        self.store=SQLiteStore(path,secret=settings.api_key())
        self.lease=ProcessLease(str(path)+".lock")
        self.injected_qa=qa_service
        self.retrieval=retrieval_service
        self.test_mode=test_mode
        self.tasks=None
        self.qa=None
        self.started=False
        self.retrieval_issue=None

    def open(self):
        self.lease.acquire()
        try:
            self.store.initialize()
            self.store.recover_interrupted()
            self.tasks=TaskManager(self.store)
            self.qa=PersistentQA(self.store,self.get_qa_service,settings=self.settings)
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
            from app.retrieval import RetrievalService
            from app.retrieval.embedding import LocalEmbedder
            from app.retrieval.types import formal_loader
            config=self.settings.retrieval_config()
            self.retrieval=RetrievalService(formal_loader(self.settings.experiment.data_dir),
                                            LocalEmbedder(config["embedding"]),config)
        except ImportError:
            self.retrieval_issue="RETRIEVAL_DEPENDENCIES_NOT_INSTALLED"
        except Exception:
            self.retrieval_issue="RETRIEVAL_INITIALIZATION_FAILED"

    def get_retrieval(self):
        if self.retrieval is None:
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
                "frontend_mode":"preview","ready":self.started and self.store.ready() and index_ready
                    and (mock_generation or self.settings.llm_configured),
                "components":{"sqlite":{"ready":self.store.ready()},
                    "retrieval":{"ready":index_ready,"issue":self.retrieval_issue},
                    "generation":{"configured":self.settings.llm_configured,
                                  "mode":"mock" if mock_generation else "api","connectivity_verified":False}},
                "available_conditions":list(cfg.conditions) if index_ready else [],
                "experiment_fingerprint":self.settings.experiment_fingerprint(),
                "configuration":self.settings.public_snapshot()}

    def close(self):
        try:
            if self.tasks:
                self.tasks.close()
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
        return self.runtime.tasks.submit(function,background_tasks)
