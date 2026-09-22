import json
from pathlib import Path

import pytest

from app.ask.quote_check import check_quote, plain_text, strip_inline_tags, words

# Shared with service-manual-ui, which runs the same file against its own
# checker, so the two cannot drift apart without one of them failing.
CASES = json.loads(
    (Path(__file__).parent / "quote_check_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize(
    "case", CASES["cases"], ids=[case["name"] for case in CASES["cases"]]
)
def test_shared_cases(case):
    page = CASES["pages"][case["page"]]
    assert check_quote(case["quote"], page) == case["outcome"]


def test_every_shared_page_is_used():
    used = {case["page"] for case in CASES["cases"]}
    assert used == set(CASES["pages"])


def test_plain_text_removes_link_targets_tags_and_emphasis():
    text = plain_text(
        'See the [tools radar](/ai-toolkit/tools) and <a href="/x">this</a>, '
        "which is **important** and _also_ my_variable."
    )
    assert " ".join(text.split()) == (
        "See the tools radar and this , which is important and also my_variable."
    )


def test_words_mark_sentence_boundaries_across_blocks():
    page = "First one. Second\n\n<li>Third</li>\n<li>Fourth (x).</li>"
    got = [(w.text, w.starts_sentence, w.ends_sentence) for w in words(page)]
    assert got == [
        ("first", True, False),
        ("one", False, True),
        ("second", True, True),
        ("third", True, True),
        ("fourth", True, False),
        ("x", False, True),
    ]


def test_strip_inline_tags_keeps_block_tags():
    body = '<ul class="x">\n<li><strong>Stop.</strong> Now <a href="/y">go</a>.</li>\n</ul>'
    assert strip_inline_tags(body) == '<ul class="x">\n<li>Stop. Now go.</li>\n</ul>'
