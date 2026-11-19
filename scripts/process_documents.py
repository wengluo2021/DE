# EUR-Lex HTML cleaner. Rule version eurlex_html_v1.
# One block is one line. Major parts are separated by a blank line.
# Main articles are div.eli-subdivision nodes whose id is art_<number>.
# Cross-references and annex correlation cells stay inside their own text.

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString

CLEANING_RULE_VERSION = "eurlex_html_v1"
ARTICLE_ID_RE = re.compile(r"^art_\d+[a-z]?$")
ARTICLE_HEADING_RE = re.compile(r"^Article \d+[a-z]?$")
CHAPTER_CONTAINER_RE = re.compile(r"^cpt_[0-9IVXLCDM]+$")
SECTION_CONTAINER_RE = re.compile(r"^cpt_([0-9IVXLCDM]+)\.sct_(\d+)$")
SENTENCE_GLUE_RE = re.compile(r"(?<=[0-9a-z])([.?!])(?=[A-Z])")
INLINE_TAGS = {"a", "span", "em", "strong", "b", "i", "sup", "sub", "abbr"}
HEADING_CLASSES = {
    "oj-doc-ti",
    "oj-ti-grseq-1",
    "oj-ti-tbl",
    "oj-ti-section-1",
    "oj-ti-section-2",
    "oj-sti-art",
    "doc-ti",
    "ti-grseq-1",
}


class Progress:
    """实时进度与剩余时间。

    示例:
        progress = Progress(total=10)
        progress.advance()
        progress.finish()
    输出格式: [Progress] 12.50% Elapsed: 00:00:01 Remaining: 00:00:07
    """

    def __init__(self, total: int) -> None:
        self.total = max(int(total), 1)
        self.done = 0
        self.started = time.monotonic()
        self._render()

    def advance(self, steps: int = 1) -> None:
        self.done += steps
        self._render()

    def finish(self) -> None:
        self.done = self.total
        self._render(final=True)

    def _render(self, final: bool = False) -> None:
        elapsed = time.monotonic() - self.started
        ratio = min(self.done / self.total, 1.0)
        remaining = 0.0 if ratio <= 0 or ratio >= 1 else elapsed * (1 - ratio) / ratio
        line = (
            f"[Progress] {ratio * 100:6.2f}% "
            f"Elapsed: {_format_duration(elapsed)} "
            f"Remaining: {_format_duration(remaining)}"
        )
        print("\r" + line, end="", flush=True)
        if final:
            print(flush=True)


def _format_duration(seconds: float) -> str:
    whole = max(0, int(seconds + 0.5))
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass
class Block:
    kind: str
    text: str
    html_id: str | None = None
    footnote_refs: list[str] = field(default_factory=list)
    block_id: str = ""
    start: int | None = None
    end: int | None = None
    footnote_record: dict | None = None


@dataclass
class RenderContext:
    footnotes: list[dict]
    tables: list[dict]
    scope: str
    table_owner_id: str


def fail(document_id: str, path: Path | None, message: str) -> None:
    location = f"document_id={document_id}"
    if path is not None:
        location += f" file={path}"
    print(f"process_documents.py: {location}: {message}", file=sys.stderr)
    raise SystemExit(1)


def class_list(tag) -> list[str]:
    value = tag.get("class") or []
    if isinstance(value, str):
        return value.split()
    return list(value)


def has_class(tag, name: str) -> bool:
    return name in class_list(tag)


def element_children(tag):
    return [child for child in tag.children if getattr(child, "name", None)]


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_inline(text: str, *, strip: bool) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    text = SENTENCE_GLUE_RE.sub(r"\1 ", text)
    return text.strip() if strip else text


def note_marker(anchor) -> tuple[str, str | None]:
    raw_text = anchor.get_text()
    leading_space = bool(raw_text) and raw_text[0].isspace()
    raw = " ".join(raw_text.split())
    inner = raw[1:-1].strip() if raw.startswith("(") and raw.endswith(")") else raw
    href = anchor.get("href") or ""
    ref = href.split("#", 1)[1] if "#" in href else None
    marker = f"({inner})"
    if leading_space:
        marker = " " + marker
    return marker, ref


def render_inline(node, *, strip: bool) -> tuple[str, list[str]]:
    if getattr(node, "name", None) == "a" and (node.get("id") or "").startswith("ntc"):
        marker, ref = note_marker(node)
        return marker, ([ref] if ref else [])
    refs: list[str] = []
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            parts.append(str(child))
            continue
        if not getattr(child, "name", None):
            continue
        if child.name == "br":
            parts.append(" ")
            continue
        if child.name == "a" and (child.get("id") or "").startswith("ntc"):
            marker, ref = note_marker(child)
            parts.append(marker)
            if ref:
                refs.append(ref)
            continue
        text, subrefs = render_inline(child, strip=False)
        parts.append(text)
        refs.extend(subrefs)
    return normalize_inline("".join(parts), strip=strip), unique(refs)


def is_note_paragraph(tag) -> bool:
    return getattr(tag, "name", None) == "p" and (has_class(tag, "oj-note") or has_class(tag, "note"))


def is_running_header(node) -> bool:
    return getattr(node, "name", None) == "table" and (
        node.find(class_="oj-hd-date") is not None or node.find(class_="hd-date") is not None
    )


def classify_p(tag) -> str:
    classes = set(class_list(tag))
    if "oj-note" in classes or "note" in classes:
        return "footnote"
    if "oj-ti-art" in classes or "ti-art" in classes:
        return "quoted_heading"
    if "oj-signatory" in classes or "signatory" in classes:
        return "signature_line"
    if classes & HEADING_CLASSES:
        return "heading"
    return "paragraph"


def is_inline(tag) -> bool:
    if tag.name in INLINE_TAGS or tag.name == "br":
        return True
    return tag.name == "div" and has_class(tag, "oj-box")


def own_rows(table):
    rows = []
    for child in table.children:
        if getattr(child, "name", None) == "tr":
            rows.append(child)
        elif getattr(child, "name", None) in {"tbody", "thead", "tfoot"}:
            rows.extend(row for row in child.children if getattr(row, "name", None) == "tr")
    return rows


def own_cells(row):
    return [cell for cell in row.children if getattr(cell, "name", None) in {"td", "th"}]


def parse_footnote(paragraph, scope: str) -> dict:
    anchor = paragraph.find("a", id=re.compile(r"^ntr"))
    text, _refs = render_inline(paragraph, strip=True)
    match = re.match(r"^\(([^)]+)\)", text)
    marker = match.group(1) if match else ""
    return {
        "marker": marker,
        "scope": scope,
        "html_id": anchor.get("id") if anchor else paragraph.get("id"),
        "text": text,
        "referenced_by": [],
    }


def render_blocks(node, ctx: RenderContext) -> list[Block]:
    if getattr(node, "name", None) == "table":
        return render_table(node, ctx)
    if getattr(node, "name", None) == "p":
        if is_note_paragraph(node):
            footnote = parse_footnote(node, ctx.scope)
            ctx.footnotes.append(footnote)
            return [Block("footnote", footnote["text"], footnote["html_id"], footnote_record=footnote)]
        text, refs = render_inline(node, strip=True)
        if not text:
            return []
        return [Block(classify_p(node), text, node.get("id"), refs)]
    blocks: list[Block] = []
    pending: list[str] = []
    pending_refs: list[str] = []

    def flush() -> None:
        text = normalize_inline("".join(pending), strip=True)
        refs = unique(pending_refs)
        pending.clear()
        pending_refs.clear()
        if text:
            blocks.append(Block("paragraph", text, None, refs))

    for child in node.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            value = str(child)
            if value.strip():
                pending.append(value)
            elif pending and value:
                pending.append(" ")
            continue
        if not getattr(child, "name", None):
            continue
        if child.name in {"script", "style", "button", "noscript", "hr", "colgroup", "col"}:
            continue
        if child.name == "a" and has_class(child, "linkToTop"):
            continue
        if is_running_header(child):
            continue
        if is_inline(child):
            text, refs = render_inline(child, strip=False)
            if text:
                pending.append(text)
                pending_refs.extend(refs)
            continue
        flush()
        if is_note_paragraph(child):
            footnote = parse_footnote(child, ctx.scope)
            ctx.footnotes.append(footnote)
            blocks.append(Block("footnote", footnote["text"], footnote["html_id"], footnote_record=footnote))
        elif child.name == "p":
            text, refs = render_inline(child, strip=True)
            if text:
                blocks.append(Block(classify_p(child), text, child.get("id"), refs))
        elif child.name == "table":
            blocks.extend(render_table(child, ctx))
        else:
            blocks.extend(render_blocks(child, ctx))
    flush()
    return blocks


def render_table(table, ctx: RenderContext) -> list[Block]:
    rows = own_rows(table)
    counts = [len(own_cells(row)) for row in rows]
    if has_class(table, "oj-table") or any(count != 2 for count in counts):
        return render_data_table(table, rows, ctx)
    return render_list_table(rows, ctx)


def render_list_table(rows, ctx: RenderContext) -> list[Block]:
    blocks: list[Block] = []
    for row in rows:
        cells = own_cells(row)
        if len(cells) != 2:
            continue
        marker, _marker_refs = cell_plain_text(cells[0], ctx)
        content = render_blocks(cells[1], ctx)
        if marker and content:
            content[0].text = f"{marker} {content[0].text}".strip()
            content[0].kind = "list_item"
            blocks.extend(content)
        elif marker:
            blocks.append(Block("list_item", marker, row.get("id")))
        else:
            blocks.extend(content)
    return blocks


def cell_plain_text(cell, ctx: RenderContext) -> tuple[str, list[str]]:
    blocks = render_blocks(cell, ctx)
    refs = [ref for block in blocks for ref in block.footnote_refs]
    return " ".join(block.text for block in blocks if block.text).strip(), unique(refs)


