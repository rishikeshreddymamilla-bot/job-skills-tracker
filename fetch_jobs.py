import os, json, datetime
import requests
from dotenv import load_dotenv
url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
load_dotenv()
app_id = os.getenv("ADZUNA_APP_ID")
app_key = os.getenv("ADZUNA_APP_KEY")

params = {"app_id": app_id, "app_key": app_key, "what": "data analyst", "results_per_page": 50}
response = requests.get(url, params=params)
response.raise_for_status()
data = response.json()
today = datetime.date.today().isoformat()
path = f"raw/{today}.json"
os.makedirs("raw", exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print(f"Saved {len(data['results'])} jobs to {path}")