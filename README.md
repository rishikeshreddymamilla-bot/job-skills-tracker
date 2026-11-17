# Data Analyst & BI Skills Tracker

**Live dashboard:** https://rishikesh-job-skills.streamlit.app/

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

*Based on 1,371 postings collected Nov 10–17, 2026. Numbers update as the daily refresh adds postings.*

- **Power BI** was the most mentioned tool, in **22%** of postings (counting description mentions only). This is partly built in, because "Power BI developer" is one of the five search terms (see data quality #3).
- **SQL** was the most mentioned skill that isn't tied to a search term, in **9%** of postings. That's certainly an undercount, since the API cuts descriptions at 500 characters and requirements usually come later in a posting.
- The most common pairing was **Power BI + data visualization/dashboards** (129 postings), followed by **SQL + Power BI** (78 postings).
- Only 328 postings (24%) listed a real salary. Among skills with at least 10 of them, postings mentioning **Power BI** had the highest median posted salary (**$123,026**, 48 postings), followed by SQL ($109,000) and Python ($108,250). Power BI developer roles tend to be more technical, so this reflects the role mix as much as the skill itself.
- Jobs are spread widely: no single state has more than 8% of postings. **Virginia** had the most (**8.0%**, 109 postings), ahead of Texas (7.6%) and California (6.1%); 8.5% didn't specify a state.

## Data quality: problems I found and how I handled them

1. **The first search returned the wrong jobs.** My first run found SQL in only 1 of 50 "data analyst" postings, which couldn't be right. Investigating the titles showed the API's keyword search matched "data" and "analyst" separately, pulling in unrelated analyst roles. I switched to exact-phrase search across five role titles. The share of postings with at least one detectable skill went from 12% to 41%.
2. **Descriptions are cut at 500 characters.** The API only returns the start of each description, which is usually the company intro, so skills listed further down are missed. I report counts as lower bounds, search titles as well as descriptions, and state the limitation on the dashboard.
3. **Selection bias from my own search terms, and a hypothesis that turned out wrong.** "Power BI developer" is one of the search terms, so I expected Power BI's count to come mostly from job titles. I tracked where each match was found to test this. Only 10.6% of Power BI matches came from the title alone; most (197 of 339) mentioned it in both title and description. So filtering to description mentions barely changes the count, because the search itself selects postings that talk about Power BI. The right fix is to record which search term found each posting and compare skills within each term; that's the next improvement.
4. **Duplicates.** The same posting can match several search terms and reappear on later days. Adzuna's job id is the primary key, and inserts use `ON CONFLICT DO NOTHING`.
5. **Estimated salaries.** Adzuna estimates salaries for postings that don't list one. Salary analysis uses only employer-posted salaries, excludes values under $15,000 (likely hourly rates), and only shows skills with at least 10 salaried postings. Only 4 skills meet that bar so far.
6. **Keyword matching errors.** "Excel" as a verb can be counted as the Excel skill; "Spark" is matched only as PySpark/Apache Spark to avoid the verb, so some Spark postings are missed. "Data visualization" includes the word "dashboard", which is broad.

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

- Store which search term found each posting, so skill demand can be compared within each role and the search-term bias measured properly.
- Compare keyword extraction with LLM-based extraction, measured against ~50 postings I label by hand.
- Group titles into seniority levels (junior / mid / senior) and compare skills by level.

## How I built this

I used Claude as a coding assistant, and it wrote most of the code. I defined the question and scope, chose the data source, set up the Neon database, API keys and secrets, ran, debugged and deployed the pipeline, investigated the data quality problems above with SQL, and decided how to handle each one.

Job data provided by [Adzuna](https://www.adzuna.com).