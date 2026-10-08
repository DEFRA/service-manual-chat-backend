from pathlib import Path

import pytest

from app.ask import corpus, schemas

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


def rule(
    text: str, url: str = "/ai-toolkit/guidance/using-data-with-ai"
) -> schemas.RuleVerbatim:
    return schemas.RuleVerbatim(text=text, source=schemas.Source(title="t", url=url))


class TestCorpus:
    def test_parse_page_splits_frontmatter_and_body(self) -> None:
        page = corpus.parse_page("/x", PAGE)

        assert page.title == "Using data with AI"
        assert page.body.startswith("## What the conditions mean")
        assert "caption" not in page.body

    def test_parse_page_without_frontmatter_uses_url_as_title(self) -> None:
        page = corpus.parse_page("/x", "Just words")

        assert page.title == "/x"
        assert page.body == "Just words"

    def test_load_corpus_keys_pages_by_url_and_ignores_other_content(
        self, content_dir: Path
    ) -> None:
        loaded = corpus.load_corpus(content_dir)

        assert set(loaded) == {
            "/ai-toolkit",
            "/ai-toolkit/guidance/using-data-with-ai",
        }

    def test_as_context_wraps_each_page(self, content_dir: Path) -> None:
        context = corpus.as_context(corpus.load_corpus(content_dir))

        assert '<page url="/ai-toolkit" title="AI digital toolkit">' in context
        assert "</page>" in context

    def test_as_context_strips_inline_tags_but_keeps_blocks(
        self, content_dir: Path
    ) -> None:
        (content_dir / "ai-toolkit" / "guidance" / "incident.md").write_text(
            "---\ntitle: Report an AI incident\n---\n"
            "<ul>\n<li><strong>Stop.</strong> The <em>rest</em>.</li>\n</ul>\n"
        )

        context = corpus.as_context(corpus.load_corpus(content_dir))

        assert "<ul>\n<li>Stop. The rest.</li>\n</ul>" in context
        assert "<strong>" not in context

    def test_content_ref_is_none_for_a_mount(self, content_dir: Path) -> None:
        assert corpus.content_ref(content_dir) is None

    def test_content_ref_reads_the_baked_in_ref(self, content_dir: Path) -> None:
        (content_dir / "REF").write_text("caefc03\n")

        assert corpus.content_ref(content_dir) == "caefc03"


class TestVerify:
    def test_verify_keeps_a_quote_that_appears_despite_line_wrapping(
        self, content_dir: Path
    ) -> None:
        quoted = (
            "For personal data, the DPIA route is for a service you are building "
            "to process it, not a way to paste it into an everyday tool."
        )
        answer = schemas.Answer(
            status="answered", message="m", rule_verbatim=rule(quoted)
        )

        assert corpus.verify(
            answer, corpus.load_corpus(content_dir)
        ).rule_verbatim == rule(quoted)

    def test_verify_drops_a_reworded_quote(
        self, content_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        answer = schemas.Answer(
            status="answered",
            message="m",
            rule_verbatim=rule("Remove personal data before pasting it in."),
        )

        assert (
            corpus.verify(answer, corpus.load_corpus(content_dir)).rule_verbatim is None
        )
        assert "outcome=not_found" in caplog.text
        assert "personal data" not in caplog.text

    def test_verify_drops_a_quote_that_stops_part_way_through_a_sentence(
        self, content_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        answer = schemas.Answer(
            status="answered",
            message="m",
            rule_verbatim=rule("The DPIA route is for a service you are building"),
        )

        assert (
            corpus.verify(answer, corpus.load_corpus(content_dir)).rule_verbatim is None
        )
        assert "outcome=partial" in caplog.text
        assert "DPIA" not in caplog.text

    def test_verify_drops_a_quote_from_an_unknown_page(self, content_dir: Path) -> None:
        answer = schemas.Answer(
            status="answered", message="m", rule_verbatim=rule("Home", "/nope")
        )

        assert (
            corpus.verify(answer, corpus.load_corpus(content_dir)).rule_verbatim is None
        )

    def test_verify_drops_sources_outside_the_corpus(self, content_dir: Path) -> None:
        answer = schemas.Answer(
            status="answered",
            message="m",
            sources=[
                schemas.Source(title="a", url="/ai-toolkit"),
                schemas.Source(title="b", url="/other"),
                schemas.Source(title="c", url="https://example.com"),
            ],
        )

        assert corpus.verify(answer, corpus.load_corpus(content_dir)).sources == [
            schemas.Source(title="a", url="/ai-toolkit")
        ]

    def test_verify_lays_out_a_long_message_and_leaves_the_quote_alone(
        self, content_dir: Path
    ) -> None:
        long_msg = " ".join(
            ["The answer comes first and it runs to ten words here."] * 10
        )
        quoted = " ".join(PAGE.split("\n\n")[-1].split())
        answer = schemas.Answer(
            status="answered", message=long_msg, rule_verbatim=rule(quoted)
        )

        verified = corpus.verify(answer, corpus.load_corpus(content_dir))

        assert "\n\n" in verified.message
        assert verified.message.split() == long_msg.split()
        assert verified.rule_verbatim == rule(quoted)

    def test_verify_leaves_a_blocked_message_alone(self, content_dir: Path) -> None:
        long_msg = " ".join(
            ["The answer comes first and it runs to ten words here."] * 10
        )
        answer = schemas.Answer(status="blocked", message=long_msg)

        assert (
            corpus.verify(answer, corpus.load_corpus(content_dir)).message == long_msg
        )
