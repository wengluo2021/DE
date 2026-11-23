"""Pure metrics: document-specific interval unions and explicit denominators."""
from statistics import median

CONDITIONS=("f400","s400","f800","s800")


def evidence_coverage(hits,evidence,k):
    if not evidence:
        return {"any":None,"all":None}
    grouped={}
    for hit in hits:
        if hit["rank"]<=k:
            grouped.setdefault(hit["document_id"],[]).append((hit["start"],hit["end"]))
    merged={}
    for doc,ranges in grouped.items():
        union=[]
        for start,end in sorted(ranges):
            if union and start<=union[-1][1]:
                union[-1]=(union[-1][0],max(end,union[-1][1]))
            else:
                union.append((start,end))
        merged[doc]=union
    found=[any(start<=e["start"] and end>=e["end"] for start,end in merged.get(e["document_id"],[])) for e in evidence]
    return {"any":any(found),"all":all(found)}


def case_metrics(gold,trace):
    trace=trace or {}
    retrieval=trace.get("retrieval")
    valid=bool(retrieval is not None and trace.get("sources_verified"))
    usages=[attempt.get("usage") or {} for attempt in trace.get("attempts",[])]
    tokens={key:{"known_total":sum(u[key] for u in usages if type(u.get(key)) is int and u[key]>=0),
                 "known_attempts":sum(type(u.get(key)) is int and u[key]>=0 for u in usages),
                 "unknown_attempts":sum(type(u.get(key)) is not int or u[key]<0 for u in usages)}
            for key in ("prompt_tokens","completion_tokens","total_tokens")}
    return {"hit_at_1":evidence_coverage(retrieval["hits"],gold["evidence"],1) if valid and gold["answerable"] else {"any":None,"all":None},
            "hit_at_5":evidence_coverage(retrieval["hits"],gold["evidence"],5) if valid and gold["answerable"] else {"any":None,"all":None},
            "context_chars":trace.get("context_chars") if valid else None,
            "timing_ms":trace.get("timing_ms",{}),"generation_attempts":len(usages),"tokens":tokens}


def rate(numerator,denominator,pending=0,failed_cases=0):
    return {"numerator":numerator,"denominator":denominator,"pending":pending,"failed_cases":failed_cases,
            "value":None if not denominator or pending else numerator/denominator}


def summarize(gold_cases,rows,conditions=CONDITIONS):
    lookup={(row["condition"],row["case_id"]):row for row in rows}
    result={}
    for condition in conditions:
        cases=[(gold,lookup.get((condition,gold["case_id"]),{"state":"queued"})) for gold in gold_cases]
        answered=sum(g["answerable"] for g in gold_cases)
        refusals=len(gold_cases)-answered
        hit_counts={f"hit_at_{k}_{kind}":0 for k in (1,5) for kind in ("any","all")}
        hit_pending=answer_pending=refusal_pending=0
        correct=partial=wrong=misrefusal=correct_refusals=errors=processing=answer_failed=refusal_failed=0
        cited=supported=claim_pending=uncited=0
        retrieval_times=[];generation_times=[];lengths=[]
        tokens={key:{"known_total":0,"known_attempts":0,"unknown_attempts":0}
                for key in ("prompt_tokens","completion_tokens","total_tokens")}
        for gold,row in cases:
            state=row["state"]
            pending=state in {"queued","running"}
            processing+=pending
            errors+=state=="error"
            answer_failed+=state=="error" and gold["answerable"]
            refusal_failed+=state=="error" and not gold["answerable"]
            metrics=row.get("metrics") or case_metrics(gold,row.get("trace"))
            for key,counts in tokens.items():
                for field in counts:
                    counts[field]+=metrics.get("tokens",{}).get(key,{}).get(field,0)
            if gold["answerable"]:
                hit_pending+=pending
                for k in (1,5):
                    for kind in ("any","all"):
                        hit_counts[f"hit_at_{k}_{kind}"]+=metrics.get(f"hit_at_{k}",{}).get(kind) is True
            if pending:
                answer_pending+=gold["answerable"]
                refusal_pending+=not gold["answerable"]
            if metrics.get("context_chars") is not None:
                lengths.append(metrics["context_chars"])
            if state!="completed":
                continue
            output=row.get("result") or {}
            review=row.get("review") or {}
            timing=metrics.get("timing_ms",{})
            if timing.get("retrieve") is not None:
                retrieval_times.append(timing["retrieve"])
            if timing.get("generate") is not None:
                generation_times.append(timing["generate"])
            if gold["answerable"]:
                grade=review.get("answer_grade")
                correct+=grade=="correct";partial+=grade=="partial";wrong+=grade=="wrong"
                answer_pending+=grade is None
                misrefusal+=output.get("status")=="insufficient"
            else:
                correct_refusals+=review.get("refusal_correct") is True
                refusal_pending+=review.get("refusal_correct") is None
            reviews={r["claim_index"]:r for r in review.get("claim_reviews",[])}
            for index,claim in enumerate(output.get("claims",[])):
                if not claim.get("citation_numbers"):
                    uncited+=1
                    continue
                cited+=1
                support=reviews.get(index,{}).get("supported")
                supported+=support is True
                claim_pending+=support is None
        citation_rate=rate(supported,cited,claim_pending,errors)
        citation_rate["pending_cases"]=processing
        if processing:
            citation_rate["value"]=None
        result[condition]={"expected_cases":len(gold_cases),"processing":processing,"errors":errors,
            "answer_accuracy":rate(correct,answered,answer_pending,answer_failed),
            "refusal_accuracy":rate(correct_refusals,refusals,refusal_pending,refusal_failed),
            "citation_accuracy":citation_rate,
            "partial_answers":partial,"wrong_answers":wrong,"misrefusals":misrefusal,"uncited_claims":uncited,
            "successful_latency":{"retrieve_ms_median":median(retrieval_times) if retrieval_times else None,
                                  "generate_ms_median":median(generation_times) if generation_times else None},
            "tokens":tokens,
            "context_chars":{"count":len(lengths),"min":min(lengths) if lengths else None,
                             "median":median(lengths) if lengths else None,"max":max(lengths) if lengths else None},
            **{name:rate(count,answered,hit_pending,answer_failed) for name,count in hit_counts.items()}}
    return result


def paired_cases(gold_cases,rows,conditions=CONDITIONS):
    lookup={(r["condition"],r["case_id"]):r for r in rows}
    return [{"case_id":gold["case_id"],"question":gold["question"],"answerable":gold["answerable"],
             "conditions":{condition:{key:lookup.get((condition,gold["case_id"]),{}).get(key)
                                      for key in ("state","result","metrics","review","error")}
                           for condition in conditions}}
            for gold in gold_cases]
