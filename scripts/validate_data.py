# Corpus checks for cleaned EUR-Lex documents.
# Offsets are Python character indexes [start, end) into the complete cleaned text.

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

DOCUMENT_ID = "eu_consumer_rights_2011_83"
QUOTED_ARTICLE_8A = "‘Article 8a"


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


def problem(
    path: Path | None,
    document_id: str,
    structure_id: str | None,
    start: object,
    end: object,
    reason: str,
) -> str:
    file_name = "-" if path is None else path.as_posix()
    span = "-" if not isinstance(start, int) or not isinstance(end, int) else f"[{start}, {end})"
    return (
        f"validate_data.py: file={file_name} document_id={document_id} "
        f"structure_id={structure_id or '-'} span={span} reason={reason}"
    )


def is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def load_json(path: Path, document_id: str, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(problem(path, document_id, None, None, None, "file does not exist"))
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(problem(path, document_id, None, None, None, f"JSON cannot be read: {exc}"))
        return None


def source_record(root: Path, document_id: str, errors: list[str]) -> dict | None:
    path = root / "data" / "sources.json"
    payload = load_json(path, document_id, errors)
    if payload is None:
        return None
    matches = [item for item in payload.get("sources", []) if item.get("document_id") == document_id]
    if len(matches) != 1:
        errors.append(
            problem(path, document_id, document_id, None, None, f"expected one source record, found {len(matches)}")
        )
        return None
    return matches[0]


def check_hash(path: Path, document_id: str, expected: object, errors: list[str]) -> bytes | None:
    if not path.is_file():
        errors.append(problem(path, document_id, None, None, None, "file does not exist"))
        return None
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        errors.append(
            problem(
                path,
                document_id,
                None,
                None,
                None,
                f"SHA-256 mismatch: expected {expected}, actual {actual}",
            )
        )
    return data


def add_item(
    items: list[dict],
    counts: dict[str, int],
    *,
    kind: str,
    structure_id: str,
    text: object,
    start: object,
    end: object,
    parent_id: str | None,
    group: str,
) -> None:
    counts[kind] = counts.get(kind, 0) + 1
    items.append(
        {
            "kind": kind,
            "structure_id": structure_id,
            "text": text,
            "start": start,
            "end": end,
            "parent_id": parent_id,
            "group": group,
        }
    )


def collect_document(document: dict, document_id: str, errors: list[str], json_path: Path) -> tuple[list[dict], dict[str, int], dict[str, str]]:
    items: list[dict] = []
    counts: dict[str, int] = {}
    seen: dict[str, str] = {}

    def claim(structure_id: object, owner: str) -> None:
        if not isinstance(structure_id, str) or not structure_id:
            errors.append(problem(json_path, document_id, None, None, None, f"{owner} is missing a structure id"))
            return
        previous = seen.get(structure_id)
        if previous is not None:
            errors.append(
                problem(
                    json_path,
                    document_id,
                    structure_id,
                    None,
                    None,
                    f"duplicate id, also used by {previous}",
                )
            )
            return
        seen[structure_id] = owner

    title = document.get("title") or {}
    claim(title.get("structure_id"), "title")
    add_item(
        items,
        counts,
        kind="title",
        structure_id=title.get("structure_id"),
        text=title.get("text"),
        start=title.get("start"),
        end=title.get("end"),
        parent_id=None,
        group="top",
    )
    for block in title.get("blocks") or []:
        claim(block.get("block_id"), "title block")
        add_item(
            items,
            counts,
            kind="block",
            structure_id=block.get("block_id"),
            text=block.get("text"),
            start=block.get("start"),
            end=block.get("end"),
            parent_id=title.get("structure_id"),
            group=f"blocks:{title.get('structure_id')}",
        )

    preamble = document.get("preamble") or {}
    claim(preamble.get("structure_id"), "preamble")
    add_item(
        items,
        counts,
        kind="preamble",
        structure_id=preamble.get("structure_id"),
        text=preamble.get("text"),
        start=preamble.get("start"),
        end=preamble.get("end"),
        parent_id=None,
        group="top",
    )
    preamble_blocks = {block.get("block_id"): block for block in preamble.get("blocks") or []}
    for block in preamble.get("blocks") or []:
        claim(block.get("block_id"), "preamble block")
        add_item(
            items,
            counts,
            kind="block",
            structure_id=block.get("block_id"),
            text=block.get("text"),
            start=block.get("start"),
            end=block.get("end"),
            parent_id=preamble.get("structure_id"),
            group=f"blocks:{preamble.get('structure_id')}",
        )
    for recital in preamble.get("recitals") or []:
        claim(recital.get("structure_id"), "recital")
        add_item(
            items,
            counts,
            kind="recital",
            structure_id=recital.get("structure_id"),
            text=recital.get("text"),
            start=recital.get("start"),
            end=recital.get("end"),
            parent_id=preamble.get("structure_id"),
            group="recitals",
        )
        for block_id in recital.get("block_ids") or []:
            block = preamble_blocks.get(block_id)
            if block is None:
                errors.append(
                    problem(
                        json_path,
                        document_id,
                        recital.get("structure_id"),
                        recital.get("start"),
                        recital.get("end"),
                        f"recital block {block_id} does not exist",
                    )
                )
                continue
            if not contains(recital, block):
                errors.append(
                    problem(
                        json_path,
                        document_id,
                        recital.get("structure_id"),
                        recital.get("start"),
                        recital.get("end"),
                        f"recital does not contain {block_id} span=[{block.get('start')}, {block.get('end')})",
                    )
                )

    chapters = document.get("chapters") or []
    articles = document.get("articles") or []
    chapter_ids = {chapter.get("structure_id") for chapter in chapters}
    for chapter in chapters:
        claim(chapter.get("structure_id"), "chapter")
        add_item(
            items,
            counts,
            kind="chapter",
            structure_id=chapter.get("structure_id"),
            text=chapter.get("text"),
            start=chapter.get("start"),
            end=chapter.get("end"),
            parent_id=None,
            group="top",
        )
        linked = [article["article_id"] for article in articles if article.get("chapter_id") == chapter.get("structure_id")]
        if linked != chapter.get("article_ids"):
            errors.append(
                problem(
                    json_path,
                    document_id,
                    chapter.get("structure_id"),
                    chapter.get("start"),
                    chapter.get("end"),
                    f"article_ids {chapter.get('article_ids')} do not match articles {linked}",
                )
            )
    sections = document.get("sections")
    if sections is None:
        sections = [section for chapter in chapters for section in chapter.get("sections") or []]
    for section in sections:
        claim(section.get("structure_id"), "section")
        chapter_id = section.get("chapter_id")
        if chapter_id not in chapter_ids:
            errors.append(
                problem(
                    json_path,
                    document_id,
                    section.get("structure_id"),
                    section.get("start"),
                    section.get("end"),
                    f"chapter_id {chapter_id} does not exist",
                )
            )
        add_item(
            items,
            counts,
            kind="section",
            structure_id=section.get("structure_id"),
            text=section.get("text"),
            start=section.get("start"),
            end=section.get("end"),
            parent_id=chapter_id,
            group=f"sections:{chapter_id}",
        )
    for article in articles:
        claim(article.get("article_id"), "article")
        chapter_id = article.get("chapter_id")
        if chapter_id is None:
            if chapters:
                errors.append(
                    problem(
                        json_path,
                        document_id,
                        article.get("article_id"),
                        article.get("start"),
                        article.get("end"),
                        "chapter_id is null while the document has chapters",
                    )
                )
            parent_id = None
            group = "top"
        else:
            if chapter_id not in chapter_ids:
                errors.append(
                    problem(
                        json_path,
                        document_id,
                        article.get("article_id"),
                        article.get("start"),
                        article.get("end"),
                        f"chapter_id {chapter_id} does not exist",
                    )
                )
            section_id = article.get("section_id")
            if section_id:
                parent_id = section_id
                group = f"articles:{section_id}"
            else:
                parent_id = chapter_id
                group = f"articles:{chapter_id}"
        add_item(
            items,
            counts,
            kind="article",
            structure_id=article.get("article_id"),
            text=article.get("text"),
            start=article.get("start"),
            end=article.get("end"),
            parent_id=parent_id,
            group=group,
        )
        for block in article.get("blocks") or []:
            claim(block.get("block_id"), "article block")
            add_item(
                items,
                counts,
                kind="block",
                structure_id=block.get("block_id"),
                text=block.get("text"),
                start=block.get("start"),
                end=block.get("end"),
                parent_id=article.get("article_id"),
                group=f"blocks:{article.get('article_id')}",
            )

    signature = document.get("signature") or {}
    claim(signature.get("structure_id"), "signature")
    add_item(
        items,
        counts,
        kind="signature",
        structure_id=signature.get("structure_id"),
        text=signature.get("text"),
        start=signature.get("start"),
        end=signature.get("end"),
        parent_id=None,
        group="top",
    )
    for block in signature.get("blocks") or []:
        claim(block.get("block_id"), "signature block")
        add_item(
            items,
            counts,
            kind="block",
            structure_id=block.get("block_id"),
            text=block.get("text"),
            start=block.get("start"),
            end=block.get("end"),
            parent_id=signature.get("structure_id"),
            group=f"blocks:{signature.get('structure_id')}",
        )

    footnote_html: dict[str, str] = {}
    for footnote in document.get("footnotes") or []:
        claim(footnote.get("structure_id"), "footnote")
        html_id = footnote.get("html_id")
        if not isinstance(html_id, str) or html_id in footnote_html:
            errors.append(
                problem(
                    json_path,
                    document_id,
                    footnote.get("structure_id"),
                    footnote.get("start"),
                    footnote.get("end"),
                    f"footnote html_id {html_id} is missing or duplicated",
                )
            )
        else:
            footnote_html[html_id] = footnote["structure_id"]
        scope = footnote.get("scope")
        if scope == "act":
            parent_id = None
            group = "top"
            for article in articles:
                if contains(article, footnote):
                    parent_id = article.get("article_id")
                    group = f"footnotes:{parent_id}"
                    break
        elif isinstance(scope, str) and scope.startswith("annex-"):
            parent_id = f"{document_id}:annex:{scope.removeprefix('annex-')}"
            group = f"footnotes:{parent_id}"
        else:
            parent_id = None
            group = f"footnotes:{scope}"
            errors.append(
                problem(
                    json_path,
                    document_id,
                    footnote.get("structure_id"),
                    footnote.get("start"),
                    footnote.get("end"),
                    f"footnote scope {scope} is not act or annex",
                )
            )
        add_item(
            items,
            counts,
            kind="footnote",
            structure_id=footnote.get("structure_id"),
            text=footnote.get("text"),
            start=footnote.get("start"),
            end=footnote.get("end"),
            parent_id=parent_id,
            group=group,
        )

    annex_ids = set()
    for annex in document.get("annexes") or []:
        claim(annex.get("structure_id"), "annex")
        annex_ids.add(annex.get("structure_id"))
        add_item(
            items,
            counts,
            kind="annex",
            structure_id=annex.get("structure_id"),
            text=annex.get("text"),
            start=annex.get("start"),
            end=annex.get("end"),
            parent_id=None,
            group="top",
        )
        blocks_by_id = {}
        for block in annex.get("blocks") or []:
            claim(block.get("block_id"), "annex block")
            blocks_by_id[block.get("block_id")] = block
            add_item(
                items,
                counts,
                kind="block",
                structure_id=block.get("block_id"),
                text=block.get("text"),
                start=block.get("start"),
                end=block.get("end"),
                parent_id=annex.get("structure_id"),
                group=f"blocks:{annex.get('structure_id')}",
            )
        for table in annex.get("tables") or []:
            claim(table.get("table_id"), "table")
            add_item(
                items,
                counts,
                kind="table",
                structure_id=table.get("table_id"),
                text=table.get("text"),
                start=table.get("start"),
                end=table.get("end"),
                parent_id=annex.get("structure_id"),
                group=f"tables:{annex.get('structure_id')}",
            )
            for row in table.get("located_rows") or []:
                block = blocks_by_id.get(row.get("block_id"))
                if block is None:
                    errors.append(
                        problem(
                            json_path,
                            document_id,
                            table.get("table_id"),
                            row.get("start"),
                            row.get("end"),
                            f"table row block {row.get('block_id')} does not exist",
                        )
                    )
                elif (row.get("start"), row.get("end"), row.get("text")) != (
                    block.get("start"),
                    block.get("end"),
                    block.get("text"),
                ):
                    errors.append(
                        problem(
                            json_path,
                            document_id,
                            row.get("block_id"),
                            row.get("start"),
                            row.get("end"),
                            "table row position differs from its block",
                        )
                    )
                add_item(
                    items,
                    counts,
                    kind="table_row",
                    structure_id=row.get("block_id"),
                    text=row.get("text"),
                    start=row.get("start"),
                    end=row.get("end"),
                    parent_id=table.get("table_id"),
                    group=f"rows:{table.get('table_id')}",
                )
    for footnote in document.get("footnotes") or []:
        scope = footnote.get("scope")
        if isinstance(scope, str) and scope.startswith("annex-"):
            parent_id = f"{document_id}:annex:{scope.removeprefix('annex-')}"
            if parent_id not in annex_ids:
                errors.append(
                    problem(
                        json_path,
                        document_id,
                        footnote.get("structure_id"),
                        footnote.get("start"),
                        footnote.get("end"),
                        f"annex {parent_id} does not exist",
                    )
                )
    block_ids = {item["structure_id"] for item in items if item["kind"] == "block"}
    for footnote in document.get("footnotes") or []:
        for block_id in footnote.get("referenced_by") or []:
            if block_id not in block_ids:
                errors.append(
                    problem(
                        json_path,
                        document_id,
                        footnote.get("structure_id"),
                        footnote.get("start"),
                        footnote.get("end"),
                        f"referenced block {block_id} does not exist",
                    )
                )
    for container in (title, preamble, signature, *articles, *(document.get("annexes") or [])):
        for block in container.get("blocks") or []:
            for ref in block.get("footnote_refs") or []:
                if ref not in footnote_html:
                    errors.append(
                        problem(
                            json_path,
                            document_id,
                            block.get("block_id"),
                            block.get("start"),
                            block.get("end"),
                            f"footnote reference {ref} does not exist",
                        )
                    )
    return items, counts, seen


def contains(parent: dict, child: dict) -> bool:
    return (
        is_int(parent.get("start"))
        and is_int(parent.get("end"))
        and is_int(child.get("start"))
        and is_int(child.get("end"))
        and parent["start"] <= child["start"]
        and child["end"] <= parent["end"]
    )


def check_main_articles(document: dict, document_id: str, json_path: Path, errors: list[str]) -> None:
    if document_id != DOCUMENT_ID:
        return
    articles = document.get("articles") or []
    numbers = [article.get("number") for article in articles]
    expected = [str(number) for number in range(1, 36)]
    if numbers != expected or any(article.get("role") != "main_article" for article in articles):
        errors.append(
            problem(
                json_path,
                document_id,
                None,
                None,
                None,
                f"main articles are {numbers}, expected 1..35",
            )
        )
    html_ids = [article.get("html_id") for article in articles]
    if html_ids != [f"art_{number}" for number in expected]:
        errors.append(problem(json_path, document_id, None, None, None, f"main article html ids are {html_ids}"))
    quoted = [
        (article.get("number"), block.get("text"))
        for article in articles
        for block in article.get("blocks") or []
        if block.get("kind") == "quoted_heading"
    ]
    if quoted != [("32", QUOTED_ARTICLE_8A), ("33", QUOTED_ARTICLE_8A)]:
        errors.append(
            problem(
                json_path,
                document_id,
                None,
                None,
                None,
                f"quoted article headings are {quoted}; Article 8a must stay inside Articles 32 and 33",
            )
        )
    article_6 = next((article for article in articles if article.get("number") == "6"), None)
    if article_6 is None or "Article 11(1)" not in article_6.get("text", ""):
        errors.append(
            problem(
                json_path,
                document_id,
                None if article_6 is None else article_6.get("article_id"),
                None if article_6 is None else article_6.get("start"),
                None if article_6 is None else article_6.get("end"),
                "the Article 11(1) cross-reference is not inside Article 6",
            )
        )
    annex_article_cells = [
        cell
        for annex in document.get("annexes") or []
        for table in annex.get("tables") or []
        for row in table.get("rows") or []
        for cell in row
        if cell in {"Article 1", "Article 3"}
    ]
    if "Article 1" not in annex_article_cells:
        errors.append(
            problem(
                json_path,
                document_id,
                None,
                None,
                None,
                "annex correlation table does not keep its own Article numbers",
            )
        )


def check_sale_of_goods(document: dict, document_id: str, json_path: Path, errors: list[str]) -> None:
    if document_id != "eu_sale_of_goods_2019_771":
        return
    if document.get("chapters"):
        errors.append(
            problem(json_path, document_id, None, None, None, "this document has no chapters; chapter objects must stay empty")
        )
    articles = document.get("articles") or []
    expected = [str(number) for number in range(1, 28)]
    numbers = [article.get("number") for article in articles]
    if numbers != expected or any(article.get("role") != "main_article" for article in articles):
        errors.append(
            problem(json_path, document_id, None, None, None, f"main articles are {numbers}, expected 1..27")
        )
    if any(article.get("chapter_id") is not None for article in articles):
        errors.append(problem(json_path, document_id, None, None, None, "chapter_id must be null"))
    html_ids = [article.get("html_id") for article in articles]
    if html_ids != [f"art_{number}" for number in expected]:
        errors.append(problem(json_path, document_id, None, None, None, f"main article html ids are {html_ids}"))
    article_10 = next((article for article in articles if article.get("number") == "10"), None)
    if article_10 is None or "within two years of that time" not in article_10.get("text", ""):
        errors.append(
            problem(
                json_path,
                document_id,
                None if article_10 is None else article_10.get("article_id"),
                None if article_10 is None else article_10.get("start"),
                None if article_10 is None else article_10.get("end"),
                "the two-year liability rule is not inside Article 10",
            )
        )
    list_items = [
        block
        for article in articles
        for block in article.get("blocks") or []
        if block.get("kind") == "list_item"
    ]
    if not list_items:
        errors.append(problem(json_path, document_id, None, None, None, "no list item was retained"))
    footnotes = document.get("footnotes") or []
    if not any(footnote.get("marker") == "1" and "OJ C 264" in (footnote.get("text") or "") for footnote in footnotes):
        errors.append(problem(json_path, document_id, None, None, None, "act footnote 1 is missing"))
    annex_cells = [
        cell
        for annex in document.get("annexes") or []
        for table in annex.get("tables") or []
        for row in table.get("rows") or []
        for cell in row
    ]
    if "Article 1" not in annex_cells or "Article 1(1)" not in annex_cells:
        errors.append(
            problem(
                json_path,
                document_id,
                None,
                None,
                None,
                "annex correlation cells were not kept as table text",
            )
        )


def check_digital_content(document: dict, document_id: str, json_path: Path, errors: list[str]) -> None:
    if document_id != "eu_digital_content_2019_770":
        return
    if document.get("chapters"):
        errors.append(
            problem(json_path, document_id, None, None, None, "this document has no chapters; chapter objects must stay empty")
        )
    if document.get("annexes"):
        errors.append(problem(json_path, document_id, None, None, None, "this document has no annex"))
    articles = document.get("articles") or []
    expected = [str(number) for number in range(1, 28)]
    numbers = [article.get("number") for article in articles]
    if numbers != expected or any(article.get("role") != "main_article" for article in articles):
        errors.append(
            problem(json_path, document_id, None, None, None, f"main articles are {numbers}, expected 1..27")
        )
    if any(article.get("chapter_id") is not None for article in articles):
        errors.append(problem(json_path, document_id, None, None, None, "chapter_id must be null"))
    html_ids = [article.get("html_id") for article in articles]
    if html_ids != [f"art_{number}" for number in expected]:
        errors.append(problem(json_path, document_id, None, None, None, f"main article html ids are {html_ids}"))
    recitals = (document.get("preamble") or {}).get("recitals") or []
    recital_numbers = [recital.get("number") for recital in recitals]
    if recital_numbers != [str(number) for number in range(1, 88)]:
        errors.append(problem(json_path, document_id, None, None, None, f"recitals are {recital_numbers}, expected 1..87"))
    article_11 = next((article for article in articles if article.get("number") == "11"), None)
    if article_11 is None or "shall not be less than two years from the time of supply" not in article_11.get("text", ""):
        errors.append(
            problem(
                json_path,
                document_id,
                None if article_11 is None else article_11.get("article_id"),
                None if article_11 is None else article_11.get("start"),
                None if article_11 is None else article_11.get("end"),
                "the two-year minimum period is not inside Article 11",
            )
        )
    list_items = [
        block
        for article in articles
        for block in article.get("blocks") or []
        if block.get("kind") == "list_item"
    ]
    if not list_items:
        errors.append(problem(json_path, document_id, None, None, None, "no list item was retained"))
    footnotes = document.get("footnotes") or []
    if len(footnotes) != 23 or not any(
        footnote.get("marker") == "1" and "OJ C 264" in (footnote.get("text") or "") for footnote in footnotes
    ):
        errors.append(problem(json_path, document_id, None, None, None, "act footnotes are incomplete"))


def section_records(document: dict) -> list[dict]:
    sections = document.get("sections")
    if sections is None:
        return [section for chapter in document.get("chapters") or [] for section in chapter.get("sections") or []]
    return sections


def check_section_structure(document: dict, document_id: str, json_path: Path, errors: list[str]) -> None:
    chapters = document.get("chapters") or []
    articles = document.get("articles") or []
    sections = section_records(document)
    nested = [section for chapter in chapters for section in chapter.get("sections") or []]
    has_ref = any(article.get("section_id") not in (None, "") for article in articles)
    if not sections and not nested and not has_ref:
        return
    if document.get("sections") is not None and [item.get("structure_id") for item in sections] != [
        item.get("structure_id") for item in nested
    ]:
        errors.append(problem(json_path, document_id, None, None, None, "top-level sections do not match chapter sections"))
    chapter_by_id = {chapter.get("structure_id"): chapter for chapter in chapters}
    seen: set[str] = set()
    sections_by_id: dict[str, dict] = {}
    for section in sections:
        structure_id = section.get("structure_id")
        if not isinstance(structure_id, str) or structure_id in seen:
            errors.append(problem(json_path, document_id, structure_id, section.get("start"), section.get("end"), "duplicate or missing section id"))
            continue
        seen.add(structure_id)
        sections_by_id[structure_id] = section
        chapter = chapter_by_id.get(section.get("chapter_id"))
        if chapter is None:
            errors.append(
                problem(
                    json_path,
                    document_id,
                    structure_id,
                    section.get("start"),
                    section.get("end"),
                    f"section chapter_id {section.get('chapter_id')} does not exist",
                )
            )
            continue
        if not contains(chapter, section):
            errors.append(
                problem(
                    json_path,
                    document_id,
                    structure_id,
                    section.get("start"),
                    section.get("end"),
                    f"section span exceeds parent chapter {chapter.get('structure_id')} "
                    f"span=[{chapter.get('start')}, {chapter.get('end')})",
                )
            )
    for article in articles:
        section_id = article.get("section_id")
        if section_id in (None, ""):
            continue
        section = sections_by_id.get(section_id)
        if section is None:
            errors.append(
                problem(
                    json_path,
                    document_id,
                    article.get("article_id"),
                    article.get("start"),
                    article.get("end"),
                    f"section_id {section_id} does not exist",
                )
            )
            continue
        if article.get("chapter_id") != section.get("chapter_id"):
            errors.append(
                problem(
                    json_path,
                    document_id,
                    article.get("article_id"),
                    article.get("start"),
                    article.get("end"),
                    f"article chapter {article.get('chapter_id')} does not match section chapter {section.get('chapter_id')}",
                )
            )
        if article.get("section_number") != section.get("number"):
            errors.append(
                problem(
                    json_path,
                    document_id,
                    article.get("article_id"),
                    article.get("start"),
                    article.get("end"),
                    f"section_number {article.get('section_number')} does not match section {section.get('number')}",
                )
            )
        if not contains(section, article):
            errors.append(
                problem(
                    json_path,
                    document_id,
                    article.get("article_id"),
                    article.get("start"),
                    article.get("end"),
                    f"article span is outside section {section_id} span=[{section.get('start')}, {section.get('end')})",
                )
            )
    for chapter in chapters:
        own_sections = [section for section in sections if section.get("chapter_id") == chapter.get("structure_id")]
        direct = [
            article
            for article in articles
            if article.get("chapter_id") == chapter.get("structure_id") and article.get("section_id") in (None, "")
        ]
        for article in direct:
            if any(contains(section, article) for section in own_sections):
                errors.append(
                    problem(
                        json_path,
                        document_id,
                        article.get("article_id"),
                        article.get("start"),
                        article.get("end"),
                        "chapter article without a section falls inside a section span",
                    )
                )
        pieces = [(article.get("start"), article.get("end"), article.get("article_id")) for article in direct]
        pieces.extend((section.get("start"), section.get("end"), section.get("structure_id")) for section in own_sections)
        ordered = sorted(pieces, key=lambda item: (item[0] is None, item[0]))
        previous = None
        expanded: list[str] = []
        for start, end, structure_id in ordered:
            if previous is not None and is_int(previous[1]) and is_int(start) and start < previous[1]:
                errors.append(
                    problem(
                        json_path,
                        document_id,
                        structure_id,
                        start,
                        end,
                        f"chapter body order is wrong after {previous[2]}",
                    )
                )
            previous = (start, end, structure_id)
            if structure_id in sections_by_id:
                expanded.extend(sections_by_id[structure_id].get("article_ids") or [])
            else:
                expanded.append(structure_id)
        if expanded != (chapter.get("article_ids") or []):
            errors.append(
                problem(
                    json_path,
                    document_id,
                    chapter.get("structure_id"),
                    chapter.get("start"),
                    chapter.get("end"),
                    f"chapter article order {chapter.get('article_ids')} does not follow sections {expanded}",
                )
            )


def check_unfair_practices(document: dict, document_id: str, json_path: Path, errors: list[str]) -> None:
    if document_id != "eu_unfair_practices_2005_29":
        return
    articles = document.get("articles") or []
    expected = [str(number) for number in range(1, 22)]
    numbers = [article.get("number") for article in articles]
    if numbers != expected or any(article.get("role") != "main_article" for article in articles):
        errors.append(problem(json_path, document_id, None, None, None, f"main articles are {numbers}, expected 1..21"))
    chapters = document.get("chapters") or []
    if [chapter.get("number") for chapter in chapters] != ["1", "2", "3", "4"]:
        errors.append(problem(json_path, document_id, None, None, None, "chapters must be 1..4"))
    if [chapter.get("html_id") for chapter in chapters] != ["cpt_1", "cpt_2", "cpt_3", "cpt_4"]:
        errors.append(problem(json_path, document_id, None, None, None, "chapter html ids must be the containers cpt_1..cpt_4"))
    sections = section_records(document)
    expected_sections = [
        "eu_unfair_practices_2005_29:chapter:2:section:1",
        "eu_unfair_practices_2005_29:chapter:2:section:2",
    ]
    if [section.get("structure_id") for section in sections] != expected_sections:
        errors.append(problem(json_path, document_id, None, None, None, f"sections are {[section.get('structure_id') for section in sections]}"))
    by_number = {article.get("number"): article for article in articles}
    if by_number.get("5", {}).get("section_id") is not None:
        errors.append(problem(json_path, document_id, by_number.get("5", {}).get("article_id"), None, None, "Article 5 must not have a section"))
    for number, section_id in (("6", expected_sections[0]), ("7", expected_sections[0]), ("8", expected_sections[1]), ("9", expected_sections[1])):
        article = by_number.get(number) or {}
        if article.get("section_id") != section_id or article.get("chapter_id") != "eu_unfair_practices_2005_29:chapter:2":
            errors.append(
                problem(
                    json_path,
                    document_id,
                    article.get("article_id"),
                    article.get("start"),
                    article.get("end"),
                    f"Article {number} section_id is {article.get('section_id')}",
                )
            )
    recitals = (document.get("preamble") or {}).get("recitals") or []
    if [recital.get("number") for recital in recitals] != [str(number) for number in range(1, 26)]:
        errors.append(problem(json_path, document_id, None, None, None, "recitals must be 1..25"))
    if [annex.get("label") for annex in document.get("annexes") or []] != ["ANNEX I", "ANNEX II"]:
        errors.append(problem(json_path, document_id, None, None, None, "annexes must be ANNEX I and ANNEX II"))


def check_unfair_terms(document: dict, document_id: str, json_path: Path, errors: list[str]) -> None:
    if document_id != "eu_unfair_terms_93_13":
        return
    articles = document.get("articles") or []
    expected = [str(number) for number in range(1, 12)]
    numbers = [article.get("number") for article in articles]
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
    if numbers != expected or [article.get("html_id") for article in articles] != html_ids:
        errors.append(problem(json_path, document_id, None, None, None, f"main articles are {numbers}, expected 1..11 from p.ti-art"))
    if any(article.get("role") != "main_article" for article in articles):
        errors.append(problem(json_path, document_id, None, None, None, "a parsed article is not a main article"))
    if document.get("chapters"):
        errors.append(problem(json_path, document_id, None, None, None, "old-style act must not have chapters"))
    if section_records(document):
        errors.append(problem(json_path, document_id, None, None, None, "old-style act must not have sections"))
    for article in articles:
        if article.get("chapter_id") is not None or article.get("section_id") is not None or article.get("heading") is not None:
            errors.append(
                problem(
                    json_path,
                    document_id,
                    article.get("article_id"),
                    article.get("start"),
                    article.get("end"),
                    "main article has a chapter, section, or invented subtitle",
                )
            )
        if any(block.get("kind") == "quoted_heading" for block in article.get("blocks") or []):
            errors.append(
                problem(
                    json_path,
                    document_id,
                    article.get("article_id"),
                    article.get("start"),
                    article.get("end"),
                    "an article heading was kept inside the article body",
                )
            )
    by_number = {article.get("number"): article for article in articles}
    article_11 = by_number.get("11") or {}
    signature = document.get("signature") or {}
    annexes = document.get("annexes") or []
    if article_11.get("text") != "Article 11\nThis Directive is addressed to the Member States.":
        errors.append(problem(json_path, document_id, article_11.get("article_id"), article_11.get("start"), article_11.get("end"), "Article 11 contains text after the addressee sentence"))
    if not str(signature.get("text") or "").startswith("Done at Luxembourg, 5 April 1993."):
        errors.append(problem(json_path, document_id, signature.get("structure_id"), signature.get("start"), signature.get("end"), "signature is missing or was merged elsewhere"))
    if is_int(article_11.get("end")) and is_int(signature.get("start")) and article_11.get("end") > signature.get("start"):
        errors.append(problem(json_path, document_id, article_11.get("article_id"), article_11.get("start"), article_11.get("end"), "Article 11 overlaps the signature"))
    if [annex.get("label") for annex in annexes] != ["ANNEX"]:
        errors.append(problem(json_path, document_id, None, None, None, "annex must be the single ANNEX"))
    annex = annexes[0] if annexes else {}
    if is_int(signature.get("end")) and is_int(annex.get("start")) and annex.get("start") < signature.get("end"):
        errors.append(problem(json_path, document_id, annex.get("structure_id"), annex.get("start"), annex.get("end"), "annex overlaps the signature"))
    footnotes = document.get("footnotes") or []
    if len(footnotes) != 4 or [footnote.get("marker") for footnote in footnotes] != ["1", "2", "3", "4"]:
        errors.append(problem(json_path, document_id, None, None, None, "footnotes must stay the four act notes (1) to (4)"))
    if footnotes and is_int(article_11.get("end")) and is_int(footnotes[0].get("start")) and footnotes[0].get("start") < article_11.get("end"):
        errors.append(problem(json_path, document_id, article_11.get("article_id"), article_11.get("start"), article_11.get("end"), "Article 11 overlaps a footnote"))
    recitals = (document.get("preamble") or {}).get("recitals") or []
    if [recital.get("ordinal") for recital in recitals] != [str(number) for number in range(1, 25)]:
        errors.append(problem(json_path, document_id, None, None, None, "Whereas paragraphs must use ordinals 1..24"))
    if any(recital.get("number") is not None or recital.get("official_number") is not None for recital in recitals):
        errors.append(problem(json_path, document_id, None, None, None, "an unnumbered Whereas paragraph has an official number"))
    annex_text = annex.get("text") or ""
    if "ARTICLE 3 (3)" not in annex_text or "Scope of subparagraphs (g), (j) and (1)" not in annex_text:
        errors.append(problem(json_path, document_id, annex.get("structure_id"), annex.get("start"), annex.get("end"), "annex cross-reference or exception heading is missing"))


def check_items(items: list[dict], text: str, document_id: str, json_path: Path, errors: list[str], progress: Progress) -> None:
    by_id = {item["structure_id"]: item for item in items if isinstance(item["structure_id"], str)}
    groups: dict[str, list[dict]] = {}
    for item in items:
        structure_id = item["structure_id"]
        start = item["start"]
        end = item["end"]
        expected = item["text"]
        if not is_int(start) or not is_int(end):
            errors.append(
                problem(json_path, document_id, structure_id, start, end, "start and end must be integers")
            )
        elif start < 0 or end < start or end > len(text):
            errors.append(
                problem(
                    json_path,
                    document_id,
                    structure_id,
                    start,
                    end,
                    f"span is outside the cleaned text of {len(text)} characters",
                )
            )
        elif not isinstance(expected, str) or text[start:end] != expected:
            errors.append(
                problem(json_path, document_id, structure_id, start, end, "cleaned text slice does not equal the stored text")
            )
        parent_id = item["parent_id"]
        if parent_id is not None:
            parent = by_id.get(parent_id)
            if parent is None:
                errors.append(
                    problem(json_path, document_id, structure_id, start, end, f"parent {parent_id} does not exist")
                )
            elif not contains(parent, item):
                errors.append(
                    problem(
                        json_path,
                        document_id,
                        structure_id,
                        start,
                        end,
                        f"span is outside parent {parent_id} span=[{parent.get('start')}, {parent.get('end')})",
                    )
                )
        groups.setdefault(item["group"], []).append(item)
        progress.advance()
    for group, members in groups.items():
        previous = None
        for item in members:
            if previous is not None and is_int(previous["start"]) and is_int(previous["end"]) and is_int(item["start"]):
                if item["start"] < previous["end"]:
                    errors.append(
                        problem(
                            json_path,
                            document_id,
                            item["structure_id"],
                            item["start"],
                            item["end"],
                            f"sibling order or overlap is wrong after {previous['structure_id']} "
                            f"span=[{previous['start']}, {previous['end']}) in {group}",
                        )
                    )
            previous = item


def validate_corpus(root: Path, document_id: str) -> tuple[list[str], dict[str, int], dict[str, str]]:
    errors: list[str] = []
    source = source_record(root, document_id, errors)
    if source is None:
        return errors, {}, {}
    snapshot = source.get("snapshot") or {}
    snapshot_path = root / str(snapshot.get("path") or "")
    check_hash(snapshot_path, document_id, snapshot.get("sha256"), errors)
    json_path = root / "data" / "processed" / f"{document_id}.json"
    document = load_json(json_path, document_id, errors)
    if document is None:
        return errors, {}, {}
    if document.get("document_id") != document_id:
        errors.append(problem(json_path, document_id, document_id, None, None, "JSON document_id does not match"))
    text_path = root / str(document.get("clean_text_path") or "")
    text_bytes = check_hash(text_path, document_id, document.get("clean_text_sha256"), errors)
    offsets = document.get("character_offsets")
    if not isinstance(offsets, dict) or offsets.get("unit") != "python_character" or offsets.get("interval") != "[start, end)":
        errors.append(
            problem(
                json_path,
                document_id,
                document_id,
                None,
                None,
                "character_offsets must describe Python character indexes [start, end)",
            )
        )
    if text_bytes is None:
        return errors, {}, {}
    text = text_bytes.decode("utf-8")
    if "\r" in text or not text.endswith("\n"):
        errors.append(problem(text_path, document_id, document_id, None, None, "cleaned text must use LF and end with one LF"))
    items, counts, defined = collect_document(document, document_id, errors, json_path)
    progress = Progress(len(items) + 1)
    check_items(items, text, document_id, json_path, errors, progress)
    check_main_articles(document, document_id, json_path, errors)
    check_sale_of_goods(document, document_id, json_path, errors)
    check_digital_content(document, document_id, json_path, errors)
    check_section_structure(document, document_id, json_path, errors)
    check_unfair_practices(document, document_id, json_path, errors)
    check_unfair_terms(document, document_id, json_path, errors)
    progress.advance()
    progress.finish()
    return errors, counts, defined


DOCUMENT_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def registered_sources(root: Path, errors: list[str]) -> list[dict]:
    path = root / "data" / "sources.json"
    if not path.is_file():
        errors.append(problem(path, "-", None, None, None, "sources.json is missing"))
        return []
    payload = load_json(path, "-", errors)
    if payload is None:
        return []
    items = payload.get("sources") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        errors.append(problem(path, "-", None, None, None, "sources must be a list"))
        return []
    if not items:
        errors.append(problem(path, "-", None, None, None, "sources list is empty"))
        return []
    seen: set[str] = set()
    valid: list[dict] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(problem(path, "-", None, None, None, f"source {index} is not an object"))
            continue
        document_id = item.get("document_id")
        if not isinstance(document_id, str) or DOCUMENT_ID_RE.fullmatch(document_id) is None:
            errors.append(problem(path, str(document_id), None, None, None, f"source {index} has invalid document_id"))
            continue
        if document_id in seen:
            errors.append(problem(path, document_id, document_id, None, None, "document_id is duplicated"))
            continue
        seen.add(document_id)
        valid.append(item)
    valid.sort(key=lambda item: item["document_id"])
    return valid


def product_inventory(root: Path, document_ids: set[str], errors: list[str]) -> None:
    """只核对 data/processed。sample_corpus 中的副本不是第二份正式文档。"""
    processed = root / "data" / "processed"
    if not processed.is_dir():
        errors.append(problem(processed, "-", None, None, None, "processed directory does not exist"))
        return
    for path in sorted([*processed.glob("*.json"), *processed.glob("*.txt")]):
        if path.stem not in document_ids:
            errors.append(problem(path, path.stem, None, None, None, "processed file is not registered in sources.json"))
    for document_id in sorted(document_ids):
        for suffix in (".json", ".txt"):
            path = processed / f"{document_id}{suffix}"
            if not path.is_file():
                errors.append(problem(path, document_id, None, None, None, "registered processed file does not exist"))


def structure_definitions(document: dict) -> list[str]:
    """结构定义。章节内的节与顶层 sections 镜像只计一次，article_ids 等引用不计入。"""
    found: list[str] = []

    def add(value: object) -> None:
        if isinstance(value, str) and value:
            found.append(value)

    title = document.get("title") or {}
    add(title.get("structure_id"))
    for block in title.get("blocks") or []:
        add(block.get("block_id"))
    preamble = document.get("preamble") or {}
    add(preamble.get("structure_id"))
    for block in preamble.get("blocks") or []:
        add(block.get("block_id"))
    for recital in preamble.get("recitals") or []:
        add(recital.get("structure_id"))
    for chapter in document.get("chapters") or []:
        add(chapter.get("structure_id"))
    for section in section_records(document):
        add(section.get("structure_id"))
    for article in document.get("articles") or []:
        add(article.get("article_id"))
        for block in article.get("blocks") or []:
            add(block.get("block_id"))
    signature = document.get("signature") or {}
    add(signature.get("structure_id"))
    for block in signature.get("blocks") or []:
        add(block.get("block_id"))
    for footnote in document.get("footnotes") or []:
        add(footnote.get("structure_id"))
    for annex in document.get("annexes") or []:
        add(annex.get("structure_id"))
        for block in annex.get("blocks") or []:
            add(block.get("block_id"))
        for table in annex.get("tables") or []:
            add(table.get("table_id"))
    return found


def structure_references(document: dict) -> list[tuple[str, str]]:
    """引用必须能解析到定义，自身不再登记为一条新的结构。"""
    refs: list[tuple[str, str]] = []
    for chapter in document.get("chapters") or []:
        owner = str(chapter.get("structure_id") or "")
        for article_id in chapter.get("article_ids") or []:
            if isinstance(article_id, str):
                refs.append((owner, article_id))
    for section in section_records(document):
        owner = str(section.get("structure_id") or "")
        chapter_id = section.get("chapter_id")
        if isinstance(chapter_id, str):
            refs.append((owner, chapter_id))
    for article in document.get("articles") or []:
        owner = str(article.get("article_id") or "")
        for key in ("chapter_id", "section_id"):
            value = article.get(key)
            if isinstance(value, str) and value:
                refs.append((owner, value))
    for recital in (document.get("preamble") or {}).get("recitals") or []:
        owner = str(recital.get("structure_id") or "")
        for block_id in recital.get("block_ids") or []:
            if isinstance(block_id, str):
                refs.append((owner, block_id))
    for footnote in document.get("footnotes") or []:
        owner = str(footnote.get("structure_id") or "")
        for block_id in footnote.get("referenced_by") or []:
            if isinstance(block_id, str):
                refs.append((owner, block_id))
    for annex in document.get("annexes") or []:
        for table in annex.get("tables") or []:
            owner = str(table.get("table_id") or "")
            for row in table.get("located_rows") or []:
                block_id = row.get("block_id")
                if isinstance(block_id, str):
                    refs.append((owner, block_id))
    return refs


def check_correspondence(root: Path, source: dict, document: dict, errors: list[str]) -> None:
    document_id = str(source.get("document_id") or "")
    json_path = root / "data" / "processed" / f"{document_id}.json"
    snapshot = source.get("snapshot") or {}
    meta = document.get("source") or {}
    if document.get("document_id") != document_id:
        errors.append(problem(json_path, document_id, document_id, None, None, "JSON document_id does not match the source record"))
    if meta.get("document_id") != document_id:
        errors.append(problem(json_path, document_id, document_id, None, None, "source metadata document_id does not match"))
    if meta.get("snapshot_path") != snapshot.get("path"):
        errors.append(problem(json_path, document_id, document_id, None, None, "snapshot path does not match sources.json"))
    if meta.get("snapshot_sha256") != snapshot.get("sha256"):
        errors.append(problem(json_path, document_id, document_id, None, None, "snapshot sha256 does not match sources.json"))
    expected_text = f"data/processed/{document_id}.txt"
    if document.get("clean_text_path") != expected_text:
        errors.append(problem(json_path, document_id, document_id, None, None, f"clean_text_path must be {expected_text}"))


def validate_all(root: Path) -> int:
    errors: list[str] = []
    sources = registered_sources(root, errors)
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        print(f"result=failed errors={len(errors)}", file=sys.stderr)
        return 1
    document_ids = {source["document_id"] for source in sources}
    product_inventory(root, document_ids, errors)
    defined_owner: dict[str, str] = {}
    summaries: list[tuple[str, dict[str, int]]] = []
    total_articles = 0
    for source in sources:
        document_id = source["document_id"]
        json_path = root / "data" / "processed" / f"{document_id}.json"
        doc_errors, counts, defined = validate_corpus(root, document_id)
        errors.extend(doc_errors)
        if json_path.is_file():
            document = load_json(json_path, document_id, errors)
            if document is not None:
                check_correspondence(root, source, document, errors)
                for owner, target in structure_references(document):
                    if defined and target not in defined:
                        errors.append(problem(json_path, document_id, owner or None, None, None, f"reference {target} does not resolve"))
        for structure_id, owner in defined.items():
            previous = defined_owner.get(structure_id)
            if previous is not None:
                errors.append(problem(json_path, document_id, structure_id, None, None, f"duplicate structure id, also used by {previous}"))
            else:
                defined_owner[structure_id] = f"{document_id}:{owner}"
        if not doc_errors:
            summaries.append((document_id, counts))
            total_articles += counts.get("article", 0)
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        print(f"result=failed errors={len(errors)}", file=sys.stderr)
        return 1
    for document_id, counts in summaries:
        rendered = " ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))
        print(f"document_id={document_id}")
        print("scope=corpus")
        print(f"offset_checks {rendered}")
    print(f"documents={len(sources)}")
    print(f"main_articles={total_articles}")
    print("result=ok")
    return 0


FORMAL_CORPUS_VERSION = "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
GOLD_FIELDS = (
    "case_id",
    "corpus_version",
    "question",
    "question_type",
    "should_refuse",
    "reference_answer",
    "key_facts",
    "evidence",
    "refusal_reason",
)
QUESTION_TYPES = {"single_article", "multi_evidence", "unanswerable"}


def structure_index(root: Path, document_id: str) -> dict[str, tuple[int, int]]:
    path = root / "data" / "processed" / f"{document_id}.json"
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    found: dict[str, tuple[int, int]] = {}

    def add(item: dict, key: str) -> None:
        identifier = item.get(key)
        if isinstance(identifier, str) and "start" in item and "end" in item:
            found.setdefault(identifier, (item["start"], item["end"]))

    for name in ("title", "preamble", "signature"):
        if isinstance(document.get(name), dict):
            add(document[name], "structure_id")
    for chapter in document.get("chapters", []):
        add(chapter, "structure_id")
        for section in chapter.get("sections") or []:
            add(section, "structure_id")
    for section in document.get("sections") or []:
        add(section, "structure_id")
    for article in document.get("articles", []):
        add(article, "article_id")
    for annex in document.get("annexes", []):
        add(annex, "structure_id")
    for recital in (document.get("preamble") or {}).get("recitals", []):
        add(recital, "structure_id")
    for footnote in document.get("footnotes", []):
        add(footnote, "structure_id")
    return found


def check_cases(documents: list[dict], structures: dict[str, dict[str, tuple[int, int]]], cases: list[dict], corpus_version: str) -> list[str]:
    errors: list[str] = []
    by_id = {doc["document_id"]: doc for doc in documents}
    seen: set[str] = set()
    for index, case in enumerate(cases, start=1):
        case_id = case.get("case_id") if isinstance(case, dict) else None
        label = case_id if isinstance(case_id, str) else f"line {index}"
        if not isinstance(case, dict) or tuple(case) != GOLD_FIELDS:
            errors.append(problem(None, label, None, None, None, "gold case fields are missing or reordered"))
            continue
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            errors.append(problem(None, label, None, None, None, "case_id is missing or duplicated"))
        else:
            seen.add(case_id)
        if case["corpus_version"] != corpus_version:
            errors.append(problem(None, label, None, None, None, "corpus_version does not match the formal corpus"))
        if case["question_type"] not in QUESTION_TYPES or not isinstance(case["should_refuse"], bool):
            errors.append(problem(None, label, None, None, None, "question_type or should_refuse is invalid"))
        if not isinstance(case["question"], str) or not case["question"].strip():
            errors.append(problem(None, label, None, None, None, "question is empty"))
        if case["should_refuse"]:
            if case["question_type"] != "unanswerable" or case["evidence"] != [] or case["key_facts"] != []:
                errors.append(problem(None, label, None, None, None, "refusal case must be unanswerable with empty evidence and key_facts"))
            if not isinstance(case["reference_answer"], str) or not case["reference_answer"].strip():
                errors.append(problem(None, label, None, None, None, "refusal reference_answer is empty"))
            if not isinstance(case["refusal_reason"], str) or not case["refusal_reason"].strip():
                errors.append(problem(None, label, None, None, None, "refusal_reason is empty"))
            continue
        if case["question_type"] == "unanswerable" or case["refusal_reason"] is not None:
            errors.append(problem(None, label, None, None, None, "answerable case is marked unanswerable or has a refusal reason"))
        if not isinstance(case["reference_answer"], str) or not case["reference_answer"].strip():
            errors.append(problem(None, label, None, None, None, "reference_answer is empty"))
        facts = case["key_facts"]
        evidence = case["evidence"]
        if not isinstance(facts, list) or not facts or not isinstance(evidence, list) or not evidence:
            errors.append(problem(None, label, None, None, None, "answerable case needs key_facts and evidence"))
            continue
        if case["question_type"] == "single_article" and len(evidence) != 1:
            errors.append(problem(None, label, None, None, None, "single_article requires exactly one evidence segment"))
        if case["question_type"] == "multi_evidence" and len(evidence) < 2:
            errors.append(problem(None, label, None, None, None, "multi_evidence requires at least two evidence segments"))
        quotes = []
        holders = []
        for item in evidence:
            if not isinstance(item, dict):
                errors.append(problem(None, label, None, None, None, "evidence item is not an object"))
                continue
            document_id = item.get("document_id")
            holder = item.get("article_id") or item.get("structure_id")
            start, end = item.get("start"), item.get("end")
            quote = item.get("quote")
            if not isinstance(document_id, str) or document_id not in by_id:
                errors.append(problem(None, label, holder if isinstance(holder, str) else None, None, None, "evidence document_id is not in the formal corpus"))
                continue
            if not isinstance(holder, str) or holder not in structures.get(document_id, {}):
                errors.append(problem(None, str(document_id), holder if isinstance(holder, str) else None, None, None, f"{label}: evidence holder is not a known article or structure"))
                continue
            if not is_int(start) or not is_int(end) or not isinstance(quote, str):
                errors.append(problem(None, document_id, holder, None, None, f"{label}: evidence offsets or quote are invalid"))
                continue
            text = by_id[document_id]["text"]
            holder_start, holder_end = structures[document_id][holder]
            if not (holder_start <= start < end <= holder_end) or not 0 < len(quote) < 400 or text[start:end] != quote:
                errors.append(problem(None, document_id, holder, start, end, f"{label}: evidence quote is outside its structure or does not match the frozen text"))
                continue
            quotes.append(quote)
            holders.append(holder)
        if isinstance(facts, list) and quotes and any(not isinstance(fact, str) or fact not in quotes for fact in facts):
            errors.append(problem(None, label, None, None, None, "a key fact is not copied from an evidence quote"))
        if case["question_type"] == "single_article" and len(set(holders)) > 1:
            errors.append(problem(None, label, None, None, None, "single_article evidence comes from more than one structure"))
    return errors


def validate_eval(root: Path) -> int:
    project = Path(__file__).resolve().parents[1]
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))
    from app.retrieval.types import formal_loader

    package = root / "data" / "formal_corpus"
    manifest_path = package / "manifest.json"
    corpus_path = root / "data" / "corpus_manifest.json"
    gold_path = root / "data" / "eval" / "gold.jsonl"
    eval_manifest_path = root / "data" / "eval" / "manifest.json"
    errors: list[str] = []
    if not manifest_path.is_file():
        errors.append(problem(manifest_path, "-", None, None, None, "formal manifest is missing"))
    else:
        package_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        version = package_manifest.get("corpus_version")
        if version != FORMAL_CORPUS_VERSION:
            errors.append(problem(manifest_path, "-", None, None, None, "formal corpus version is not the frozen version"))
        if corpus_path.is_file():
            corpus_manifest = json.loads(corpus_path.read_text(encoding="utf-8"))
            if corpus_manifest.get("corpus_version") != version:
                errors.append(problem(corpus_path, "-", None, None, None, "corpus manifest version differs from the formal package"))
        try:
            documents = formal_loader(package)(version)
        except Exception as exc:
            errors.append(problem(package, "-", None, None, None, f"formal_loader failed: {exc}"))
            documents = []
        if documents and (len(documents) != 5 or len({doc["document_id"] for doc in documents}) != 5 or sum(len(doc["articles"]) for doc in documents) != 121):
            errors.append(problem(package, "-", None, None, None, "formal corpus is not five documents and 121 main articles"))
        if not gold_path.is_file() or not eval_manifest_path.is_file():
            errors.append(problem(gold_path, "-", None, None, None, "gold.jsonl or eval manifest is missing"))
        else:
            raw = gold_path.read_bytes()
            if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
                errors.append(problem(gold_path, "-", None, None, None, "gold.jsonl must be UTF-8 LF without BOM and must end with LF"))
            cases = []
            for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
                if not line.strip():
                    errors.append(problem(gold_path, f"line {line_number}", None, None, None, "blank line in gold.jsonl"))
                    continue
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    errors.append(problem(gold_path, f"line {line_number}", None, None, None, f"invalid JSON: {exc}"))
            structures = {doc["document_id"]: structure_index(root, doc["document_id"]) for doc in documents}
            errors.extend(check_cases(documents, structures, cases, version))
            answerable = [case for case in cases if isinstance(case, dict) and case.get("should_refuse") is False]
            refusals = [case for case in cases if isinstance(case, dict) and case.get("should_refuse") is True]
            if len(cases) != 30 or len(answerable) != 24 or len(refusals) != 6:
                errors.append(problem(gold_path, "-", None, None, None, f"expected 30 cases, 24 answerable and 6 refusals, found {len(cases)}, {len(answerable)}, {len(refusals)}"))
            covered = {item.get("document_id") for case in answerable if isinstance(case, dict) for item in case.get("evidence", []) if isinstance(item, dict)}
            expected = {doc["document_id"] for doc in documents}
            if expected and not expected <= covered:
                errors.append(problem(gold_path, "-", None, None, None, f"answerable questions do not cover {sorted(expected - covered)}"))
            manifest = json.loads(eval_manifest_path.read_text(encoding="utf-8"))
            actual = hashlib.sha256(raw).hexdigest()
            if manifest.get("gold_version") != actual or manifest.get("gold_sha256") != actual:
                errors.append(problem(eval_manifest_path, "-", None, None, None, "gold_version does not match gold.jsonl bytes"))
            if manifest.get("corpus_version") != version or manifest.get("question_count") != 30:
                errors.append(problem(eval_manifest_path, "-", None, None, None, "eval manifest corpus version or question count does not match"))
            if manifest.get("answerable_count") != 24 or manifest.get("refusal_count") != 6:
                errors.append(problem(eval_manifest_path, "-", None, None, None, "eval manifest answerable or refusal count does not match"))
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        print(f"result=failed errors={len(errors)}", file=sys.stderr)
        return 1
    print("scope=eval")
    print(f"corpus_version={FORMAL_CORPUS_VERSION}")
    print("questions=30 answerable=24 refusal=6")
    print("result=ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Validate cleaned corpus offsets and identifiers.")
    parser.add_argument("--scope", required=True, choices=["corpus", "eval"])
    parser.add_argument("--document-id", default=None)
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.data_root.resolve() if args.data_root is not None else Path(__file__).resolve().parents[1]
    if args.scope == "eval":
        if args.document_id:
            print("validate_data.py: --document-id is not used with --scope eval", file=sys.stderr)
            return 1
        return validate_eval(root)
    if not args.document_id:
        return validate_all(root)
    errors, counts, _defined = validate_corpus(root, args.document_id)
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        print(f"result=failed errors={len(errors)}", file=sys.stderr)
        return 1
    rendered = " ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))
    print(f"document_id={args.document_id}")
    print(f"scope={args.scope}")
    print(f"offset_checks {rendered}")
    print("result=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
