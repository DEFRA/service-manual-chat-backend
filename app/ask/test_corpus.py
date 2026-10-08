from pathlib import Path

import pytest

from app.ask.corpus import as_context, content_ref, load_corpus, parse_page, verify
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


def test_parse_page_splits_frontmatter_and_body() -> None:
    page = parse_page("/x", PAGE)
    assert page.title == "Using data with AI"
    assert page.body.startswith("## What the conditions mean")
    assert "caption" not in page.body


def test_parse_page_without_frontmatter_uses_url_as_title() -> None:
    page = parse_page("/x", "Just words")
    assert page.title == "/x"
    assert page.body == "Just words"


def test_load_corpus_keys_pages_by_url_and_ignores_other_content(
    content_dir: Path,
) -> None:
    corpus = load_corpus(content_dir)
    assert set(corpus) == {"/ai-toolkit", "/ai-toolkit/guidance/using-data-with-ai"}


def test_as_context_wraps_each_page(content_dir: Path) -> None:
    context = as_context(load_corpus(content_dir))
    assert '<page url="/ai-toolkit" title="AI digital toolkit">' in context
    assert "</page>" in context


def test_as_context_strips_inline_tags_but_keeps_blocks(content_dir: Path) -> None:
    (content_dir / "ai-toolkit" / "guidance" / "incident.md").write_text(
        "---\ntitle: Report an AI incident\n---\n"
        "<ul>\n<li><strong>Stop.</strong> The <em>rest</em>.</li>\n</ul>\n"
    )
    context = as_context(load_corpus(content_dir))
    assert "<ul>\n<li>Stop. The rest.</li>\n</ul>" in context
    assert "<strong>" not in context


def rule(
    text: str, url: str = "/ai-toolkit/guidance/using-data-with-ai"
) -> RuleVerbatim:
    return RuleVerbatim(text=text, source=Source(title="t", url=url))


def test_verify_keeps_a_quote_that_appears_despite_line_wrapping(
    content_dir: Path,
) -> None:
    quoted = (
        "For personal data, the DPIA route is for a service you are building "
        "to process it, not a way to paste it into an everyday tool."
    )
    answer = Answer(status="answered", message="m", rule_verbatim=rule(quoted))
    assert verify(answer, load_corpus(content_dir)).rule_verbatim == rule(quoted)


def test_verify_drops_a_reworded_quote(
    content_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    answer = Answer(
        status="answered",
        message="m",
        rule_verbatim=rule("Remove personal data before pasting it in."),
    )
    assert verify(answer, load_corpus(content_dir)).rule_verbatim is None
    assert "outcome=not_found" in caplog.text
    assert "personal data" not in caplog.text


def test_verify_drops_a_quote_that_stops_part_way_through_a_sentence(
    content_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    answer = Answer(
        status="answered",
        message="m",
        rule_verbatim=rule("The DPIA route is for a service you are building"),
    )
    assert verify(answer, load_corpus(content_dir)).rule_verbatim is None
    assert "outcome=partial" in caplog.text
    assert "DPIA" not in caplog.text


def test_verify_drops_a_quote_from_an_unknown_page(content_dir: Path) -> None:
    answer = Answer(status="answered", message="m", rule_verbatim=rule("Home", "/nope"))
    assert verify(answer, load_corpus(content_dir)).rule_verbatim is None


def test_verify_drops_sources_outside_the_corpus(content_dir: Path) -> None:
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


LONG = " ".join(["The answer comes first and it runs to ten words here."] * 10)


def test_verify_lays_out_a_long_message_and_leaves_the_quote_alone(
    content_dir: Path,
) -> None:
    quoted = " ".join(PAGE.split("\n\n")[-1].split())
    answer = Answer(status="answered", message=LONG, rule_verbatim=rule(quoted))
    verified = verify(answer, load_corpus(content_dir))
    assert "\n\n" in verified.message
    assert verified.message.split() == LONG.split()
    assert verified.rule_verbatim == rule(quoted)


def test_verify_leaves_a_blocked_message_alone(content_dir: Path) -> None:
    answer = Answer(status="blocked", message=LONG)
    assert verify(answer, load_corpus(content_dir)).message == LONG


def test_content_ref_is_none_for_a_mount(content_dir: Path) -> None:
    assert content_ref(content_dir) is None


def test_content_ref_reads_the_baked_in_ref(content_dir: Path) -> None:
    (content_dir / "REF").write_text("caefc03\n")
    assert content_ref(content_dir) == "caefc03"


def test_verify_ends_numbered_steps_on_the_page_s_last_step() -> None:
    page = parse_page(
        "/ai-toolkit/guidance/report-an-ai-incident",
        "<ol>\n<li>Stop using the AI tool immediately.</li>\n"
        "<li>Do not delete or change anything.</li>\n"
        "<li>Report it through your organisation's security incident process.</li>\n"
        "</ol>\n",
    )
    answer = Answer(
        status="answered",
        message=(
            "Follow these steps. 1. Stop using the AI tool immediately. 2. Do not "
            "delete or change anything. 3. Report it through your organisation's "
            "security incident process. A personal data breach has a deadline."
        ),
    )

    message = verify(answer, {page.url: page}).message

    assert message.endswith(
        "security incident process.\n\nA personal data breach has a deadline."
    )
    assert message.split() == answer.message.split()
