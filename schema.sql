-- One row per job posting. Adzuna's id is the primary key,
-- so the same posting can never be stored twice.
CREATE TABLE IF NOT EXISTS jobs (
    job_id              TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    company             TEXT,
    location            TEXT,
    state               TEXT,
    category            TEXT,
    description         TEXT,
    salary_min          NUMERIC,
    salary_max          NUMERIC,
    salary_is_predicted BOOLEAN,
    contract_type       TEXT,
    contract_time       TEXT,
    posted_at           TIMESTAMPTZ,
    redirect_url        TEXT,
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per skill we look for.
CREATE TABLE IF NOT EXISTS skills (
    skill_id  SERIAL PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    category  TEXT
);

-- Which skills each job mentions, and how we found them.
-- One job has many skills; one skill appears in many jobs (many-to-many).
CREATE TABLE IF NOT EXISTS job_skills (
    job_id    TEXT    NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    skill_id  INTEGER NOT NULL REFERENCES skills(skill_id),
    method    TEXT    NOT NULL CHECK (method IN ('keyword', 'llm')),
    found_in  TEXT    CHECK (found_in IN ('title', 'description', 'both')),
    PRIMARY KEY (job_id, skill_id, method)
);
