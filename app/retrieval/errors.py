"""统一业务异常：核心代码、命令行与 API 共用错误码和可读说明。"""


class RetrievalError(Exception):
    """code 供程序区分错误，message 供人查看，status 指定 HTTP 状态码。"""
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status

    def as_dict(self):
        # HTTP 状态由响应头携带；响应正文固定只有 code 和 message。
        return {"code": self.code, "message": self.message}
