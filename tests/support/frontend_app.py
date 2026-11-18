"""Explicit synthetic browser acceptance app; no Chroma or paid model calls."""
import os
from contextlib import nullcontext

from app.config import load_settings
from app.main import create_app
from app.qa.service import QAService
from app.qa.errors import QAError
from app.qa.client import ChatCompletionsClient
from tests.support.c_fixtures import document_loader,retrieve
from tests.support.evaluation_fixtures import dataset,EvaluationGenerator


class FrontendRetrieval:
    def __init__(self):
        self.indexes=self
    def lock(self):
        return nullcontext()
    def completed(self,version):
        return {"index_version":"c-fixture-index-v1"},document_loader(version)
    def documents(self,version):
        return document_loader(version)
    def document(self,document_id,version):
        for doc in self.documents(version):
            if doc["document_id"]==document_id:
                return doc
        raise QAError("NOT_FOUND","Synthetic document does not exist",404)
    def chunks(self,document_id,condition,version):
        self.document(document_id,version)
        hit=retrieve(question="synthetic",condition=condition,corpus_version=version)["hits"][0]
        return [{key:hit[key] for key in ("chunk_id","document_id","corpus_version","condition","start","end","text","article_ids")}]
    def search_result(self,question,condition,corpus_version,top_k=5):
        return retrieve(question=question,condition=condition,corpus_version=corpus_version,top_k=top_k)
    def compare(self,question,left_condition,right_condition,corpus_version):
        sides=[self.search_result(question,c,corpus_version) for c in (left_condition,right_condition)]
        for side in sides:
            side["context_chars"]=sum(len(h["text"]) for h in side["hits"])
        return {"question":question,"corpus_version":corpus_version,"index_version":"c-fixture-index-v1",
                "left":sides[0],"right":sides[1]}
    def build_indexes(self,version):
        self.documents(version)
        return {"index_version":"c-fixture-index-v1","synthetic":True}


def create_frontend_app():
    if os.environ.get("DERAG_TEST_EVALUATION")!="1" or not os.environ.get("DERAG_TEST_DATA_DIR"):
        raise RuntimeError("Explicit isolated synthetic test opt-in is required")
    settings=load_settings(environ={},overrides={"data_dir":os.environ["DERAG_TEST_DATA_DIR"],
                          "gold_version":"fixture-gold-v1","generation":{"provider":"mock","model":"fixture-model"}})
    generator=EvaluationGenerator(failure="synthetic-error")
    retrieval=FrontendRetrieval()
    qa=QAService(settings,retriever=retrieval.search_result,document_loader=retrieval.documents,generator=generator,
                 index_version="c-fixture-index-v1")
    return create_app(settings,qa_service=qa,retrieval_service=retrieval,test_mode=True,gold_loader=dataset)


def create_unconfigured_app():
    if not os.environ.get("DERAG_TEST_DATA_DIR"):
        raise RuntimeError("An isolated data directory is required")
    settings=load_settings(environ={},overrides={"data_dir":os.environ["DERAG_TEST_DATA_DIR"]})
    return create_app(settings)


def create_real_frontend_app():
    """One-question real API acceptance; evaluation disabled, sources synthetic."""
    if (os.environ.get("DERAG_TEST_REAL_API")!="1" or not os.environ.get("DERAG_TEST_API_ENV")
            or not os.environ.get("DERAG_TEST_DATA_DIR")):
        raise RuntimeError("Explicit real-API test opt-in and existing local configuration are required")
    settings=load_settings(environ={},env_file=os.environ["DERAG_TEST_API_ENV"],
                          overrides={"data_dir":os.environ["DERAG_TEST_DATA_DIR"],"gold_version":None,
                                     "generation":{"transport":"curl"}})
    retrieval=FrontendRetrieval()
    qa=QAService(settings,retriever=retrieval.search_result,document_loader=retrieval.documents,
                 generator=ChatCompletionsClient(settings),index_version="c-fixture-index-v1")
    return create_app(settings,qa_service=qa,retrieval_service=retrieval,test_mode=True)
