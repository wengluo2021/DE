"""CLI for the shared QA service. Synthetic evidence is always explicit."""
import argparse
import json
from pathlib import Path

from app.config import ROOT, load_settings
from app.qa.client import ChatCompletionsClient, redact
from app.qa.errors import QAError
from app.qa.service import QAService


def main(argv=None):
    parser = argparse.ArgumentParser(description="DERag evidence-grounded question answering")
    parser.add_argument("--config", default="config/experiment.json")
    parser.add_argument("--env-file")
    parser.add_argument("--transport", choices=("httpx", "curl"))
    parser.add_argument("--question", required=True)
    parser.add_argument("--condition", choices=("f400", "s400", "f800", "s800"), default="s400")
    parser.add_argument("--conversation-id")
    parser.add_argument("--fixtures", action="store_true", help="Use fixed synthetic evidence, not real retrieval")
    parser.add_argument("--mock-llm", action="store_true", help="Use the explicit test generator; requires --fixtures")
    parser.add_argument("--output", type=Path, help="Write a new JSON evidence file; existing files are never overwritten")
    args = parser.parse_args(argv)
    settings = None
    output = None
    try:
        if args.mock_llm and not args.fixtures:
            raise QAError("INVALID_REQUEST", "Mock generation requires explicit synthetic fixtures", 422)
        override = {"generation": {}}
        if args.transport:
            override["generation"]["transport"] = args.transport
        if args.mock_llm:
            override["generation"].update(provider="mock", model="fixture-model")
        settings = load_settings(args.config, env_file=args.env_file, overrides=override)
        if args.fixtures and settings.experiment.mode == "formal":
            raise QAError("INVALID_REQUEST", "Formal mode cannot use synthetic fixtures", 422)
        if args.output:
            output = args.output if args.output.is_absolute() else ROOT / args.output
            if output.exists():
                raise QAError("OUTPUT_EXISTS", "Choose a new output filename; existing evidence is preserved", 409)
        if not args.mock_llm and not settings.llm_configured:
            raise QAError("LLM_NOT_CONFIGURED", "Configure generation before making a real request", 503)
        if args.fixtures:
            from tests.support.c_fixtures import document_loader, retrieve, FixtureGenerator
            loader, retriever, index = document_loader, retrieve, "c-fixture-index-v1"
            generator = FixtureGenerator() if args.mock_llm else ChatCompletionsClient(settings)
        else:
            try:
                from app.retrieval import RetrievalService
                from app.retrieval.embedding import LocalEmbedder
                from app.retrieval.types import formal_loader
            except ImportError:
                raise QAError("RETRIEVAL_NOT_CONFIGURED", "Install and verify the retrieval dependencies before using formal evidence", 503) from None
            config = settings.retrieval_config()
            loader = formal_loader(Path(config["data_dir"]))
            retrieval = RetrievalService(loader, LocalEmbedder(config["embedding"]), config)
            with retrieval.indexes.lock():
                manifest, _ = retrieval.indexes.completed(settings.experiment.corpus_version)
            index = manifest["index_version"]
            retriever = retrieval.search_result
            generator = ChatCompletionsClient(settings)
        service = QAService(settings, retriever=retriever, document_loader=loader,
                            generator=generator, index_version=index)
        result, trace = service.ask_with_trace(args.question, args.condition,
                                              settings.experiment.corpus_version, args.conversation_id)
        record = {"state": "completed", "synthetic_evidence": args.fixtures, "mock_llm": args.mock_llm,
                  "result": result.model_dump(mode="json"), "trace": trace.to_dict(),
                  "config": settings.public_snapshot(), "experiment_fingerprint": settings.experiment_fingerprint()}
        exit_code = 0
    except QAError as exc:
        record = {"state": "failed", "error": exc.as_dict(), "trace": exc.trace}
        exit_code = 1
    except (ValueError, OSError):
        record = {"state": "failed", "error": {"code": "CONFIGURATION_ERROR", "message": "Could not load the configured inputs"}}
        exit_code = 1
    except Exception:
        record = {"state": "failed", "error": {"code": "INTERNAL_ERROR", "message": "Inspect the configured dependencies and inputs"}}
        exit_code = 1
    record = redact(record, settings.api_key() if settings else "")
    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if output is not None and record.get("error", {}).get("code") != "OUTPUT_EXISTS":
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    print(text)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
