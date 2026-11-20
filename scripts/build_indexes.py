from app.retrieval.types import FIXTURE_CORPUS_VERSION
# 命令行只负责选配置、选数据和组装依赖，建库复用 RetrievalService。
import argparse
from pathlib import Path
import sys

from app.retrieval import RetrievalService
from app.retrieval.embedding import LocalEmbedder, MockEmbedder
from app.retrieval.types import fixture_loader, canonical
from app.config import load_settings
from app.data import corpus_loader


def main():
    parser = argparse.ArgumentParser(description="Build B's four indexes; fixtures never write formal indexes")
    parser.add_argument("--config")
    parser.add_argument("--fixtures", action="store_true")
    parser.add_argument("--mock", action="store_true", help="Test vectors; requires --fixtures")
    parser.add_argument("--corpus-version")
    parser.add_argument("--data-dir")
    parser.add_argument("--model-dir")
    args = parser.parse_args()
    # 模拟向量只允许配合合成数据，避免误把它用于正式法规实验。
    if args.mock and not args.fixtures:
        parser.error("--mock requires --fixtures")
    overrides={}
    if args.data_dir:overrides["data_dir"]=args.data_dir
    if args.model_dir:overrides["embedding"]={"model_dir":args.model_dir}
    if args.corpus_version:overrides["corpus_version"]=args.corpus_version
    settings=load_settings(args.config,overrides=overrides)
    if args.fixtures and settings.experiment.mode=="formal":
        parser.error("Formal mode cannot build synthetic fixture indexes")
    config=settings.retrieval_config()
    # 默认读取 A 的正式 manifest；缺失时明确失败，不自动回退到样例。
    loader = corpus_loader(Path(config["data_dir"]),formal=settings.experiment.mode=="formal")
    version = args.corpus_version or config["corpus_version"]
    if args.fixtures:
        # 合成数据按 mock/real 分目录保存，与正式数据及另一种模式的索引隔离。
        loader, version = fixture_loader, FIXTURE_CORPUS_VERSION
        config["data_dir"] = str(Path(config["data_dir"]) / "b-fixtures" / ("mock" if args.mock else "real"))
    service = RetrievalService(loader, MockEmbedder() if args.mock else LocalEmbedder(config["embedding"]), config)
    try:
        print(canonical(service.build_indexes(version)))
    finally:
        service.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Index build failed: {exc}", file=sys.stderr)
        sys.exit(1)
