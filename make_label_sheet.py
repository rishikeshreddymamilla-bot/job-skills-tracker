import os

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from db import get_connection
from skills_dictionary import SKILLS

SAMPLE_QUERY = "queries/10_eval_sample.sql"
OUT_PATH = "eval/label_sheet.xlsx"

# Never overwrite an existing sheet: the query picks a NEW random sample each run,
# so overwriting would throw away your labels.
if os.path.exists(OUT_PATH):
    raise SystemExit(f"{OUT_PATH} already exists. Rename or delete it first if you really want a new sample.")

with open(SAMPLE_QUERY, encoding="utf-8") as f:
    sql = f.read()

conn = get_connection()
cur = conn.cursor()
cur.execute(sql)
rows = cur.fetchall()
cur.close()
conn.close()

if len(rows) != 50:
    print(f"Warning: expected 50 postings, got {len(rows)}.")

skill_names = [s["name"] for s in SKILLS]

wb = Workbook()
ws = wb.active
ws.title = "labels"

# Header: job info, then one column per skill, then notes.
headers = ["job_id", "title", "description"] + skill_names + ["notes"]
ws.append(headers)
for job_id, title, description in rows:
    clean_description = " ".join((description or "").split())
    ws.append([job_id, title, clean_description] + [None] * len(skill_names) + [None])

last_row = len(rows) + 1
first_skill_col = 4
last_skill_col = 3 + len(skill_names)
notes_col = last_skill_col + 1

# Layout: readable description, narrow skill columns with vertical headers, frozen header + job columns.
ws.column_dimensions["A"].width = 12
ws.column_dimensions["B"].width = 28
ws.column_dimensions["C"].width = 70
for col in range(first_skill_col, notes_col):
    ws.column_dimensions[ws.cell(1, col).column_letter].width = 4.5
ws.column_dimensions[ws.cell(1, notes_col).column_letter].width = 35

for cell in ws[1]:
    cell.font = Font(bold=True)
    cell.alignment = Alignment(vertical="bottom", wrap_text=True)
for col in range(first_skill_col, notes_col):
    ws.cell(1, col).alignment = Alignment(text_rotation=90, horizontal="center")
ws.row_dimensions[1].height = 120

for row in ws.iter_rows(min_row=2, max_row=last_row):
    for cell in row:
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    for cell in row[first_skill_col - 1:last_skill_col]:
        cell.alignment = Alignment(horizontal="center", vertical="top")

ws.freeze_panes = "D2"

# Skill cells only accept 1 (or blank), and turn green when filled.
first_letter = ws.cell(2, first_skill_col).column_letter
last_letter = ws.cell(2, last_skill_col).column_letter
skill_range = f"{first_letter}2:{last_letter}{last_row}"
dv = DataValidation(type="whole", operator="equal", formula1="1", allow_blank=True,
                    error="Type 1 if the posting mentions this skill, or leave it blank.",
                    errorTitle="Use 1 or blank")
ws.add_data_validation(dv)
dv.add(skill_range)
ws.conditional_formatting.add(skill_range, CellIsRule(operator="equal", formula=["1"],
                              fill=PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")))

# A second sheet with the labeling rules, so they're in front of you while you work.
rules = wb.create_sheet("rules")
for line in [
    "Put 1 under a skill if the posting clearly asks for or uses it. Leave blank otherwise.",
    "Use only the title and description in this sheet. Don't open the real posting.",
    "'Excel in a fast-paced environment' is NOT Excel. Clear variations count: PowerBI = Power BI, T-SQL = SQL, Postgres = PostgreSQL.",
    "SQL databases count as SQL too: MySQL means 1 under MySQL AND 1 under SQL.",
    "Dashboards, reports or visualizations count as Data Visualization.",
    "'Spreadsheets' alone is not Excel: leave blank and write it in notes.",
    "No skills at all? Leave the whole row blank. That's a valid answer.",
    "Unsure? Decide, and write why in notes. Consistency matters more than perfection.",
    "Label blind: don't look at what the regex found first.",
]:
    rules.append([line])
rules.column_dimensions["A"].width = 120

os.makedirs("eval", exist_ok=True)
wb.save(OUT_PATH)
print(f"Wrote {len(rows)} postings to {OUT_PATH}. Open it in Excel and type 1 under each skill a posting mentions.")
