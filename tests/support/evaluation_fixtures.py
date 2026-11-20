"""Deliberately synthetic 24/6 plan for software tests, never formal gold."""
import json

from app.evaluation.data import GoldCase,GoldDataset
from app.qa.client import GenerationResponse
from app.qa.errors import QAError


def dataset():
    cases=[]
    for index in range(30):
        answerable=index<24
        cases.append(GoldCase(schema_version="1.0",case_id=f"synthetic-{index:02}",
             question=f"synthetic-{'answer' if answerable else 'refuse'}-{index:02}",topic="synthetic plumbing only",
             answerable=answerable,reference_answer="GOLD_ONLY_REFERENCE" if answerable else None,
             key_facts=["GOLD_ONLY_FACT"] if answerable else [],
             evidence=[{"document_id":"fixture","article_id":"fixture-a002","start":23,"end":25,"text":"B."}] if answerable else [],
             unanswerable_reason=None if answerable else "GOLD_ONLY_REASON"))
    return GoldDataset("fixture-en-v2","fixture-gold-v1",cases,True)


class EvaluationGenerator:
    def __init__(self,*,failure=None,gate=None):
        self.messages=[]
        self.failure=failure
        self.gate=gate

    def generate(self,messages):
        self.messages.append(messages)
        if self.gate:
            self.gate.wait(5)
        question=json.loads(messages[1]["content"])["question"]
        if question==self.failure:
            raise QAError("SYNTHETIC_FAILURE","Deliberate offline test failure",503)
        refuse=question.startswith("synthetic-refuse")
        payload={"status":"insufficient" if refuse else "answered",
                 "claims":[] if refuse else [{"text":"Article 2 states B.","citation_numbers":[1]}]}
        content=json.dumps(payload)
        usage={"prompt_tokens":20,"completion_tokens":10,"total_tokens":30}
        raw={"content":content,"model":"fixture-model","usage":usage}
        return GenerationResponse(content,"fixture-model","stop",usage,"synthetic-response",raw)
