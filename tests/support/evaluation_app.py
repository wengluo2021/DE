"""Opt-in offline HTTP smoke factory. Never imported by app.main production startup."""
import os

from app.config import load_settings
from app.main import create_app
from app.qa.service import QAService
from tests.support.c_fixtures import document_loader,retrieve
from tests.support.evaluation_fixtures import dataset,EvaluationGenerator


def create_evaluation_app():
    if os.environ.get("DERAG_TEST_EVALUATION")!="1" or not os.environ.get("DERAG_TEST_DATA_DIR"):
        raise RuntimeError("Explicit isolated synthetic test opt-in is required")
    settings=load_settings(environ={},overrides={"data_dir":os.environ["DERAG_TEST_DATA_DIR"],
                          "gold_version":"fixture-gold-v1","generation":{"provider":"mock","model":"fixture-model"}})
    generator=EvaluationGenerator()
    service=QAService(settings,retriever=retrieve,document_loader=document_loader,generator=generator,
                      index_version="c-fixture-index-v1")
    app=create_app(settings,qa_service=service,test_mode=True,gold_loader=dataset)
    app.state.test_generator=generator
    return app