def render_data_table(table, rows, ctx: RenderContext) -> list[Block]:
    rendered_rows: list[list[str]] = []
    blocks: list[Block] = []
    for row in rows:
        cell_values: list[str] = []
        refs: list[str] = []
        for cell in own_cells(row):
            text, cell_refs = cell_plain_text(cell, ctx)
            cell_values.append(text)
            refs.extend(cell_refs)
        if not any(cell_values):
            continue
        rendered_rows.append(cell_values)
        blocks.append(Block("table_row", " | ".join(cell_values), row.get("id"), unique(refs)))
    if rendered_rows:
        ctx.table_index = getattr(ctx, "table_index", 0) + 1
        ctx.tables.append(
            {
                "table_id": f"{ctx.table_owner_id}:table:{ctx.table_index}",
                "rows": rendered_rows,
            }
        )
    return blocks


def assign_ids(blocks: list[Block], prefix: str) -> None:
    for index, block in enumerate(blocks, start=1):
        block.block_id = f"{prefix}:block:{index}"


def pack(lines: list[str]) -> str:
    return "\n".join(line.rstrip() for line in lines if line.strip())


def block_payload(block: Block) -> dict:
    payload = {
        "block_id": block.block_id,
        "kind": block.kind,
        "start": block.start,
        "end": block.end,
        "text": block.text,
    }
    if block.html_id:
        payload["html_id"] = block.html_id
    if block.footnote_refs:
        payload["footnote_refs"] = block.footnote_refs
    return payload


def parse_preamble(node, ctx: RenderContext) -> tuple[list[Block], list[dict]]:
    blocks: list[Block] = []
    recitals: list[dict] = []
    for child in element_children(node):
        html_id = child.get("id") or ""
        if html_id.startswith("rct_"):
            start = len(blocks)
            rendered = render_blocks(child, ctx)
            for block in rendered:
                block.kind = "recital"
            blocks.extend(rendered)
            refs = unique([ref for block in rendered for ref in block.footnote_refs])
            recitals.append(
                {
                    "number": html_id.split("_", 1)[1],
                    "html_id": html_id,
                    "text": "\n".join(block.text for block in rendered),
                    "footnote_refs": refs,
                    "block_start": start,
                    "block_count": len(rendered),
                }
            )
        elif html_id.startswith("cit_"):
            rendered = render_blocks(child, ctx)
            for block in rendered:
                if block.kind == "paragraph":
                    block.kind = "citation"
            blocks.extend(rendered)
        else:
            blocks.extend(render_blocks(child, ctx))
    return blocks, recitals


def parse_article(
    node,
    document_id: str,
    chapter_id: str | None,
    ctx: RenderContext,
    section_id: str | None = None,
    section_number: str | None = None,
) -> dict:
    html_id = node.get("id") or ""
    number = ""
    subtitle = None
    skipped_title = False
    skipped_subtitle = False
    body_roots = []
    for child in element_children(node):
        if not skipped_title and child.name == "p" and has_class(child, "oj-ti-art"):
            text, _refs = render_inline(child, strip=True)
            if ARTICLE_HEADING_RE.fullmatch(text):
                number = text.split()[1]
                skipped_title = True
                continue
        if not skipped_subtitle and child.name == "div" and has_class(child, "eli-title"):
            subtitle, _refs = render_inline(child, strip=True)
            skipped_subtitle = True
            continue
        body_roots.append(child)
    expected = html_id.removeprefix("art_")
    if number != expected:
        fail(document_id, None, f"article heading {number!r} does not match html id {html_id}")
    article_id = f"{document_id}:article:{number}"
    saved_owner = ctx.table_owner_id
    ctx.table_owner_id = article_id
    blocks: list[Block] = []
    for child in body_roots:
        blocks.extend(render_blocks(child, ctx))
    ctx.table_owner_id = saved_owner
    assign_ids(blocks, article_id)
    lines = [f"Article {number}"]
    if subtitle:
        lines.append(subtitle)
    lines.extend(block.text for block in blocks)
    return {
        "article_id": article_id,
        "role": "main_article",
        "number": number,
        "heading": subtitle,
        "html_id": html_id,
        "chapter_id": chapter_id,
        "section_id": section_id,
        "section_number": section_number,
        "blocks": [block_payload(block) for block in blocks],
        "text": pack(lines),
        "_blocks": blocks,
    }


def chapter_article_nodes(chapter):
    found = []
    for node in chapter.find_all("div", id=ARTICLE_ID_RE):
        if "eli-subdivision" not in class_list(node):
            continue
        parent = node.find_parent("div", id=ARTICLE_ID_RE)
        if parent is not None:
            continue
        found.append(node)
    return found


def join_parts(head: list[str], parts: list[str]) -> str:
    text = pack(head)
    body = "\n\n".join(part for part in parts if part)
    if text and body:
        return f"{text}\n\n{body}"
    return text or body


def parse_section(
    node,
    document_id: str,
    chapter_id: str,
    chapter_number: str,
    ctx: RenderContext,
    progress: Progress,
) -> dict:
    html_id = node.get("id") or ""
    match = SECTION_CONTAINER_RE.fullmatch(html_id)
    if match is None or match.group(1) != chapter_number:
        fail(document_id, None, f"section {html_id} does not belong to chapter {chapter_number}")
    section_number = match.group(2)
    section_id = f"{document_id}:chapter:{chapter_number}:section:{section_number}"
    label = None
    heading = None
    for child in element_children(node):
        if child.name == "p" and has_class(child, "oj-ti-section-1"):
            label, _refs = render_inline(child, strip=True)
        elif child.name == "div" and has_class(child, "eli-title"):
            heading, _refs = render_inline(child, strip=True)
    articles = []
    for child in element_children(node):
        child_id = child.get("id") or ""
        if ARTICLE_ID_RE.fullmatch(child_id) and "eli-subdivision" in class_list(child):
            articles.append(
                parse_article(child, document_id, chapter_id, ctx, section_id, section_number)
            )
            progress.advance()
    return {
        "structure_id": section_id,
        "structure_type": "section",
        "html_id": html_id,
        "number": section_number,
        "label": label,
        "heading": heading,
        "chapter_id": chapter_id,
        "article_ids": [article["article_id"] for article in articles],
        "text": join_parts([line for line in (label, heading) if line], [article["text"] for article in articles]),
        "_articles": articles,
    }


def parse_chapter(node, document_id: str, ctx: RenderContext, progress: Progress) -> dict:
    html_id = node.get("id") or ""
    roman = html_id.removeprefix("cpt_")
    chapter_id = f"{document_id}:chapter:{roman}"
    label = None
    heading = None
    for child in element_children(node):
        if child.name == "p" and has_class(child, "oj-ti-section-1"):
            label, _refs = render_inline(child, strip=True)
        elif child.name == "div" and has_class(child, "eli-title"):
            heading, _refs = render_inline(child, strip=True)
    lines = [line for line in (label, heading) if line]
    has_sections = any(
        SECTION_CONTAINER_RE.fullmatch(child.get("id") or "") for child in element_children(node)
    )
    if has_sections:
        articles = []
        sections = []
        body = []
        for child in element_children(node):
            child_id = child.get("id") or ""
            if ARTICLE_ID_RE.fullmatch(child_id) and "eli-subdivision" in class_list(child):
                article = parse_article(child, document_id, chapter_id, ctx)
                articles.append(article)
                body.append(("article", article))
                progress.advance()
            elif SECTION_CONTAINER_RE.fullmatch(child_id):
                section = parse_section(child, document_id, chapter_id, roman, ctx, progress)
                sections.append(section)
                articles.extend(section["_articles"])
                body.append(("section", section))
        return {
            "structure_id": chapter_id,
            "structure_type": "chapter",
            "html_id": html_id,
            "number": roman,
            "label": label,
            "heading": heading,
            "article_ids": [article["article_id"] for article in articles],
            "text": join_parts(lines, [part["text"] for _kind, part in body]),
            "_articles": articles,
            "_sections": sections,
            "_body": body,
        }
    articles = []
    for article_node in chapter_article_nodes(node):
        articles.append(parse_article(article_node, document_id, chapter_id, ctx))
        progress.advance()
    article_text = "\n\n".join(article["text"] for article in articles)
    text = pack(lines)
    if article_text:
        text = f"{text}\n\n{article_text}" if text else article_text
    return {
        "structure_id": chapter_id,
        "structure_type": "chapter",
        "html_id": html_id,
        "number": roman,
        "label": label,
        "heading": heading,
        "article_ids": [article["article_id"] for article in articles],
        "text": text,
        "_articles": articles,
    }


def parse_annex(node, document_id: str, ctx: RenderContext) -> dict:
    html_id = node.get("id") or ""
    label = html_id.removeprefix("anx_")
    annex_id = f"{document_id}:annex:{label}"
    ctx.scope = f"annex-{label}"
    ctx.table_owner_id = annex_id
    ctx.table_index = 0
    blocks = render_blocks(node, ctx)
    assign_ids(blocks, annex_id)
    generated = f"ANNEX {label}"
    heading = next((block.text for block in blocks if block.text), "")
    # anx_I stays "ANNEX I". A bare "ANNEX" heading must not become "ANNEX 1".
    display = heading if heading.startswith("ANNEX") and heading != generated and len(heading) <= 40 else generated
    return {
        "structure_id": annex_id,
        "structure_type": "annex",
        "html_id": html_id,
        "label": display,
        "blocks": [block_payload(block) for block in blocks],
        "tables": ctx.tables,
        "text": pack(block.text for block in blocks),
        "_blocks": blocks,
    }


