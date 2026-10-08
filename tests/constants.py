"""Values the tests assert against, written out here and not imported from app/.

A test that reads its expected value from the code under test cannot fail when
that value changes.
"""

from app.ask import schemas

ASK_DAILY_USAGE_COLLECTION = "ask_daily_usage"

ERROR_ANSWER = schemas.Answer(
    status="error",
    message="The toolkit could not answer just now. Try again in a minute.",
)
CEILING_ANSWER = schemas.Answer(
    status="error",
    message="The toolkit has reached today's limit. Try again tomorrow.",
    reason="daily_limit",
)
BLOCKED_ANSWER = schemas.Answer(
    status="blocked",
    message="This question cannot be answered here.",
)
