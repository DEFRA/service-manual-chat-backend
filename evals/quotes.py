"""Checking a quoted rule the way docs/golden-set.md defines it.

"A quote passes if the words and their order match the source. Differences in
spacing, line breaks and surrounding punctuation are fine. A quote fails if
any word is changed, added or removed, or if a condition is dropped."

This is looser than the backend's `verify()` about markup (a Markdown link or
an HTML tag inside the sentence) and stricter about selective quoting.
"""

import re

WORD = r"[a-z0-9]+(?:['-][a-z0-9]+)*"
# Heading marks and list markers at the start of a line, as the backend's
# quote_check strips them: a numbered list's "1." is not a word on the page.
BLOCK_MARKER = re.compile(r"^ *(?:#{1,6}|[-*+]|\d+[.)]) +", re.MULTILINE)
# Table cells keep a mark at each end once the tags are gone, so a quote that
# reads across a row, or from a cell into the text around the table, can be
# told from one that sits inside a cell. Private-use characters: never on a
# page, and not word characters, so they sit between words like any space.
CELL_OPEN = re.compile(r"<\s*t[dh]\b[^<>]*>", re.IGNORECASE)
CELL_CLOSE = re.compile(r"<\s*/\s*t[dh]\s*>", re.IGNORECASE)
CELL_MARKS = "\ue000\ue001"
TIDY = str.maketrans(
    {"‑": "-", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', " ": " "}
)


def plain(body: str) -> str:
    """The page as a reader sees it: no link targets, tags or emphasis marks. Line breaks kept."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    text = CELL_OPEN.sub("\ue000", text)
    text = CELL_CLOSE.sub("\ue001", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\*\*|__|`", "", text)
    text = BLOCK_MARKER.sub("", text)
    return text.translate(TIDY)


def locate(quote: str, page_body: str) -> tuple[int, int] | None:
    """Where the quote's words appear, in order, in the plain page. None if they do not."""
    words = re.findall(WORD, BLOCK_MARKER.sub("", quote).translate(TIDY).lower())
    if not words:
        return None
    pattern = (
        r"(?<![a-z0-9])" + r"[^a-z0-9]+".join(map(re.escape, words)) + r"(?![a-z0-9])"
    )
    match = re.search(pattern, plain(page_body).lower())
    return match.span() if match else None


def whole_sentences(page_body: str, span: tuple[int, int]) -> bool:
    """False when the quote starts or stops part way through a sentence.

    That is the "condition dropped" failure: every word is from the page, but
    the half that was cut changes what the rule permits.
    """
    text = plain(page_body)
    before = text[: span[0]].rstrip(" \t\"'(*-#>")
    starts_clean = before == "" or before[-1] in ".!?:\n" + CELL_MARKS
    after = text[span[1] :]
    # A colon that closes the line introduces a list; the sentence itself is whole.
    # A cell's edge ends its sentence as a line break would.
    ends_clean = (
        re.match(r"[\"')]*[.!?]|[\"')]*:?[ \t]*(\n|$|[" + CELL_MARKS + "])", after)
        is not None
    )
    return starts_clean and ends_clean


def stitched(page_body: str, span: tuple[int, int]) -> bool:
    """True when the quote reads across a table: from one cell into another, or
    from a cell into the text around the table. Every word is on the page, but
    the page never says them as one line."""
    inside = plain(page_body)[span[0] : span[1]]
    return any(mark in inside for mark in CELL_MARKS)
