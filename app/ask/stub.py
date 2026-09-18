"""Offline answers, so the front end can be run with no model and no key.

Ported from service-manual-ui `src/server/ai-ask/__fixtures__/answers.js` so
both repos agree on the contract. Selection is by keyword rather than at
random, so a demonstration shows the same answer to the same question every
time. Every rule_verbatim text is copied exactly from the toolkit page it
cites.
"""

import re

from app.ask.schemas import Answer, RuleVerbatim, Source

USING_DATA = Source(
    title="Using data with AI",
    url="/ai-toolkit/guidance/using-data-with-ai",
    section="What the conditions mean",
)

PERSONAL_DATA_ANSWER = Answer(
    status="answered",
    message=(
        "Microsoft 365 Copilot is an enterprise tool inside the Defra tenant, so "
        "Defra's data boundary applies. That is not the same as clearance to use "
        "personal data in it."
    ),
    rule_verbatim=RuleVerbatim(
        text=(
            "For personal data, the DPIA route is for a service you are building "
            "to process it, not a way to paste it into an everyday tool. For "
            "everyday use, remove personal data first."
        ),
        source=USING_DATA,
    ),
    sources=[
        USING_DATA,
        Source(
            title="Microsoft 365 Copilot",
            url="/ai-toolkit/tools/microsoft-365-copilot",
        ),
    ],
)

CHOOSING_A_TOOL_ANSWER = Answer(
    status="answered",
    message=(
        "Start from the data you will use, then check the tools radar for a tool "
        "cleared for that classification. The radar entry tells you the status of "
        "the tool and any conditions on using it."
    ),
    sources=[
        Source(title="Choosing a tool", url="/ai-toolkit/guidance/choosing-a-tool"),
        Source(title="Find a tool", url="/ai-toolkit/tools"),
    ],
)

GENERAL_ANSWER = Answer(
    status="answered",
    message=(
        "The AI digital toolkit covers choosing a tool, the data you can use with "
        "it, the patterns teams reuse, and how to get support. Ask about any of "
        "those and the answer will link to the guidance it came from."
    ),
    sources=[
        Source(title="AI digital toolkit", url="/ai-toolkit"),
        Source(title="Deliver with AI", url="/ai-toolkit/deliver-with-ai"),
    ],
)

# The five outcomes that are not an answer, one each, so the front end can
# build and test the screens for them. Triggered by words unlikely to appear
# in the questions above.
NEED_MORE_DETAIL = Answer(
    status="need_more_detail",
    message="The toolkit covers a few different things. Which is closest?",
    options=[
        "Choosing a tool for a task",
        "What data I can use with a tool",
        "Building a service that uses AI",
        "Getting support from the team",
    ],
    sources=[Source(title="AI digital toolkit", url="/ai-toolkit")],
)

OUTSIDE_TOOLKIT = Answer(
    status="cannot_answer",
    reason="outside_toolkit",
    message=(
        "The toolkit is about using AI at Defra, and this question is about "
        "something else, so it has no answer here."
    ),
)

NO_GUIDANCE_YET = Answer(
    status="cannot_answer",
    reason="no_guidance_yet",
    message=(
        "The toolkit does not have guidance on buying AI products or services "
        "yet. This question has been noted as a gap."
    ),
    sources=[Source(title="Deliver with AI", url="/ai-toolkit/deliver-with-ai")],
)

TALK_TO_A_PERSON = Answer(
    status="talk_to_a_person",
    message=(
        "Whether your own project needs a data protection impact assessment is a "
        "decision about that project, not something the toolkit can answer in "
        "general. The AI Capability and Enablement team can look at it with you."
    ),
    sources=[USING_DATA],
)

BLOCKED = Answer(
    status="blocked",
    message=(
        "This service cannot help with that. It answers questions about using "
        "AI at Defra."
    ),
)

ERROR = Answer(
    status="error",
    message="The toolkit could not answer just now. Try again in a minute.",
)

MATCHERS: list[tuple[tuple[str, ...], Answer]] = [
    (("break the", "simulate an error"), ERROR),
    (("medical", "legal advice", "diagnos"), BLOCKED),
    (("my project", "my service", "do we need a dpia"), TALK_TO_A_PERSON),
    (("procurement", "buying", "buy an"), NO_GUIDANCE_YET),
    (("pension", "expenses", "parking"), OUTSIDE_TOOLKIT),
    (("getting started", "where do i start", "help me"), NEED_MORE_DETAIL),
    (("personal data", "copilot"), PERSONAL_DATA_ANSWER),
    (("tool", "radar", "approved"), CHOOSING_A_TOOL_ANSWER),
]

# Openings that mean "carry on from what I just asked" rather than "here is a
# new subject".
FOLLOW_UP_OPENINGS = (
    "what about",
    "and ",
    "but ",
    "so ",
    "why",
    "how about",
    "what if",
    "does that",
    "is that",
    "can i still",
)

# Words that only mean something against the question before them.
REFERRING_WORDS = frozenset(
    {"it", "that", "this", "they", "them", "those", "these", "instead"}
)

# A short question does the same job: "what about agents?" only makes sense
# against the question before it.
FOLLOW_UP_WORD_COUNT = 8


def reads_as_follow_up(asked: str) -> bool:
    # Digits stay: "article 9" is two words, not one.
    words = re.sub(r"[^a-z0-9\s]", "", asked).split()
    return (
        asked.startswith(FOLLOW_UP_OPENINGS)
        or len(words) <= FOLLOW_UP_WORD_COUNT
        or any(word in REFERRING_WORDS for word in words)
    )


def stub_answer(question: str, previous_question: str | None = None) -> Answer:
    """Pick the stub answer for a question.

    Following up is the normal case, not the exception, so a question that
    reads as a follow-up is answered as one, naming what it follows on from.
    """
    asked = question.lower()
    answer = next(
        (answer for keywords, answer in MATCHERS if any(k in asked for k in keywords)),
        GENERAL_ANSWER,
    )

    if (
        not previous_question
        or not reads_as_follow_up(asked)
        or answer.status != "answered"
    ):
        return answer

    return answer.model_copy(
        update={"message": f'Still on "{previous_question}": {answer.message}'}
    )
