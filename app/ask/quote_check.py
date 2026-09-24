"""Does a quoted rule appear, word for word, on the page it cites?

The golden set defines an exact quote: the words and their order match the
source, and differences in spacing, line breaks and surrounding punctuation
do not count. A quote fails if a word is changed, added or removed, or if a
condition is dropped. The third failure is the one that matters, so it is
reported separately: a service that quotes accurately but selectively is more
dangerous than one that paraphrases openly.

The comparison is made against the page as a reader sees it. Many rules are
written inside markup, `<li><strong>The rule.</strong> The explanation.</li>`,
or hold a Markdown link, and a word-for-word quote of either does not appear
in the raw source. Tags and link targets are removed first, and emphasis
marks count as punctuation.

service-manual-ui has the same check in `src/server/ai-ask/quote-check.js`,
and both are run against the one list of cases in `quote_check_cases.json`.
Change all three together.
"""

import re
from dataclasses import dataclass
from typing import Literal

Outcome = Literal["ok", "not_found", "partial", "stitched", "empty"]

# Tags that sit inside a sentence. Every other tag ends a block, and a block
# boundary is a sentence boundary: a list item that is a fragment with no full
# stop is still a whole thing to quote.
INLINE_TAGS = frozenset(
    {
        "a",
        "abbr",
        "b",
        "br",
        "code",
        "em",
        "i",
        "kbd",
        "mark",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
    }
)

# After the tag name comes either `>` or a space or slash and then whatever,
# so the name and the rest never overlap and the scan is linear.
TAG = re.compile(r"<\s*/?([a-zA-Z][a-zA-Z0-9]*)(?:[\s/][^<>]*)?>")
# A link target is either wrapped in angle brackets, which is how Markdown
# writes a URL holding parentheses, or runs to the first closing one.
IMAGE = re.compile(r"!\[([^\[\]]*)\]\((?:<[^<>]*>|[^()<>]*)\)")
LINK = re.compile(r"\[([^\[\]]*)\]\((?:<[^<>]*>|[^()<>]*)\)")
# Heading marks, list markers and block quotes at the start of a line.
BLOCK_MARKER = re.compile(r"^ *(?:#{1,6}|[-*+]|\d+[.)]) +", re.MULTILINE)
BLOCK_QUOTE = re.compile(r"^ *> *", re.MULTILINE)
BLANK_LINE = re.compile(r"\n[ \t]*\n")
# A table cell's opening tag. Each cell becomes its own block, marked so a
# quote cannot be stitched together out of cells: a row read across is not a
# sentence, however whole each cell is.
CELL_OPEN = re.compile(r"<\s*t[dh]\b[^<>]*>", re.IGNORECASE)
CELL_MARK = "\ue000"  # private use: never on a page, dropped before matching
# Punctuation, brackets and emphasis marks at either end of a token are not
# part of the word. "(ATRS)." and "ATRS" are the same word, "**Using.**" is
# "Using", and a bare "-" is no word at all.
# What can follow a full stop and still be the same sentence end: closing
# quotes and brackets, and Markdown emphasis marks.
CLOSERS = "\"')]*_"
SENTENCE_END = ".!?:"

ENTITIES = {
    "&amp;": "&",
    "&nbsp;": " ",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
}
TYPOGRAPHY = str.maketrans(
    {
        "\u2018": "'",  # left single quotation mark
        "\u2019": "'",  # right single quotation mark
        "\u201c": '"',  # left double quotation mark
        "\u201d": '"',  # right double quotation mark
        "\u2010": "-",  # hyphen
        "\u2011": "-",  # non-breaking hyphen
        "\u2012": "-",  # figure dash
        "\u00a0": " ",  # no-break space
    }
)


def _tag_to_text(match: re.Match[str]) -> str:
    return " " if match.group(1).lower() in INLINE_TAGS else "\n\n"


def strip_inline_tags(markdown: str) -> str:
    """The page with `<strong>`, `<a>` and the like removed, blocks intact.

    This is what the model is given, so it is never asked to quote through
    markup it cannot see the point of.
    """
    return TAG.sub(
        lambda m: "" if m.group(1).lower() in INLINE_TAGS else m.group(0), markdown
    )


def plain_text(markdown: str) -> str:
    """The page as a reader sees it, with a blank line between blocks."""
    text = BLOCK_MARKER.sub("\n\n", markdown)
    text = BLOCK_QUOTE.sub("\n\n", text)
    text = TAG.sub(_tag_to_text, text)
    text = IMAGE.sub(r"\1", text)
    text = LINK.sub(r"\1", text)
    for entity, char in ENTITIES.items():
        text = text.replace(entity, char)
    return text.translate(TYPOGRAPHY)


@dataclass(frozen=True)
class Word:
    text: str
    starts_sentence: bool
    ends_sentence: bool
    cell: int | None


def _strip_punctuation(token: str) -> str:
    start, end = 0, len(token)
    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1
    return token[start:end]


def _ends_sentence(token: str) -> bool:
    return token.rstrip(CLOSERS).endswith(tuple(SENTENCE_END))


def words(markdown: str) -> list[Word]:
    """The page's words in order, each knowing whether a sentence starts or ends
    on it and which table cell, if any, it sits in."""
    result: list[Word] = []
    marked = CELL_OPEN.sub(lambda m: m.group(0) + CELL_MARK, markdown)
    cells = 0
    for block in BLANK_LINE.split(plain_text(marked)):
        cell = None
        if CELL_MARK in block:
            cells += 1
            cell = cells
            block = block.replace(CELL_MARK, " ")
        tokens = block.split()
        kept: list[tuple[str, str]] = []
        for token in tokens:
            word = _strip_punctuation(token).lower()
            if word:
                kept.append((word, token))
            elif kept:
                # Punctuation on its own, as in `<a href="/x">this</a>.` once
                # the tag is gone, belongs to the word before it: that is where
                # the sentence ends.
                previous_word, previous_token = kept[-1]
                kept[-1] = (previous_word, previous_token + token)
        for i, (word, token) in enumerate(kept):
            first = i == 0
            last = i == len(kept) - 1
            starts = first or _ends_sentence(kept[i - 1][1])
            result.append(Word(word, starts, last or _ends_sentence(token), cell))
    return result


def check_quote(quote: str, page_markdown: str) -> Outcome:
    """Whether the quote is on the page, word for word and whole.

    `ok`: the words appear in order and run from the start of a sentence to
    the end of one. `stitched`: the words appear in order but the match takes
    in a table cell and something outside it, another cell or the text
    around the table, so they were never one sentence. A quote may still run
    across whole list items: the four incident steps are one quote.
    `partial`: the words appear but the quote starts or stops part way
    through a sentence, so a condition may have been dropped.
    `not_found`: a word was changed, added or removed. `empty`: nothing left
    to check once markup and whitespace are gone, which would otherwise match
    every page.
    """
    wanted = [word.text for word in words(quote)]
    if not wanted:
        return "empty"
    page = words(page_markdown)
    n = len(wanted)
    outcome: Outcome = "not_found"
    for start in range(len(page) - n + 1):
        if [word.text for word in page[start : start + n]] != wanted:
            continue
        matched = page[start : start + n]
        cells = {word.cell for word in matched}
        if len(cells) > 1:
            outcome = "stitched"
        elif matched[0].starts_sentence and matched[-1].ends_sentence:
            return "ok"
        elif outcome == "not_found":
            outcome = "partial"
    return outcome
