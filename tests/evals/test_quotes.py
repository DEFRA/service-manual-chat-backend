from evals.quotes import locate, whole_sentences

# The golden set's three worked examples, on a page with the markup real pages have.
PAGE = """## Personal data

<li><strong>DPIA required.</strong> The assessment must be completed first.</li>

For personal data, the DPIA route is for a service you are building to
process it, not a way to paste it into an everyday tool. Remove it first.

You must publish a record in the [Algorithmic Transparency Recording Standard (ATRS)](https://example.test/atrs).
"""
RULE = "For personal data, the DPIA route is for a service you are building to process it, not a way to paste it into an everyday tool."


def test_the_exact_rule_passes_across_a_line_break() -> None:
    span = locate(RULE, PAGE)
    assert span
    assert whole_sentences(PAGE, span)


def test_a_changed_word_is_not_found() -> None:
    assert locate(RULE.replace("an everyday tool", "a normal tool"), PAGE) is None


def test_a_dropped_condition_is_found_but_is_not_a_whole_sentence() -> None:
    cut = "The DPIA route is for a service you are building to process it."
    span = locate(cut, PAGE)
    assert span is not None
    assert span is not None
    assert whole_sentences(PAGE, span) is False


def test_a_quote_that_stops_before_the_condition_is_not_a_whole_sentence() -> None:
    span = locate(
        "For personal data, the DPIA route is for a service you are building to process it",
        PAGE,
    )
    assert span is not None
    assert whole_sentences(PAGE, span) is False


def test_a_link_inside_the_sentence_does_not_fail_the_quote() -> None:
    quote = "You must publish a record in the Algorithmic Transparency Recording Standard (ATRS)."
    span = locate(quote, PAGE)
    assert span
    assert whole_sentences(PAGE, span)


def test_a_rule_inside_html_is_found() -> None:
    assert locate("The assessment must be completed first.", PAGE)


def test_a_typographic_hyphen_is_forgiven_but_a_split_word_is_not() -> None:
    page = "This is non-negotiable."
    assert locate("This is non\u2011negotiable.", page)
    assert locate("This is non negotiable-ish.", page) is None


def test_part_of_a_word_does_not_count() -> None:
    assert locate("person", PAGE) is None


def test_a_sentence_that_introduces_a_list_is_whole_even_though_it_ends_in_a_colon() -> (
    None
):
    page = "Status tells you how established a tool is, not whether you may use it:\n\n- Using\n- Trialling\n"
    span = locate(
        "Status tells you how established a tool is, not whether you may use it.", page
    )
    assert span
    assert whole_sentences(page, span)
    partial = locate("Status tells you how established a tool is", page)
    assert partial is not None
    assert whole_sentences(page, partial) is False


STEPS_PAGE = """## What to do

Follow these steps as soon as you realise an incident has happened.

<ol class="govuk-list">
<li><strong>Stop using the AI tool immediately.</strong></li>
<li><strong>Do not delete or change anything.</strong> The people handling the incident need to see what happened.</li>
</ol>
"""


def test_a_numbered_list_quoted_with_its_numbers_is_the_same_words() -> None:
    # The reader sees "1." on the page; the backend's check strips list markers from both sides.
    quote = "Follow these steps as soon as you realise an incident has happened.\n\n1. Stop using the AI tool immediately.\n2. Do not delete or change anything. The people handling the incident need to see what happened."
    span = locate(quote, STEPS_PAGE)
    assert span
    assert whole_sentences(STEPS_PAGE, span)


def test_a_number_inside_a_sentence_is_still_a_word() -> None:
    assert locate("within 72 hours", "Report it within 72 hours.") is not None
    assert locate("within 27 hours", "Report it within 72 hours.") is None


TABLE = """<table>
<tr><th scope="row">Personal data</th><td><strong>No</strong></td><td><strong>DPIA required</strong> before use</td><td><strong>No</strong></td></tr>
</table>

## What the conditions mean
"""


def test_a_table_row_read_across_is_stitched_not_a_quote() -> None:
    from evals.quotes import stitched

    span = locate("Personal data | No | DPIA required before use | No", TABLE)
    assert span is not None
    assert stitched(TABLE, span)


def test_one_cell_on_its_own_is_a_whole_quote() -> None:
    from evals.quotes import stitched

    span = locate("DPIA required before use", TABLE)
    assert span
    assert whole_sentences(TABLE, span)
    assert not stitched(TABLE, span)


def test_a_cell_joined_to_the_heading_after_the_table_is_stitched() -> None:
    from evals.quotes import stitched

    span = locate("No. What the conditions mean.", TABLE)
    assert span is not None
    assert stitched(TABLE, span)
