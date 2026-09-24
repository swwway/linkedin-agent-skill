---
name: cv-rewrite
description: >-
  Rewrite resume bullets with the X-Y-Z formula (accomplished X, as measured
  by Y, by doing Z) and tailor a copy of the resume to one job description,
  without inventing a skill, number or title. Use when the user says
  "rewrite my resume bullets", "tailor my CV to this job", "XYZ my resume",
  "make my bullets stronger", "адаптируй резюме под вакансию", "перепиши
  опыт". Step 3 of the job-hunt loop.
---

# cv-rewrite

Turns bullets that describe duties into bullets that prove results, in the
vocabulary the target postings use. Every claim in the output traces back
to something the user actually did.

## Inputs

- The base resume (path in `~/.claude/linkedin/career.md`). **Never edit it.**
  Tailored versions are new files:
  `~/.claude/linkedin/cv/<company>-<role>.md` (and `.docx` if asked).
- The target: one job description, or the role if this is a general rewrite.
- The *has the evidence* list from `/cv-keywords`, if it ran.
- The never-list and the proof list from `career.md`.

Missing the target or the resume: ask, once, batched.

## The formula

Accomplished **X** as measured by **Y**, by doing **Z**. Laszlo Bock
popularised it at Google. In practice the order flexes: lead with the
strongest of the three.

```
before  Automated key operational workflows, reducing manual processing time.
after   Cut broker verification from {{number: minutes}} to {{number: minutes}}
        per case by automating the checks in {{tool}}, across {{number}} cases a month.
```

## Rules

1. **Lead with a verb that names the work.** Built, cut, shipped, automated,
   reconciled. Never "responsible for", "helped with", "assisted in",
   "participated in".
2. **A number in every bullet, from the user.** If you do not have it, write
   `{{number: what to count}}` and add it to the question list. Never an
   estimate, never "approximately", never a range you made up. A placeholder
   costs one question. An invented number costs the offer at the reference
   check.
3. **One idea per bullet, two lines at most.**
4. **Keywords only where the evidence exists.** A missing keyword with no
   evidence goes on the gap list, with the honest options: adjacent
   experience to foreground, a line for the cover letter, or apply anyway
   because it is a nice-to-have. It does not go in the resume.
5. **The never-list wins over the job description.** If a posting asks for
   a term on the never-list, describe the underlying work in the words
   around it, or leave it out. Say which you did.
6. **Reorder before rewriting.** The most relevant role or project moves to
   the top of its section; the most relevant bullet moves to the top of its
   role. Cut what the target does not care about.
7. **Cut filler:** various, multiple, different, successfully, effectively.

## Output

1. The tailored resume, written to the new file.
2. **Provenance table**: every bullet in the new version, and the base
   resume line or user message it came from. A bullet with no source is
   deleted, not defended.
3. **Before and after** for the five highest-impact bullets, one line each on
   why the after is stronger.
4. **Questions**: every `{{placeholder}}`, as one numbered list the user can
   answer in one message.
5. **Gap list** from rule 4.
6. Run `../cv-diagnose/ats_check.py` on the new file with the never-list. It
   must not come back BLOCKED.

Nothing is sent to an employer from here. The user reviews the file and
applies themselves.
