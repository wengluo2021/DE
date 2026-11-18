"""两种无重叠分块：保留原文字符，返回 Python 字符下标 [start, end)。

阅读顺序：chunk_document 总入口 → _structured 结构感知 → _split_large 超长拆分。
这里不做 strip 或换行替换等清洗，否则引用位置会与 A 冻结的正文错开。
"""
import hashlib
import re

from .errors import RetrievalError
from .types import CONDITIONS, Chunk

# 章/节必须从一行开头识别；句末标点和换行则是拆分超长条文的候选边界。
HEADING = re.compile(
    r"^[ \t]*(?:第[零〇一二三四五六七八九十百千万两0-9]+[章节]|"
    r"(?:Chapter|Section)[ \t]+(?:[0-9]+|[IVXLCDM]+)\b)[^\n]*(?:\n|$)",
    re.MULTILINE | re.IGNORECASE)
# 英文句末后必须是空白或结尾，避免把 3.14 / example.org 的点当作句末。
# 这是确定性标点规则，不是能识别所有英文缩写的语言学分句器。
BOUNDARY = re.compile(
    r"[。！？；](?:[”’」』])?[ \t]*(?:\n+)?|"
    r'''[.!?;](?:["'”’])?(?=\s|$)[ \t]*(?:\n+)?|\n+''')


def _split_large(text, start, end, limit, stats):
    """将超长单元按句子/段落打包；一个句子仍超限时才按字符硬切。"""
    # 正则在局部切片上运行，m.end() 要加 start 才是完整原文中的位置。
    edges = [start] + [start + m.end() for m in BOUNDARY.finditer(text[start:end])]
    if edges[-1] != end:
        edges.append(end)
    # spans 是已确定的区间；pending 是尚可继续加入下一短句的当前块。
    spans, pending = [], None
    for a, b in zip(edges, edges[1:]):
        if a == b:
            continue
        if b - a > limit:
            if pending:
                spans.append(pending)
                pending = None
            # 统计发生了多少次“单句也装不下”的回退，不是统计生成了多少块。
            stats["long_sentence_fallback"] += 1
            spans.extend((p, min(p + limit, b)) for p in range(a, b, limit))
        elif pending and b - pending[0] <= limit:
            pending = (pending[0], b)
        else:
            if pending:
                spans.append(pending)
            pending = (a, b)
    if pending:
        spans.append(pending)
    return spans


def _structured(doc, limit, stats):
    """优先保留完整法条，同章同节内能装下就合并；章/节之间强制分开。"""
    text, articles = doc["text"], doc["articles"]
    # 以 A 标注的条文区间为准，仅在区间外找章/节标题，避免误判正文中的引用或示例。
    headings = [m for m in HEADING.finditer(text)
                if not any(max(m.start(), a["start"]) < min(m.end(), a["end"]) for a in articles)]
    # hard 记录不能跨越的位置；下一章标题从自己的块开始，不被上一条吞进去。
    hard = sorted({0, len(text), *(m.start() for m in headings)})
    if not articles:
        stats["no_article_fallback"] += 1
    # 即使正文里没有识别到标题，A 标注的章/节发生变化时也必须分块。
    for previous, current in zip(articles, articles[1:]):
        if (previous.get("chapter"), previous.get("section")) != (current.get("chapter"), current.get("section")):
            between = [m.start() for m in headings if previous["end"] <= m.start() <= current["start"]]
            hard.append(between[0] if between else current["start"])
    hard = sorted(set(hard))
    result = []
    for left, right in zip(hard, hard[1:]):
        starts = [a["start"] for a in articles if left <= a["start"] < right]
        # 标题/前言归入首条；条间空白归入前条，确保所有字符都恰好被覆盖一次。
        units = ([left] + starts[1:] + [right]) if starts else [left, right]
        pending = None
        for a, b in zip(units, units[1:]):
            if b - a > limit:
                if pending:
                    result.append(pending)
                    pending = None
                # 标题加首条太长时，允许先拆开标题，再对各部分按句子/段落拆分。
                title_ends = [m.end() for m in headings if a <= m.start() < m.end() < b]
                cuts = [a] + title_ends + [b]
                for x, y in zip(cuts, cuts[1:]):
                    result.extend(_split_large(text, x, y, limit, stats))
            elif pending and b - pending[0] <= limit:
                # 贪心合并：同一章/节的下一完整单元仍装得下，就扩展当前块。
                pending = (pending[0], b)
            else:
                if pending:
                    result.append(pending)
                pending = (a, b)
        if pending:
            result.append(pending)
    return result


def chunk_document(doc: dict, method: str, max_chars: int, *, condition=None, stats=None) -> list[Chunk]:
    """公共分块入口；max_chars 按 Python len 计数，标点、空格、换行都算字符。"""
    if type(max_chars) is not int or max_chars <= 0 or method not in ("fixed", "structured"):
        raise RetrievalError("INVALID_REQUEST", "Invalid chunk method/character limit", 422)
    # 调用方传入的空字典也要保留，便于累计多个文档的回退和空文档统计。
    stats = stats if stats is not None else {}
    for key in ("long_sentence_fallback", "no_article_fallback", "empty_documents"):
        stats.setdefault(key, 0)
    text = doc["text"]
    if not text:
        stats["empty_documents"] += 1
        return []
    condition = condition or ("f" if method == "fixed" else "s") + str(max_chars)
    # 固定窗口直接每 max_chars 字切一次；结构法则先找法条/章节边界。
    spans = ([(s, min(s + max_chars, len(text))) for s in range(0, len(text), max_chars)]
             if method == "fixed" else _structured(doc, max_chars, stats))
    chunks = []
    for start, end in spans:
        # 同一语料版本、方法、长度和位置生成同一个 ID，重复建库可覆盖而不会重复插入。
        key = f"{doc['corpus_version']}|{method}|{max_chars}|{doc['document_id']}|{start}|{end}"
        # article_ids 按实际区间相交判定，标题或空白块可能没有条号。
        chunks.append(Chunk(chunk_id=hashlib.sha256(key.encode("utf-8")).hexdigest(),
                            corpus_version=doc["corpus_version"], condition=condition,
                            boundary_method=method, target_chars=max_chars,
                            document_id=doc["document_id"], start=start, end=end,
                            text=text[start:end], article_ids=[a["article_id"] for a in doc["articles"]
                            if max(start, a["start"]) < min(end, a["end"])]))
    validate_coverage(doc, chunks, max_chars)
    return chunks


def validate_coverage(doc, chunks, limit):
    """用连续游标检查：没有漏字、重复、越界、超长或擅自改写原文。"""
    cursor = 0
    for chunk in chunks:
        if not (chunk["start"] == cursor < chunk["end"] <= len(doc["text"]) and
                chunk["end"] - cursor <= limit and chunk["text"] == doc["text"][cursor:chunk["end"]]):
            raise RetrievalError("SOURCE_MISMATCH", "Chunks do not exactly cover frozen text")
        cursor = chunk["end"]
    if cursor != len(doc["text"]):
        raise RetrievalError("SOURCE_MISMATCH", "Chunks omit source characters")


def chunks_for_condition(doc, condition, stats=None):
    """把 f400/s400/f800/s800 映射到同一套分块函数，供建库和校验共同调用。"""
    if condition not in CONDITIONS:
        raise RetrievalError("INVALID_REQUEST", "Unknown condition", 422)
    method, limit = CONDITIONS[condition]
    return chunk_document(doc, method, limit, condition=condition, stats=stats)
