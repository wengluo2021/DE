"""Read A's richer EUR-Lex export through C's strict source contract.

The projection is in memory only. B always receives the complete original
dictionary, including its original article structure and source digest.
"""
from app.contracts import Article, Document


_DOCUMENT_EXTRAS = {"kind", "chapters", "sections", "source_fields"}
_ARTICLE_EXTRAS = {"role", "number", "heading", "html_id", "chapter_id",
                   "section_id", "section_number", "blocks", "text"}


def document_view(source):
    if isinstance(source, Document):
        return Document.model_validate(source.model_dump())
    if not isinstance(source, dict):
        raise ValueError("Expected a source document")
    if "kind" not in source:
        return Document.model_validate(source)
    if source["kind"] not in {"formal_corpus", "sample_corpus"}:
        raise ValueError("Unsupported A document kind")
    if set(source) != set(Document.model_fields) | _DOCUMENT_EXTRAS:
        raise ValueError("Unexpected A document fields")
    if (not isinstance(source["source_fields"], dict)
            or not isinstance(source["chapters"], list)
            or not isinstance(source["sections"], list)):
        raise ValueError("Invalid A source structure")
    articles = []
    for original in source["articles"]:
        if not isinstance(original, dict) or set(original) != set(Article.model_fields) | _ARTICLE_EXTRAS:
            raise ValueError("Unexpected A article fields")
        article = Article.model_validate({key: original[key] for key in Article.model_fields})
        if (original["role"] != "main_article"
                or original["chapter_id"] != article.chapter
                or original["section_id"] != article.section
                or original["text"] != source["text"][article.start:article.end]):
            raise ValueError("A article aliases or text differ from the frozen source")
        if not isinstance(original["blocks"], list):
            raise ValueError("A article blocks must be a list")
        for block in original["blocks"]:
            if (not isinstance(block, dict) or type(block.get("start")) is not int
                    or type(block.get("end")) is not int
                    or not article.start <= block["start"] < block["end"] <= article.end
                    or block.get("text") != source["text"][block["start"]:block["end"]]):
                raise ValueError("A block differs from its frozen article")
        articles.append(article.model_dump())
    view = {key: source[key] for key in Document.model_fields}
    view["articles"] = articles
    return Document.model_validate(view)
