from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app
from app.retrieval.vector_store import ChromaStore
from app.retrieval.errors import RetrievalError
import os
import json
import subprocess
import sys
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


def test_single_vector_survives_native_shutdown_and_fresh_process(tmp_path):
    from app.config import ROOT
    conditions=("f400","s400","f800","s800")
    store=ChromaStore(tmp_path)
    try:
        chunk={"chunk_id":"synthetic-one","document_id":"synthetic","start":0,"end":1}
        for condition in conditions:
            store.upsert(condition,[chunk],[[1.0,0.0]])
        for condition in conditions:
            assert store.ids(condition)=={"synthetic-one"}
            assert store.query(condition,[0.9,0.435889894],5)[0][1]==pytest.approx(0.1,abs=1e-6)
    finally:
        store.close()
    # A fresh interpreter must recover actual native indexes without a surviving Python cache.
    code="""
import json,sys
from pathlib import Path
from app.retrieval.vector_store import ChromaStore
store=ChromaStore(Path(sys.argv[1]))
try:
    print(json.dumps({c:store.query(c,[0.9,0.435889894],5) for c in ('f400','s400','f800','s800')}))
finally:
    store.close()
"""
    result=subprocess.run([sys.executable,"-c",code,str(tmp_path)],cwd=ROOT,text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr
    recovered=json.loads(result.stdout)
    for condition in conditions:
        assert len(recovered[condition])==1 and recovered[condition][0][0]=="synthetic-one"
        assert recovered[condition][0][1]==pytest.approx(0.1,abs=1e-6)