def is_legacy_act(document) -> bool:
    """旧式 EUR-Lex 正文用 p.ti-art，没有 eli-subdivision 条文容器。"""
    return document.find("p", class_="ti-art") is not None and document.find("div", class_="eli-subdivision") is None


def legacy_host(document):
    title = document.find("p", class_="doc-ti")
    if title is None or title.parent is None:
        fail(document.get("id") or "legacy", None, "old-style act title is missing")
    return title.parent


def is_annex_container(node) -> bool:
    if getattr(node, "name", None) != "div":
        return False
    heading = node.find("p", class_="doc-ti")
    if heading is None:
        return False
    text, _refs = render_inline(heading, strip=True)
    return text == "ANNEX"


def is_legacy_boundary(node) -> bool:
    if is_annex_container(node) or (node.name == "div" and has_class(node, "final")):
        return True
    return node.name == "p" and (has_class(node, "ti-art") or has_class(node, "note"))


def legacy_visible_nodes(document) -> list:
    return [child for child in element_children(legacy_host(document)) if not skip_node(child)]


def legacy_work_count(document) -> int:
    nodes = legacy_visible_nodes(document)
    articles = sum(1 for node in nodes if node.name == "p" and has_class(node, "ti-art"))
    notes = sum(
        1
        for node in nodes
        if node.name == "p" and has_class(node, "note") and node.find("a", id=re.compile(r"^ntr")) is not None
    )
    annexes = sum(1 for node in nodes if is_annex_container(node))
    return articles + notes + annexes + 3


def parse_legacy_article(heading, body_nodes, document_id: str, ctx: RenderContext) -> dict:
    text, _refs = render_inline(heading, strip=True)
    if not ARTICLE_HEADING_RE.fullmatch(text):
        fail(document_id, None, f"old-style article heading {text!r} is not a main article title")
    number = text.split()[1]
    article_id = f"{document_id}:article:{number}"
    saved_owner = ctx.table_owner_id
    ctx.table_owner_id = article_id
    blocks: list[Block] = []
    for node in body_nodes:
        blocks.extend(render_blocks(node, ctx))
    ctx.table_owner_id = saved_owner
    assign_ids(blocks, article_id)
    lines = [f"Article {number}", *(block.text for block in blocks)]
    return {
        "article_id": article_id,
        "role": "main_article",
        "number": number,
        "heading": None,
        "html_id": heading.get("id"),
        "chapter_id": None,
        "section_id": None,
        "section_number": None,
        "blocks": [block_payload(block) for block in blocks],
        "text": pack(lines),
        "_blocks": blocks,
    }


def parse_legacy_preamble(nodes, document_id: str, ctx: RenderContext) -> tuple[list[Block], list[dict]]:
    blocks: list[Block] = []
    recitals: list[dict] = []
    ordinal = 0
    for node in nodes:
        start = len(blocks)
        rendered = render_blocks(node, ctx)
        text = "\n".join(block.text for block in rendered)
        if text.startswith("Whereas"):
            for block in rendered:
                block.kind = "recital"
            ordinal += 1
            recitals.append(
                {
                    "number": None,
                    "ordinal": str(ordinal),
                    "official_number": None,
                    "numbering": "unnumbered_whereas_paragraph",
                    "html_id": node.get("id"),
                    "text": text,
                    "footnote_refs": unique([ref for block in rendered for ref in block.footnote_refs]),
                    "block_start": start,
                    "block_count": len(rendered),
                }
            )
        elif text.startswith("Having regard") or text.startswith("In cooperation"):
            for block in rendered:
                if block.kind == "paragraph":
                    block.kind = "citation"
        blocks.extend(rendered)
    assign_ids(blocks, f"{document_id}:preamble")
    for recital in recitals:
        start = recital.pop("block_start")
        count = recital.pop("block_count")
        recital["structure_id"] = f"{document_id}:recital:{recital['ordinal']}"
        recital["block_ids"] = [blocks[start + offset].block_id for offset in range(count)]
    return blocks, recitals


def append_legacy_note(paragraph, ctx_doc: dict) -> bool:
    footnote = parse_footnote(paragraph, "act")
    if not footnote.get("html_id"):
        if not ctx_doc["footnotes"]:
            fail(ctx_doc["document_id"], None, "old-style footnote continuation has no preceding marker")
        previous = ctx_doc["footnotes"][-1]
        previous["text"] = f"{previous['text']} {footnote['text']}".strip()
        ctx_doc["act_footnote_blocks"][-1].text = previous["text"]
        return False
    ctx_doc["footnotes"].append(footnote)
    ctx_doc["act_footnote_blocks"].append(
        Block("footnote", footnote["text"], footnote["html_id"], footnote_record=footnote)
    )
    return True


def parse_legacy_annex(node, document_id: str, ctx: RenderContext) -> dict:
    annex_id = f"{document_id}:annex:1"
    ctx.scope = "annex-1"
    ctx.table_owner_id = annex_id
    ctx.table_index = 0
    blocks = render_blocks(node, ctx)
    assign_ids(blocks, annex_id)
    heading = next((block.text for block in blocks if block.text), "")
    if heading != "ANNEX":
        fail(document_id, None, f"old-style annex heading is {heading!r}")
    return {
        "structure_id": annex_id,
        "structure_type": "annex",
        "html_id": node.get("id"),
        "label": "ANNEX",
        "blocks": [block_payload(block) for block in blocks],
        "tables": ctx.tables,
        "text": pack(block.text for block in blocks),
        "_blocks": blocks,
    }


def parse_legacy(document, ctx_doc: dict, ctx: RenderContext, progress: Progress) -> None:
    document_id = ctx_doc["document_id"]
    nodes = legacy_visible_nodes(document)
    index = 0
    title_nodes = []
    while index < len(nodes) and nodes[index].name == "p" and has_class(nodes[index], "doc-ti"):
        title_nodes.append(nodes[index])
        index += 1
    if not title_nodes:
        fail(document_id, None, "old-style act has no title before the articles")
    title_blocks: list[Block] = []
    for node in title_nodes:
        title_blocks.extend(render_blocks(node, ctx))
    assign_ids(title_blocks, f"{document_id}:title")
    ctx_doc["title_blocks"] = title_blocks
    progress.advance()

    preamble_nodes = []
    while index < len(nodes) and not (nodes[index].name == "p" and has_class(nodes[index], "ti-art")):
        preamble_nodes.append(nodes[index])
        index += 1
    preamble_blocks, recitals = parse_legacy_preamble(preamble_nodes, document_id, ctx)
    ctx_doc["preamble_blocks"] = preamble_blocks
    ctx_doc["recitals"] = recitals
    ctx_doc["preamble_html_id"] = None
    progress.advance()

    while index < len(nodes) and nodes[index].name == "p" and has_class(nodes[index], "ti-art"):
        heading = nodes[index]
        index += 1
        body = []
        while index < len(nodes) and not is_legacy_boundary(nodes[index]):
            body.append(nodes[index])
            index += 1
        article = parse_legacy_article(heading, body, document_id, ctx)
        ctx_doc["loose_articles"].append(article)
        ctx_doc["body"].append(("article", article))
        progress.advance()
    if not ctx_doc["body"]:
        fail(document_id, None, "old-style act has no p.ti-art main articles")
    if index >= len(nodes) or not has_class(nodes[index], "final"):
        fail(document_id, None, "the last main article does not end at the signature")
    signature_blocks = render_blocks(nodes[index], ctx)
    assign_ids(signature_blocks, f"{document_id}:signature")
    ctx_doc["signature_blocks"] = signature_blocks
    ctx_doc["signature_html_id"] = None
    index += 1
    progress.advance()

    while index < len(nodes) and nodes[index].name == "p" and has_class(nodes[index], "note"):
        if append_legacy_note(nodes[index], ctx_doc):
            progress.advance()
        index += 1
    annexes = [node for node in nodes[index:] if is_annex_container(node)]
    leftover = [node for node in nodes[index:] if not is_annex_container(node)]
    if leftover or len(annexes) != 1:
        fail(document_id, None, "old-style notes or annex boundary is incomplete")
    annex_ctx = RenderContext([], [], "annex-1", f"{document_id}:annex:1")
    annex = parse_legacy_annex(annexes[0], document_id, annex_ctx)
    ctx_doc["annexes"].append(annex)
    ctx_doc["footnotes"].extend(annex_ctx.footnotes)
    progress.advance()


def is_work(node) -> bool:
    if getattr(node, "name", None) == "p" and has_class(node, "oj-note"):
        return node.find_parent("div", id=re.compile(r"^anx_")) is None
    if getattr(node, "name", None) != "div":
        return False
    html_id = node.get("id") or ""
    if html_id in {"pbl_1", "fnp_1"} or CHAPTER_CONTAINER_RE.fullmatch(html_id) or html_id.startswith("anx_"):
        return True
    if ARTICLE_ID_RE.fullmatch(html_id) and "eli-subdivision" in class_list(node):
        return node.find_parent("div", id=re.compile(r"^anx_")) is None
    if has_class(node, "eli-main-title"):
        return node.find_parent("div", id=re.compile(r"^anx_")) is None
    return False


def skip_node(node) -> bool:
    if node.name in {"script", "style", "button", "noscript", "hr"}:
        return True
    if node.name == "a" and has_class(node, "linkToTop"):
        return True
    if is_running_header(node):
        return True
    return False


def walk(node, ctx_doc: dict, ctx: RenderContext, progress: Progress) -> None:
    for child in element_children(node):
        if skip_node(child):
            continue
        if is_work(child):
            handle(child, ctx_doc, ctx, progress)
            continue
        if child.name == "div":
            walk(child, ctx_doc, ctx, progress)


