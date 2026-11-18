# Checking the judge by hand

Two of the six measures, Grounded and Complete, are marked by a second AI model
acting as judge. This page explains how people check the judge: two markers each
mark 20 answers blind, then compare their marks with the judge's.

Do it again whenever the judge's model or its instructions in `evals/judge.py`
change. Marking takes each marker about 45 minutes.

Twenty answers can't prove the judge is good. They can show that it's bad. A low
agreement figure is a useful result, not a failure.

## Making the sample

The organiser, usually the technical lead, does this before anyone marks.

1. Pick a judged full run under `evals/results/`.
2. Choose 20 answers that weren't in an earlier sample. Include a mix of
   sections, and some rows that expect a refusal or "no such rule".
3. Make a **sample page** showing, for each answer: the question, the
   expected status, the expected answer, the named source pages, the
   service's message, and the quoted rule the judge saw. Where the service's
   quote check dropped a quote, say so. Number the answers K01 to K20.
4. Make a separate **key page** with the judge's Grounded and Complete
   verdict for each answer, and its reason. Both are in the run's
   `verdicts.json.gz`, under `judged`, matched on `run` and `question_id`.
5. Give the markers this page and the sample page. Keep the key page back.

## Before you start marking

1. Copy the marking sheet at the bottom of this page into your own page. Your
   marks go there, so the other marker can't see them.
2. Open the sample page. Don't open the key page until you've marked all 20.
3. Open the toolkit site in another tab: <https://digital.defra.gov.uk/ai-toolkit>
4. Don't discuss the answers with the other marker until you've both
   finished.

## The two measures

These are the golden set's own definitions. They are the only marking scheme, so
don't add criteria of your own.

**Grounded.** "Is every fact in the answer traceable to the named source pages?
An answer that is true but not on those pages fails." The quoted rule is part of
the answer: a rule quoted from a page the row doesn't name fails.

**Complete.** "Does the answer contain the claim in the Expected answer column?
Citing the right page is not enough." Every part of the expected answer must be
there. A good answer that misses a part fails.

## How to mark one answer

1. Read the question and the expected answer.
2. Read the service's message and its quoted rule.
3. **Grounded.** Open each named source page on the toolkit site. For every
   fact in the message and in the quoted rule, find it on one of those
   pages. If every fact is there, pass. If any fact isn't on a named page,
   fail, even if the fact is true and even if it's on another toolkit page. A
   quoted rule from a page the row doesn't name fails, even when the words
   are exactly right.
4. **Complete.** Split the expected answer into its parts and tick each one
   off in the message. Every part must be there. Don't judge whether it's
   helpful or well written, or whether it points to the right page. For
   example, if the expected answer is "no, and remove it first" and the
   message links to the page without saying no, fail it.
5. Write pass or fail in the Grounded and Complete columns. If you fail an
   answer, write one line in Notes saying which fact is unsupported or which
   claim is missing.

Don't mark the writing. Length, tone and hedging aren't part of these two
measures.

## Worked example: a pass

**Question:** What can I put into a public AI tool?

**Expected answer:** Public or open information, and OFFICIAL with privacy
settings on. Not OFFICIAL-SENSITIVE, not personal data, not SECRET.

**Named source pages:** Using data with AI

**Message:** You can put public or open data, and OFFICIAL data, into a public
consumer tool. For OFFICIAL data, you must turn on privacy settings first, which
means switching off model training and chat history. You cannot put
OFFICIAL-SENSITIVE data, personal data, or anything SECRET or above into a
public consumer tool.

- **Grounded: pass.** Every fact is on Using data with AI. The message cites
  other pages too. That doesn't matter, because the facts are on the named
  page.
- **Complete: pass.** All four parts of the expected answer are there.

## Worked example: a fail

**Question:** Do I need static analysis on AI-generated code?

**Expected answer:** Yes, and dependency scanning as well.

**Named source pages:** Security

**Message:** Yes. SonarQube, Defra's static analysis gate, must be run on all
AI-generated code before it is merged. AI-authored code is held to the same
standard as hand-written code.

- **Grounded: pass.** Every fact is on the Security page.
- **Complete: fail.** The expected answer has two parts and the message has
  only the first. Note: "no mention of dependency scanning".

A message can pass one measure and fail the other. Mark them separately.

## Answers with no named source pages

Some rows expect the service to refuse, to say the toolkit has no rule, or to
block an injection attempt. These rows name no source pages, but you still mark
them.

- **Grounded** fails only if the message states a toolkit fact that's on no
  toolkit page. A plain refusal has no facts, so it passes.
- **Complete** is whether the message does what the expected answer
  describes. If the expected answer is "no such rule exists" and the message
  says the toolkit doesn't cover it, pass. If it invents a rule, fail.

## Things that aren't mistakes

- **A true fact from a page the row doesn't name fails Grounded.** That's the
  definition working. If you think the row should name that page, fail it
  and say so in Notes. The golden set's owner decides.
- **A missing quoted rule.** If the service dropped a quote for not matching
  the page, the reader doesn't see it. Mark what's there.
- **A different true rule that means the same thing.** For Complete, ask
  whether the expected claim is present, not whether the rule is a good one.

## When you've finished marking

1. Open the key page.
2. Fill in the two "Judge" columns of your sheet from the key.
3. Count the cells where your mark and the judge's are the same, and write
   the number out of 40 in the "Agreement" line.
4. For each disagreement, read the judge's reason and label it **judge
   wrong**, **I was wrong** or **expected answer unclear**, with one sentence
   in Notes saying why.
5. Tell the organiser. Both markers and the organiser then go through the
   disagreements together.

## The last check

In September 2026, the two markers agreed with the judge on 38 and 27 of 40
verdicts. After going through every disagreement, the judge was wrong on 1 of
40. The rest were people reading "complete" differently, which led to the
"every part must be there" rule above.

## Marking sheet

Copy from here down into your own page. Fill the first three columns before
opening the key, and the last three after.

**Marker:**

**Date:**

**Agreement with the judge:** \_\_\_ of 40

| Answer | Grounded | Complete | Notes | Judge: Grounded | Judge: Complete | Disagreement |
|---|---|---|---|---|---|---|
| K01 | | | | | | |
| K02 | | | | | | |
| K03 | | | | | | |
| K04 | | | | | | |
| K05 | | | | | | |
| K06 | | | | | | |
| K07 | | | | | | |
| K08 | | | | | | |
| K09 | | | | | | |
| K10 | | | | | | |
| K11 | | | | | | |
| K12 | | | | | | |
| K13 | | | | | | |
| K14 | | | | | | |
| K15 | | | | | | |
| K16 | | | | | | |
| K17 | | | | | | |
| K18 | | | | | | |
| K19 | | | | | | |
| K20 | | | | | | |
