"""Score the regex and the LLM against your hand labels: precision, recall and F1, overall and per skill.

Run:  python evaluate.py
Reads eval/label_sheet.xlsx (your labels) and eval/llm_results.csv (from llm_extract.py).
Writes small result files to eval/ that contain no posting text, so they're safe to put on GitHub.
"""
import csv
import os
import time

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from eval_utils import SKILL_NAMES, load_sheet, regex_matches, regex_skills

LLM_PATH = "eval/llm_results.csv"

# Paid-tier prices per 1M tokens (input, output), from Google AI Studio's pricing page, Nov 2026.
# Gemini 3.8 Flash is $0.75 / $3.75 until Dec 31, 2026, then $1.50 / $7.50; we use the later, standard price.
PRICES_PER_M = {
    "gemini-3.8-flash": (1.50, 7.50),
    "gemini-3.5-flash-lite": (0.30, 2.50),
}
MIN_EXAMPLES_PER_SKILL = 5   # per-skill scores from fewer labeled postings than this are too noisy to trust


def score(tp, fp, fn):
    """Precision: of what the method found, how much was right. Recall: of what was really there, how much it found."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def compare(postings, predictions, method):
    """Count true positives, false positives and misses for every (posting, skill) pair."""
    totals = {"tp": 0, "fp": 0, "fn": 0}
    per_skill = {s: {"tp": 0, "fp": 0, "fn": 0} for s in SKILL_NAMES}
    errors = []
    for p in postings:
        truth = p["labels"]
        found = predictions[p["job_id"]]
        for skill in SKILL_NAMES:
            if skill in found and skill in truth:
                kind = "tp"
            elif skill in found:
                kind = "fp"
                errors.append({"method": method, "job_id": p["job_id"], "skill": skill, "error": "false positive"})
            elif skill in truth:
                kind = "fn"
                errors.append({"method": method, "job_id": p["job_id"], "skill": skill, "error": "missed"})
            else:
                continue
            totals[kind] += 1
            per_skill[skill][kind] += 1
    return totals, per_skill, errors


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_review_workbook(postings, errors, path="eval/errors_review.xlsx"):
    """Local-only file (contains posting text, so it's gitignored): every mistake next to the text that caused it."""
    by_id = {p["job_id"]: p for p in postings}
    wb = Workbook()
    ws = wb.active
    ws.title = "mistakes"
    ws.append(["method", "error", "skill", "regex matched on", "regex matched words",
               "job_id", "title", "description", "your labels", "your notes"])
    for e in errors:
        p = by_id[e["job_id"]]
        where, words = regex_matches(p["title"], p["description"]).get(e["skill"], ("", ""))
        ws.append([e["method"], e["error"], e["skill"],
                   where if e["method"] == "Regex" else "", words if e["method"] == "Regex" else "",
                   str(e["job_id"]), p["title"], p["description"],
                   ", ".join(sorted(p["labels"])), p["notes"]])
    widths = [14, 14, 18, 14, 18, 14, 30, 80, 28, 30]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


def main():
    postings, problems = load_sheet()
    if problems:
        print("Fix these cells in the label sheet first:")
        for problem in problems:
            print("  ", problem)
        raise SystemExit(1)

    total_labels = sum(len(p["labels"]) for p in postings)
    if total_labels == 0:
        raise SystemExit("No labels found. Type 1 under each skill a posting mentions in eval/label_sheet.xlsx, save, then re-run.")
    no_skill_postings = sum(1 for p in postings if not p["labels"])

    # Regex: run it on the exact same frozen text, and time it.
    start = time.time()
    regex_preds = {p["job_id"]: regex_skills(p["title"], p["description"]) for p in postings}
    regex_seconds = (time.time() - start) / len(postings)

    methods = {"Regex": regex_preds}
    llm_cost_per_1000 = llm_seconds = None
    if os.path.exists(LLM_PATH):
        with open(LLM_PATH, newline="", encoding="utf-8") as f:
            llm_rows = {row["job_id"]: row for row in csv.DictReader(f)}
        missing = [p["job_id"] for p in postings if p["job_id"] not in llm_rows]
        if missing:
            print(f"Warning: no LLM answer yet for {len(missing)} postings. Re-run llm_extract.py to finish them.")
            print("Scoring both methods on the postings the LLM has answered, so the comparison stays fair.\n")
            postings = [p for p in postings if p["job_id"] in llm_rows]
        used = [llm_rows[p["job_id"]] for p in postings]
        models = {r.get("model", "gemini-3.8-flash") for r in used}
        if len(models) > 1:
            raise SystemExit(f"eval/llm_results.csv mixes models ({', '.join(sorted(models))}). "
                             "Delete it and re-run llm_extract.py with one model.")
        model = models.pop()
        methods[f"LLM ({model})"] = {
            jid: set(filter(None, row["llm_skills"].split(";"))) for jid, row in llm_rows.items()
        }
        avg_in = sum(int(r["input_tokens"]) for r in used) / len(used)
        avg_out = sum(int(r["output_tokens"]) for r in used) / len(used)
        in_price, out_price = PRICES_PER_M.get(model, (None, None))
        if in_price is None:
            print(f"Note: no price listed for {model} in evaluate.py, so cost shows as 0. Add it to PRICES_PER_M.")
            in_price = out_price = 0.0
        llm_cost_per_1000 = 1000 * (avg_in * in_price + avg_out * out_price) / 1_000_000
        llm_seconds = sum(float(r["seconds"]) for r in used) / len(used)
    else:
        print("No LLM results yet (run llm_extract.py). Scoring the regex only.\n")

    summary_rows, skill_rows, all_errors = [], {s: {"skill": s} for s in SKILL_NAMES}, []
    for method, preds in methods.items():
        totals, per_skill, errors = compare(postings, preds, method)
        precision, recall, f1 = score(**totals)
        is_llm = method != "Regex"
        summary_rows.append({
            "method": method,
            "postings": len(postings),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "true_positives": totals["tp"],
            "false_positives": totals["fp"],
            "missed": totals["fn"],
            "seconds_per_posting": round(llm_seconds if is_llm else regex_seconds, 4),
            "cost_per_1000_postings_usd": round(llm_cost_per_1000, 4) if is_llm else 0.0,
        })
        for skill, counts in per_skill.items():
            support = counts["tp"] + counts["fn"]
            skill_rows[skill]["labeled_postings"] = support
            skill_rows[skill][f"{method} F1"] = round(score(**counts)[2], 3) if support or counts["fp"] else ""
            skill_rows[skill][f"{method} false positives"] = counts["fp"]
            skill_rows[skill][f"{method} missed"] = counts["fn"]
        all_errors.extend(errors)

    # Save results (no posting text, so these can go on GitHub).
    write_csv("eval/results_summary.csv", summary_rows, list(summary_rows[0].keys()))
    skill_list = sorted(skill_rows.values(), key=lambda r: -r["labeled_postings"])
    write_csv("eval/per_skill.csv", skill_list, list(skill_list[0].keys()))
    write_csv("eval/errors.csv", all_errors, ["method", "job_id", "skill", "error"])
    write_review_workbook(postings, all_errors)
    write_csv("eval/labels.csv",
              [{"job_id": p["job_id"], "true_skills": ";".join(sorted(p["labels"]))} for p in postings],
              ["job_id", "true_skills"])

    # Print a readable report.
    print(f"Evaluation set: {len(postings)} postings, {total_labels} labeled skill mentions, "
          f"{no_skill_postings} postings with no listed skill.\n")
    width = max(len(r["method"]) for r in summary_rows) + 2
    print(f"{'Method':<{width}}{'Precision':>10}{'Recall':>9}{'F1':>7}{'FP':>5}{'Missed':>8}{'$/1,000':>10}")
    for r in summary_rows:
        print(f"{r['method']:<{width}}{r['precision']:>10.3f}{r['recall']:>9.3f}{r['f1']:>7.3f}"
              f"{r['false_positives']:>5}{r['missed']:>8}{r['cost_per_1000_postings_usd']:>10.4f}")

    print(f"\nPer skill (only skills with at least {MIN_EXAMPLES_PER_SKILL} labeled postings; fewer is too noisy):")
    for r in skill_list:
        if r["labeled_postings"] >= MIN_EXAMPLES_PER_SKILL:
            scores = "  ".join(f"{m} F1 {r[m + ' F1']}" for m in methods)
            print(f"  {r['skill']:<20} {r['labeled_postings']:>3} labeled   {scores}")

    print("\nSaved: eval/results_summary.csv, eval/per_skill.csv, eval/errors.csv, eval/labels.csv")
    print("Open eval/errors_review.xlsx next: every mistake next to the posting text that caused it.")
    print("(Don't open and re-save the .csv files in Excel: it turns long job IDs into 5.96E+09 and breaks them.)")


if __name__ == "__main__":
    main()
