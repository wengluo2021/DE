# 对 C 暴露统一业务服务和异常，导入这里不会下载模型或开始建库。
from .service import RetrievalService
from .errors import RetrievalError

__all__ = ["RetrievalService", "RetrievalError"]
