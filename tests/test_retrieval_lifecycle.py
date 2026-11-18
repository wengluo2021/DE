from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app
from app.retrieval.vector_store import ChromaStore
from app.retrieval.errors import RetrievalError
import os
import pytest


def test_close_once_does_not_release_another_clients_shared_store(tmp_path):
    first,second=ChromaStore(tmp_path),ChromaStore(tmp_path)
    first.collection("s400",create=True)
    first.close();first.close()
    assert second.ids("s400")==set()
    second.close()
    reopened=ChromaStore(tmp_path)
    assert reopened.ids("s400")==set()
    reopened.close()


def test_runtime_leaves_caller_owned_retrieval_open(tmp_path):
    calls=[]
    class External:
        def close(self):calls.append("closed")
    settings=load_settings(environ={},overrides={"data_dir":str(tmp_path)})
    with TestClient(create_app(settings,retrieval_service=External())):
        pass
    assert calls==[]


@pytest.mark.skipif(os.name!="nt",reason="Windows native path budget")
def test_deep_native_index_path_fails_before_creating_store(tmp_path):
    path=tmp_path/("deep-"*35)
    with pytest.raises(RetrievalError) as error:ChromaStore(path)
    assert error.value.code=="INDEX_PATH_TOO_LONG" and not path.exists()
