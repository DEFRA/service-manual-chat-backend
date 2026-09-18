"""The wire shape of Ask the toolkit.

This is the contract with service-manual-ui, which maps it in
`src/server/ai-ask/answer.js`. Field names are snake_case on the wire and the
front end owns the conversion to camelCase, so nothing here should be renamed
without changing both sides.

`rule_verbatim` is the one field with a rule of its own: its text must be
copied exactly from the toolkit page it cites. The model explains around a
rule, it never rewrites one. The front end checks the quote against the page
and drops it if the words differ, so a paraphrase is not shown, it is lost.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Matches MAX_QUESTION_LENGTH in service-manual-ui `src/server/ai-ask/constants.js`.
MAX_QUESTION_LENGTH = 500


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    # The question asked before this one, so a follow-up ("what about agents?")
    # can be read against it. Sent by the front end from its session; a durable
    # conversation lives here later, this is enough for a local loop.
    previous_question: str | None = Field(default=None, max_length=MAX_QUESTION_LENGTH)
    conversation_id: str | None = None


class Source(BaseModel):
    title: str
    # An internal path such as /ai-toolkit/guidance/using-data-with-ai. The
    # front end only renders sources for pages it serves.
    url: str
    section: str | None = None


class RuleVerbatim(BaseModel):
    text: str
    source: Source


# The six outcomes the design history agreed. The front end has only ever seen
# `answered`; the other five are the screens it has not built yet.
Status = Literal[
    # A real answer, possibly with a rule quoted word for word.
    "answered",
    # Too broad to answer well. `options` offers two to four ways to narrow it,
    # and the front end keeps free text underneath.
    "need_more_detail",
    # No answer. `reason` says which kind: outside what the toolkit covers, or
    # a gap the toolkit has not filled yet (worth recording).
    "cannot_answer",
    # The question is about the reader's own project or decision, where the
    # toolkit points at the team rather than answering.
    "talk_to_a_person",
    # Refused, in neutral words. Never "your question was flagged".
    "blocked",
    # The backend could not get an answer this time; try again.
    "error",
]

CannotAnswerReason = Literal["outside_toolkit", "no_guidance_yet"]

MIN_OPTIONS = 2
MAX_OPTIONS = 4


class Answer(BaseModel):
    status: Status
    # Always present: what the page shows the reader, whatever the status.
    message: str
    rule_verbatim: RuleVerbatim | None = None
    sources: list[Source] = Field(default_factory=list)
    # need_more_detail only: two to four narrower questions to pick from.
    options: list[str] = Field(default_factory=list)
    # cannot_answer only.
    reason: CannotAnswerReason | None = None

    @model_validator(mode="after")
    def fields_match_status(self) -> "Answer":
        if self.status == "need_more_detail":
            if not MIN_OPTIONS <= len(self.options) <= MAX_OPTIONS:
                msg = f"need_more_detail carries {MIN_OPTIONS} to {MAX_OPTIONS} options"
                raise ValueError(msg)
        elif self.options:
            msg = "options belong to need_more_detail only"
            raise ValueError(msg)

        if self.status == "cannot_answer":
            if self.reason is None:
                msg = "cannot_answer needs a reason"
                raise ValueError(msg)
        elif self.reason is not None:
            msg = "reason belongs to cannot_answer only"
            raise ValueError(msg)

        if self.status != "answered" and self.rule_verbatim is not None:
            msg = "only an answer quotes a rule"
            raise ValueError(msg)
        return self
