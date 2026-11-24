import os

import altair as alt
import pandas as pd
import streamlit as st

from db import get_connection

st.set_page_config(page_title="Data Analyst & BI Skills Tracker", layout="wide")

# On Streamlit Cloud the database URL lives in the app's Secrets, not in .env.
# Copy it into the environment so db.get_connection() works the same everywhere.
if "DATABASE_URL" not in os.environ:
    try:
        os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
    except Exception:
        pass  # running locally: db.py reads .env instead

MIN_REAL_SALARY = 15000   # below this is probably an hourly rate, not a yearly salary
MIN_JOBS_FOR_PAY = 10     # don't show an average built from a handful of jobs
NO_STATE = "Nationwide / not specified"
CATEGORY_LABELS = {
    "language": "Language", "bi_tool": "BI tool", "database": "Database",
    "data_eng": "Data engineering", "cloud": "Cloud", "concept": "Concept",
}


# ---------- Load data (cached for an hour, so the database isn't queried on every click) ----------

def fetch(sql):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [c[0] for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)
    finally:
        conn.close()


@st.cache_data(ttl=3600)
def load_data():
    jobs = fetch("""
        SELECT job_id, title, company, state, contract_time,
               salary_min, salary_max, salary_is_predicted,
               posted_at, first_seen_at, redirect_url
        FROM jobs;
    """)
    matches = fetch("""
        SELECT js.job_id, s.name AS skill, s.category, js.found_in
        FROM job_skills js
        JOIN skills s ON s.skill_id = js.skill_id
        WHERE js.method = 'keyword';
    """)

    # Postgres NUMERIC arrives as Python Decimal; convert to normal numbers for pandas.
    for col in ["salary_min", "salary_max"]:
        jobs[col] = pd.to_numeric(jobs[col], errors="coerce")
    jobs["state"] = jobs["state"].fillna(NO_STATE)
    matches["category"] = matches["category"].map(CATEGORY_LABELS).fillna(matches["category"])
    jobs["contract_time"] = (jobs["contract_time"].fillna("not specified")
                             .str.replace("_", " "))
    jobs["first_seen_day"] = pd.to_datetime(jobs["first_seen_at"], utc=True).dt.date

    # A salary is "real" only if the employer posted it (Adzuna estimates the rest).
    jobs["salary_mid"] = (jobs["salary_min"] + jobs["salary_max"].fillna(jobs["salary_min"])) / 2
    jobs["real_salary"] = jobs["salary_mid"].where(
        (jobs["salary_is_predicted"] == False) & (jobs["salary_min"] >= MIN_REAL_SALARY)  # noqa: E712
    )
    return jobs, matches


try:
    jobs, matches = load_data()
except (Exception, SystemExit) as e:
    st.error(f"Couldn't load data from the database: {e}")
    st.stop()


# ---------- Header ----------

st.title("What skills do data analyst & BI jobs actually ask for?")
st.caption(
    "US job postings for data analyst, BI analyst, business intelligence analyst, reporting analyst "
    "and Power BI developer roles, collected daily from the Adzuna API, stored in Postgres, "
    "and scanned for skills."
)

if jobs.empty:
    st.warning("No jobs in the database yet. Run fetch_jobs.py, load_jobs.py and extract_skills.py first.")
    st.stop()


# ---------- Sidebar filters ----------

with st.sidebar:
    st.header("Filters")
    states = sorted(jobs["state"].unique(), key=lambda s: (s == NO_STATE, s))
    picked_states = st.multiselect("State", states, placeholder="All states")

    job_types = sorted(jobs["contract_time"].unique())
    picked_types = st.multiselect("Job type", job_types, placeholder="All job types")

    categories = sorted(matches["category"].dropna().unique())
    picked_categories = st.multiselect("Skill category", categories, placeholder="All categories")

    description_only = st.checkbox(
        "Count description mentions only",
        help="Ignore skills found only in the job title. One search term is 'Power BI developer', "
             "so title matches inflate Power BI. This reduces that bias.",
    )

filtered_jobs = jobs
if picked_states:
    filtered_jobs = filtered_jobs[filtered_jobs["state"].isin(picked_states)]
if picked_types:
    filtered_jobs = filtered_jobs[filtered_jobs["contract_time"].isin(picked_types)]

