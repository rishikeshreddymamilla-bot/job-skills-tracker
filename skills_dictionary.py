# Each skill: a standard name, a category, and the regex patterns that count as a mention.
# \b means "word boundary", so r"\bsql\b" matches "SQL" or "T-SQL" but not "PostgreSQL".
# case_sensitive=True is for names that are also ordinary words or letters (R, Excel, SAS).

SKILLS = [
    # Query languages and programming
    {"name": "SQL",        "category": "language", "patterns": [r"\bsql\b"]},
    {"name": "Python",     "category": "language", "patterns": [r"\bpython\b"]},
    {"name": "R",          "category": "language", "patterns": [r"\bR\b(?!&)"], "case_sensitive": True},
    {"name": "SAS",        "category": "language", "patterns": [r"\bSAS\b"], "case_sensitive": True},

    # BI and visualization tools
    {"name": "Power BI",   "category": "bi_tool",  "patterns": [r"\bpower\s?bi\b"]},
    {"name": "Tableau",    "category": "bi_tool",  "patterns": [r"\btableau\b"]},
    {"name": "Looker",     "category": "bi_tool",  "patterns": [r"\blooker\b"]},
    {"name": "Excel",      "category": "bi_tool",  "patterns": [r"\bExcel\b"], "case_sensitive": True},
    {"name": "SSRS",       "category": "bi_tool",  "patterns": [r"\bssrs\b"]},

    # Databases and data platforms
    {"name": "PostgreSQL", "category": "database", "patterns": [r"\bpostgre(s|sql)\b"]},
    {"name": "MySQL",      "category": "database", "patterns": [r"\bmysql\b"]},
    {"name": "Snowflake",  "category": "database", "patterns": [r"\bsnowflake\b"]},
    {"name": "dbt",        "category": "data_eng", "patterns": [r"\bdbt\b"]},
    {"name": "ETL",        "category": "data_eng", "patterns": [r"\betl\b"]},
    {"name": "Spark",      "category": "data_eng", "patterns": [r"\bpyspark\b", r"\bapache spark\b"]},

    # Cloud
    {"name": "AWS",        "category": "cloud",    "patterns": [r"\baws\b", r"\bamazon web services\b"]},
    {"name": "Azure",      "category": "cloud",    "patterns": [r"\bazure\b"]},
    {"name": "GCP",        "category": "cloud",    "patterns": [r"\bgcp\b", r"\bgoogle cloud\b"]},

    # Methods and concepts
    {"name": "Statistics",         "category": "concept", "patterns": [r"\bstatistic(s|al)\b"]},
    {"name": "Machine Learning",   "category": "concept", "patterns": [r"\bmachine learning\b"]},
    {"name": "A/B Testing",        "category": "concept", "patterns": [r"\ba/b test"]},
    {"name": "Data Visualization", "category": "concept", "patterns": [r"\bdata visuali[sz]ation\b", r"\bdashboards?\b"]},
]
