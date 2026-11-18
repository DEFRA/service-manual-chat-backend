# Decision records

Short records of the decisions behind Ask the toolkit: what was decided, why,
and what would make it worth revisiting. Add a new numbered file for a new
decision; to reverse one, add a record that replaces it and mark the old one
"superseded".

1. [The backend is Python FastAPI with Pydantic AI](0001-backend-language.md)
2. [Send the whole toolkit with every question](0002-whole-toolkit-in-the-prompt.md)
3. [Answer with Claude Sonnet 4.6](0003-claude-sonnet-4-6.md)
4. [Use the service's own Bedrock guardrail](0004-our-own-guardrail.md)
5. [Keep the conversation in the site, not the backend](0005-stateless-backend.md)
6. [Quote rules word for word, and check every quote](0006-rules-quoted-word-for-word.md)
7. [The site waits for the answer in one call](0007-synchronous-call.md)
8. [The site calls the backend without a token, for launch](0008-no-token-on-the-call-for-launch.md)
