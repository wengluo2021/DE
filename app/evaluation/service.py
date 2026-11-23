"""Four-condition evaluation through the same persistent QA boundary as /ask."""
from copy import deepcopy
from contextlib import nullcontext

from app.contracts import AskRequest,Document
from app.qa.client import ChatCompletionsClient
from app.qa.errors import QAError
from app.qa.persistent import PersistentQA
from .data import load_gold,validate_cases,source_structures
from app.data.document_view import document_view
from .repository import EvaluationAskStore


class EvaluationService:
    def __init__(self,settings,repository,tasks,qa_provider,*,p800_qa_provider=None,gold_loader=None,test_mode=False,admission=None):
        self.settings,self.repo,self.tasks,self.qa_provider=settings,repository,tasks,qa_provider
        self.p800_qa_provider=p800_qa_provider
        self.gold_loader=gold_loader
        self.test_mode=test_mode
        self.admission=admission or nullcontext()

    def submit(self,request,background_tasks=None):
        with self.admission:
            cfg=self.settings.experiment
            if (request.corpus_version,request.gold_version)!=(cfg.corpus_version,cfg.gold_version):
                raise QAError("VERSION_MISMATCH","Evaluation versions differ from the active configuration",409)
            if self.repo.active() or self.repo.store.has_active_tasks():
                raise QAError("TASK_ALREADY_RUNNING","Wait for the current background task before evaluation",409)
            service=self.qa_provider()
            if not service.index_version:
                raise QAError("INDEX_NOT_CONFIGURED","Evaluation requires one fixed index version",409)
            if service.settings.experiment_fingerprint()!=self.settings.experiment_fingerprint():
                raise QAError("CONFIGURATION_MISMATCH","QA and evaluation configurations differ",409)
            if isinstance(service.generator,ChatCompletionsClient) and not self.settings.llm_configured:
                raise QAError("LLM_NOT_CONFIGURED","Generation service is not configured",503)
            if self.gold_loader is not None and not self.test_mode:
                raise QAError("TEST_DATA_FORBIDDEN","Injected gold loaders require explicit test mode",409)
            dataset=deepcopy(self.gold_loader() if self.gold_loader else load_gold(self.settings,service.document_loader))
            if (dataset.corpus_version,dataset.gold_version)!=(request.corpus_version,request.gold_version):
                raise QAError("VERSION_MISMATCH","Frozen gold versions differ from the requested versions",409)
            if dataset.synthetic and (not self.test_mode or cfg.mode=="formal"):
                raise QAError("TEST_DATA_FORBIDDEN","Synthetic cases cannot enter formal evaluation",409)
            try:
                originals=list(service.document_loader(dataset.corpus_version))
                docs=[document_view(d) for d in originals]
                validate_cases(dataset.cases,docs,source_structures(self.settings,originals))
                if sum(c.answerable for c in dataset.cases)!=24 or len(dataset.cases)!=30:
                    raise ValueError("Expected 24/6 frozen cases")
                if any(d.corpus_version!=dataset.corpus_version for d in docs):
                    raise ValueError("Corpus mismatch")
            except (ValueError,TypeError,KeyError,StopIteration):
                raise QAError("INVALID_GOLD_DATA","Frozen gold cases or source evidence failed validation",409) from None
            planned=self.repo.create(self.settings,dataset,service.index_version)
            try:
                self.tasks.schedule(planned["task_id"],lambda:self._run(planned,dataset,service),background_tasks)
            except Exception:
                error={"code":"EVALUATION_SCHEDULING_FAILED","message":"Evaluation could not be scheduled"}
                self.repo.fail_run(planned["run_id"],error)
                if self.repo.store.begin_task(planned["task_id"]):
                    self.repo.store.finish_task(planned["task_id"],error=error)
                raise QAError(error["code"],error["message"],503) from None
            return planned

    def submit_p800(self,request,background_tasks=None):
        """Run the optional P800 parent-child extension as a separate 30-item run.

        The frozen four-condition experiment and its 120 saved rows are never
        touched: the extension writes its own run with conditions=("p800",).
        """
        with self.admission:
            cfg=self.settings.experiment
            if (request.corpus_version,request.gold_version)!=(cfg.corpus_version,cfg.gold_version):
                raise QAError("VERSION_MISMATCH","Evaluation versions differ from the active configuration",409)
            if self.repo.active() or self.repo.store.has_active_tasks():
                raise QAError("TASK_ALREADY_RUNNING","Wait for the current background task before evaluation",409)
            if self.p800_qa_provider is None:
                raise QAError("P800_NOT_READY","P800 evaluation is unavailable",503)
            service=self.p800_qa_provider()
            if not service.index_version:
                raise QAError("P800_NOT_READY","P800 evaluation requires a built P800 index",409)
            if service.settings.experiment_fingerprint()!=self.settings.experiment_fingerprint():
                raise QAError("CONFIGURATION_MISMATCH","QA and evaluation configurations differ",409)
            if isinstance(service.generator,ChatCompletionsClient) and not self.settings.llm_configured:
                raise QAError("LLM_NOT_CONFIGURED","Generation service is not configured",503)
            if self.gold_loader is not None and not self.test_mode:
                raise QAError("TEST_DATA_FORBIDDEN","Injected gold loaders require explicit test mode",409)
            dataset=deepcopy(self.gold_loader() if self.gold_loader else load_gold(self.settings,service.document_loader))
            if (dataset.corpus_version,dataset.gold_version)!=(request.corpus_version,request.gold_version):
                raise QAError("VERSION_MISMATCH","Frozen gold versions differ from the requested versions",409)
            if dataset.synthetic and (not self.test_mode or cfg.mode=="formal"):
                raise QAError("TEST_DATA_FORBIDDEN","Synthetic cases cannot enter formal evaluation",409)
            try:
                originals=list(service.document_loader(dataset.corpus_version))
                docs=[document_view(d) for d in originals]
                validate_cases(dataset.cases,docs,source_structures(self.settings,originals))
                if sum(c.answerable for c in dataset.cases)!=24 or len(dataset.cases)!=30:
                    raise ValueError("Expected 24/6 frozen cases")
                if any(d.corpus_version!=dataset.corpus_version for d in docs):
                    raise ValueError("Corpus mismatch")
            except (ValueError,TypeError,KeyError,StopIteration):
                raise QAError("INVALID_GOLD_DATA","Frozen gold cases or source evidence failed validation",409) from None
            planned=self.repo.create(self.settings,dataset,service.index_version,conditions=("p800",))
            try:
                self.tasks.schedule(planned["task_id"],lambda:self._run(planned,dataset,service,conditions=("p800",)),background_tasks)
            except Exception:
                error={"code":"EVALUATION_SCHEDULING_FAILED","message":"P800 evaluation could not be scheduled"}
                self.repo.fail_run(planned["run_id"],error)
                if self.repo.store.begin_task(planned["task_id"]):
                    self.repo.store.finish_task(planned["task_id"],error=error)
                raise QAError(error["code"],error["message"],503) from None
            return planned

    def _run(self,planned,dataset,service,conditions=None):
        conditions=tuple(conditions or self.settings.experiment.conditions)
        run_id,task_id=planned["run_id"],planned["task_id"]
        processed=errors=0
        try:
            self.repo.start_run(run_id)
            for condition in conditions:
                for case in dataset.cases:
                    store=EvaluationAskStore(self.repo,run_id,condition,case.case_id)
                    qa=PersistentQA(store,lambda:service,settings=self.settings)
                    # Only the original question and retrieval settings cross into QA.
                    # Gold references, labels and preceding cases never become messages.
                    request=AskRequest(question=case.question,condition=condition,corpus_version=dataset.corpus_version)
                    try:
                        qa.ask(request)
                    except QAError as exc:
                        errors+=1
                        saved=self.repo.get_case(run_id,condition,case.case_id)
                        if saved["state"] in {"queued","running"}:
                            self.repo.finish_case(run_id,condition,case.case_id,None,saved["trace"],exc.as_dict())
                    processed+=1
                    self.tasks.progress(task_id,processed,len(dataset.cases)*len(conditions))
            self.repo.complete_run(run_id)
            return {"run_id":run_id,"processed":processed,"total":len(dataset.cases)*len(conditions),"errors":errors}
        except Exception:
            self.repo.fail_run(run_id,{"code":"EVALUATION_FAILED","message":"Evaluation stopped; saved cases remain available"})
            raise QAError("EVALUATION_FAILED","Evaluation stopped; inspect its saved cases",503) from None