if filtered_jobs.empty:
    st.warning("No jobs match these filters.")
    st.stop()

filtered_matches = matches[matches["job_id"].isin(filtered_jobs["job_id"])]
if description_only:
    filtered_matches = filtered_matches[filtered_matches["found_in"].isin(["description", "both"])]
if picked_categories:
    filtered_matches = filtered_matches[filtered_matches["category"].isin(picked_categories)]

total_jobs = len(filtered_jobs)


# ---------- Headline numbers ----------

jobs_with_skill = filtered_matches["job_id"].nunique()
median_pay = filtered_jobs["real_salary"].median()
days_collected = filtered_jobs["first_seen_day"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Jobs analyzed", f"{total_jobs:,}")
c2.metric("Jobs with a detected skill", f"{100 * jobs_with_skill / total_jobs:.0f}%",
          help="Low because Adzuna only provides the first 500 characters of each description.")
c3.metric("Median posted salary", "n/a" if pd.isna(median_pay) else f"${median_pay:,.0f}",
          help="Only salaries the employer posted. Adzuna's estimated salaries are excluded.")
c4.metric("Days of data", days_collected)


tab_skills, tab_pay, tab_pairs, tab_where, tab_jobs, tab_eval, tab_method = st.tabs(
    ["Skills demand", "Pay by skill", "Skills together", "Where & when", "Postings", "Regex vs LLM", "Method & limitations"]
)


# ---------- Skills demand ----------

with tab_skills:
    skill_counts = (filtered_matches.groupby(["skill", "category"])["job_id"].nunique()
                    .reset_index(name="jobs"))
    skill_counts["pct_of_jobs"] = 100 * skill_counts["jobs"] / total_jobs

    if skill_counts.empty:
        st.info("No skills found for these filters.")
    else:
        chart = (
            alt.Chart(skill_counts)
            .mark_bar()
            .encode(
                x=alt.X("pct_of_jobs:Q", title="% of jobs mentioning the skill"),
                y=alt.Y("skill:N", sort="-x", title=None),
                color=alt.Color("category:N", title="Category"),
                tooltip=["skill", "category", "jobs", alt.Tooltip("pct_of_jobs:Q", format=".1f", title="% of jobs")],
            )
            .properties(height=max(300, 26 * len(skill_counts)))
        )
        st.altair_chart(chart, width="stretch")
        st.caption(
            "Percentages are of all jobs in the current filter, including jobs where no skill was detected. "
            "Because descriptions are cut at 500 characters, treat these as lower bounds and compare skills "
            "with each other rather than reading them as exact shares."
        )


# ---------- Pay by skill ----------

with tab_pay:
    paid = filtered_matches.merge(filtered_jobs[["job_id", "real_salary"]], on="job_id")
    paid = paid.dropna(subset=["real_salary"])
    pay = (paid.groupby("skill")["real_salary"]
           .agg(median_salary="median", jobs="count").reset_index())
    pay = pay[pay["jobs"] >= MIN_JOBS_FOR_PAY]

    if pay.empty:
        st.info(f"Not enough jobs with posted salaries yet (each skill needs at least {MIN_JOBS_FOR_PAY}).")
    else:
        chart = (
            alt.Chart(pay)
            .mark_bar()
            .encode(
                x=alt.X("median_salary:Q", title="Median posted salary (USD)", axis=alt.Axis(format="$,.0f")),
                y=alt.Y("skill:N", sort="-x", title=None),
                tooltip=["skill", alt.Tooltip("median_salary:Q", format="$,.0f"), alt.Tooltip("jobs:Q", title="jobs with posted salary")],
            )
            .properties(height=max(250, 26 * len(pay)))
        )
        st.altair_chart(chart, width="stretch")
        st.caption(
            f"Only employer-posted salaries of at least ${MIN_REAL_SALARY:,} (lower values are usually hourly). "
            f"Skills with fewer than {MIN_JOBS_FOR_PAY} salaried jobs are hidden. "
            "A higher median doesn't mean the skill causes higher pay: seniority and location also differ."
        )


# ---------- Skills together ----------

with tab_pairs:
    per_job = filtered_matches[["job_id", "skill"]].drop_duplicates()
    pairs = per_job.merge(per_job, on="job_id", suffixes=("_a", "_b"))
    pairs = pairs[pairs["skill_a"] < pairs["skill_b"]]  # each pair once, no skill with itself
    top_pairs = (pairs.groupby(["skill_a", "skill_b"]).size()
                 .reset_index(name="jobs").sort_values("jobs", ascending=False).head(15))

    if top_pairs.empty:
        st.info("No postings mention two or more skills for these filters.")
    else:
        top_pairs["pair"] = top_pairs["skill_a"] + " + " + top_pairs["skill_b"]
        chart = (
            alt.Chart(top_pairs)
            .mark_bar()
            .encode(
                x=alt.X("jobs:Q", title="Jobs mentioning both"),
                y=alt.Y("pair:N", sort="-x", title=None),
                tooltip=["pair", "jobs"],
            )
            .properties(height=max(250, 26 * len(top_pairs)))
        )
        st.altair_chart(chart, width="stretch")
        st.caption("Skills that show up together in the same posting: a guide to which skills to learn as a set.")


# ---------- Where & when ----------

with tab_where:
    left, right = st.columns(2)

    by_state = filtered_jobs.groupby("state").size().reset_index(name="jobs")
    left.subheader("Jobs by state")
    left.altair_chart(
        alt.Chart(by_state).mark_bar().encode(
            x=alt.X("jobs:Q", title="Jobs"),
            y=alt.Y("state:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            tooltip=["state", "jobs"],
        ).properties(height=max(250, 22 * len(by_state))),
        width="stretch",
    )

    by_day = filtered_jobs.groupby("first_seen_day").size().reset_index(name="new_jobs")
    by_day["first_seen_day"] = pd.to_datetime(by_day["first_seen_day"])
    right.subheader("New postings collected per day")
    right.altair_chart(
        alt.Chart(by_day).mark_line(point=True).encode(
            x=alt.X("first_seen_day:T", title="Day collected"),
            y=alt.Y("new_jobs:Q", title="New jobs"),
            tooltip=[alt.Tooltip("first_seen_day:T", title="Day"), "new_jobs"],
        ),
        width="stretch",
    )
    right.caption("Counts each posting on the day it first appeared. Grows as the daily refresh runs.")


# ---------- Postings ----------

with tab_jobs:
    search = st.text_input("Search job titles", placeholder="e.g. senior, Power BI, healthcare")
    skills_per_job = (filtered_matches.groupby("job_id")["skill"]
                      .apply(lambda s: ", ".join(sorted(set(s)))).rename("skills_detected"))
    table = filtered_jobs.merge(skills_per_job, on="job_id", how="left")
    table["skills_detected"] = table["skills_detected"].fillna("")
    if search:
        table = table[table["title"].str.contains(search, case=False, na=False, regex=False)]

    def salary_label(row):
        if pd.isna(row["salary_min"]):
            return ""
        text = f"${row['salary_min']:,.0f}"
        if pd.notna(row["salary_max"]) and row["salary_max"] != row["salary_min"]:
            text += f" - ${row['salary_max']:,.0f}"
        return text + (" (estimated)" if row["salary_is_predicted"] else "")

    table = table.assign(salary=table.apply(salary_label, axis=1) if not table.empty else "")
    st.dataframe(
        table[["title", "company", "state", "salary", "skills_detected", "redirect_url"]]
        .sort_values("title"),
        hide_index=True,
        column_config={
            "title": "Job title",
            "company": "Company",
            "state": "State",
            "salary": "Salary",
            "skills_detected": "Skills detected",
            "redirect_url": st.column_config.LinkColumn("Posting", display_text="View on Adzuna"),
        },
    )
    st.caption(f"{len(table):,} postings. Job listings provided by [Adzuna](https://www.adzuna.com).")


# ---------- Regex vs LLM ----------

with tab_eval:
    summary_path, per_skill_path = "eval/results_summary.csv", "eval/per_skill.csv"
    if not os.path.exists(summary_path):
        st.info("The regex-vs-LLM evaluation hasn't been run yet.")
    else:
        summary = pd.read_csv(summary_path)
        st.markdown(
            "Does an LLM find skills in job postings better than keyword (regex) matching? Both methods read the "
            f"same **{int(summary['postings'].iloc[0])} postings**, and I labeled the skills in each one by hand to "
            "create the answer key. **Precision** = of the skills a method found, the share that were really there. "
            "**Recall** = of the skills really there, the share it found. **F1** combines the two."
        )

        cols = st.columns(len(summary))
        for col, (_, row) in zip(cols, summary.iterrows()):
            cost = row["cost_per_1000_postings_usd"]
            col.metric(f"{row['method']} F1", f"{row['f1']:.2f}",
                       help=f"Precision {row['precision']:.2f}, recall {row['recall']:.2f}. "
                            f"Cost per 1,000 postings: ${cost:,.2f}.")

        long = summary.melt(id_vars="method", value_vars=["precision", "recall", "f1"],
                            var_name="measure", value_name="score")
        long["measure"] = long["measure"].map({"precision": "Precision", "recall": "Recall", "f1": "F1"})
        st.altair_chart(
            alt.Chart(long).mark_bar().encode(
                x=alt.X("measure:N", title=None, sort=["Precision", "Recall", "F1"], axis=alt.Axis(labelAngle=0)),
                xOffset=alt.XOffset("method:N"),
                y=alt.Y("score:Q", title="Score (0 to 1)", scale=alt.Scale(domain=[0, 1])),
                color=alt.Color("method:N", title="Method"),
                tooltip=["method", "measure", alt.Tooltip("score:Q", format=".2f")],
            ).properties(height=320),
            width="stretch",
        )

        st.dataframe(
            summary.rename(columns={
                "method": "Method", "precision": "Precision", "recall": "Recall", "f1": "F1",
                "false_positives": "False positives", "missed": "Missed",
                "seconds_per_posting": "Seconds per posting", "cost_per_1000_postings_usd": "Cost per 1,000 postings ($)",
            })[["Method", "Precision", "Recall", "F1", "False positives", "Missed",
                "Seconds per posting", "Cost per 1,000 postings ($)"]],
            hide_index=True,
        )

        if os.path.exists(per_skill_path):
            per_skill = pd.read_csv(per_skill_path)
            per_skill = per_skill[per_skill["labeled_postings"] >= 5]
            f1_cols = [c for c in per_skill.columns if c.endswith(" F1")]
            st.subheader("By skill")
            st.dataframe(per_skill[["skill", "labeled_postings"] + f1_cols]
                         .rename(columns={"skill": "Skill", "labeled_postings": "Postings with this skill"}),
                         hide_index=True)

        st.caption(
            "Small test set: differences of a few points can be chance, and skills with fewer than 5 labeled postings "
            "are hidden. Cost uses the model's standard paid-tier price (the test itself ran on the free tier). "
            "Both methods only see the first 500 characters of each description, like the rest of this dashboard."
        )


# ---------- Method & limitations ----------

with tab_method:
    st.markdown(f"""
**How the data is collected**
1. A scheduled GitHub Action calls the Adzuna API every day for five exact job phrases
   (data analyst, business intelligence analyst, BI analyst, reporting analyst, Power BI developer).
2. Postings are flattened and stored in Postgres (Neon). Adzuna's job id is the primary key,
   so the same posting is never counted twice, even if it matches several search terms or reappears on later days.
3. Each title and description is scanned with a dictionary of skill patterns (regular expressions).
4. This dashboard reads from the database and refreshes its cache every hour.

**Limitations to keep in mind**
- **Descriptions are truncated.** Adzuna provides only the first 500 characters, so skills listed further down
  a posting are missed. Counts are lower bounds; the ranking between skills is more reliable than the percentages.
- **Search-term bias.** "Power BI developer" is one of the search terms, so Power BI appears in many titles by
  design. Most Power BI postings mention it in the description too, so the description-only filter only partly reduces this.
- **Keyword matching makes mistakes.** "Excel" as a verb ("excel in a fast-paced team") can count as the Excel skill;
  "Spark" is only matched as PySpark or Apache Spark to avoid the verb, so some Spark jobs are missed.
- **Salaries.** Adzuna estimates salaries for postings that don't list one; those estimates are excluded here.
  Salaries under ${MIN_REAL_SALARY:,} are treated as hourly and excluded.
- **Coverage.** These are postings indexed by Adzuna, not every job in the US.
""")

st.divider()
st.caption("Built with Python, PostgreSQL (Neon), GitHub Actions and Streamlit. Job data from [Adzuna](https://www.adzuna.com).")
