"""Dispose only Chroma clients created by each test; keep C-only imports light."""
import sys

import pytest


@pytest.fixture(autouse=True)
def close_test_chroma_stores(monkeypatch):
    module=sys.modules.get("app.retrieval.vector_store")
    if module is None:
        yield
        return
    created=[]
    original=module.ChromaStore.__init__
    def tracked(self,*args,**kwargs):
        original(self,*args,**kwargs)
        created.append(self)
    monkeypatch.setattr(module.ChromaStore,"__init__",tracked)
    try:
        yield
    finally:
        for store in reversed(created):
            store.close()
