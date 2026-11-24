"""Fair second look at the labels: every case where your label, the regex and the LLM don't all agree,
WITHOUT showing which method said what, so the review can't lean toward either one.

Run:  python make_review_list.py
Writes eval/review_list.xlsx (contains posting text, keep it off GitHub).
For each row, decide from the text and the labeling rules whether the job asks for that skill,
then make your label sheet match your decision.
"""
import csv
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from eval_utils import SKILL_NAMES, load_sheet, regex_skills

LLM_PATH = "eval/llm_results.csv"
OUT_PATH = "eval/review_list.xlsx"

if not os.path.exists(LLM_PATH):
    raise SystemExit("Run llm_extract.py first, so both methods can be reviewed equally.")

postings, problems = load_sheet()
if problems:
    raise SystemExit("Fix the label sheet first: " + "; ".join(problems))
with open(LLM_PATH, newline="", encoding="utf-8") as f:
    llm = {r["job_id"]: set(filter(None, r["llm_skills"].split(";"))) for r in csv.DictReader(f)}

wb = Workbook()
ws = wb.active
ws.title = "review"
ws.append(["job_id", "title", "description", "skill", "your current label",
           "your decision (1 = job asks for it, blank = no)"])
count = 0
for p in postings:
    if p["job_id"] not in llm:
        continue
    regex = regex_skills(p["title"], p["description"])
    for skill in SKILL_NAMES:
        votes = {skill in p["labels"], skill in regex, skill in llm[p["job_id"]]}
        if len(votes) > 1:   # not everyone agrees
            ws.append([str(p["job_id"]), p["title"], p["description"], skill,
                       1 if skill in p["labels"] else None, None])
            count += 1

for i, width in enumerate([14, 28, 80, 18, 12, 22], start=1):
    ws.column_dimensions[ws.cell(1, i).column_letter].width = width
for cell in ws[1]:
    cell.font = Font(bold=True)
    cell.alignment = Alignment(wrap_text=True, vertical="bottom")
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = Alignment(vertical="top", wrap_text=True)
ws.freeze_panes = "A2"

rules = wb.create_sheet("rules")
for line in [
    "Decide each row from the text and these rules only. The sheet doesn't say which method found what, on purpose.",
    "A skill counts if the JOB clearly asks for or uses it. A skill named only in the company description doesn't count.",
    "A skill named in the title counts ('Power BI Developer' means Power BI). A title alone doesn't imply other skills.",
    "'Excel in a fast-paced environment' is NOT Excel. Lowercase 'excel' used as the tool IS Excel.",
    "Clear variations count: PowerBI = Power BI, T-SQL = SQL, Postgres = PostgreSQL.",
    "SQL databases count as SQL too: MySQL or PostgreSQL means SQL as well.",
    "Dashboards, reports or visualizations count as Data Visualization. 'Spreadsheets' alone is not Excel.",
    "Then copy each decision into eval/label_sheet.xlsx, save it, and re-run python evaluate.py.",
]:
    rules.append([line])
rules.column_dimensions["A"].width = 120

wb.save(OUT_PATH)
print(f"{count} cases to review, written to {OUT_PATH}.")