def handle(node, ctx_doc: dict, ctx: RenderContext, progress: Progress) -> None:
    html_id = node.get("id") or ""
    document_id = ctx_doc["document_id"]
    if has_class(node, "eli-main-title"):
        blocks = render_blocks(node, ctx)
        assign_ids(blocks, f"{document_id}:title")
        ctx_doc["title_blocks"] = blocks
        progress.advance()
        return
    if html_id == "pbl_1":
        blocks, recitals = parse_preamble(node, ctx)
        assign_ids(blocks, f"{document_id}:preamble")
        for recital in recitals:
            start = recital.pop("block_start")
            count = recital.pop("block_count")
            recital["structure_id"] = f"{document_id}:recital:{recital['number']}"
            recital["block_ids"] = [blocks[start + offset].block_id for offset in range(count)]
        ctx_doc["preamble_blocks"] = blocks
        ctx_doc["recitals"] = recitals
        progress.advance()
        return
    if CHAPTER_CONTAINER_RE.fullmatch(html_id):
        chapter = parse_chapter(node, document_id, ctx, progress)
        ctx_doc["chapters"].append(chapter)
        ctx_doc["body"].append(("chapter", chapter))
        progress.advance()
        return
    if ARTICLE_ID_RE.fullmatch(html_id) and "eli-subdivision" in class_list(node):
        if node.find_parent("div", id=re.compile(r"^cpt_")) is not None:
            return
        article = parse_article(node, document_id, None, ctx)
        ctx_doc["loose_articles"].append(article)
        ctx_doc["body"].append(("article", article))
        progress.advance()
        return
    if html_id == "fnp_1":
        blocks = render_blocks(node, ctx)
        assign_ids(blocks, f"{document_id}:signature")
        ctx_doc["signature_blocks"] = blocks
        progress.advance()
        return
    if html_id.startswith("anx_"):
        annex_tables: list[dict] = []
        annex_footnotes: list[dict] = []
        annex_ctx = RenderContext(annex_footnotes, annex_tables, "act", "")
        annex = parse_annex(node, document_id, annex_ctx)
        ctx_doc["annexes"].append(annex)
        ctx_doc["footnotes"].extend(annex_footnotes)
        progress.advance()
        return
    if node.name == "p" and has_class(node, "oj-note"):
        footnote = parse_footnote(node, "act")
        ctx_doc["footnotes"].append(footnote)
        ctx_doc["act_footnote_blocks"].append(
            Block("footnote", footnote["text"], footnote["html_id"], footnote_record=footnote)
        )
        progress.advance()


def link_footnotes(ctx_doc: dict) -> None:
    by_html_id = {footnote["html_id"]: footnote for footnote in ctx_doc["footnotes"] if footnote.get("html_id")}
    blocks: list[Block] = []
    blocks.extend(ctx_doc["title_blocks"])
    blocks.extend(ctx_doc["preamble_blocks"])
    blocks.extend(ctx_doc["signature_blocks"])
    blocks.extend(ctx_doc["act_footnote_blocks"])
    for article in ordered_articles(ctx_doc):
        blocks.extend(article["_blocks"])
    for annex in ctx_doc["annexes"]:
        blocks.extend(annex["_blocks"])
    for block in blocks:
        for ref in block.footnote_refs:
            footnote = by_html_id.get(ref)
            if footnote is not None and block.block_id not in footnote["referenced_by"]:
                footnote["referenced_by"].append(block.block_id)


class TextCursor:
    """记录组装过程中的 Python 字符位置。区间是 [start, end)。"""

    def __init__(self) -> None:
        self._parts: list[str] = []
        self.pos = 0

    def write(self, text: str) -> tuple[int, int]:
        start = self.pos
        self._parts.append(text)
        self.pos += len(text)
        return start, self.pos

    def value(self) -> str:
        return "".join(self._parts)


def place_separated(
    cursor: TextCursor,
    document_id: str,
    entries: list[tuple[Block | None, str]],
    separator: str,
) -> tuple[int, int] | None:
    if not entries:
        return None
    start = cursor.pos
    for index, (owner, line) in enumerate(entries):
        if line.rstrip() != line or not line.strip():
            fail(document_id, None, f"cleaned line has edge whitespace: {line!r}")
        if index:
            cursor.write(separator)
        span_start, span_end = cursor.write(line)
        if owner is not None:
            owner.start = span_start
            owner.end = span_end
            if owner.footnote_record is not None:
                owner.footnote_record["start"] = span_start
                owner.footnote_record["end"] = span_end
    return start, cursor.pos


def place_article(cursor: TextCursor, document_id: str, article: dict) -> None:
    entries: list[tuple[Block | None, str]] = [(None, f"Article {article['number']}")]
    if article["heading"]:
        entries.append((None, article["heading"]))
    entries.extend((block, block.text) for block in article["_blocks"])
    span = place_separated(cursor, document_id, entries, "\n")
    if span is None:
        fail(document_id, None, f"{article['article_id']} has no text")
    article["start"], article["end"] = span


def place_section(cursor: TextCursor, document_id: str, section: dict) -> None:
    head = [line for line in (section["label"], section["heading"]) if line]
    start = cursor.pos
    placed = False
    if head:
        place_separated(cursor, document_id, [(None, line) for line in head], "\n")
        placed = True
    for article in section["_articles"]:
        if placed:
            cursor.write("\n\n")
        placed = True
        place_article(cursor, document_id, article)
    section["start"] = start
    section["end"] = cursor.pos


def place_chapter(cursor: TextCursor, document_id: str, chapter: dict) -> None:
    head = [line for line in (chapter["label"], chapter["heading"]) if line]
    start = cursor.pos
    if "_body" not in chapter:
        articles = chapter["_articles"]
        if head:
            place_separated(cursor, document_id, [(None, line) for line in head], "\n")
        for index, article in enumerate(articles):
            if head or index:
                cursor.write("\n\n")
            place_article(cursor, document_id, article)
        chapter["start"] = start
        chapter["end"] = cursor.pos
        return
    placed = False
    if head:
        place_separated(cursor, document_id, [(None, line) for line in head], "\n")
        placed = True
    for kind, part in chapter["_body"]:
        if placed:
            cursor.write("\n\n")
        placed = True
        if kind == "section":
            place_section(cursor, document_id, part)
        else:
            place_article(cursor, document_id, part)
    chapter["start"] = start
    chapter["end"] = cursor.pos


def bind_recitals(document_id: str, ctx_doc: dict) -> None:
    by_id = {block.block_id: block for block in ctx_doc["preamble_blocks"]}
    for recital in ctx_doc["recitals"]:
        blocks: list[Block] = []
        for block_id in recital["block_ids"]:
            block = by_id.get(block_id)
            if block is None or block.start is None or block.end is None:
                fail(document_id, None, f"{recital['structure_id']} block {block_id} has no position")
            blocks.append(block)
        recital["start"] = blocks[0].start
        recital["end"] = blocks[-1].end
        for left, right in zip(blocks, blocks[1:]):
            if right.start != left.end + 1:
                fail(document_id, None, f"{recital['structure_id']} blocks are not contiguous")


def bind_tables(document_id: str, annex: dict) -> None:
    row_blocks = [block for block in annex["_blocks"] if block.kind == "table_row"]
    index = 0
    for table in annex["tables"]:
        count = len(table["rows"])
        chunk = row_blocks[index : index + count]
        index += count
        if len(chunk) != count:
            fail(document_id, None, f"{table['table_id']} is missing row positions")
        located = []
        for block, cells in zip(chunk, table["rows"]):
            expected = " | ".join(cells)
            if block.text != expected or block.start is None or block.end is None:
                fail(document_id, None, f"{table['table_id']} row does not match its block")
            located.append(
                {
                    "block_id": block.block_id,
                    "text": block.text,
                    "start": block.start,
                    "end": block.end,
                }
            )
        for left, right in zip(located, located[1:]):
            if right["start"] != left["end"] + 1:
                fail(document_id, None, f"{table['table_id']} rows are not contiguous")
        table["located_rows"] = located
        if located:
            table["start"] = located[0]["start"]
            table["end"] = located[-1]["end"]
            table["text"] = "\n".join(row["text"] for row in located)
    if index != len(row_blocks):
        fail(document_id, None, f"{annex['structure_id']} has extra table rows")


def check_recorded_slices(document_id: str, text: str, items: list[tuple[str, str, int, int]]) -> None:
    for structure_id, expected, start, end in items:
        if not isinstance(start, int) or not isinstance(end, int) or text[start:end] != expected:
            fail(document_id, None, f"{structure_id} span=[{start}, {end}) does not match its text")


def ordered_articles(ctx_doc: dict) -> list[dict]:
    articles: list[dict] = []
    for kind, part in ctx_doc["body"]:
        if kind == "chapter":
            articles.extend(part["_articles"])
        else:
            articles.append(part)
    return articles


def assemble_legacy(ctx_doc: dict) -> str:
    parts: list[str] = []
    title = pack(block.text for block in ctx_doc["title_blocks"])
    if title:
        parts.append(title)
    preamble = pack(block.text for block in ctx_doc["preamble_blocks"])
    if preamble:
        parts.append(preamble)
    for _kind, part in ctx_doc["body"]:
        if part["text"]:
            parts.append(part["text"])
    signature = pack(block.text for block in ctx_doc["signature_blocks"])
    if signature:
        parts.append(signature)
    footnotes = pack(block.text for block in ctx_doc["act_footnote_blocks"])
    if footnotes:
        parts.append(footnotes)
    for annex in ctx_doc["annexes"]:
        if annex["text"]:
            parts.append(annex["text"])
    return "\n\n".join(parts) + "\n"


