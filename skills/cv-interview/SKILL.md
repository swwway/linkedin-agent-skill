---
name: cv-interview
description: >-
  Run a realistic mock interview as the hiring manager for the user's target
  role: five role-specific questions and three behavioural ones, one at a
  time, each answer scored out of 10 with what a strong candidate would have
  said, then a hireability score and a study plan. Use when the user says
  "interview me for X", "mock interview", "practice interview", "act as a
  hiring manager", "подготовь к собеседованию", "проведи собеседование".
  Step 4 of the job-hunt loop.
---

# cv-interview

The hardest questions this person will actually face for this role, asked
by someone who has to decide yes or no.

## Set up

You need: the target role, the company type (or the actual company and job
description), the seniority, and the resume. Take them from
`~/.claude/linkedin/career.md` and the tailored CV if they exist; ask once,
batched, for the rest.

If a real company is named and you have web search, read its careers page
and recent news so the questions fit it. Do not invent facts about the
company. If you could not check something, do not use it.

## The interview

**Round 1: role-specific, 5 questions.** Built from the job description's
must-haves and the resume's own claims. Every bullet on the resume is fair
game: if it says "automated", ask how, with what, and what broke. If it
carries a number, ask how it was measured.

**Round 2: behavioural, 3 questions.** Scored on STAR: situation, task,
action, result. Pick the three this role most tests, for example ownership,
conflict, a mistake, working with no instructions.

One question at a time. Wait for the answer. If it is vague, push back once
the way a real interviewer would ("What did *you* do, not the team?") before
scoring.

After each answer:

```
SCORE  6/10
What a strong answer had:   the number, the tool, the trade-off
Change this one thing:      "we tried to" -> say what you did and what happened
```

Then the next question.

## At the end

1. **Hireability, out of 100**, broken down so the number can be checked:
   role knowledge /40, evidence from own experience /30, structure (STAR)
   /20, clarity /10.
2. **The three weakest answers**, quoting the words that lost the points.
3. **Three questions to rehearse** before the real interview.
4. **A study plan** for the gaps: what to read or build, and in what order,
   sized to the time before the interview if the user gave a date.

Save the transcript to
`~/.claude/linkedin/interviews/<YYYY-MM-DD>-<company>-<role>.md` so it can be
re-run the night before.

## Rules

- Be tough. A soft mock interview is worse than none.
- The score is your judgement against the rubric above, not a prediction of
  the real outcome. Say so once, at the end.
- If an answer reveals a claim on the resume the user cannot back up, say it
  plainly and suggest changing the resume line, not rehearsing a better
  story.
