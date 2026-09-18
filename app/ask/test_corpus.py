from pathlib import Path

import pytest

from app.ask.corpus import as_context, load_corpus, parse_page, verify
from app.ask.schemas import Answer, RuleVerbatim, Source

PAGE = """---
title: Using data with AI
caption: Deliver with AI
---

## What the conditions mean

For personal data, the DPIA route is for a service you are building to
process it, not a way to paste it into an everyday tool.
"""


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    (tmp_path / "ai-toolkit").mkdir()
    (tmp_path / "ai-toolkit" / "guidance").mkdir()
    (tmp_path / "ai-toolkit.md").write_text(
        "---\ntitle: AI digital toolkit\n---\nHome\n"
    )
    (tmp_path / "ai-toolkit" / "guidance" / "using-data-with-ai.md").write_text(PAGE)
    (tmp_path / "other.md").write_text("---\ntitle: Not toolkit\n---\nNo\n")
    return tmp_path


def test_parse_page_splits_frontmatter_and_body():
    page = parse_page("/x", PAGE)
    assert page.title == "Using data with AI"
    assert page.body.startswith("## What the conditions mean")
    assert "caption" not in page.body


def test_parse_page_without_frontmatter_uses_url_as_title():
    page = parse_page("/x", "Just words")
    assert page.title == "/x"
    assert page.body == "Just words"


def test_load_corpus_keys_pages_by_url_and_ignores_other_content(content_dir):
    corpus = load_corpus(content_dir)
    assert set(corpus) == {"/ai-toolkit", "/ai-toolkit/guidance/using-data-with-ai"}


def test_as_context_wraps_each_page(content_dir):
    context = as_context(load_corpus(content_dir))
    assert '<page url="/ai-toolkit" title="AI digital toolkit">' in context
    assert "</page>" in context


def rule(text: str, url: str = "/ai-toolkit/guidance/using-data-with-ai"):
    return RuleVerbatim(text=text, source=Source(title="t", url=url))


def test_verify_keeps_a_quote_that_appears_despite_line_wrapping(content_dir):
    quoted = (
        "For personal data, the DPIA route is for a service you are building "
        "to process it, not a way to paste it into an everyday tool."
    )
    answer = Answer(status="answered", message="m", rule_verbatim=rule(quoted))
    assert verify(answer, load_corpus(content_dir)).rule_verbatim == rule(quoted)


def test_verify_drops_a_reworded_quote(content_dir):
    answer = Answer(
        status="answered",
        message="m",
        rule_verbatim=rule("Remove personal data before pasting it in."),
    )
    assert verify(answer, load_corpus(content_dir)).rule_verbatim is None


def test_verify_drops_a_quote_from_an_unknown_page(content_dir):
    answer = Answer(status="answered", message="m", rule_verbatim=rule("Home", "/nope"))
    assert verify(answer, load_corpus(content_dir)).rule_verbatim is None


def test_verify_drops_sources_outside_the_corpus(content_dir):
    answer = Answer(
        status="answered",
        message="m",
        sources=[
            Source(title="a", url="/ai-toolkit"),
            Source(title="b", url="/other"),
            Source(title="c", url="https://example.com"),
        ],
    )
    assert verify(answer, load_corpus(content_dir)).sources == [
        Source(title="a", url="/ai-toolkit")
    ]
