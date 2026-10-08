"""The writing counts: messages that break a GOV.UK style rule the prompt sets.

Not bars. The golden set does not test tone, so these sit beside the bars
and are compared between steps of a prompt story. Each is a count of
messages across all passes, as CAIT-287 reported them.
"""

import re
import statistics
import typing

# A dash used as punctuation: an en or em dash anywhere, or a hyphen with a
# space on either side. A hyphen inside a word ("follow-up") is not counted.
DASH = re.compile(r"[–—]|\s-\s|\s-$|^-\s")
ATTRIBUTION = re.compile(r"the toolkit says|the guidance", re.IGNORECASE)
ABBREVIATIONS = ("DPIA", "MCP", "ATRS", "ALB")


def unspelt(message: str) -> bool:
    """Uses an abbreviation with no "(ABBR)" after its name anywhere in the message."""
    for abbreviation in ABBREVIATIONS:
        used = re.search(rf"\b{abbreviation}s?\b", message)
        if used and f"({abbreviation}" not in message:
            return True
    return False


def opens_with_abbreviation(message: str) -> bool:
    first = re.match(r"\W*(\w+)", message)
    return first is not None and first.group(1).rstrip("s") in ABBREVIATIONS


def counts(answers: list[dict[str, typing.Any]]) -> dict[str, typing.Any]:
    messages = [r["answer"]["message"] for r in answers if r["ok"]]
    words = [len(m.split()) for m in messages]
    return {
        "messages": len(messages),
        "dashes used as punctuation": sum(bool(DASH.search(m)) for m in messages),
        '"the toolkit says" or "the guidance"': sum(
            bool(ATTRIBUTION.search(m)) for m in messages
        ),
        "paragraph breaks": sum("\n" in m.strip() for m in messages),
        "abbreviations not spelt out": sum(unspelt(m) for m in messages),
        "opening with an abbreviation": sum(
            opens_with_abbreviation(m) for m in messages
        ),
        "median words": statistics.median(words) if words else 0,
        "longest words": max(words, default=0),
    }
