from pathlib import Path

import pytest

from app.ask import corpus as corpus_module
from app.ask import schemas

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
    page = corpus_module.parse_page("/x", PAGE)
    assert page.title == "Using data with AI"
    assert page.body.startswith("## What the conditions mean")
    assert "caption" not in page.body


def test_parse_page_without_frontmatter_uses_url_as_title() -> None:
    page = corpus_module.parse_page("/x", "Just words")
    assert page.title == "/x"
    assert page.body == "Just words"


def test_load_corpus_keys_pages_by_url_and_ignores_other_content(
    content_dir: Path,
) -> None:
    corpus = corpus_module.load_corpus(content_dir)
    assert set(corpus) == {"/ai-toolkit", "/ai-toolkit/guidance/using-data-with-ai"}


def test_as_context_wraps_each_page(content_dir: Path) -> None:
    context = corpus_module.as_context(corpus_module.load_corpus(content_dir))
    assert '<page url="/ai-toolkit" title="AI digital toolkit">' in context
    assert "</page>" in context


def test_as_context_strips_inline_tags_but_keeps_blocks(content_dir: Path) -> None:
    (content_dir / "ai-toolkit" / "guidance" / "incident.md").write_text(
        "---\ntitle: Report an AI incident\n---\n"
        "<ul>\n<li><strong>Stop.</strong> The <em>rest</em>.</li>\n</ul>\n"
    )
    context = corpus_module.as_context(corpus_module.load_corpus(content_dir))
    assert "<ul>\n<li>Stop. The rest.</li>\n</ul>" in context
    assert "<strong>" not in context


def rule(
    text: str, url: str = "/ai-toolkit/guidance/using-data-with-ai"
) -> schemas.RuleVerbatim:
    return schemas.RuleVerbatim(text=text, source=schemas.Source(title="t", url=url))


