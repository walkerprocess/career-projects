# JobFit Resume Intelligence Tracker

A lightweight career operations project that scores internship postings against your resume themes and turns the job search into a measurable pipeline.

## Why this project

Reddit and hiring discussion trends point to a practical pattern: projects should prove SQL/Python/visualization, answer business questions, and give you interview stories. This tracker supports that by mapping job descriptions to your skills and producing next actions.

## Run

```bash
python src/score_jobs.py
```

The script now searches the Remotive public jobs API plus Yahoo/Google News RSS for current analytics, information systems, product analytics, and cybersecurity internship leads. It scores the live results against your resume keyword profile and writes `outputs/live_jobfit_report.md`.

If the live fetch fails, it falls back to `data/sample_jobs.csv` and creates `outputs/jobfit_report.md`.

## Resume bullet draft

Created a Python-based job-fit scoring tool that maps internship descriptions to resume keywords, prioritizes applications, and generates targeted next steps for a structured recruiting pipeline.
