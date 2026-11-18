"""Persistence boundary around the shared QA service; no alternate answer path."""
import sqlite3
from app.qa.errors import QAError


class PersistentQA:
    def __init__(self,store,service_provider,*,settings=None):
        self.store=store
        self.service_provider=service_provider
        self.settings=settings

    def ask(self,request):
        try:
            ask_id,conversation_id=self.store.start_ask(request)
        except sqlite3.Error:
            raise QAError("STORAGE_UNAVAILABLE","Ask storage is unavailable",503) from None
        trace=None
        initial={"ask_id":ask_id,"conversation_id":conversation_id,"question":request.question,
                 "condition":request.condition,"corpus_version":request.corpus_version,
                 "retrieval":None,"attempts":[],"sources_verified":False,
                 "configuration":self.settings.public_snapshot() if self.settings else {},
                 "experiment_fingerprint":self.settings.experiment_fingerprint() if self.settings else None}
        try:
            self.store.save_progress(ask_id,initial)
            service=self.service_provider()
            result,trace=service.ask_with_trace(request.question,request.condition,request.corpus_version,
                                               conversation_id,ask_id=ask_id,
                                               on_progress=lambda trace:self.store.save_progress(ask_id,trace))
            self.store.finish_ask(result,trace.to_dict())
            return result
        except QAError as exc:
            self._save_failure(ask_id,exc.as_dict(),exc.trace or initial)
            raise
        except Exception:
            error=QAError("STORAGE_OR_SERVICE_ERROR","The ask could not be completed and saved",503)
            self._save_failure(ask_id,error.as_dict(),trace.to_dict() if trace else initial)
            raise error from None

    def _save_failure(self,ask_id,error,trace):
        try:
            self.store.fail_ask(ask_id,error,trace)
        except sqlite3.Error:
            raise QAError("STORAGE_UNAVAILABLE","Ask storage is unavailable; recovery will retain its interrupted record",503) from None