def assemble(ctx_doc: dict) -> str:
    document_id = ctx_doc["document_id"]
    legacy = assemble_legacy(ctx_doc)
    cursor = TextCursor()
    recorded: list[tuple[str, str, int, int]] = []

    def separate() -> None:
        if cursor.pos:
            cursor.write("\n\n")

    def remember(structure_id: str, expected: str, span: tuple[int, int] | None) -> None:
        if span is None:
            fail(document_id, None, f"{structure_id} has no text to locate")
        recorded.append((structure_id, expected, span[0], span[1]))

    if ctx_doc["title_blocks"]:
        separate()
        span = place_separated(
            cursor, document_id, [(block, block.text) for block in ctx_doc["title_blocks"]], "\n"
        )
        ctx_doc["title_span"] = span
        remember(f"{document_id}:title", pack(block.text for block in ctx_doc["title_blocks"]), span)
        for block in ctx_doc["title_blocks"]:
            remember(block.block_id, block.text, (block.start, block.end))

    if ctx_doc["preamble_blocks"]:
        separate()
        span = place_separated(
            cursor, document_id, [(block, block.text) for block in ctx_doc["preamble_blocks"]], "\n"
        )
        ctx_doc["preamble_span"] = span
        remember(f"{document_id}:preamble", pack(block.text for block in ctx_doc["preamble_blocks"]), span)
        for block in ctx_doc["preamble_blocks"]:
            remember(block.block_id, block.text, (block.start, block.end))
        bind_recitals(document_id, ctx_doc)
        for recital in ctx_doc["recitals"]:
            remember(recital["structure_id"], recital["text"], (recital["start"], recital["end"]))

    for kind, part in ctx_doc["body"]:
        if not part["text"]:
            continue
        separate()
        if kind == "chapter":
            place_chapter(cursor, document_id, part)
            remember(part["structure_id"], part["text"], (part["start"], part["end"]))
            for section in part.get("_sections", []):
                remember(section["structure_id"], section["text"], (section["start"], section["end"]))
            articles = part["_articles"]
        else:
            place_article(cursor, document_id, part)
            articles = [part]
        for article in articles:
            remember(article["article_id"], article["text"], (article["start"], article["end"]))
            for block in article["_blocks"]:
                remember(block.block_id, block.text, (block.start, block.end))

    if ctx_doc["signature_blocks"]:
        separate()
        span = place_separated(
            cursor, document_id, [(block, block.text) for block in ctx_doc["signature_blocks"]], "\n"
        )
        ctx_doc["signature_span"] = span
        remember(f"{document_id}:signature", pack(block.text for block in ctx_doc["signature_blocks"]), span)
        for block in ctx_doc["signature_blocks"]:
            remember(block.block_id, block.text, (block.start, block.end))

    if ctx_doc["act_footnote_blocks"]:
        separate()
        place_separated(
            cursor, document_id, [(block, block.text) for block in ctx_doc["act_footnote_blocks"]], "\n"
        )
        for block in ctx_doc["act_footnote_blocks"]:
            remember(block.block_id, block.text, (block.start, block.end))

    for annex in ctx_doc["annexes"]:
        if not annex["text"]:
            continue
        separate()
        span = place_separated(cursor, document_id, [(block, block.text) for block in annex["_blocks"]], "\n")
        annex["start"], annex["end"] = span
        remember(annex["structure_id"], annex["text"], span)
        for block in annex["_blocks"]:
            remember(block.block_id, block.text, (block.start, block.end))
        bind_tables(document_id, annex)
        for table in annex["tables"]:
            if "text" in table:
                remember(table["table_id"], table["text"], (table["start"], table["end"]))

    cursor.write("\n")
    text = cursor.value()
    if text != legacy:
        limit = min(len(text), len(legacy))
        index = next((i for i in range(limit) if text[i] != legacy[i]), limit)
        fail(
            document_id,
            None,
            f"assembled text diverges from the accepted packing at character {index}; "
            f"new length {len(text)}, accepted length {len(legacy)}",
        )
    check_recorded_slices(document_id, text, recorded)
    for footnote in ctx_doc["footnotes"]:
        start = footnote.get("start")
        end = footnote.get("end")
        if not isinstance(start, int) or not isinstance(end, int) or text[start:end] != footnote["text"]:
            fail(
                document_id,
                None,
                f"{footnote.get('structure_id')} span=[{start}, {end}) does not match its text",
            )
    return text


def public_article(article: dict) -> dict:
    payload = {key: value for key, value in article.items() if key != "_blocks"}
    payload["blocks"] = [block_payload(block) for block in article["_blocks"]]
    return payload


def public_chapter(chapter: dict) -> dict:
    payload = dict(chapter)
    payload.pop("_articles", None)
    payload.pop("_body", None)
    private_sections = payload.pop("_sections", None)
    if private_sections:
        public_sections = []
        for section in private_sections:
            item = dict(section)
            item.pop("_articles", None)
            public_sections.append(item)
        payload["sections"] = public_sections
    return payload


def public_annex(annex: dict) -> dict:
    payload = {key: value for key, value in annex.items() if key != "_blocks"}
    payload["blocks"] = [block_payload(block) for block in annex["_blocks"]]
    return payload


def sale_of_goods_checks(document_id: str, ctx_doc: dict, text: str) -> list[str]:
    """27 个主条文来自独立 DOM 清点，缺条时不得通过。"""
    problems: list[str] = []
    if ctx_doc["chapters"]:
        problems.append(f"chapters are {[chapter['number'] for chapter in ctx_doc['chapters']]}, expected none")
    articles = ordered_articles(ctx_doc)
    numbers = [article["number"] for article in articles]
    expected = [str(number) for number in range(1, 28)]
    if numbers != expected:
        problems.append(f"main article numbers are {numbers}, expected 1..27")
    if any(article["chapter_id"] is not None for article in articles):
        problems.append("a main article has a chapter_id")
    by_number = {article["number"]: article for article in articles}
    required = [
        "DIRECTIVE (EU) 2019/771 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL",
        "of 20 May 2019",
        "on certain aspects concerning contracts for the sale of goods",
        "(Text with EEA relevance)",
        "The purpose of this Directive is to contribute to the proper functioning of the internal market",
        "within two years of that time",
        "shall not be less than one year",
        "By 1 July 2021",
        "twentieth day following that of its publication",
        "However, Article 22 shall apply from 1 January 2022.",
        "This Directive is addressed to the Member States.",
        "(1) OJ C 264, 20.7.2016, p. 57.",
        "CORRELATION TABLE",
        "Article 1(1) | Article 1",
    ]
    for snippet in required:
        if snippet not in text:
            problems.append(f"missing snippet: {snippet}")
    article_10 = by_number.get("10")
    if article_10 is None or "within two years of that time" not in article_10["text"]:
        problems.append("the two-year liability rule is not inside Article 10")
    article_24 = by_number.get("24")
    if article_24 is None or "By 1 July 2021" not in article_24["text"]:
        problems.append("the transposition deadline is not inside Article 24")
    if [annex["label"] for annex in ctx_doc["annexes"]] != ["ANNEX"]:
        problems.append(f"annex labels are {[annex['label'] for annex in ctx_doc['annexes']]}")
    return problems


def digital_content_checks(document_id: str, ctx_doc: dict, text: str) -> list[str]:
    """27 个主条文和 87 项序言来自独立 DOM 清点，缺条时不得通过。"""
    problems: list[str] = []
    if ctx_doc["chapters"]:
        problems.append(f"chapters are {[chapter['number'] for chapter in ctx_doc['chapters']]}, expected none")
    if ctx_doc["annexes"]:
        problems.append(f"annexes are {[annex['label'] for annex in ctx_doc['annexes']]}, expected none")
    articles = ordered_articles(ctx_doc)
    numbers = [article["number"] for article in articles]
    expected = [str(number) for number in range(1, 28)]
    if numbers != expected:
        problems.append(f"main article numbers are {numbers}, expected 1..27")
    if any(article["chapter_id"] is not None for article in articles):
        problems.append("a main article has a chapter_id")
    recital_numbers = [recital["number"] for recital in ctx_doc["recitals"]]
    if recital_numbers != [str(number) for number in range(1, 88)]:
        problems.append(f"recital numbers are {recital_numbers}, expected 1..87")
    if len(ctx_doc["footnotes"]) != 23:
        problems.append(f"footnotes are {len(ctx_doc['footnotes'])}, expected 23")
    by_number = {article["number"]: article for article in articles}
    required = [
        "DIRECTIVE (EU) 2019/770 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL",
        "of 20 May 2019",
        "on certain aspects concerning contracts for the supply of digital content and digital services",
        "(Text with EEA relevance)",
        "The purpose of this Directive is to contribute to the proper functioning of the internal market",
        "that period shall not be less than two years from the time of supply",
        "By 1 July 2021",
        "twentieth day following that of its publication",
        "which occurs from 1 January 2022",
        "Articles 19 and 20 of this Directive which shall only apply to contracts concluded from that date",
        "This Directive is addressed to the Member States.",
        "(1) OJ C 264, 20.7.2016, p. 57.",
    ]
    for snippet in required:
        if snippet not in text:
            problems.append(f"missing snippet: {snippet}")
    article_11 = by_number.get("11")
    if article_11 is None or "shall not be less than two years from the time of supply" not in article_11["text"]:
        problems.append("the two-year minimum period is not inside Article 11")
    article_24 = by_number.get("24")
    if article_24 is None or "By 1 July 2021" not in article_24["text"]:
        problems.append("the transposition deadline is not inside Article 24")
    if article_24 is None or "Articles 19 and 20" not in article_24["text"]:
        problems.append("the Articles 19 and 20 application limit is not inside Article 24")
    return problems


