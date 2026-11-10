import os, json, datetime, time
import requests
from dotenv import load_dotenv

load_dotenv()
app_id = os.getenv("ADZUNA_APP_ID")
app_key = os.getenv("ADZUNA_APP_KEY")
if app_id is None or app_key is None:
    raise SystemExit("Adzuna keys not found. Check your .env file.")

# Exact job phrases we care about. Each is searched separately.
SEARCH_TERMS = [
    "data analyst",
    "business intelligence analyst",
    "bi analyst",
    "reporting analyst",
    "power bi developer",
]
PAGES_PER_TERM = 4  # 4 pages x 50 = up to 200 jobs per term

today = datetime.date.today().isoformat()
os.makedirs("raw", exist_ok=True)

for term in SEARCH_TERMS:
    all_results = []

    for page in range(1, PAGES_PER_TERM + 1):
        url = f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what_phrase": term,      # exact phrase, not loose keyword matching
            "results_per_page": 50,   # Adzuna's maximum
        }
        response = requests.get(url, params=params)
        response.raise_for_status()

        results = response.json().get("results", [])
        all_results.extend(results)

        if len(results) < 50:
            break  # fewer than a full page means we've reached the end
        time.sleep(1)  # be polite to the API between calls

    slug = term.replace(" ", "_")
    path = f"raw/{today}_{slug}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"search_term": term, "results": all_results}, f, indent=2)
    print(f"{term}: saved {len(all_results)} jobs to {path}")
