from app.retrieval.types import FIXTURE_CORPUS_VERSION
# 命令行只负责选配置、选数据和组装依赖，建库复用 RetrievalService。
import argparse
from pathlib import Path
import sys

from app.retrieval import RetrievalService
from app.retrieval.embedding import LocalEmbedder, MockEmbedder
from app.retrieval.types import load_config, fixture_loader, formal_loader, canonical


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
    config = load_config(args.config, data_dir=args.data_dir, model_dir=args.model_dir)
    # 默认读取 A 的正式 manifest；缺失时明确失败，不自动回退到样例。
    loader = formal_loader(Path(config["data_dir"]))
    version = args.corpus_version or config["corpus_version"]
    if args.fixtures:
        # 合成数据按 mock/real 分目录保存，与正式数据及另一种模式的索引隔离。
        loader, version = fixture_loader, FIXTURE_CORPUS_VERSION
        config["data_dir"] = str(Path(config["data_dir"]) / "b-fixtures" / ("mock" if args.mock else "real"))
    service = RetrievalService(loader, MockEmbedder() if args.mock else LocalEmbedder(config["embedding"]), config)
    print(canonical(service.build_indexes(version)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Index build failed: {exc}", file=sys.stderr)
        sys.exit(1)
