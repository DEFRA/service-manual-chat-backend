import pytest

from app.ask.layout import LONG_ANSWER_WORDS, lay_out, page_steps, sentences

PADDING = "Padding only makes the answer long enough to be laid out at all."


def long(message: str) -> str:
    """The message with sentences added to the end until it is over the limit."""
    while len(message.split()) <= LONG_ANSWER_WORDS:
        message += " " + PADDING
    return message


def test_a_message_of_90_words_or_fewer_is_left_alone():
    message = " ".join(["One two three four five six seven eight nine."] * 10)
    assert len(message.split()) == LONG_ANSWER_WORDS
    assert lay_out(message) == message


def test_a_message_that_already_has_a_line_break_is_left_alone():
    message = long("The first point.\nThe second point.")
    assert lay_out(message) == message


@pytest.mark.parametrize(
    "message",
    [
        long("The rules depend on the data. Public data can go into any tool."),
        long("Stop using the tool. First, tell your manager. Second, report it."),
        long("1. AI assistant. A hosted stack. 2. Agent swarms. Many agents."),
        long("Report it if you: pasted data; shared output; or left history on."),
        "Act now. 1. Stop the tool. 2. Tell your manager. 3. Report it.",
    ],
)
def test_no_word_is_changed(message):
    assert lay_out(message).split() == message.split()


def test_steps_each_start_a_line():
    message = long(
        "Remove the personal data now. First, stop using the tool. Second, do not "
        "delete anything. The people need to see what happened. "
        "Third, tell your line manager."
    )
    lines = lay_out(message).split("\n")
    assert lines[:3] == [
        "Remove the personal data now.",
        "First, stop using the tool.",
        "Second, do not delete anything. The people need to see what happened.",
    ]
    assert lines[3].startswith("Third, tell your line manager. " + PADDING)
    assert len(lines) == 4


def test_a_numbered_answer_has_each_number_on_its_own_line():
    message = long(
        "There are two. 1. AI assistant. A Defra-hosted stack. 2. Agent swarms. "
        "Several agents work together."
    )
    lines = lay_out(message).split("\n")
    assert lines[0] == "There are two."
    assert lines[1] == "1. AI assistant. A Defra-hosted stack."
    assert lines[2].startswith("2. Agent swarms. Several agents work together.")


SHORT_STEPS = (
    "Act now. 1. Stop using the tool. 2. Tell your line manager. "
    "3. Report it to the data protection team."
)


def test_three_numbered_steps_are_laid_out_however_short_the_answer():
    assert len(SHORT_STEPS.split()) <= LONG_ANSWER_WORDS
    assert lay_out(SHORT_STEPS).split("\n") == [
        "Act now.",
        "1. Stop using the tool.",
        "2. Tell your line manager.",
        "3. Report it to the data protection team.",
    ]


def test_two_numbered_steps_in_a_short_answer_stay_on_one_line():
    message = "Act now. 1. Stop using the tool. 2. Tell your line manager."
    assert lay_out(message) == message


def test_numbers_that_do_not_count_up_from_one_are_not_a_list():
    message = long("Use version 4. The older version 2. Was withdrawn last year.")
    assert "\nThe older" not in lay_out(message)
    assert "\nWas withdrawn" not in lay_out(message)


def test_a_list_with_semicolons_has_each_item_on_its_own_line():
    message = long(
        "You must report it if you did any of these: put personal data into a "
        "tool; left chat history switched on; or shared output about real "
        "people. If you are not sure, report it anyway."
    )
    assert lay_out(message).split("\n")[:5] == [
        "You must report it if you did any of these:",
        "put personal data into a tool;",
        "left chat history switched on;",
        "or shared output about real people.",
        "If you are not sure, report it anyway.",
    ]


def test_prose_is_the_first_sentence_alone_then_pairs():
    message = long("Alpha one. Bravo two. Charlie three. Delta four. Echo five.")
    assert lay_out(message).split("\n\n")[:3] == [
        "Alpha one.",
        "Bravo two. Charlie three.",
        "Delta four. Echo five.",
    ]


def test_one_sentence_is_not_left_on_its_own_at_the_end():
    sentence = " ".join(["word"] * 22) + "."
    message = " ".join([sentence.capitalize()] * 6)
    paragraphs = lay_out(message).split("\n\n")
    assert [len(sentences(p)) for p in paragraphs] == [1, 2, 3]


@pytest.mark.parametrize("opener", ["This", "That", "It", "These"])
def test_a_paragraph_never_starts_on_a_sentence_that_points_back(opener):
    message = long(
        f"Alpha one. {opener} is two. Bravo three. Charlie four. {opener} is five."
    )
    paragraphs = lay_out(message).split("\n\n")
    assert paragraphs[0] == f"Alpha one. {opener} is two."
    assert paragraphs[1].startswith(f"Bravo three. Charlie four. {opener} is five.")
    assert not any(p.startswith(("This", "That", "It ", "These")) for p in paragraphs)


