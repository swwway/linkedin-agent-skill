#!/usr/bin/env python3
"""
keywords.py - count what real job descriptions ask for, then check which of
those terms the resume carries, buries, or only lists without proof.

What this is:  document frequency over the job descriptions you give it. A term
that shows up in 4 of 5 postings for the role is a keyword; a term in one of
them is that company's wish. The sample is the files you pass in - five real
postings beat any claim about "1,000 job descriptions", and the report says
how many it read.

What this is NOT:  a market survey. It cannot see postings you did not give
it, and it does not know which terms are noise until you read the list. Every
number it prints is a count over your files. Nothing is uploaded.

Usage
  python3 keywords.py jd1.txt jd2.txt jd3.txt
  python3 keywords.py --resume cv.md jobs/frontend/          # a folder of .txt/.md
  python3 keywords.py --resume cv.docx jobs/ --top 40 --json
"""

import argparse
import json
import math
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
TERMS = os.path.join(HERE, "terms.json")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

TOKEN = re.compile(r"[^\W_][\w+#]*(?:[./&-][\w+#]+)*[+#]*")
SEGMENT = re.compile(r"[\n\r,;:!?()\[\]{}|•·●▪◦\"“”«»]+|\.(?=\s|$)|\s[-–—]\s|\t")
URL = re.compile(r"https?://\S+|www\.\S+")
MIDDLE_OK = {"of", "on", "to", "and"}   # ruby on rails, attention to detail, profit and loss
NUMERIC = re.compile(r"^\d[\d+.,%x]*$")
CYRILLIC = re.compile("[а-я]")

RU_ENDINGS = sorted("""
    иями ями ами ием иях ого его ому ему ыми ими ией ий ый ой ая яя ое ее ие ые ую юю
    ия ию ии ом ем ам ям ах ях ов ев ей а я о е ы и у ю ь й
""".split(), key=len, reverse=True)

SECTION_WORDS = {
    "summary": {"summary", "professional summary", "profile", "about", "about me",
                "objective", "о себе", "обо мне", "профиль"},
    "experience": {"experience", "work experience", "professional experience",
                   "employment", "employment history", "work history",
                   "опыт", "опыт работы", "профессиональный опыт"},
    "projects": {"projects", "personal projects", "selected projects", "pet projects",
                 "проекты", "pet-проекты", "личные проекты"},
    "skills": {"skills", "technical skills", "core skills", "key skills", "hard skills",
               "tech stack", "stack", "technologies", "tools", "навыки",
               "ключевые навыки", "стек", "технический стек", "технологии"},
    "education": {"education", "образование"},
}
SECTION_OF = {w: k for k, ws in SECTION_WORDS.items() for w in ws}


# ------------------------------------------------------------ normalisation

def norm(tok):
    t = tok.lower().replace("ё", "е")
    if re.search(r"[+#./&]", t):
        return t
    if CYRILLIC.search(t):
        if len(t) > 5:
            for end in RU_ENDINGS:
                if t.endswith(end) and len(t) - len(end) >= 4:
                    return t[: -len(end)]
        return t
    if len(t) > 5 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 3 and t.endswith("s") and not t.endswith(("ss", "us", "is")):
        return t[:-1]
    return t


