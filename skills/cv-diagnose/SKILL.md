---
name: cv-diagnose
description: >-
  Diagnose a resume the way an applicant tracking system and a recruiter's
  first scan would: parser killers, weak sections, missing signals, and the
  top 5 fixes ranked by impact. Use when the user says "diagnose my resume",
  "audit my CV", "is my resume ATS-friendly", "why am I not getting
  interviews", "разбери резюме", "проверь CV", or uploads a resume and asks
  what is wrong with it. Step 1 of the job-hunt loop.
---

# cv-diagnose

Fix the file before the words. A bullet rewrite is wasted on a resume the
parser reads as soup, so this runs first.

## Before you start

1. Read `~/.claude/linkedin/career.md` if it exists: base resume path, target
   role, seniority, the never-list. If it does not exist, copy
   `templates/career.md` there and fill what the user has told you.
2. You need four things: the resume, the target role, the seniority, the
   market (country). Ask for whatever is missing in **one** batched question,
   not one at a time.
3. Take the original file (.docx or .pdf) when there is one, not a paste. The
   layout checks only run on the file.

## Run the tool

```bash
python3 ats_check.py resume.docx --never "term1,term2"   # never-list from career.md
python3 ats_check.py resume.docx --text                   # what the parser reads, in order
```

It reports CRITICAL / WARN / INFO and a verdict: BLOCKED (a parser drops or
mangles something), REVIEW, CLEAN. It checks tables, text boxes, columns and
header/footer content in .docx; icon-font and broken glyphs; contact lines,
phone format and work-authorisation wording; canonical section headings;
mixed date formats; length; bullets with no number, weak openers, first
person; cliches and filler; the never-list.

Always read the `--text` output yourself too. It is the resume the ATS sees.

## Then diagnose, in this order

**1. ATS killers.** Everything CRITICAL, quoted, with the fix.

**2. Facts that cost interviews.** Things the script cannot know. Check the
resume against what the user has told you or shown you: outdated location,
a work-authorisation line that no longer matches their status, a
qualification or certificate they hold that is not on the page, a title that
overstates or undersells the seniority they are targeting.

**3. Section by section.** For summary, experience, education, skills: quote
the weakest line and say why it fails the scan.

**4. Missing signals.** What a hiring manager for this role, at this level,
in this market expects to see and does not. Name only signals the user could
truthfully add. If the gap is real, say it is a gap.

**5. Top 5 fixes, ranked by impact.** What to change first, and exactly how.
Show a before and after for at least one bullet. If the after needs a number
you do not have, write `{{number: what to count}}` and ask for it.

## Rules

- Quote the user's actual lines. No generic advice.
- Never invent a number, a tool, a title or a qualification to demonstrate a
  fix. A placeholder and a question, every time.
- Personal documents the user shares (visa, ID, national insurance or social
  security numbers, date of birth, test candidate IDs) are evidence for you,
  not content for the CV. None of them goes on the page. Right to work is
  one plain line; the proof is given at the employer's check, not before.
- Do not soften it. A resume that is not landing interviews has a reason.
- End by saying which step comes next: `/cv-keywords` with real job
  descriptions.
