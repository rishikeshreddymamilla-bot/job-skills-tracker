"""Ask Gemini which skills each of the 50 evaluation postings mentions, and save the answers.

Run:  python llm_extract.py                          (uses gemini-3.8-flash)
      python llm_extract.py gemini-3.5-flash-lite    (lighter model, if the default is overloaded)
Needs GEMINI_API_KEY in .env, and a labeled (or at least created) eval/label_sheet.xlsx.
Safe to re-run: postings that already have an answer are skipped.
"""
import csv
import json
import os
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from eval_utils import SKILL_NAMES, load_sheet

DEFAULT_MODEL = "gemini-3.8-flash"   # free tier on Google AI Studio (check aistudio.google.com if it's ever renamed)
SECONDS_BETWEEN_CALLS = 7       # free tier allows only a few requests per minute; this keeps us under it
MAX_ATTEMPTS = 5
REQUEST_TIMEOUT_SECONDS = 120    # give up on a single request after this long, then retry (without it, a call can hang forever)
OUT_PATH = "eval/llm_results.csv"
FIELDS = ["job_id", "model", "llm_skills", "input_tokens", "output_tokens", "seconds"]

# The model gets the SAME rules you followed when labeling, so the comparison is fair.
INSTRUCTIONS = """You are labeling job postings for a skills study.
Read ONLY the job title and description below, and return the skills from the allowed list
that the posting clearly asks for or uses.

Rules:
- Count a skill only if the job clearly asks for or uses it. "Excel in a fast-paced environment" is NOT Excel.
- Clear variations count: PowerBI = Power BI, T-SQL = SQL, Postgres = PostgreSQL.
- SQL databases count as SQL too: a posting asking for MySQL gets both MySQL and SQL.
- Dashboards, reports or visualizations count as Data Visualization.
- "Spreadsheets" alone is not Excel.
- A skill named in the job title counts (a "Power BI Developer" title means Power BI).
- But don't infer skills the text doesn't name: a "Data Analyst" title alone does NOT mean SQL.
- Only count skills the job itself needs. A skill mentioned only in the company description
  (for example "we are a Microsoft Azure partner") does not count.
- If no listed skill is mentioned, return an empty list.
"""

# Structured output: Gemini must answer with {"skills": [...]}, choosing only from our 22 names.
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {"skills": {"type": "ARRAY", "items": {"type": "STRING", "enum": SKILL_NAMES}}},
    "required": ["skills"],
}


class GeminiUnavailable(Exception):
    """Gemini kept answering 'overloaded' or 'timed out' after every retry."""


def ask_gemini(client, model, title, description):
    """One API call, retried on rate limits and server errors. Returns (skills, input_tokens, output_tokens)."""
    prompt = f"{INSTRUCTIONS}\nTitle: {title}\nDescription: {description}"
    config = types.GenerateContentConfig(
        temperature=0,                       # same input -> same answer, as far as possible
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
    )
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            skills = json.loads(response.text).get("skills", [])
            usage = response.usage_metadata
            input_tokens = (usage.prompt_token_count or 0) if usage else 0
            # Gemini bills "thinking" tokens as output, so count them too.
            output_tokens = ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else 0
            return skills, input_tokens, output_tokens
        except errors.APIError as e:
            retryable = e.code == 429 or (e.code or 0) >= 500
            if not retryable:
                raise
            if attempt == MAX_ATTEMPTS:
                raise GeminiUnavailable(f"API error {e.code} on every attempt") from e
            wait = 30 * attempt
            print(f"   API error {e.code}, waiting {wait}s and retrying (attempt {attempt}/{MAX_ATTEMPTS})", flush=True)
            time.sleep(wait)
        except json.JSONDecodeError:
            if attempt == MAX_ATTEMPTS:
                raise
            print("   Couldn't read the answer as JSON, retrying", flush=True)
        except Exception as e:
            # Network problems: timeouts, dropped connections, Wi-Fi blips.
            if attempt == MAX_ATTEMPTS:
                raise GeminiUnavailable(f"{type(e).__name__} on every attempt") from e
            print(f"   {type(e).__name__}: {e}. Waiting 15s and retrying (attempt {attempt}/{MAX_ATTEMPTS})", flush=True)
            time.sleep(15)


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not found. Add it to your .env file.")

    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    postings, _ = load_sheet()
    print(f"{len(postings)} postings in the evaluation set. Using model {model}.", flush=True)

    # Skip postings that already have an answer, so a crash or rate limit doesn't mean starting over.
    done = set()
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        # All 50 answers must come from ONE model, or the comparison is mixed.
        if rows and "model" not in rows[0]:
            raise SystemExit(f"{OUT_PATH} is from an older version of this script. Delete it and run again.")
        used = {row["model"] for row in rows}
        if used and used != {model}:
            raise SystemExit(f"{OUT_PATH} already has answers from {', '.join(sorted(used))}. To switch to {model}, "
                             f"delete {OUT_PATH} first so all 50 answers come from the same model.")
        done = {row["job_id"] for row in rows}
        print(f"{len(done)} already done, skipping those.")
    todo = [p for p in postings if p["job_id"] not in done]

    client = genai.Client(api_key=api_key,
                          http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_SECONDS * 1000))
    new_file = not os.path.exists(OUT_PATH)
    with open(OUT_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()

        for i, p in enumerate(todo, start=1):
            print(f"[{i}/{len(todo)}] asking Gemini about job {p['job_id']}...", flush=True)
            start = time.time()
            try:
                skills, input_tokens, output_tokens = ask_gemini(client, model, p["title"], p["description"])
            except GeminiUnavailable as e:
                print(f"\nStopped: Gemini isn't responding right now ({e}). This is on Google's side, usually")
                print("because the free tier is busy. Your progress is saved. Options:")
                print("  - try again later:        python llm_extract.py")
                print("  - or use a lighter model: delete eval/llm_results.csv, then run")
                print("                            python llm_extract.py gemini-3.5-flash-lite")
                raise SystemExit(1)
            seconds = round(time.time() - start, 2)
            skills = sorted({s for s in skills if s in SKILL_NAMES})   # belt and braces: keep only known names
            writer.writerow({
                "job_id": p["job_id"],
                "model": model,
                "llm_skills": ";".join(skills),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "seconds": seconds,
            })
            f.flush()   # save each answer immediately
            print(f"   found: {', '.join(skills) or '(none)'}  ({seconds}s)", flush=True)
            if i < len(todo):
                time.sleep(SECONDS_BETWEEN_CALLS)

    print(f"Done. Answers saved to {OUT_PATH}. Next: python evaluate.py")


if __name__ == "__main__":
    main()
