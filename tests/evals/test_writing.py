import typing

from evals import writing


def answers(*messages: str) -> list[dict[str, typing.Any]]:
    return [{"ok": True, "answer": {"message": m}} for m in messages]


def test_a_dash_between_words_counts_and_a_hyphen_inside_a_word_does_not() -> None:
    found = writing.counts(
        answers("Stop — report it.", "Stop - report it.", "A follow-up question.")
    )
    assert found["dashes used as punctuation"] == 2


def test_attribution_is_counted_once_per_message() -> None:
    found = writing.counts(
        answers("The guidance says so. The toolkit says so.", "Report it.")
    )
    assert found['"the toolkit says" or "the guidance"'] == 1


def test_an_abbreviation_is_spelt_out_when_its_name_comes_first() -> None:
    assert writing.unspelt("You need a DPIA.")
    assert not writing.unspelt(
        "You need a data protection impact assessment (DPIA). The DPIA comes first."
    )


def test_a_plural_abbreviation_counts() -> None:
    assert writing.unspelt("Staff in ALBs can use it.")


def test_a_message_that_opens_with_an_abbreviation() -> None:
    assert writing.opens_with_abbreviation("MCP servers need approval.")
    assert not writing.opens_with_abbreviation(
        "Model Context Protocol (MCP) servers need approval."
    )


def test_failed_calls_are_not_messages() -> None:
    found = writing.counts([{"ok": False}, *answers("Yes.")])
    assert found["messages"] == 1
