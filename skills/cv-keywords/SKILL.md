---
name: cv-keywords
description: >-
  Find the keywords real job descriptions for the target role ask for, and
  which of them the resume is missing, buries, or only lists without proof.
  Counts over actual postings, not a guess about "the market". Use when the
  user says "find missing keywords", "what keywords should my resume have",
  "act as a recruiter", "scan job descriptions for X", "ключевые слова для
  резюме", "сравни резюме с вакансией", or pastes a job post next to their
  CV. Step 2 of the job-hunt loop.
---

# cv-keywords

You cannot optimise for keywords until you know which ones the postings
actually repeat. So this counts them.

## Get the postings first

The sample is whatever job descriptions are in the folder. Five to ten for
one role is a good sample; one is a single company's wishlist.

1. If the user pasted or linked postings, save each one as plain text in
   `~/.claude/linkedin/jobs/<role-slug>/<company>.txt`. Fetch links with the
   web tools if you have them. Do not log into LinkedIn or any job board on
   their behalf.
2. If they gave none and you have web search, find 5-10 **current** postings
   for the role, seniority and location, save them the same way, and list
   the URLs you used.
3. If you have neither, ask for 3-5 pasted postings. Do not substitute your
   own idea of what the market wants and call it data.

## Run the tool

```bash
python3 keywords.py --resume ~/.claude/linkedin/cv/base.md ~/.claude/linkedin/jobs/<role-slug>/
python3 keywords.py --resume cv.docx jd1.txt jd2.txt --top 40 --json
```

It ranks terms by how many postings contain them (`3/5` = in 3 of 5), keeps
only terms in at least a quarter of them, drops a phrase's fragments when
they never appear alone, and checks each term against the resume:

| status | meaning |
| --- | --- |
| `ok` | present, with proof outside the skills list |
| `SKILLS` | listed in skills, no bullet proves it. Recruiters discount these. |
| `BURIED` | first proof is in the bottom third of the page |
| `MISSING` | not there |

Kinds: `named` (capitalised or symbol-bearing: tools, products, titles,
places), `soft` (from the soft list in `terms.json`), `term` (everything
else). Light stemming handles plurals and Russian endings; synonyms it does
not, so "detail-oriented" does not count as "attention to detail". That
judgement is yours.

## Then report

1. **The ranked list**, with noise removed. Locations, company names and
   generic verbs that slipped through are not keywords; drop them and add
   the repeat offenders to `boilerplate` in `terms.json`.
2. **Missing, split in two.** For every MISSING or SKILLS term, check the
   base resume and whatever else the user has told you:
   - *has the evidence, wrong words* - the experience is there under another
     name. This is the rewrite list.
   - *genuinely absent* - it is a gap. It goes on the gap list, never into
     the resume.
3. **Rising terms.** Only claim a term is trending if it is measured: more
   frequent in the newest postings of the sample, or backed by a source you
   searched and cite. Otherwise label it "judgement, not measured".
4. **Cut list.** Cliches in the resume that take space from keywords. Run
   `../cv-diagnose/ats_check.py` if it is installed; it flags them.
5. **Five actions, ranked**, that move the resume from screened out to
   shortlisted fastest.

Hand the *has the evidence* list to `/cv-rewrite`.

## Say this honestly

The report is a count over the files in the folder. Say how many postings
it read. It is not "1,000 job descriptions" and it does not know what
Workday's ranking does with the terms. Matching the words postings actually
use is the claim, and it is a good one.
