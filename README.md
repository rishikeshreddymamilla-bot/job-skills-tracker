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

**Stack:** Python (requests, pandas), PostgreSQL on Neon, SQL (CTEs, window functions, self-joins, conditional aggregation), Streamlit + Altair, GitHub Actions, Gemini API (for the extraction test below).

## Key findings

*Based on 1,371 postings collected Nov 10–17, 2026. Numbers update as the daily refresh adds postings.*

- **Power BI** was the most mentioned tool, in **22%** of postings (counting description mentions only). This is partly built in, because "Power BI developer" is one of the five search terms (see data quality #3).
- **SQL** was the most mentioned skill that isn't tied to a search term, in **9%** of postings. That's certainly an undercount, since the API cuts descriptions at 500 characters and requirements usually come later in a posting.
- The most common pairing was **Power BI + data visualization/dashboards** (129 postings), followed by **SQL + Power BI** (78 postings).
- Only 328 postings (24%) listed a real salary. Among skills with at least 10 of them, postings mentioning **Power BI** had the highest median posted salary (**$123,026**, 48 postings), followed by SQL ($109,000) and Python ($108,250). Power BI developer roles tend to be more technical, so this reflects the role mix as much as the skill itself.
- Jobs are spread widely: no single state has more than 8% of postings. **Virginia** had the most (**8.0%**, 109 postings), ahead of Texas (7.6%) and California (6.1%); 8.5% didn't specify a state.

## Data quality: problems I found and how I handled them

1. **The first search returned the wrong jobs.** My first run found SQL in only 1 of 50 "data analyst" postings, which couldn't be right. Investigating the titles showed the API's keyword search matched "data" and "analyst" separately, pulling in unrelated analyst roles. I switched to exact-phrase search across five role titles. The share of postings with at least one detectable skill went from 12% to 41%.
2. **Descriptions are cut at 500 characters.** The API only returns the start of each description, which is usually the company intro, so skills listed further down are missed. I report counts as lower bounds, search titles as well as descriptions, and state the limitation on the dashboard. In a hand-labeled random sample, 44% of postings named none of the tracked skills in the text the API returns (see the extraction test below).
3. **Selection bias from my own search terms, and a hypothesis that turned out wrong.** "Power BI developer" is one of the search terms, so I expected Power BI's count to come mostly from job titles. I tracked where each match was found to test this. Only 10.6% of Power BI matches came from the title alone; most (197 of 339) mentioned it in both title and description. So filtering to description mentions barely changes the count, because the search itself selects postings that talk about Power BI. The right fix is to record which search term found each posting and compare skills within each term; that's the next improvement.
4. **Duplicates.** The same posting can match several search terms and reappear on later days. Adzuna's job id is the primary key, and inserts use `ON CONFLICT DO NOTHING`.
5. **Estimated salaries.** Adzuna estimates salaries for postings that don't list one. Salary analysis uses only employer-posted salaries, excludes values under $15,000 (likely hourly rates), and only shows skills with at least 10 salaried postings. Only 4 skills meet that bar so far.
6. **Keyword matching errors.** "Excel" as a verb can be counted as the Excel skill; "Spark" is matched only as PySpark/Apache Spark to avoid the verb, so some Spark postings are missed. "Data visualization" includes the word "dashboard", which is broad. The extraction test below measures how often the keyword rules go wrong: 1 wrong skill and 5 missed skills across 50 hand-labeled postings.

## Regex vs. LLM skill extraction

**The question:** Would an LLM pull skills out of postings more accurately than my keyword (regex) dictionary, and would it be worth the cost?

**How I tested it**

- **A fixed answer key.** I drew 50 random postings from the database (from all postings, not only ones the regex matched, so the test isn't tilted toward it) and froze them, so every method is scored on the same text.
- **Labeled by hand.** I marked which of the 22 tracked skills each posting asks for, following written rules. For example, a skill mentioned only in the company intro doesn't count, "Excel in a fast-paced environment" isn't Excel, and MySQL counts as SQL.
- **Two methods, same input.** The regex extractor, and Gemini 3.5 Flash-Lite with structured output limited to the same 22 skill names, temperature 0, and the same labeling rules in its prompt.
- **F1 instead of accuracy.** Most posting–skill pairs are "no" (52 "yes" out of 1,100), so a method that finds nothing at all would still score 95% accuracy. Precision, recall and F1 only count the skills that are actually there.
- **A blind second look at the labels.** After the first scoring, I listed every posting–skill pair where my label, the regex and the LLM didn't all agree, hid which method said what, and re-decided each one from the text. Re-checking only one method's mistakes would have tilted the answer key toward that method.

**Results** (50 postings, 52 labeled skill mentions)

| Method | Precision | Recall | F1 | Wrong skills | Missed skills | Cost per 1,000 postings |
|---|---|---|---|---|---|---|
| Regex | 0.979 | 0.904 | **0.940** | 1 | 5 | $0 |
| Gemini 3.5 Flash-Lite | 0.878 | 0.827 | 0.851 | 6 | 9 | ~$0.14* |

\*At the standard paid-tier price; the test itself ran on the free tier.

By skill (only skills with at least 5 labeled postings): both methods scored a perfect 1.0 on Power BI (16 postings) and SQL (6). The difference is in Data Visualization (15): regex F1 0.93, LLM 0.73.

**What I learned**

- **The regex was more accurate and free, so it stays in the pipeline.** The LLM is cheap (about 14 cents per 1,000 postings), so cost wasn't the deciding factor; accuracy was.
- **The LLM reads meaning, which cut both ways.** It caught dashboard mentions I had missed on my first pass of labeling (the blind review corrected those labels), but it also added skills the job plausibly needs but never names.
- **The 500-character cut-off matters more than the extractor.** 22 of the 50 postings (44%) name none of the tracked skills in the text the API returns, and no extraction method can recover what isn't there.
- **Limits of this test.** 52 skill mentions is a small sample, and only three skills appear often enough to score on their own. My labeling rules count skills that are written in the text, which is what a keyword dictionary is designed to find, so the test leans toward the regex. I used the smaller Gemini model because the larger one was overloaded on the free tier at test time. On full-length postings, where skills are often described instead of named, an LLM may do better; that's the next experiment.

The dashboard's **Regex vs LLM** tab shows these results.

**Reproduce it:**

```
python make_label_sheet.py                    # draws the 50-posting sample into eval/label_sheet.xlsx; label it by hand
python llm_extract.py gemini-3.5-flash-lite   # needs GEMINI_API_KEY in .env
python evaluate.py                            # scores both methods, writes eval/*.csv
python make_review_list.py                    # blind list of disagreements to re-check
```

The label sheet isn't in the repo because it contains posting text. `eval/labels.csv` has the final labels (job ids and skills only).

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
| `queries/10_eval_sample.sql`, `make_label_sheet.py` | Draws the frozen 50-posting sample and builds the labeling sheet |
| `llm_extract.py` | Asks Gemini for each posting's skills (structured output, retries, resumes after a crash) |
| `eval_utils.py`, `evaluate.py` | Scores the regex and the LLM against the hand labels |
| `make_review_list.py` | Lists disagreements for a blind second look at the labels |
| `eval/` | Test results: summary, per-skill scores, every error, final labels, LLM answers |

## Run it locally

1. `python -m venv venv` and activate it, then `pip install -r requirements.txt`
2. Create `.env` with `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` (free key from developer.adzuna.com) and `DATABASE_URL` (any Postgres; I use Neon's free tier). Add `GEMINI_API_KEY` (free from Google AI Studio) only if you want to re-run the extraction test.
3. `python create_tables.py`, `python fetch_jobs.py`, `python load_jobs.py`, `python extract_skills.py`
4. `streamlit run app.py`

## Next steps

- Store which search term found each posting, so skill demand can be compared within each role and the search-term bias measured properly.
- Re-run the regex vs. LLM test on full-length postings (for example from company job boards that publish complete descriptions), where an LLM may have more of an advantage.
- Group titles into seniority levels (junior / mid / senior) and compare skills by level.

## How I built this

I used Claude as a coding assistant, and it wrote most of the code. I defined the question and scope, chose the data source, set up the Neon database, API keys and secrets, ran, debugged and deployed the pipeline, investigated the data quality problems above with SQL, and decided how to handle each one. For the extraction test, I labeled the 50 postings myself and did the blind review of every disagreement.

Job data provided by [Adzuna](https://www.adzuna.com).
