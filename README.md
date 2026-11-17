# Data Analyst & BI Skills Tracker

**Live dashboard:** (https://rishikesh-job-skills.streamlit.app/)

**The question:** Which skills and tools do US data analyst and BI job postings actually ask for, and how does that change with salary and location?

I'm graduating with an M.S. in Computer Science and targeting data analyst / BI roles, so I built a pipeline that collects real job postings every day and measures what employers ask for, instead of guessing from blog posts.

## How it works

```
Adzuna Jobs API ──► fetch_jobs.py ──► raw/<date>_<term>.json
  (5 exact job phrases,               (untouched copy of each response)
   up to 4 pages each)
                                            │
                                            ▼
                                       load_jobs.py ──► PostgreSQL (Neon)
                                       (flatten JSON,     jobs ◄── job_skills ──► skills
                                        skip duplicates)
                                            │
                                            ▼
                                     extract_skills.py
                                     (regex skill dictionary,
                                      title vs. description)
                                            │
                                            ▼
                              queries/*.sql      app.py (Streamlit dashboard)

GitHub Actions runs fetch → load → extract every day at 11:00 UTC.
```

**Stack:** Python (requests, pandas), PostgreSQL on Neon, SQL (CTEs, window functions, self-joins, conditional aggregation), Streamlit + Altair, GitHub Actions.

## Key findings

*(Fill these in from `python run_query.py queries/...`. Use your real numbers.)*

- **[FILL IN]** was the most requested skill, mentioned in **[X]%** of postings (description mentions only, to remove search-term bias).
- **[FILL IN]** and **[FILL IN]** were the skills most often requested together (`06_skill_pairs.sql`).
- Postings mentioning **[FILL IN]** had the highest median posted salary (**$[X]**), among skills with at least 10 salaried postings (`05_salary_by_skill.sql`).
- **[X]%** of postings came from **[FILL IN state]** (`07_jobs_by_state.sql`).

## Data quality: problems I found and how I handled them

1. **The first search returned the wrong jobs.** My first run found SQL in only 1 of 50 "data analyst" postings, which couldn't be right. Investigating the titles showed the API's keyword search matched "data" and "analyst" separately, pulling in unrelated analyst roles. I switched to exact-phrase search across five role titles. The share of postings with at least one detectable skill went from 12% to [FILL IN, from 01_overview.sql]%.
2. **Descriptions are cut at 500 characters.** The API only returns the start of each description, which is usually the company intro, so skills listed further down are missed. I report counts as lower bounds, search titles as well as descriptions, and state the limitation on the dashboard.
3. **Selection bias from my own search terms.** "Power BI developer" is one of the search terms, so Power BI appears in many titles by design. I track where each match was found (title, description, or both). `03_title_vs_description.sql` shows [FILL IN]% of Power BI matches came only from titles, and the dashboard has a toggle to count description mentions only.
4. **Duplicates.** The same posting can match several search terms and reappear on later days. Adzuna's job id is the primary key, and inserts use `ON CONFLICT DO NOTHING`.
5. **Estimated salaries.** Adzuna estimates salaries for postings that don't list one. Salary analysis uses only employer-posted salaries, excludes values under $15,000 (likely hourly rates), and only shows skills with at least 10 salaried postings.
6. **Keyword matching errors.** "Excel" as a verb can be counted as the Excel skill; "Spark" is matched only as PySpark/Apache Spark to avoid the verb, so some Spark postings are missed. Next step below.

## Repository structure

| File | What it does |
|---|---|
| `fetch_jobs.py` | Calls the Adzuna API and saves raw JSON |
| `schema.sql`, `create_tables.py` | Defines and creates the three tables |
| `load_jobs.py` | Flattens JSON and loads it into Postgres without duplicates |
| `skills_dictionary.py`, `extract_skills.py` | Keyword skill extraction |
| `queries/*.sql`, `run_query.py` | The SQL analysis behind the findings |
| `app.py` | Streamlit dashboard |
| `.github/workflows/daily_refresh.yml` | Daily automated refresh |
| `db.py` | Shared database connection |

## Run it locally

1. `python -m venv venv` and activate it, then `pip install -r requirements.txt`
2. Create `.env` with `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` (free key from developer.adzuna.com) and `DATABASE_URL` (any Postgres; I use Neon's free tier)
3. `python create_tables.py`, `python fetch_jobs.py`, `python load_jobs.py`, `python extract_skills.py`
4. `streamlit run app.py`

## Next steps

- Compare keyword extraction with LLM-based extraction, measured against ~50 postings I label by hand.
- Group titles into seniority levels (junior / mid / senior) and compare skills by level.

## How I built this

[Optional, edit in your own words. Suggested:] I used Claude as a coding assistant. I defined the question and scope, set up the database and secrets, ran and debugged the pipeline, investigated the data quality problems above with SQL, and decided how to handle each one.

Job data provided by [Adzuna](https://www.adzuna.com).
