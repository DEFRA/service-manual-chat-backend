# 6. Quote rules word for word, and check every quote

**Status:** accepted, 10 September 2026

## Context

The toolkit mixes rules (what you must do) and advice. A model asked to explain
a rule may reword it, and a reworded rule can change its meaning. GOV.UK style
lets advice be paraphrased; a rule must not be.

## Decision

The model explains around a rule and never rewrites it. A rule goes in the
answer's `rule_verbatim` field, with the page it comes from. The backend checks
the quote's words are on that page and drops it if not; the site checks again
before showing it. A source that is not a toolkit page is dropped too.

## Consequences

- A made-up or reworded rule never reaches the reader.
- A real rule credited to the wrong page can still get through: the check
  proves the words are on the page named, not that it is the right rule.
- The check compares words, not characters, and does not join words across
  table cells. Some correct quotes that span markup are dropped.
- The backend and the site each have a copy of the check. They share a set of
  test cases and must stay in step.

## Revisit when

- the checks are found to let through a wrong rule that a Bedrock guardrail
  grounding check would have stopped.
