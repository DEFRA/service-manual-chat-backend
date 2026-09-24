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


def test_plain_text_removes_link_targets_and_tags():
    text = plain_text(
        'See the [tools radar](/ai-toolkit/tools) and <a href="/x">this</a>.'
    )
    assert " ".join(text.split()) == "See the tools radar and this ."


def test_words_treat_emphasis_marks_as_punctuation_but_keep_an_inner_underscore():
    got = [
        (w.text, w.starts_sentence, w.ends_sentence)
        for w in words("**Using.** _Also_ my_variable")
    ]
    assert got == [
        ("using", True, True),
        ("also", True, False),
        ("my_variable", False, True),
    ]


def test_plain_text_removes_a_link_target_in_angle_brackets_parentheses_and_all():
    text = plain_text(
        "See [Travelling securely](<https://intranet.example/Travel(1).aspx>) first."
    )
    assert text == "See Travelling securely first."


def test_words_give_stray_punctuation_from_a_stripped_tag_to_the_word_before():
    got = [
        (w.text, w.starts_sentence, w.ends_sentence)
        for w in words('Read <a href="/x">this</a>. Then that')
    ]
    assert got == [
        ("read", True, False),
        ("this", False, True),
        ("then", True, False),
        ("that", False, True),
    ]


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


def test_words_number_each_table_cell_and_leave_the_text_around_it_unnumbered():
    page = "Before.\n\n<table><tr><th>A b</th><td>C</td></tr></table>\n\nAfter."
    assert [(w.text, w.cell) for w in words(page)] == [
        ("before", None),
        ("a", 1),
        ("b", 1),
        ("c", 2),
        ("after", None),
    ]
