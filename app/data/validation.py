"""Single validation boundary shared by preflight, preparation and evaluation."""
from app.evaluation.data import load_gold
from .corpus import corpus_loader


def validate_bundle(settings,*,corpus_only=False):
    cfg=settings.experiment
    loader=corpus_loader(cfg.data_dir,formal=cfg.mode=="formal")
    documents=loader(cfg.corpus_version)
    gold=None if corpus_only else load_gold(settings,loader)
    return {"schema_version":"1.0","state":"validated","mode":cfg.mode,
            "corpus_version":cfg.corpus_version,"gold_version":gold.gold_version if gold else None,
            "document_count":len(documents),"article_count":sum(len(d["articles"]) for d in documents),
            "text_chars":sum(len(d["text"]) for d in documents),
            "answerable_count":sum(c.answerable for c in gold.cases) if gold else None,
            "unanswerable_count":sum(not c.answerable for c in gold.cases) if gold else None,
            "corpus_only":corpus_only,"experiment_fingerprint":settings.experiment_fingerprint(),
            "external_model_calls":0}