@pytest.mark.parametrize("opener", ["However,", "If so,", "Check the", "For example,"])
def test_a_paragraph_starts_where_the_answer_turns(opener):
    message = long(
        f"Alpha one. Bravo two. {opener} charlie three. Delta four. Echo five. "
        "Foxtrot six."
    )
    paragraphs = lay_out(message).split("\n\n")
    assert paragraphs[:2] == ["Alpha one.", "Bravo two."]
    assert paragraphs[2].startswith(f"{opener} charlie three. Delta four.")


def test_a_word_that_only_begins_like_an_opener_does_not_count():
    message = long(
        "Alpha one. Bravo two. Charlie three. Italy is four. Echo five. Thisbe is six."
    )
    assert "\n\nItaly is four. Echo five.\n\nThisbe is six." in lay_out(message)


def test_three_long_sentences_are_left_alone():
    sentence = " ".join(["word"] * 31) + "."
    message = " ".join([sentence.capitalize()] * 3)
    assert lay_out(message) == message


def test_an_abbreviation_or_a_number_does_not_end_a_sentence():
    assert sentences("Use a tool, e.g. Copilot. See step 2. Then stop.") == [
        "Use a tool, e.g. Copilot.",
        "See step 2. Then stop.",
    ]


INCIDENT_PAGE = """Follow these steps as soon as you realise an incident has happened.

<ol class="govuk-list govuk-list--number govuk-list--spaced">
<li><strong>Stop using the AI tool immediately.</strong></li>
<li><strong>Do not delete or change anything.</strong> The people handling the incident need to see clearly what happened.</li>
<li><strong>Tell your line manager and your team's information asset owner.</strong> Give a short description of what happened and what data was involved.</li>
<li><strong>Report it through your organisation's security incident process.</strong> If you are not sure what that is, your line manager or information asset owner can tell you.</li>
</ol>
"""
LICENCE_PAGE = """Follow the existing process.

1. Request a [service code](https://example.test/code) first.
2. Raise a service request in MyPortal.
"""
STEPS = page_steps([INCIDENT_PAGE, LICENCE_PAGE])
INCIDENT_ANSWER = (
    "Names are personal data, so this is an AI incident. Follow these steps as "
    "soon as possible. 1. Stop using the AI tool immediately. 2. Do not delete "
    "or change anything. 3. Tell your line manager and your team's information "
    "asset owner, with a short description of what happened. 4. Report it "
    "through your organisation's security incident process. If you do not know "
    "what that is, your line manager or information asset owner can tell you. "
    "A personal data breach may need to be reported to the Information "
    "Commissioner's Office within 72 hours, so do not delay."
)


def test_page_steps_are_the_items_of_numbered_lists_as_the_reader_sees_them():
    assert STEPS[0] == "Stop using the AI tool immediately."
    assert STEPS[3].startswith("Report it through your organisation's security")
    assert STEPS[3].endswith("information asset owner can tell you.")
    assert STEPS[4:] == (
        "Request a service code first.",
        "Raise a service request in MyPortal.",
    )


def test_text_after_the_last_step_gets_a_paragraph_of_its_own():
    laid_out = lay_out(INCIDENT_ANSWER, STEPS)

    steps, closing = laid_out.split("\n\n")
    assert steps.split("\n")[-1] == (
        "4. Report it through your organisation's security incident process. If "
        "you do not know what that is, your line manager or information asset "
        "owner can tell you."
    )
    assert closing == (
        "A personal data breach may need to be reported to the Information "
        "Commissioner's Office within 72 hours, so do not delay."
    )
    assert laid_out.split() == INCIDENT_ANSWER.split()


def test_a_last_step_with_nothing_after_it_is_left_alone():
    message = INCIDENT_ANSWER.partition(" A personal data breach")[0]
    assert "\n\n" not in lay_out(message, STEPS)
    assert lay_out(message, STEPS) == lay_out(message)


def test_a_last_step_that_is_not_one_of_a_page_s_steps_is_left_alone():
    message = long(
        "Follow these steps when choosing a tool. 1. Check whether a script "
        "would do the job. 2. Check the tools radar. 3. Turn on privacy "
        "settings before any Defra work. A tool that is not on the radar has "
        "not been looked at yet."
    )
    assert lay_out(message, STEPS) == lay_out(message)


def test_with_no_page_steps_numbered_lines_are_as_they_were():
    assert "\n\n" not in lay_out(INCIDENT_ANSWER)
