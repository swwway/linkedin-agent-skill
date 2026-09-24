#!/usr/bin/env python3
"""
ats_check.py - scan a resume for what gets it dropped or buried by an
applicant tracking system before a person ever reads it.

What this is:  deterministic checks for the documented parser failure modes -
tables, text boxes, multi-column sections and header/footer content in .docx,
icon-font and broken-glyph characters, missing contact lines, non-standard
section headings, mixed date formats - plus the bullet-level problems a
recruiter's first scan punishes: no number, weak opener, filler, cliche.

What this is NOT:  Workday, Greenhouse, Lever, iCIMS or Taleo. It does not call
them and it cannot promise their verdict. It checks the failure modes they
are known to share. Everything runs locally. Nothing is uploaded.

Usage
  python3 ats_check.py resume.docx
  python3 ats_check.py resume.md --never "AI agents,LLM"
  pbpaste | python3 ats_check.py -
  python3 ats_check.py resume.docx --json
  python3 ats_check.py resume.pdf --text      # print what a parser would read
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"

# ----------------------------------------------------------------- vocabulary

SECTIONS = {
    "summary": ["summary", "professional summary", "profile", "professional profile",
                "about", "about me", "objective", "career objective",
                "summary of qualifications", "о себе", "обо мне", "профиль",
                "цель", "краткое резюме"],
    "experience": ["experience", "work experience", "professional experience",
                   "relevant experience", "employment", "employment history",
                   "work history", "career history", "опыт", "опыт работы",
                   "профессиональный опыт", "места работы", "трудовой опыт"],
    "projects": ["projects", "personal projects", "selected projects",
                 "side projects", "pet projects", "проекты", "pet-проекты",
                 "личные проекты", "избранные проекты"],
    "skills": ["skills", "technical skills", "core skills", "key skills",
               "hard skills", "skills and tools", "tools", "tech stack", "stack",
               "technologies", "навыки", "ключевые навыки", "профессиональные навыки",
               "стек", "технический стек", "технологии", "инструменты"],
    "education": ["education", "education and training", "образование"],
    "certifications": ["certifications", "certificates", "licenses",
                       "courses", "сертификаты", "курсы", "повышение квалификации"],
    "languages": ["languages", "языки", "знание языков", "иностранные языки"],
    "awards": ["awards", "achievements", "honors", "награды", "достижения"],
    "publications": ["publications", "talks", "публикации", "выступления"],
    "volunteering": ["volunteering", "volunteer experience", "волонтерство"],
}
HEADING_LOOKUP = {h: key for key, names in SECTIONS.items() for h in names}

WEAK_OPENERS = re.compile(
    r"^(responsible for|helped|helping|assisted|assisting|worked on|working on|"
    r"participated|involved in|tasked with|duties included|in charge of|"
    r"handled|supported|отвечал|отвечала|помогал|помогала|участвовал|"
    r"участвовала|занимался|занималась|работал над|работала над|выполнял|"
    r"выполняла|осуществлял|осуществляла|в обязанности входило|обязанности)\b",
    re.IGNORECASE)

FIRST_PERSON = re.compile(r"(?<!\w)(i|my|me|я|мой|моя|мои|мне|меня)(?!\w)", re.IGNORECASE)

CLICHES = [
    "results-driven", "results driven", "results-oriented", "team player",
    "hard-working", "hardworking", "detail-oriented", "detail oriented",
    "self-starter", "go-getter", "synergy", "passionate",
    "highly motivated", "self-motivated", "think outside the box", "proven track record",
    "excellent communication skills", "strong communication skills",
    "fast learner", "quick learner", "best of breed", "value add",
    "strategic thinker", "go-to person", "people person",
    "стрессоустойчив", "коммуникабельн", "ответственн", "целеустремлен",
    "целеустремлён", "исполнительн", "обучаем", "нацелен на результат",
    "командный игрок", "пунктуальн", "активная жизненная позиция",
]
FILLER = ["various", "multiple", "different", "successfully", "effectively",
          "several", "numerous", "различные", "различных", "успешно",
          "эффективно", "многочисленные"]

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\d)\+?\d[\d\s().-]{7,}\d(?!\d)")
LINKEDIN = re.compile(r"linkedin\.com/in/", re.IGNORECASE)
WORK_AUTH = re.compile(
    r"seeking (?:the )?right to work|require[sd]? (?:visa )?sponsorship|"
    r"need(?:s|ing)? (?:visa )?sponsorship|visa (?:required|needed)|"
    r"awaiting (?:a )?(?:visa|work permit)|without (?:the )?right to work|"
    r"ищу (?:визу|спонсорство)|нужна виза", re.IGNORECASE)
GITHUB = re.compile(r"github\.com/", re.IGNORECASE)

MONTHS_EN = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
MONTHS_RU = r"(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*"
DATE_STYLES = [
    ("MM/YYYY", re.compile(r"(?<!\d)(?:0?[1-9]|1[0-2])[/.](?:19|20)\d{2}(?!\d)")),
    ("YYYY-MM", re.compile(r"(?<!\d)(?:19|20)\d{2}-(?:0[1-9]|1[0-2])(?!\d)")),
    ("Month YYYY", re.compile(MONTHS_EN + r"\s+(?:19|20)\d{2}", re.IGNORECASE)),
    ("Месяц ГГГГ", re.compile(MONTHS_RU + r"\s+(?:19|20)\d{2}", re.IGNORECASE)),
]
YEAR_RANGE = re.compile(
    r"(?<![\d/.-])(?:19|20)\d{2}\s*[-–—]\s*(?:(?:19|20)\d{2}(?![\d/.-])|present|now|current|"
    r"today|н\.\s?в\.|наст\.? время|настоящее время|по настоящее время)",
    re.IGNORECASE)

BULLET = re.compile(r"^\s*(?:[-*•▪‣◦–·●■►✓✔]|\d{1,2}[.)])\s+")
PUA = re.compile("[-\U000f0000-\U0010ffff]")
EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿⭐⭕⌚-⏿]")
INVISIBLE = re.compile("[​-‏⁠-⁤﻿­]")


# ------------------------------------------------------------------- reading

def _para_text(p):
    # only run content: w:tab inside w:pPr/w:tabs is a tab-stop definition, not text
    parts = []
    for run in p.iter(W + "r"):
        for node in run:
            if node.tag == W + "t" and node.text:
                parts.append(node.text)
            elif node.tag == W + "tab":
                parts.append("\t")
            elif node.tag in (W + "br", W + "cr"):
                parts.append("\n")
    return "".join(parts)


def _walk_paragraphs(elem, out):
    """Collect w:p in reading order, skipping mc:Fallback duplicates."""
    for child in elem:
        if child.tag == MC_FALLBACK:
            continue
        if child.tag == W + "p":
            text = _para_text(child)
            is_list = child.find(W + "pPr/" + W + "numPr") is not None
            style = child.find(W + "pPr/" + W + "pStyle")
            if style is not None and "list" in (style.get(W + "val") or "").lower():
                is_list = True
            for line in text.split("\n"):
                out.append(("- " + line.strip()) if is_list and line.strip() else line)
        else:
            _walk_paragraphs(child, out)


def read_docx(path):
    layout = {"tables": 0, "text_boxes": 0, "images": 0, "columns": 1,
              "header_footer_text": ""}
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
        lines = []
        _walk_paragraphs(root, lines)
        layout["tables"] = len(root.findall(".//" + W + "tbl"))
        layout["text_boxes"] = len(root.findall(".//" + W + "txbxContent"))
        layout["images"] = len(root.findall(".//" + A + "blip")) + \
            len(root.findall(".//{urn:schemas-microsoft-com:vml}imagedata"))
        for cols in root.iter(W + "cols"):
            try:
                layout["columns"] = max(layout["columns"], int(cols.get(W + "num") or 1))
            except ValueError:
                pass
        hf = []
        for name in z.namelist():
            if re.match(r"word/(header|footer)\d*\.xml$", name):
                part = []
                _walk_paragraphs(ET.fromstring(z.read(name)), part)
                hf.extend(l for l in part if l.strip())
        layout["header_footer_text"] = "\n".join(hf)
    return lines, layout


def read_pdf(path):
    try:
        from pypdf import PdfReader  # optional, not required
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except ImportError:
        pass
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-layout", path, "-"],
                              capture_output=True, text=True, check=True).stdout
    raise SystemExit("ats_check: cannot read PDF here (no pypdf, no pdftotext). "
                     "Paste the text, or pass the .docx.")


def strip_markdown(line):
    line = re.sub(r"^\s*#{1,6}\s+", "", line)
    line = re.sub(r"(\*\*|__)(.+?)\1", r"\2", line)
    line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 \2", line)
    return line


def load(path):
    """Return (kind, lines, layout-or-None)."""
    if path == "-":
        return "text", sys.stdin.read().splitlines(), None
    if not os.path.isfile(path):
        raise SystemExit(f"ats_check: no such file: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        lines, layout = read_docx(path)
        return "docx", lines, layout
    if ext == ".pdf":
        return "pdf", read_pdf(path).splitlines(), None
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read().splitlines()
    if ext in (".md", ".markdown"):
        return "markdown", [strip_markdown(l) for l in raw], None
    return "text", raw, None


# -------------------------------------------------------------------- checks

def heading_key(line):
    clean = re.sub(r"[#*_:|]+", " ", line).strip().lower().replace("ё", "е")
    clean = re.sub(r"\s+", " ", clean)
    if not clean or len(clean.split()) > 5:
        return None
    return HEADING_LOOKUP.get(clean)


def looks_like_heading(line):
    s = line.strip()
    if not s or len(s.split()) > 4 or s.endswith("."):
        return False
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and (all(c.isupper() for c in letters) or s.endswith(":"))


def check(kind, lines, layout, never):
    findings = []

    def add(level, area, message, hits=None):
        findings.append({"level": level, "area": area, "message": message,
                         "lines": [{"n": n, "text": t} for n, t in (hits or [])]})

    numbered = [(i + 1, l.strip()) for i, l in enumerate(lines) if l.strip()]
    text = "\n".join(l for _, l in numbered)
    words = len(re.findall(r"\w+", text))

    # layout (docx only)
    if layout:
        if layout["tables"]:
            add("CRITICAL", "layout", f"{layout['tables']} table(s) - many parsers read "
                "cells out of order or drop them. Rebuild as plain paragraphs.")
        if layout["text_boxes"]:
            add("CRITICAL", "layout", f"{layout['text_boxes']} text box(es) - content "
                "inside text boxes is routinely skipped by parsers.")
        if layout["columns"] > 1:
            add("CRITICAL", "layout", f"{layout['columns']}-column section - parsers that "
                "read line by line merge the columns into one scrambled stream.")
        hf = layout["header_footer_text"]
        if hf:
            if EMAIL.search(hf) or PHONE.search(hf):
                add("CRITICAL", "contact", "contact details sit in the page header/footer - "
                    "many parsers never read headers. Move them into the body, line 1-3.")
            else:
                add("WARN", "layout", "text in the page header/footer is often skipped: "
                    + hf.replace("\n", " | ")[:120])
        if layout["images"]:
            add("WARN", "layout", f"{layout['images']} image(s) - parsers ignore them; "
                "a photo is also a rejection risk in the US/UK market.")
    elif kind == "pdf":
        add("INFO", "layout", "PDF layout (columns, tables) cannot be checked here. "
            "Run with --text and read the order the words come out in.")

    # characters
    for name, rx, level, why in [
        ("broken glyphs", PUA, "CRITICAL", "icon-font or subset-font characters in the "
         "Private Use Area - the parser reads them as garbage"),
        ("replacement chars", re.compile("�"), "CRITICAL", "U+FFFD in the text layer - "
         "the file lost characters on export"),
        ("emoji", EMOJI, "WARN", "emoji and pictographs are dropped or mangled"),
        ("invisible chars", INVISIBLE, "WARN", "zero-width or soft-hyphen characters "
         "split keywords so a search for them misses"),
    ]:
        hits = [(n, l) for n, l in numbered if rx.search(l)]
        if hits:
            add(level, "characters", f"{name}: {why}", hits[:6])

    # contact
    top = "\n".join(l for _, l in numbered[:12])
    if not EMAIL.search(text):
        add("CRITICAL", "contact", "no email address in the body text")
    elif not EMAIL.search(top):
        add("WARN", "contact", "email is not in the first lines - put contact details "
            "directly under the name")
    phones = [m.group(0).strip() for m in PHONE.finditer(top)]
    if not PHONE.search(text):
        add("WARN", "contact", "no phone number found")
    elif len(phones) > 1:
        add("INFO", "contact", f"{len(phones)} phone numbers ({', '.join(phones)}) - keep "
            "the one for the country you are applying in")
    trunk = [p for p in phones if re.match(r"\+\s*(44|49|33|39|61|380|7)[\s(]*0", p)]
    if trunk:
        add("WARN", "contact", "international format keeps the trunk 0 (" + ", ".join(trunk)
            + ") - drop the 0 after the country code, e.g. +44 7911 123456")
    visa = [(n, l) for n, l in numbered if WORK_AUTH.search(l)]
    if visa:
        add("WARN", "contact", "work-authorisation line reads as 'needs sponsorship'. "
            "Many forms auto-reject on it. If you already have the right to work, say so "
            "plainly; if you do not, leave it off the CV and answer the form question", visa)
    if not LINKEDIN.search(text):
        add("WARN", "contact", "no linkedin.com/in/ URL")

    # sections
    found, custom = {}, []
    for idx, (n, l) in enumerate(numbered):
        key = heading_key(l)
        if key:
            found.setdefault(key, n)
        elif idx > 2 and looks_like_heading(l):
            custom.append((n, l))
    if "experience" not in found and "projects" not in found:
        add("CRITICAL", "sections", "no Experience heading found - parsers map canonical "
            "names (Experience / Work Experience / Опыт работы) and drop the rest")
    for key in ("skills", "education"):
        if key not in found:
            add("WARN", "sections", f"no {key.capitalize()} heading found")
    if custom:
        add("WARN", "sections", "heading-like lines that match no standard section - "
            "rename to a canonical heading, or ignore if these are job titles", custom[:6])

    # dates
    styles = {}
    for label, rx in DATE_STYLES:
        for n, l in numbered:
            m = rx.search(l)
            if m:
                styles.setdefault(label, (n, m.group(0)))
    year_only = [(n, l) for n, l in numbered if YEAR_RANGE.search(l)]
    if len(styles) > 1:
        add("WARN", "dates", "date formats are mixed - pick one and use it everywhere: "
            + ", ".join(f'{k} ("{v[1]}", L{v[0]})' for k, v in styles.items()))
    if year_only and not styles:
        add("WARN", "dates", "year-only ranges (2021 - 2023) - parsers compute months of "
            "experience from month + year", year_only[:4])

    # length
    pages = words / 500
    if words < 250:
        add("WARN", "length", f"{words} words - thin; most parsers and recruiters expect "
            "350-650 words for one page")
    elif words > 1100:
        add("WARN", "length", f"{words} words - over two pages of text (650-1,100 is the "
            "two-page window)")

    # bullets
    bullets = [(n, BULLET.sub("", l)) for n, l in numbered if BULLET.match(l)]
    if not bullets:
        add("WARN", "bullets", "no bullet lines detected - if the source has bullets they "
            "were lost in the paste; if not, experience written as paragraphs scans badly")
    else:
        no_num = [(n, b) for n, b in bullets if not re.search(r"\d", b)]
        weak = [(n, b) for n, b in bullets if WEAK_OPENERS.match(b)]
        me = [(n, b) for n, b in bullets if FIRST_PERSON.search(b)]
        long_ = [(n, b) for n, b in bullets if len(b) > 220]
        if no_num:
            level = "WARN" if len(no_num) / len(bullets) > 0.4 else "INFO"
            add(level, "bullets", f"{len(no_num)} of {len(bullets)} bullets have no number",
                no_num[:8])
        if weak:
            add("WARN", "bullets", "weak openers - lead with what you did, not that you "
                "were near it", weak[:8])
        if me:
            add("INFO", "bullets", "first person in bullets - drop the pronoun", me[:4])
        if long_:
            add("WARN", "bullets", "bullets over two lines - one idea per bullet", long_[:4])

    # wording
    def term_hits(terms):
        out = []
        for n, l in numbered:
            low = l.lower().replace("ё", "е")
            for t in terms:
                if re.search(r"(?<!\w)" + re.escape(t.replace("ё", "е")), low):
                    out.append((n, f"{t}: {l}"))
        return out
    cl = term_hits(CLICHES)
    if cl:
        add("WARN", "wording", "cliches recruiters skip past - replace with the proof "
            "they stand in for", cl[:8])
    fl = term_hits(FILLER)
    if fl:
        add("INFO", "wording", "filler words - cut them", fl[:6])

    # never-list
    for term in never:
        rx = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)
        hits = [(n, l) for n, l in numbered if rx.search(l)]
        if hits:
            add("CRITICAL", "never-list", f'"{term}" is on your never-list', hits)

    critical = sum(f["level"] == "CRITICAL" for f in findings)
    warns = sum(f["level"] == "WARN" for f in findings)
    verdict = "BLOCKED" if critical else "REVIEW" if warns else "CLEAN"
    return {"format": kind, "words": words, "pages": round(pages, 1),
            "sections": sorted(found, key=found.get), "verdict": verdict,
            "critical": critical, "warnings": warns, "findings": findings}


# -------------------------------------------------------------------- output

def render(name, r):
    out = [f"ATS CHECK  {name}  ({r['format']}, {r['words']} words, ~{r['pages']} pages)", ""]
    for level in ("CRITICAL", "WARN", "INFO"):
        group = [f for f in r["findings"] if f["level"] == level]
        if not group:
            continue
        out.append(level)
        for f in group:
            out.append(f"  {f['area']:<11}{f['message']}")
            for h in f["lines"]:
                t = h["text"] if len(h["text"]) <= 90 else h["text"][:87] + "..."
                out.append(f"  {'':<11}  L{h['n']:<4}{t}")
        out.append("")
    out.append("SECTIONS  " + (", ".join(r["sections"]) or "none recognised"))
    out.append(f"VERDICT   {r['verdict']}  {r['critical']} critical, {r['warnings']} warnings")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Check a resume for ATS parsing and "
                                 "recruiter-scan problems.")
    ap.add_argument("input", help=".docx, .pdf, .md or .txt file, or - for stdin")
    ap.add_argument("--never", default="",
                    help="comma-separated terms that must not appear anywhere")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--text", action="store_true",
                    help="print the extracted text, the order a parser reads it in")
    args = ap.parse_args()

    kind, lines, layout = load(args.input)
    lines = [unicodedata.normalize("NFC", l) for l in lines]
    if args.text:
        print("\n".join(l for l in lines if l.strip()))
        return
    never = [t.strip() for t in args.never.split(",") if t.strip()]
    result = check(kind, lines, layout, never)
    result["file"] = args.input
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render(os.path.basename(args.input) if args.input != "-" else "stdin", result))


if __name__ == "__main__":
    main()
