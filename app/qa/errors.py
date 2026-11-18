"""Public error semantics shared by the QA service and later HTTP routes."""


class QAError(Exception):
    def __init__(self, code, message, status=502, *, retryable=False, trace=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.retryable = retryable
        self.trace = trace

    def as_dict(self):
        return {"code": self.code, "message": self.message}