def unfair_practices_checks(document_id: str, ctx_doc: dict, text: str) -> list[str]:
    """21 个主条文、4 章和 Chapter 2 的两个节来自独立 DOM 清点。"""
    problems: list[str] = []
    chapters = ctx_doc["chapters"]
    if [chapter["number"] for chapter in chapters] != ["1", "2", "3", "4"]:
        problems.append(f"chapters are {[chapter['number'] for chapter in chapters]}, expected 1..4")
    if [chapter["html_id"] for chapter in chapters] != ["cpt_1", "cpt_2", "cpt_3", "cpt_4"]:
        problems.append("chapter containers are not cpt_1..cpt_4")
    articles = ordered_articles(ctx_doc)
    numbers = [article["number"] for article in articles]
    expected = [str(number) for number in range(1, 22)]
    if numbers != expected:
        problems.append(f"main article numbers are {numbers}, expected 1..21")
    sections = [section for chapter in chapters for section in chapter.get("_sections", [])]
    expected_sections = [
        f"{document_id}:chapter:2:section:1",
        f"{document_id}:chapter:2:section:2",
    ]
    if [section["structure_id"] for section in sections] != expected_sections:
        problems.append(f"sections are {[section['structure_id'] for section in sections]}")
    by_number = {article["number"]: article for article in articles}
    chapter_2 = f"{document_id}:chapter:2"
    if by_number.get("5", {}).get("chapter_id") != chapter_2 or by_number.get("5", {}).get("section_id") is not None:
        problems.append("Article 5 must belong directly to Chapter 2")
    for number in ("6", "7"):
        if by_number.get(number, {}).get("section_id") != expected_sections[0]:
            problems.append(f"Article {number} must belong to Section 1 of Chapter 2")
    for number in ("8", "9"):
        if by_number.get(number, {}).get("section_id") != expected_sections[1]:
            problems.append(f"Article {number} must belong to Section 2 of Chapter 2")
    if by_number.get("1", {}).get("section_id") is not None or by_number.get("21", {}).get("section_id") is not None:
        problems.append("Articles 1 and 21 have no section")
    if by_number.get("21", {}).get("chapter_id") != f"{document_id}:chapter:4":
        problems.append("Article 21 must belong to Chapter 4")
    chapter = next((item for item in chapters if item["number"] == "2"), None)
    if chapter is not None:
        if "Section 1" not in chapter["text"] or "Section 2" not in chapter["text"]:
            problems.append("Chapter 2 text is missing a section heading")
        for section in chapter.get("_sections", []):
            if section.get("start", 0) < chapter.get("start", 0) or section.get("end", 0) > chapter.get("end", 0):
                problems.append(f"{section['structure_id']} is outside Chapter 2")
            if not str(section.get("text", "")).startswith("Section "):
                problems.append(f"{section['structure_id']} does not start with its label")
    recital_numbers = [recital["number"] for recital in ctx_doc["recitals"]]
    if recital_numbers != [str(number) for number in range(1, 26)]:
        problems.append(f"recitals are {recital_numbers}, expected 1..25")
    if [annex["label"] for annex in ctx_doc["annexes"]] != ["ANNEX I", "ANNEX II"]:
        problems.append(f"annexes are {[annex['label'] for annex in ctx_doc['annexes']]}")
    article_5 = by_number.get("5", {}).get("text", "")
    if "Unfair commercial practices shall be prohibited." not in article_5:
        problems.append("the prohibition is not inside Article 5")
    if "shall be regarded as misleading if it contains false information" not in by_number.get("6", {}).get("text", ""):
        problems.append("the misleading-action condition is not inside Article 6")
    if "by 12 June 2007" not in by_number.get("19", {}).get("text", "") or "by 12 December 2007" not in by_number.get("19", {}).get("text", ""):
        problems.append("Article 19 transposition and application dates were not kept")
    if "day following its publication" not in by_number.get("20", {}).get("text", ""):
        problems.append("Article 20 entry into force was not kept")
    if not text:
        problems.append("cleaned text is empty")
    return problems


def unfair_terms_checks(document_id: str, ctx_doc: dict, text: str) -> list[str]:
    """11 个主条文来自 p.ti-art 清点。序言没有官方编号。"""
    problems: list[str] = []
    if ctx_doc["chapters"]:
        problems.append(f"chapters are {[chapter['number'] for chapter in ctx_doc['chapters']]}, expected none")
    articles = ordered_articles(ctx_doc)
    numbers = [article["number"] for article in articles]
    expected = [str(number) for number in range(1, 12)]
    if numbers != expected:
        problems.append(f"main article numbers are {numbers}, expected 1..11")
    html_ids = [
        "d1e196-29-1",
        "d1e210-29-1",
        "d1e245-29-1",
        "d1e268-29-1",
        "d1e282-29-1",
        "d1e288-29-1",
        "d1e302-29-1",
        "d1e321-29-1",
        "d1e327-29-1",
        "d1e333-29-1",
        "d1e360-29-1",
    ]
    if [article["html_id"] for article in articles] != html_ids:
        problems.append("main article html ids do not match the p.ti-art nodes")
    if any(article["chapter_id"] is not None or article["section_id"] is not None or article["heading"] is not None for article in articles):
        problems.append("a main article has a chapter, section, or invented subtitle")
    by_number = {article["number"]: article for article in articles}
    article_11 = by_number.get("11")
    if article_11 is None or article_11["text"] != "Article 11\nThis Directive is addressed to the Member States.":
        problems.append("Article 11 absorbed text beyond the addressee sentence")
    ordinals = [recital.get("ordinal") for recital in ctx_doc["recitals"]]
    if ordinals != [str(number) for number in range(1, 25)]:
        problems.append(f"recital ordinals are {ordinals}, expected 1..24")
    if any(recital.get("number") is not None or recital.get("official_number") is not None for recital in ctx_doc["recitals"]):
        problems.append("an unnumbered Whereas paragraph was given an official recital number")
    if [annex["label"] for annex in ctx_doc["annexes"]] != ["ANNEX"]:
        problems.append(f"annex labels are {[annex['label'] for annex in ctx_doc['annexes']]}")
    if len(ctx_doc["footnotes"]) != 4:
        problems.append(f"footnotes are {len(ctx_doc['footnotes'])}, expected 4")
    required = [
        "COUNCIL DIRECTIVE 93/13/EEC",
        "of 5 April 1993",
        "on unfair terms in consumer contracts",
        "THE COUNCIL OF THE EUROPEAN COMMUNITIES,",
        "Whereas it is necessary to adopt measures with the aim of progressively establishing the internal market",
        "HAS ADOPTED THIS DIRECTIVE:",
        "The purpose of this Directive is to approximate the laws, regulations and administrative provisions",
        "(a) ‘unfair terms’ means the contractual terms defined in Article 3;",
        "not be binding on the consumer",
        "no later than 31 December 1994",
        "contracts concluded after 31 December 1994",
        "Done at Luxembourg, 5 April 1993.",
        "For the Council",
        "(1) OJ No C 73, 24. 3. 1992, p. 7.",
        "OJ No C 326, 16. 12. 1991, p. 108 and OJ No C 21, 25. 1. 1993.",
        "TERMS REFERRED TO IN ARTICLE 3 (3)",
        "Scope of subparagraphs (g), (j) and (1)",
        "Subparagraph (g) is without hindrance to terms",
        "Subparagraphs (g), (j) and (1) do not apply to:",
    ]
    for snippet in required:
        if snippet not in text:
            problems.append(f"missing snippet: {snippet}")
    forbidden = [
        "L 95/29",
        "21.4.1993",
        "Official Journal of the European Communities",
    ]
    for snippet in forbidden:
        if snippet in text:
            problems.append(f"running header remains in the text: {snippet}")
    if "Article 3" in by_number.get("2", {}).get("text", "") and any(article["number"] == "3a" for article in articles):
        problems.append("an Article 3 cross-reference became a main article")
    return problems


