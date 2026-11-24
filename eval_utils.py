"""Shared helpers for the evaluation: read the frozen label sheet, and run the regex extractor."""
import os
import re

from openpyxl import load_workbook

from skills_dictionary import SKILLS

SHEET_PATH = "eval/label_sheet.xlsx"
SKILL_NAMES = [s["name"] for s in SKILLS]


def load_sheet(path=SHEET_PATH):
    """Return one dict per posting: job_id, title, description, and the set of skills you marked with 1.

    The posting text comes from the sheet itself (a frozen copy), not the database,
    so the test stays the same even if the database is reset or Adzuna changes a posting.
    """
    if not os.path.exists(path):
        raise SystemExit(f"{path} not found. Run python make_label_sheet.py first.")
    wb = load_workbook(path, data_only=True)
    ws = wb["labels"]
    header = [c.value for c in ws[1]]
    postings, problems = [], []
    for row_number, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        record = dict(zip(header, row))
        if record.get("job_id") is None:
            continue
        labels = set()
        for skill in SKILL_NAMES:
            value = record.get(skill)
            if value in (None, ""):
                continue
            if str(value).strip() in ("1", "1.0"):
                labels.add(skill)
            else:
                problems.append(f"row {row_number}, {skill}: '{value}' is not 1 or blank")
        postings.append({
            "job_id": str(record["job_id"]),
            "title": record.get("title") or "",
            "description": record.get("description") or "",
            "labels": labels,
            "notes": record.get("notes") or "",
        })
    return postings, problems


_compiled = [
    (s["name"], [re.compile(p, 0 if s.get("case_sensitive") else re.IGNORECASE) for p in s["patterns"]])
    for s in SKILLS
]


def regex_skills(title, description):
    """Same logic as extract_skills.py: a skill counts if any of its patterns appears in the title or description."""
    return set(regex_matches(title, description))


def regex_matches(title, description):
    """For each skill the regex finds: where it matched ('title', 'description' or 'both') and the matched words."""
    found = {}
    for name, patterns in _compiled:
        in_title = [m.group(0) for p in patterns for m in [p.search(title or "")] if m]
        in_desc = [m.group(0) for p in patterns for m in [p.search(description or "")] if m]
        if in_title or in_desc:
            where = "both" if in_title and in_desc else "title" if in_title else "description"
            found[name] = (where, ", ".join(sorted(set(in_title + in_desc))))
    return found