def test_verify_keeps_a_quote_that_appears_despite_line_wrapping(
    content_dir: Path,
) -> None:
    quoted = (
        "For personal data, the DPIA route is for a service you are building "
        "to process it, not a way to paste it into an everyday tool."
    )
    answer = schemas.Answer(status="answered", message="m", rule_verbatim=rule(quoted))
    assert corpus_module.verify(
        answer, corpus_module.load_corpus(content_dir)
    ).rule_verbatim == rule(quoted)


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
@pytest.mark.parametrize("has_other_source", [False, True])
def test_verify_adds_the_verified_quotes_page_with_its_own_title[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
    has_other_source: bool,
) -> None:
    corpus = corpus_module.load_corpus(content_dir)
    quoted = rule(" ".join(PAGE.split("\n\n")[-1].split()))
    sources: list[schemas.Source] = (
        [corpus_module.source_for(corpus["/ai-toolkit"])] if has_other_source else []
    )
    answer = answer_type(
        status="answered", message="m", rule_verbatim=quoted, sources=sources
    )

    verified = corpus_module.verify(answer, corpus)

    assert type(verified) is answer_type
    assert verified.rule_verbatim == quoted
    assert verified.sources == [
        *sources,
        schemas.Source(title="Using data with AI", url=quoted.source.url),
    ]
    assert answer.sources == sources
    assert corpus_module.verify(verified, corpus) == verified


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
def test_verify_does_not_duplicate_the_quotes_page[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
) -> None:
    quoted = rule(" ".join(PAGE.split("\n\n")[-1].split()))
    source = schemas.Source(
        title="Already listed", url=quoted.source.url, section="Rule"
    )
    answer = answer_type(
        status="answered", message="m", rule_verbatim=quoted, sources=[source]
    )

    verified = corpus_module.verify(answer, corpus_module.load_corpus(content_dir))

    assert verified.sources == [source]
    assert verified.rule_verbatim == quoted


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
@pytest.mark.parametrize(
    "quoted",
    [
        rule("Remove personal data before pasting it in."),
        rule("The DPIA route is for a service you are building"),
        rule("Home", "/nope"),
    ],
)
@pytest.mark.parametrize("has_existing_source", [False, True])
def test_verify_rejected_quotes_add_no_source[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
    quoted: schemas.RuleVerbatim,
    has_existing_source: bool,
) -> None:
    existing_url = quoted.source.url if quoted.source.url != "/nope" else "/ai-toolkit"
    sources = (
        [schemas.Source(title="Existing", url=existing_url)]
        if has_existing_source
        else []
    )
    answer = answer_type(
        status="answered", message="m", rule_verbatim=quoted, sources=sources
    )

    verified = corpus_module.verify(answer, corpus_module.load_corpus(content_dir))

    assert verified.rule_verbatim is None
    assert verified.sources == sources


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
def test_verify_deduplicates_sources_by_url_preserving_first_entry_and_order[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
) -> None:
    first = schemas.Source(title="First", url="/ai-toolkit")
    second = schemas.Source(title="Data", url="/ai-toolkit/guidance/using-data-with-ai")
    answer = answer_type(
        status="answered",
        message="m",
        sources=[
            first,
            second,
            schemas.Source(title="Different title", url=first.url, section="Section"),
        ],
    )

    verified = corpus_module.verify(answer, corpus_module.load_corpus(content_dir))

    assert verified.sources == [first, second]


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
def test_verify_repairs_an_invalid_source_url_using_a_unique_exact_title[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
    caplog: pytest.LogCaptureFixture,
) -> None:
    corpus = corpus_module.load_corpus(content_dir)
    source = schemas.Source(
        title="Using data with AI",
        url="/ai-toolkit/guidance/using data with ai?private=secret",
        section="Unverified section",
    )
    answer = answer_type(status="answered", message="m", sources=[source])

    with caplog.at_level("INFO", logger=corpus_module.__name__):
        verified = corpus_module.verify(answer, corpus)

    assert verified.sources == [
        schemas.Source(
            title="Using data with AI", url="/ai-toolkit/guidance/using-data-with-ai"
        )
    ]
    assert answer.sources == [source]
    assert corpus_module.verify(verified, corpus) == verified
    assert "Repaired a source" in caplog.text
    assert "secret" not in caplog.text
    assert "Unverified section" not in caplog.text


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
@pytest.mark.parametrize(
    "title",
    ["Unknown private title", "using data with ai", "Using data with AI ", ""],
)
def test_verify_drops_invalid_urls_without_an_exact_title_match[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
    title: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    answer = answer_type(
        status="answered",
        message="m",
        sources=[schemas.Source(title=title, url="/private-input")],
    )

    verified = corpus_module.verify(answer, corpus_module.load_corpus(content_dir))

    assert verified.sources == []
    assert "outcome=no_title_match" in caplog.text
    assert "private" not in caplog.text


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
def test_verify_drops_invalid_urls_with_ambiguous_titles_but_keeps_valid_urls[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
    caplog: pytest.LogCaptureFixture,
) -> None:
    corpus = corpus_module.load_corpus(content_dir)
    original = corpus["/ai-toolkit/guidance/using-data-with-ai"]
    duplicate = corpus_module.Page(
        "/ai-toolkit/duplicate", original.title, original.body
    )
    corpus[duplicate.url] = duplicate
    valid = schemas.Source(title="Model title", url=original.url, section="Existing")
    answer = answer_type(
        status="answered",
        message="m",
        sources=[
            schemas.Source(title=original.title, url="/invalid-private-input"),
            valid,
        ],
    )

    verified = corpus_module.verify(answer, corpus)

    assert verified.sources == [valid]
    assert "outcome=ambiguous_title" in caplog.text
    assert "private" not in caplog.text


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
@pytest.mark.parametrize("repair_first", [False, True])
def test_verify_deduplicates_after_url_repair[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
    repair_first: bool,
) -> None:
    corpus = corpus_module.load_corpus(content_dir)
    page = corpus["/ai-toolkit/guidance/using-data-with-ai"]
    valid = schemas.Source(title="Existing", url=page.url, section="Section")
    invalid = schemas.Source(title=page.title, url="/invalid")
    other = schemas.Source(title="Toolkit", url="/ai-toolkit")
    sources = (
        [invalid, other, valid, invalid]
        if repair_first
        else [valid, other, invalid, invalid]
    )
    answer = answer_type(status="answered", message="m", sources=sources)

    verified = corpus_module.verify(answer, corpus)

    expected = corpus_module.source_for(page) if repair_first else valid
    assert verified.sources == [expected, other]


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
def test_verify_keeps_a_valid_url_even_when_its_title_names_a_different_page[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
) -> None:
    source = schemas.Source(
        title="Using data with AI", url="/ai-toolkit", section="Existing"
    )
    answer = answer_type(status="answered", message="m", sources=[source])

    verified = corpus_module.verify(answer, corpus_module.load_corpus(content_dir))

    assert verified.sources == [source]


@pytest.mark.parametrize("answer_type", [schemas.Answer, schemas.ModelAnswer])
@pytest.mark.parametrize("has_listed_source", [False, True])
def test_source_url_repair_does_not_repair_a_quoted_rules_citation[
    AnswerT: (schemas.Answer, schemas.ModelAnswer)
](
    content_dir: Path,
    answer_type: type[AnswerT],
    caplog: pytest.LogCaptureFixture,
    has_listed_source: bool,
) -> None:
    source = schemas.Source(title="Using data with AI", url="/invalid")
    quote = schemas.RuleVerbatim(
        text=" ".join(PAGE.split("\n\n")[-1].split()), source=source
    )
    answer = answer_type(
        status="answered",
        message="m",
        sources=[source] if has_listed_source else [],
        rule_verbatim=quote,
    )

    verified = corpus_module.verify(answer, corpus_module.load_corpus(content_dir))

    expected = (
        [
            schemas.Source(
                title="Using data with AI",
                url="/ai-toolkit/guidance/using-data-with-ai",
            )
        ]
        if has_listed_source
        else []
    )
    assert verified.sources == expected
    assert verified.rule_verbatim is None
    assert answer.rule_verbatim == quote
    assert "outcome=no_page" in caplog.text


def test_verify_drops_a_reworded_quote(
    content_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    answer = schemas.Answer(
        status="answered",
        message="m",
        rule_verbatim=rule("Remove personal data before pasting it in."),
    )
    assert (
        corpus_module.verify(
            answer, corpus_module.load_corpus(content_dir)
        ).rule_verbatim
        is None
    )
    assert "outcome=not_found" in caplog.text
    assert "personal data" not in caplog.text


def test_verify_drops_a_quote_that_stops_part_way_through_a_sentence(
    content_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    answer = schemas.Answer(
        status="answered",
        message="m",
        rule_verbatim=rule("The DPIA route is for a service you are building"),
    )
    assert (
        corpus_module.verify(
            answer, corpus_module.load_corpus(content_dir)
        ).rule_verbatim
        is None
    )
    assert "outcome=partial" in caplog.text
    assert "DPIA" not in caplog.text


def test_verify_drops_a_quote_from_an_unknown_page(content_dir: Path) -> None:
    answer = schemas.Answer(
        status="answered", message="m", rule_verbatim=rule("Home", "/nope")
    )
    assert (
        corpus_module.verify(
            answer, corpus_module.load_corpus(content_dir)
        ).rule_verbatim
        is None
    )


def test_verify_drops_sources_outside_the_corpus(content_dir: Path) -> None:
    answer = schemas.Answer(
        status="answered",
        message="m",
        sources=[
            schemas.Source(title="a", url="/ai-toolkit"),
            schemas.Source(title="b", url="/other"),
            schemas.Source(title="c", url="https://example.com"),
        ],
    )
    assert corpus_module.verify(
        answer, corpus_module.load_corpus(content_dir)
    ).sources == [schemas.Source(title="a", url="/ai-toolkit")]


LONG = " ".join(["The answer comes first and it runs to ten words here."] * 10)


def test_verify_lays_out_a_long_message_and_leaves_the_quote_alone(
    content_dir: Path,
) -> None:
    quoted = " ".join(PAGE.split("\n\n")[-1].split())
    answer = schemas.Answer(status="answered", message=LONG, rule_verbatim=rule(quoted))
    verified = corpus_module.verify(answer, corpus_module.load_corpus(content_dir))
    assert "\n\n" in verified.message
    assert verified.message.split() == LONG.split()
    assert verified.rule_verbatim == rule(quoted)


def test_verify_leaves_a_blocked_message_alone(content_dir: Path) -> None:
    answer = schemas.Answer(status="blocked", message=LONG)
    assert (
        corpus_module.verify(answer, corpus_module.load_corpus(content_dir)).message
        == LONG
    )


def test_content_ref_is_none_for_a_mount(content_dir: Path) -> None:
    assert corpus_module.content_ref(content_dir) is None


def test_content_ref_reads_the_baked_in_ref(content_dir: Path) -> None:
    (content_dir / "REF").write_text("caefc03\n")
    assert corpus_module.content_ref(content_dir) == "caefc03"


def test_verify_ends_numbered_steps_on_the_page_s_last_step() -> None:
    page = corpus_module.parse_page(
        "/ai-toolkit/guidance/report-an-ai-incident",
        "<ol>\n<li>Stop using the AI tool immediately.</li>\n"
        "<li>Do not delete or change anything.</li>\n"
        "<li>Report it through your organisation's security incident process.</li>\n"
        "</ol>\n",
    )
    answer = schemas.Answer(
        status="answered",
        message=(
            "Follow these steps. 1. Stop using the AI tool immediately. 2. Do not "
            "delete or change anything. 3. Report it through your organisation's "
            "security incident process. A personal data breach has a deadline."
        ),
    )

    message = corpus_module.verify(answer, {page.url: page}).message

    assert message.endswith(
        "security incident process.\n\nA personal data breach has a deadline."
    )
    assert message.split() == answer.message.split()