def expected_checks(document_id: str, ctx_doc: dict, text: str) -> list[str]:
    if document_id == "eu_sale_of_goods_2019_771":
        return sale_of_goods_checks(document_id, ctx_doc, text)
    if document_id == "eu_unfair_terms_93_13":
        return unfair_terms_checks(document_id, ctx_doc, text)
    if document_id == "eu_digital_content_2019_770":
        return digital_content_checks(document_id, ctx_doc, text)
    if document_id == "eu_unfair_practices_2005_29":
        return unfair_practices_checks(document_id, ctx_doc, text)
    if document_id != "eu_consumer_rights_2011_83":
        return []
    problems: list[str] = []
    articles = [article for chapter in ctx_doc["chapters"] for article in chapter["_articles"]]
    numbers = [article["number"] for article in articles]
    if numbers != [str(number) for number in range(1, 36)]:
        problems.append(f"main article numbers are {numbers}, expected 1..35")
    chapters = [chapter["number"] for chapter in ctx_doc["chapters"]]
    if chapters != ["I", "II", "III", "IV", "V", "VI"]:
        problems.append(f"chapters are {chapters}")
    ranges = {
        "I": range(1, 5),
        "II": range(5, 6),
        "III": range(6, 17),
        "IV": range(17, 23),
        "V": range(23, 31),
        "VI": range(31, 36),
    }
    by_number = {article["number"]: article for article in articles}
    for roman, span in ranges.items():
        chapter_id = f"{document_id}:chapter:{roman}"
        for number in span:
            article = by_number.get(str(number))
            if article is None or article["chapter_id"] != chapter_id:
                problems.append(f"Article {number} is not in chapter {roman}")
    if [annex["label"] for annex in ctx_doc["annexes"]] != ["ANNEX I", "ANNEX II"]:
        problems.append("annex labels are not ANNEX I, ANNEX II")
    recital_numbers = [recital["number"] for recital in ctx_doc["recitals"]]
    if recital_numbers != [str(number) for number in range(1, 68)]:
        problems.append(f"recital numbers are {recital_numbers}, expected 1..67")
    quoted = [
        block.text
        for article in articles
        for block in article["_blocks"]
        if block.kind == "quoted_heading"
    ]
    if quoted.count("‘Article 8a") != 2:
        problems.append(f"quoted Article 8a headings are {quoted}")
    required = [
        "DIRECTIVE 2011/83/EU OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL",
        "of 25 October 2011",
        "on consumer rights, amending Council Directive 93/13/EEC",
        "(Text with EEA relevance)",
        "THE EUROPEAN PARLIAMENT AND THE COUNCIL OF THE EUROPEAN UNION,",
        "The purpose of this Directive is, through the achievement of a high level of consumer protection, to contribute to the proper functioning of the internal market",
        "(1) ‘consumer’ means any natural person who, in contracts covered by this Directive, is acting for purposes which are outside his trade, business, craft or profession;",
        "in accordance with Article 11(1), as well as the model withdrawal form set out in Annex I(B);",
        "not later than 30 days from the conclusion of the contract.",
        "This Directive shall enter into force on the 20th day following its publication in the Official Journal of the European Union.",
        "This Directive is addressed to the Member States.",
        "Done at Strasbourg, 25 October 2011.",
        "(1) OJ C 317, 23.12.2009, p. 54.",
        "You have the right to withdraw from this contract within 14 days without giving any reason.",
        "day 1. To exercise the right of withdrawal",
        "Directive 85/577/EEC | Directive 97/7/EC | This Directive",
        "Article 1 |  | Article 3 read in conjunction with Article 2, points 8 and 9, and Article 16, point (h)",
        " | Article 1 | Article 1 read in conjunction with Article 2, point 7",
        "(1) OJ L 364, 9.12.2004, p. 1.",
        "(*1) Delete as appropriate.",
    ]
    for snippet in required:
        if snippet not in text:
            problems.append(f"missing snippet: {snippet}")
    article_32 = by_number.get("32")
    article_33 = by_number.get("33")
    if article_32 is None or "‘Article 8a" not in article_32["text"]:
        problems.append("Article 32 does not contain the quoted Article 8a")
    if article_33 is None or "‘Article 8a" not in article_33["text"]:
        problems.append("Article 33 does not contain the quoted Article 8a")
    if any(article["number"] == "8a" for article in articles):
        problems.append("quoted Article 8a was promoted to a main article")
    forbidden = [
        "Table of contents",
        "Cookie",
        "Switch to mobile",
        "Experimental features",
        "Access current version",
        "Hide consolidated versions",
        "Multilingual display",
        "L 304/64",
    ]
    for snippet in forbidden:
        if snippet in text:
            problems.append(f"page chrome remains: {snippet}")
    if "\r" in text or not text.endswith("\n"):
        problems.append("clean text does not use a single trailing LF")
    missing_refs = sorted(
        {
            ref
            for article in articles
            for block in article["_blocks"]
            if any(
                ref not in {footnote.get("html_id") for footnote in ctx_doc["footnotes"]}
                for ref in block.footnote_refs
            )
            for ref in block.footnote_refs
            if ref not in {footnote.get("html_id") for footnote in ctx_doc["footnotes"]}
        }
    )
    if missing_refs:
        problems.append(f"unresolved footnote refs: {missing_refs}")
    unreferenced = [footnote["html_id"] for footnote in ctx_doc["footnotes"] if not footnote["referenced_by"]]
    if unreferenced:
        problems.append(f"footnotes without an in-text reference: {unreferenced}")
    problems.extend(duplicate_position_problems(text, ctx_doc))
    return problems


def duplicate_position_problems(text: str, ctx_doc: dict) -> list[str]:
    """重复文本必须落在各自组装位置，不能都等于全文第一次 find 的结果。"""
    problems: list[str] = []
    grouped: dict[str, list[int]] = {}
    blocks: list[Block] = []
    blocks.extend(ctx_doc["title_blocks"])
    blocks.extend(ctx_doc["preamble_blocks"])
    blocks.extend(ctx_doc["signature_blocks"])
    blocks.extend(ctx_doc["act_footnote_blocks"])
    for article in ordered_articles(ctx_doc):
        heading = f"Article {article['number']}"
        if text[article["start"] : article["start"] + len(heading)] != heading:
            problems.append(f"{article['article_id']} does not begin at its recorded position")
        blocks.extend(article["_blocks"])
    for annex in ctx_doc["annexes"]:
        blocks.extend(annex["_blocks"])
    for block in blocks:
        if block.start is None:
            problems.append(f"{block.block_id} has no position")
            continue
        grouped.setdefault(block.text, []).append(block.start)
    repeated = 0
    for value, starts in grouped.items():
        if len(starts) < 2:
            continue
        repeated += 1
        first = text.find(value)
        if len(set(starts)) != len(starts) or all(start == first for start in starts):
            problems.append(f"duplicate text collapsed to one position: {value[:80]!r}")
    by_marker: dict[str, list[int]] = {}
    for footnote in ctx_doc["footnotes"]:
        by_marker.setdefault(footnote["marker"], []).append(footnote["start"])
    for marker, starts in by_marker.items():
        if len(starts) > 1 and len(set(starts)) != len(starts):
            problems.append(f"footnote marker {marker} shares one span")
    if repeated == 0 and not any(len(starts) > 1 for starts in by_marker.values()):
        problems.append("no repeated text was available to prove occurrence-specific positions")
    return problems


DOCUMENT_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def load_catalog(root: Path) -> tuple[list[dict], list[str]]:
    """读取来源清单。顺序按 document_id 固定，不扫描 raw 目录。"""
    source_path = root / "data" / "sources.json"
    if not source_path.is_file():
        return [], [f"file={source_path}: sources.json is missing"]
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [f"file={source_path}: sources.json cannot be read: {exc}"]
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        return [], [f"file={source_path}: sources must be a list"]
    items = payload["sources"]
    if not items:
        return [], [f"file={source_path}: sources list is empty"]
    errors: list[str] = []
    seen: set[str] = set()
    valid: list[dict] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"file={source_path}: source {index} is not an object")
            continue
        document_id = item.get("document_id")
        if not isinstance(document_id, str) or DOCUMENT_ID_RE.fullmatch(document_id) is None:
            errors.append(f"file={source_path}: source {index} has invalid document_id {document_id!r}")
            continue
        if document_id in seen:
            errors.append(f"file={source_path}: document_id {document_id} is duplicated")
            continue
        seen.add(document_id)
        snapshot = item.get("snapshot")
        relative = snapshot.get("path") if isinstance(snapshot, dict) else None
        digest = snapshot.get("sha256") if isinstance(snapshot, dict) else None
        path = Path(relative) if isinstance(relative, str) else None
        if path is None or path.is_absolute() or ".." in path.parts or not relative:
            errors.append(f"file={source_path} document_id={document_id}: snapshot path is invalid")
            continue
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            errors.append(f"file={source_path} document_id={document_id}: snapshot sha256 is invalid")
            continue
        valid.append(item)
    valid.sort(key=lambda item: item["document_id"])
    return valid, errors