def load_terms(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    def keys(words):
        return {tuple(norm(w) for w in TOKEN.findall(x)) for x in words}

    stop = {k[0] for k in keys(raw["stopwords"]) if len(k) == 1}
    boiler = keys(raw["boilerplate"])
    return stop, {k[0] for k in boiler if len(k) == 1}, boiler, keys(raw["soft"])


# ------------------------------------------------------------------ reading

def read_text(path):
    if path.lower().endswith(".docx"):
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
        return "\n".join("".join(t.text or "" for t in p.iter(W + "t"))
                         for p in root.iter(W + "p"))
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def expand(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            out.extend(os.path.join(p, f) for f in sorted(os.listdir(p))
                       if f.lower().endswith((".txt", ".md", ".docx")))
        else:
            out.append(p)
    return out


def segments(text):
    text = URL.sub(" ", text)
    for seg in SEGMENT.split(text):
        toks = [t.rstrip(".-/&") for t in TOKEN.findall(seg)]
        toks = [t for t in toks if t]
        if toks:
            yield toks


# ------------------------------------------------------------------ mining

def grams(toks, stop, boiler_single, boiler_multi):
    normed = [norm(t) for t in toks]
    for i in range(len(toks)):
        for n in (1, 2, 3):
            if i + n > len(toks):
                break
            key = tuple(normed[i:i + n])
            first, last = key[0], key[-1]
            if first in stop or last in stop:
                continue
            if n == 2 and (first in boiler_single or last in boiler_single):
                continue
            if n == 3 and key[1] in stop and (key[1] not in MIDDLE_OK or first in
                                               boiler_single or last in boiler_single):
                continue
            if any(NUMERIC.match(k) for k in key) or any(len(k) < 2 and k not in ("c", "r")
                                                         for k in key):
                continue
            if n == 1 and first in boiler_single:
                continue
            if key in boiler_multi:
                continue
            surface = toks[i:i + n]
            yield key, " ".join(surface), i


def mine(jd_texts, stop, boiler_single, boiler_multi, soft):
    df, tf = Counter(), Counter()
    forms = defaultdict(Counter)
    capital = Counter()
    for text in jd_texts:
        seen = set()
        for toks in segments(text):
            for key, surface, pos in grams(toks, stop, boiler_single, boiler_multi):
                tf[key] += 1
                seen.add(key)
                forms[key][surface.lower()] += 1
                if any(c.isupper() for c in surface[1:]) or \
                        (pos > 0 and surface[:1].isupper()):
                    capital[key] += 1
        for key in seen:
            df[key] += 1

    n = len(jd_texts)
    min_df = 1 if n == 1 else max(2, round(0.25 * n))
    cands = {}
    for key, d in df.items():
        if d < min_df:
            continue
        kind = classify(key, forms[key], capital[key], tf[key], soft)
        if n == 1 and tf[key] < 2 and kind != "named":
            continue
        cands[key] = {"df": d, "tf": tf[key], "kind": kind,
                      "term": forms[key].most_common(1)[0][0]}

    # drop a shorter term that never appears outside a longer kept one
    for key in list(cands):
        for other, o in cands.items():
            if len(other) > len(key) and o["df"] == cands[key]["df"] \
                    and o["tf"] >= cands[key]["tf"] and contains(other, key):
                del cands[key]
                break
    return cands, min_df


def contains(big, small):
    k = len(small)
    return any(big[i:i + k] == small for i in range(len(big) - k + 1))


def classify(key, forms, caps, tf, soft):
    if any(key == s or contains(key, s) for s in soft if s):
        return "soft"
    surface = next(iter(forms))
    if re.search(r"[+#./&\d]", surface) or caps * 2 >= tf and caps:
        return "named"
    return "term"


# ------------------------------------------------------------------- resume

def index_resume(text):
    """[(line_no, section, [normed token lists])]"""
    rows, section = [], "top"
    lines = [l for l in text.splitlines()]
    for i, raw in enumerate(lines, 1):
        clean = re.sub(r"[#*_:|]+", " ", raw).strip().lower().replace("ё", "е")
        clean = re.sub(r"\s+", " ", clean)
        if clean in SECTION_OF:
            section = SECTION_OF[clean]
            continue
        segs = [[norm(t) for t in s] for s in segments(raw)]
        if segs:
            rows.append((i, section, segs))
    return rows, len(lines)


def locate(key, rows):
    hits = []
    for line, section, segs in rows:
        if any(contains(tuple(s), key) for s in segs):
            hits.append((line, section))
    return hits


def status(hits, total_lines):
    if not hits:
        return "MISSING", ""
    sections = sorted({s for _, s in hits})
    if sections == ["skills"]:
        return "SKILLS", "listed in skills, no bullet proves it"
    proof = [(l, s) for l, s in hits if s != "skills"]
    first = min(l for l, _ in proof)
    if first > total_lines * 2 / 3:
        return "BURIED", f"first proof at line {first} of {total_lines}"
    return "ok", ", ".join(sections)


# ------------------------------------------------------------------- output

def main():
    ap = argparse.ArgumentParser(description="Rank job-description keywords by how many "
                                 "postings ask for them, and check them against a resume.")
    ap.add_argument("jds", nargs="+", help="job description files or folders (.txt/.md/.docx)")
    ap.add_argument("--resume", help="resume file (.txt/.md/.docx)")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--terms", default=TERMS, help="path to terms.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    files = expand(args.jds)
    if not files:
        sys.exit("keywords: no job description files found")
    stop, boiler_single, boiler_multi, soft = load_terms(args.terms)
    texts = [read_text(f) for f in files]
    cands, min_df = mine(texts, stop, boiler_single, boiler_multi, soft)
    ranked = sorted(cands.items(), key=lambda kv: (-kv[1]["df"], -kv[1]["tf"], -len(kv[0])))
    shown = ranked[: args.top]

    rows, total = (index_resume(read_text(args.resume)) if args.resume else ([], 0))
    for key, c in shown:
        if args.resume:
            c["status"], c["where"] = status(locate(key, rows), total)

    n = len(files)
    if args.json:
        print(json.dumps({"job_descriptions": n, "files": files, "min_df": min_df,
                          "candidates": len(cands),
                          "terms": [dict(c) for _, c in shown]},
                         ensure_ascii=False, indent=2))
        return

    print(f"KEYWORDS  {n} job description(s), {len(cands)} terms in >= {min_df} of them, "
          f"top {len(shown)} shown")
    if n < 3:
        print("          under 3 postings: this is one company's wishlist, not the market")
    if args.resume:
        print(f"          resume: {os.path.basename(args.resume)}")
    print()
    width = max([len(c["term"]) for _, c in shown] + [4])
    width = min(width, 32)
    for i, (key, c) in enumerate(shown, 1):
        term = c["term"] if len(c["term"]) <= width else c["term"][: width - 3] + "..."
        line = f"  {i:>2}  {term:<{width}}  {c['df']}/{n:<3} {c['kind']:<6}"
        if args.resume:
            line += f" {c['status']:<8}{c['where']}"
        print(line.rstrip())

    if args.resume and shown:
        weight = sum(c["df"] for _, c in shown)
        got = sum(c["df"] for _, c in shown if c["status"] == "ok")
        counts = Counter(c["status"] for _, c in shown)
        print()
        print(f"COVERAGE  {100 * got / weight:.0f}% of demand weight   "
              f"ok {counts['ok']} | skills-only {counts['SKILLS']} | "
              f"buried {counts['BURIED']} | missing {counts['MISSING']}")


if __name__ == "__main__":
    main()
