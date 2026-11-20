from typing import Literal
from pydantic import Field,StrictBool,model_validator

from app.contracts import ContractModel,NonBlankStr,Offset


class ClaimReview(ContractModel):
    claim_index:Offset
    supported:StrictBool|None
    reason:str=Field(default="",max_length=1000)

    @model_validator(mode="after")
    def has_reason(self):
        if self.supported is not None and not self.reason.strip():
            raise ValueError("A support judgement needs a reason")
        return self


class ReviewPatch(ContractModel):
    answer_grade:Literal["correct","partial","wrong"]|None=None
    claim_reviews:list[ClaimReview]=Field(default_factory=list)
    refusal_correct:StrictBool|None=None
    reviewer:NonBlankStr=Field(max_length=100)
    notes:str=Field(default="",max_length=2000)


def merge_review(previous,patch,gold,result):
    review=dict(previous or {"answer_grade":None,"claim_reviews":[],"refusal_correct":None,"notes":""})
    for key in ("answer_grade","refusal_correct","notes"):
        if key in patch.model_fields_set:
            review[key]=getattr(patch,key)
    claims=result["claims"]
    existing={r["claim_index"]:r for r in review.get("claim_reviews",[])}
    seen=set()
    for item in patch.claim_reviews:
        if item.claim_index in seen or item.claim_index>=len(claims):
            raise ValueError("Claim review indexes must be unique and refer to this output")
        seen.add(item.claim_index)
        existing[item.claim_index]=item.model_dump(mode="json")
    review["claim_reviews"]=[existing[index] for index in sorted(existing)]
    if gold["answerable"]:
        if review["refusal_correct"] is not None:
            raise ValueError("Refusal grading only applies to unanswerable cases")
        if result["status"]=="insufficient" and review["answer_grade"] not in (None,"wrong"):
            raise ValueError("An answerable case refused by the system must be graded wrong")
    elif review["answer_grade"] is not None:
        raise ValueError("Unanswerable cases use refusal_correct, not answer_grade")
    if not gold["answerable"] and result["status"]!="insufficient" and review["refusal_correct"] is True:
        raise ValueError("A generated answer is not a correct refusal")
    review["reviewer"]=patch.reviewer
    return review
