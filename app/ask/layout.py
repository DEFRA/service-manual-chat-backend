"""Put a long answer on separate lines without changing a word of it.

The model writes a long answer as one paragraph. Asking it for line breaks in
the prompt works, but the answers get longer and reach for a second page
(CAIT-301). So the prompt is left alone and the breaks are added here, after
the model has answered. Only whitespace changes: a space between two
sentences becomes a line break or a blank line.

The front end shows a line break as a line break (`white-space: pre-wrap`).
"""

import re

# Chris's rule for usability round 2: only an answer over this is laid out.
# Three or more numbered steps are the exception (CAIT-302): people follow
# them in order, so each has its own line however short the answer is.
LONG_ANSWER_WORDS = 90

# A paragraph never starts on one of these: the sentence points back at the one
# before it, so the two stay together.
POINTS_BACK = ("This", "That", "It", "These")
# A paragraph starts on one of these wherever it can: the answer turns here.
TURNS = ("However", "If", "Check", "For example")
STEPS = (
    "First",
    "Second",
    "Third",
    "Fourth",
    "Fifth",
    "Sixth",
    "Next",
    "Then",
    "After that",
    "Finally",
    "Lastly",
)
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.")

_SENTENCE_GAP = re.compile(
    r"(?<=[.?!])\s+(?=[A-Z\"'(])|(?<=[.?!][\"')])\s+(?=[A-Z\"'(])"
)
_NUMBER = re.compile(r"(?:^|\s+)(\d{1,2})[.)]\s+(?=[A-Z])")
_BARE_NUMBER = re.compile(r"(?:^|\s)\d{1,2}\.$")
_LIST_ITEMS = 3


def _starts_with(sentence: str, openers: tuple[str, ...]) -> bool:
    return any(re.match(rf"{re.escape(opener)}\b", sentence) for opener in openers)


def sentences(message: str) -> list[str]:
    """The message's sentences in order, joined by single spaces in the original."""
    found: list[str] = []
    held = ""
    for piece in _SENTENCE_GAP.split(message):
        piece = held + piece
        # "e.g. Copilot" and "step 2. Then" are not the end of a sentence.
        if piece.endswith(ABBREVIATIONS) or _BARE_NUMBER.search(piece):
            held = piece + " "
            continue
        found.append(piece)
        held = ""
    if held:
        found.append(held.rstrip())
    return found


def _numbered(message: str, fewest: int) -> list[str] | None:
    """The message cut before each of "1.", "2.", "3." if it counts up from 1."""
    marks = list(_NUMBER.finditer(message))
    if len(marks) < fewest or [int(m.group(1)) for m in marks] != list(
        range(1, len(marks) + 1)
    ):
        return None
    starts = [m.start(1) for m in marks]
    lead = [message[: starts[0]].rstrip()] if starts[0] else []
    return lead + [
        message[start:end].rstrip()
        for start, end in zip(starts, [*starts[1:], len(message)], strict=True)
    ]


def _is_list(sentence: str) -> bool:
    """A colon, then three or more items with semicolons between them."""
    _, colon, items = sentence.partition(": ")
    return bool(colon) and items.count("; ") >= _LIST_ITEMS - 1


def _list_lines(sentence: str) -> list[str]:
    head, _, items = sentence.partition(": ")
    *rest, last = items.split("; ")
    return [head + ":", *(item + ";" for item in rest), last]


def _paragraphs(parts: list[str]) -> list[str]:
    """The first sentence on its own, because the answer is in it, then pairs."""
    groups = [[parts[0]]]
    for sentence in parts[1:]:
        current = groups[-1]
        full = len(current) >= 2 or len(groups) == 1
        if _starts_with(sentence, POINTS_BACK):
            current.append(sentence)
        elif full or _starts_with(sentence, TURNS):
            groups.append([sentence])
        else:
            current.append(sentence)
    # One sentence left on its own at the end joins the paragraph before it,
    # unless it is a turn, which is worth its own line.
    if len(groups) > 2 and len(groups[-1]) == 1:
        (last,) = groups[-1]
        if not _starts_with(last, TURNS):
            groups.pop()
            groups[-1].append(last)
    return [" ".join(group) for group in groups]


def lay_out(message: str) -> str:
    """The same words, with steps and list items on their own lines and
    anything else in short paragraphs."""
    if "\n" in message:
        return message

    is_long = len(message.split()) > LONG_ANSWER_WORDS
    numbered = _numbered(message, fewest=2 if is_long else _LIST_ITEMS)
    if numbered:
        return "\n".join(numbered)
    if not is_long:
        return message

    parts = sentences(message)
    if any(_is_list(part) for part in parts):
        return "\n".join(
            line
            for part in parts
            for line in (_list_lines(part) if _is_list(part) else [part])
        )

    if sum(_starts_with(part, STEPS) for part in parts) >= 2:
        lines = [parts[0]]
        for part in parts[1:]:
            if _starts_with(part, STEPS):
                lines.append(part)
            else:
                lines[-1] += " " + part
        return "\n".join(lines)

    if len(parts) <= 3:
        return message
    return "\n\n".join(_paragraphs(parts))