def snapshot_errors(root: Path, source: dict) -> list[str]:
    document_id = source["document_id"]
    snapshot = source["snapshot"]
    path = root / snapshot["path"]
    if not path.is_file():
        return [f"document_id={document_id} file={path}: registered snapshot path does not exist"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != snapshot["sha256"]:
        return [f"document_id={document_id} file={path}: snapshot sha256 mismatch: {actual}"]
    return []


def load_source(root: Path, document_id: str) -> dict:
    source_path = root / "data" / "sources.json"
    if not source_path.is_file():
        fail(document_id, source_path, "sources.json is missing")
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(document_id, source_path, f"sources.json cannot be read: {exc}")
    matches = [item for item in payload.get("sources", []) if item.get("document_id") == document_id]
    if not matches:
        fail(document_id, source_path, "document_id is not registered")
    if len(matches) > 1:
        fail(document_id, source_path, "document_id is duplicated in sources.json")
    return matches[0]


def source_metadata(source: dict) -> dict:
    snapshot = source["snapshot"]
    return {
        "document_id": source["document_id"],
        "title": source["title"],
        "institution": source["institution"],
        "language": source["language"],
        "official_url": source["official_url"],
        "eli": source["eli"],
        "celex": source["celex"],
        "version_type": source["version_type"],
        "source_format": source["source_format"],
        "dates": source["dates"],
        "official_journal": source["official_journal"],
        "snapshot_path": snapshot["path"],
        "snapshot_sha256": snapshot["sha256"],
    }


def cleaning_rule_metadata(legacy: bool) -> dict:
    """现代页面沿用原说明。旧式页面按实际的 p.ti-art 和 p.note 规则写说明。"""
    rules = {
        "version": CLEANING_RULE_VERSION,
        "encoding": "utf-8",
        "newline": "LF",
        "whitespace": "Each block is one line. Whitespace inside a block, including NBSP, collapses to a single space. Major parts are separated by one blank line. The file ends with one LF.",
        "sentence_spacing": "A missing space after a lowercase letter or digit and before an uppercase letter is restored. This repairs text nodes split by inline boxes.",
        "footnotes": "In-text note anchors render as (n). The note remains at its position and records the blocks that cite it.",
        "lists": "Two-column layout tables render as 'marker text' lines.",
        "tables": "oj-table rows render as cells joined by ' | ', and empty cells stay in place.",
        "main_articles": "A main article is a div.eli-subdivision whose id is art_<number> and whose parent is not an annex. Quoted article headings and annex correlation cells are not main articles.",
        "excluded": "Navigation, language selection, search, cookies, download controls, the page table of contents, the duplicate EUR-Lex title, and the Official Journal running header.",
        "character_offsets": (
            "Python character indexes into the complete cleaned text, using [start, end). "
            "Not UTF-8 bytes or model tokens. Positions are recorded during assembly."
        ),
    }
    if legacy:
        rules["main_articles"] = (
            "A main article starts at a p.ti-art heading and continues through the adjacent content that follows it. "
            "It ends at the next main-article heading, the signature, the footnotes, or the annex boundary. "
            "Cross-references in the body and annex headings are not main articles."
        )
        rules["footnotes"] = (
            "A p.note with an ntr definition anchor starts a footnote. "
            "A continuation p.note without a new definition anchor is merged into the previous footnote. "
            "The citation relationship and the full text are kept. "
            "In this file, 6 p.note elements correspond to 4 footnotes."
        )
    return rules


def build_document(root: Path, source: dict, progress: Progress) -> tuple[str, dict]:
    document_id = source["document_id"]
    html_path = root / source["snapshot"]["path"]
    if not html_path.is_file():
        fail(document_id, html_path, "registered snapshot path does not exist")
    html_bytes = html_path.read_bytes()
    actual_hash = hashlib.sha256(html_bytes).hexdigest()
    if actual_hash != source["snapshot"]["sha256"]:
        fail(document_id, html_path, f"snapshot sha256 mismatch: {actual_hash}")
    if source.get("version_type") != "original_publication":
        fail(document_id, html_path, f"version_type is {source.get('version_type')}, expected original_publication")
    soup = BeautifulSoup(html_bytes, "html.parser")
    document = soup.select_one("#document1")
    if document is None:
        fail(document_id, html_path, "#document1 is missing")
    progress.advance()
    ctx = RenderContext([], [], "act", document_id)
    ctx_doc = {
        "document_id": document_id,
        "title_blocks": [],
        "preamble_blocks": [],
        "recitals": [],
        "chapters": [],
        "loose_articles": [],
        "body": [],
        "signature_blocks": [],
        "act_footnote_blocks": [],
        "annexes": [],
        "footnotes": [],
    }
    if is_legacy_act(document):
        parse_legacy(document, ctx_doc, ctx, progress)
    else:
        walk(document, ctx_doc, ctx, progress)
    seen_notes = {footnote.get("html_id") for footnote in ctx_doc["footnotes"]}
    for footnote in ctx.footnotes:
        html_id = footnote.get("html_id")
        if html_id not in seen_notes:
            ctx_doc["footnotes"].append(footnote)
            seen_notes.add(html_id)
    assign_ids(ctx_doc["act_footnote_blocks"], f"{document_id}:footnote-lines")
    for index, footnote in enumerate(ctx_doc["footnotes"], start=1):
        marker = footnote["marker"] or str(index)
        footnote["structure_id"] = f"{document_id}:footnote:{footnote['scope']}:{marker}"
    link_footnotes(ctx_doc)
    text = assemble(ctx_doc)
    problems = expected_checks(document_id, ctx_doc, text)
    if problems:
        for problem in problems:
            print(f"process_documents.py: document_id={document_id} file={html_path}: {problem}", file=sys.stderr)
        raise SystemExit(1)
    articles = [public_article(article) for article in ordered_articles(ctx_doc)]
    chapters = [public_chapter(chapter) for chapter in ctx_doc["chapters"]]
    annexes = [public_annex(annex) for annex in ctx_doc["annexes"]]
    preamble_blocks = ctx_doc["preamble_blocks"]
    quoted = [block["text"] for article in articles for block in article["blocks"] if block["kind"] == "quoted_heading"]
    statistics = {
        "chapters": len(chapters),
        "main_articles": len(articles),
        "recitals": len(ctx_doc["recitals"]),
        "annexes": len(annexes),
        "footnotes": len(ctx_doc["footnotes"]),
        "tables": sum(len(annex["tables"]) for annex in annexes),
        "paragraphs": sum(1 for article in articles for block in article["blocks"] if block["kind"] == "paragraph"),
        "list_items": sum(1 for article in articles for block in article["blocks"] if block["kind"] == "list_item"),
        "quoted_article_headings": quoted,
    }
    sections = [section for chapter in chapters for section in chapter.get("sections", [])]
    if sections:
        statistics["sections"] = len(sections)
    for footnote in ctx_doc["footnotes"]:
        footnote.pop("marker_key", None)
    payload = {
        "document_id": document_id,
        "cleaning_rule_version": CLEANING_RULE_VERSION,
        "character_offsets": {
            "unit": "python_character",
            "interval": "[start, end)",
            "basis": "complete cleaned text",
            "newline": "LF",
            "note": (
                "Offsets are Python character indexes into the complete cleaned text. "
                "clean_text[start:end] equals the structure text. They are not UTF-8 byte offsets "
                "or model token counts. Each position is recorded while the text is assembled, "
                "so a repeated paragraph, article number, or footnote keeps the position of that occurrence."
            ),
        },
        "source": source_metadata(source),
        "clean_text_path": f"data/processed/{document_id}.txt",
        "clean_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "cleaning_rules": cleaning_rule_metadata(is_legacy_act(document)),
        "statistics": statistics,
        "title": {
            "structure_id": f"{document_id}:title",
            "structure_type": "title",
            "start": ctx_doc["title_span"][0],
            "end": ctx_doc["title_span"][1],
            "blocks": [block_payload(block) for block in ctx_doc["title_blocks"]],
            "text": pack(block.text for block in ctx_doc["title_blocks"]),
        },
        "preamble": {
            "structure_id": f"{document_id}:preamble",
            "structure_type": "preamble",
            "html_id": ctx_doc.get("preamble_html_id", "pbl_1"),
            "start": ctx_doc["preamble_span"][0],
            "end": ctx_doc["preamble_span"][1],
            "blocks": [block_payload(block) for block in preamble_blocks],
            "recitals": ctx_doc["recitals"],
            "text": pack(block.text for block in preamble_blocks),
        },
        "chapters": chapters,
        "articles": articles,
        "signature": {
            "structure_id": f"{document_id}:signature",
            "structure_type": "signature",
            "html_id": ctx_doc.get("signature_html_id", "fnp_1"),
            "start": ctx_doc["signature_span"][0],
            "end": ctx_doc["signature_span"][1],
            "blocks": [block_payload(block) for block in ctx_doc["signature_blocks"]],
            "text": pack(block.text for block in ctx_doc["signature_blocks"]),
        },
        "footnotes": ctx_doc["footnotes"],
        "annexes": annexes,
    }
    if sections:
        payload["sections"] = sections
    return text, payload


def write_outputs(root: Path, document_id: str, text: str, payload: dict) -> tuple[Path, Path]:
    output_dir = root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    text_path = output_dir / f"{document_id}.txt"
    json_path = output_dir / f"{document_id}.json"
    text_bytes = text.encode("utf-8")
    actual = hashlib.sha256(text_bytes).hexdigest()
    if actual != payload["clean_text_sha256"]:
        fail(document_id, text_path, "clean text hash changed before writing")
    text_path.write_bytes(text_bytes)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    reread = text_path.read_bytes()
    if reread != text_bytes:
        fail(document_id, text_path, "written text bytes differ from the hashed text")
    return text_path, json_path


def count_work(document) -> int:
    if is_legacy_act(document):
        return legacy_work_count(document)
    return sum(1 for node in document.find_all(True) if is_work(node))


def process_registered(root: Path, source: dict) -> None:
    document_id = source["document_id"]
    html_path = root / source["snapshot"]["path"]
    if not html_path.is_file():
        fail(document_id, html_path, "registered snapshot path does not exist")
    soup = BeautifulSoup(html_path.read_bytes(), "html.parser")
    document = soup.select_one("#document1")
    if document is None:
        fail(document_id, html_path, "#document1 is missing")
    progress = Progress(count_work(document) + 2)
    progress.advance()
    text, payload = build_document(root, source, progress)
    text_path, json_path = write_outputs(root, document_id, text, payload)
    progress.finish()
    stats = payload["statistics"]
    print(f"document_id={document_id}")
    print(f"text={text_path}")
    print(f"json={json_path}")
    print(f"clean_text_sha256={payload['clean_text_sha256']}")
    print(
        "chapters={chapters} main_articles={main_articles} recitals={recitals} "
        "annexes={annexes} footnotes={footnotes} tables={tables} "
        "paragraphs={paragraphs} list_items={list_items}".format(**stats)
    )
    print("quoted_article_headings=" + " | ".join(stats["quoted_article_headings"]))


def run_all(root: Path) -> int:
    sources, errors = load_catalog(root)
    if errors:
        for error in errors:
            print(f"process_documents.py: {error}", file=sys.stderr)
        print("succeeded=0", file=sys.stderr)
        print(f"failed={len(errors)}", file=sys.stderr)
        print("result=failed", file=sys.stderr)
        return 1
    progress = Progress(len(sources))
    succeeded = 0
    failed = 0
    for source in sources:
        problems = snapshot_errors(root, source)
        if problems:
            failed += 1
            for problem in problems:
                print(f"process_documents.py: {problem}", file=sys.stderr)
            progress.advance()
            continue
        try:
            process_registered(root, source)
        except SystemExit:
            failed += 1
        else:
            succeeded += 1
        progress.advance()
    progress.finish()
    print(f"batch_documents={len(sources)}")
    print(f"succeeded={succeeded}")
    print(f"failed={failed}")
    if failed:
        print("result=failed", file=sys.stderr)
        return 1
    print("result=ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Clean registered EUR-Lex HTML snapshots.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--document-id")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.data_root.resolve() if args.data_root is not None else Path(__file__).resolve().parents[1]
    if args.all:
        return run_all(root)
    source = load_source(root, args.document_id)
    process_registered(root, source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
