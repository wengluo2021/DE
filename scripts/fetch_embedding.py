"""显式下载固定 commit 的模型到项目目录，生成校验清单；程序启动时不自动下载。"""
import argparse
import json
from pathlib import Path
import re
import sys

from app.retrieval.types import load_config, file_hash, write_json
from app.retrieval.embedding import LocalEmbedder
from app.retrieval.errors import RetrievalError
from app.config import load_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--model-dir")
    args = parser.parse_args()
    overrides={"embedding":{"model_dir":args.model_dir}} if args.model_dir else {}
    config=load_settings(args.config,overrides=overrides).retrieval_config()["embedding"]
    # 必须固定到 40 位 commit；main/latest 后续可能变动，无法保证老师拿到同一模型。
    if not re.fullmatch(r"[0-9a-f]{40}", config["revision"]):
        raise RetrievalError("INVALID_REQUEST", "Use an immutable 40-character revision", 422)
    directory = Path(config["model_dir"])
    from huggingface_hub import snapshot_download
    # 只下载稠密向量所需的模块配置、分词器、权重和说明/许可证，不下载重复 ONNX 或稀疏权重。
    snapshot_download(repo_id=config["model_id"], revision=config["revision"], local_dir=directory,
                      allow_patterns=["*.json", "1_Pooling/config.json", "pytorch_model.bin", "model.safetensors",
                                      "sentencepiece.bpe.model", "README.md", "LICENSE"],
                      ignore_patterns=["onnx/*"], max_workers=3)
    # 清单记录相对路径和文件内容哈希；模型目录复制到其他机器后仍可校验。
    files = {p.relative_to(directory).as_posix(): file_hash(p) for p in sorted(directory.rglob("*"))
             if p.is_file() and ".cache" not in p.relative_to(directory).parts and p.name != "derag-model-manifest.json"}
    manifest = {"model_id": config["model_id"], "revision": config["revision"], "files": files}
    write_json(directory / "derag-model-manifest.json", manifest)
    # 下载后立即检查清单与实际目录；这里只校验文件，不运行模型编码。
    LocalEmbedder(config).identity()
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Model preparation failed: {exc}", file=sys.stderr)
        sys.exit(1)
