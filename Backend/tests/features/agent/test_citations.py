from app.features.agent.citations import SourcesTagFilter, parse_declared, select_citations, sources_line
from app.features.agent.schemas import SourceCitation


def _c(name, page, score=0.5, page_end=None, doc=None):
    return SourceCitation(
        document_id=doc or name, document_filename=name, chunk_index=0, snippet="s", score=score, page=page, page_end=page_end
    )


def _stream(filter_, pieces):
    shown = "".join(filter_.feed(p) for p in pieces) + filter_.finish()
    return shown


def test_filter_hides_the_block_even_when_the_tag_is_split_across_deltas():
    f = SourcesTagFilter()
    shown = _stream(f, ["پاسخ نهایی.\n\n<sou", "rces>a.pdf|12; b.pdf|3</sou", "rces>"])
    assert shown == "پاسخ نهایی.\n\n" and f.visible == shown
    assert parse_declared(f.block) == [("a.pdf", 12), ("b.pdf", 3)]


def test_filter_releases_text_that_only_looked_like_the_tag():
    f = SourcesTagFilter()
    assert _stream(f, ["a < b and <sou"]) == "a < b and <sou"
    assert f.block == ""


def test_parse_accepts_persian_digits_and_missing_pages():
    assert parse_declared("نشریه.pdf|۱۲۳\n- data.xlsx") == [("نشریه.pdf", 123), ("data.xlsx", None)]


def test_only_declared_sources_that_the_tools_really_returned_are_kept():
    collected = [_c("a.pdf", 12, 0.6), _c("a.pdf", 12, 0.5), _c("a.pdf", 99, 0.9), _c("r.pdf", 5, 1.0, page_end=9)]
    chosen = select_citations(collected, "a.pdf|12; r.pdf|7; ghost.pdf|1; a.pdf|50</sources>")
    assert [(c.document_filename, c.page) for c in chosen] == [("a.pdf", 12), ("r.pdf", 7)]
    assert chosen[1].page_end is None  # a page inside a read range becomes that single page


def test_without_a_usable_block_the_best_distinct_pages_are_used():
    collected = [_c("a.pdf", 1, 0.2), _c("a.pdf", 1, 0.9), _c("b.pdf", 2, 0.8), _c("c.pdf", 3, 0.7), _c("d.pdf", 4, 0.6)]
    chosen = select_citations(collected, "")
    assert [(c.document_filename, c.page) for c in chosen] == [("a.pdf", 1), ("b.pdf", 2), ("c.pdf", 3)]


def test_history_line_lists_documents_and_pages():
    line = sources_line([_c("a.pdf", 12).model_dump(), _c("x.xlsx", None).model_dump()])
    assert line == "[منابع این پاسخ: a.pdf (صفحه 12)، x.xlsx]"
    assert sources_line([]) == ""
