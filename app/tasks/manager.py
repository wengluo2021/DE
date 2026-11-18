from concurrent.futures import ThreadPoolExecutor

from app.qa.errors import QAError


class TaskManager:
    """Matches B's submit(function, background_tasks); functions are not pickled."""
    def __init__(self, store):
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=1,thread_name_prefix="derag-task")
        self.closed = False

    def submit(self, function, background_tasks=None, *, kind="indexes", dedupe_key="indexes", total=1):
        if self.closed:
            raise QAError("TASK_MANAGER_CLOSED", "Task service is stopping", 503)
        task = self.store.create_task(kind,dedupe_key,total)
        self.schedule(task["task_id"],function,background_tasks)
        return task

    def schedule(self,task_id,function,background_tasks=None):
        """Schedule an already persisted task (e.g. an atomic evaluation plan)."""
        if self.closed:
            raise QAError("TASK_MANAGER_CLOSED", "Task service is stopping", 503)
        if self.store.task(task_id)["state"]!="queued":
            raise QAError("TASK_NOT_QUEUED", "Task is no longer queued", 409)
        if background_tasks is not None:
            background_tasks.add_task(self._enqueue,task_id,function)
        else:
            self._enqueue(task_id,function)

    def _enqueue(self,task_id,function):
        if not self.closed:
            self.executor.submit(self._run,task_id,function)

    def _run(self,task_id,function):
        if not self.store.begin_task(task_id):
            return
        try:
            result = function()
            self.store.finish_task(task_id,result=result)
        except QAError as exc:
            self.store.finish_task(task_id,error=exc.as_dict())
        except Exception:
            self.store.finish_task(task_id,error={"code":"TASK_FAILED","message":"Task failed; inspect its configured inputs"})

    def get(self,task_id):
        return self.store.task(task_id)

    def progress(self,task_id,completed,total):
        self.store.progress_task(task_id,completed,total)

    def close(self):
        self.closed=True
        self.executor.shutdown(wait=True)
