from csv import DictReader
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "sample_jobs.csv"
OUTPUT = ROOT / "outputs" / "jobfit_report.md"
LIVE_OUTPUT = ROOT / "outputs" / "live_jobfit_report.md"

NEWS_QUERIES = [
    "business analytics internship students remote",
    "data analyst internship college students remote",
    "information systems internship students United States",
    "cybersecurity internship college students remote",
    "product analytics internship students",
]

JOB_API_QUERIES = [
    "business analyst intern",
    "data analyst intern",
    "analytics intern",
    "product analyst intern",
    "cybersecurity intern",
    "information systems intern",
]

RESUME_KEYWORDS = {
    "python": 5,
    "machine": 4,
    "learning": 4,
    "analytics": 5,
    "sql": 5,
    "dashboard": 4,
    "dashboards": 4,
    "business": 4,
    "ai": 4,
    "azure": 3,
    "security": 4,
    "cryptography": 4,
    "systems": 3,
    "operations": 3,
    "logistics": 4,
    "stakeholder": 3,
    "react": 3,
    "typescript": 3,
}


def tokenize(text):
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return set(cleaned.split())


def score(description):
    tokens = tokenize(description)
    hits = {word: weight for word, weight in RESUME_KEYWORDS.items() if word in tokens}
    return sum(hits.values()), hits


def load_jobs():
    with DATA.open(newline="", encoding="utf-8") as file:
        return list(DictReader(file))


def fetch_yahoo_news(query, limit=10):
    xml = fetch_rss([
        f"https://news.search.yahoo.com/rss?p={quote_plus(query)}",
        f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en",
    ])
    root = ET.fromstring(xml)
    rows = []
    for item in root.findall("./channel/item")[:limit]:
        title = text(item, "title")
        description = strip_html(text(item, "description"))
        rows.append({
            "company": source_to_company(text(item, "source")),
            "role": title,
            "category": "Live lead",
            "description": f"{title} {description}",
            "published": text(item, "pubDate"),
            "link": text(item, "link"),
            "query": query,
        })
    return rows


def fetch_rss(urls):
    last_error = None
    for url in urls:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 career-portfolio-project"})
        try:
            with urlopen(request, timeout=12) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
    raise last_error


def text(item, tag):
    found = item.find(tag)
    return "" if found is None or found.text is None else found.text.strip()


def strip_html(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def source_to_company(source):
    return source or "Yahoo News"


def load_live_leads():
    leads = []
    leads.extend(load_remotive_jobs())
    for query in NEWS_QUERIES:
        leads.extend(fetch_yahoo_news(query))
    deduped = {}
    for lead in leads:
        deduped.setdefault(lead["link"] or lead["role"], lead)
    return list(deduped.values())


def load_remotive_jobs():
    jobs = []
    for query in JOB_API_QUERIES:
        url = f"https://remotive.com/api/remote-jobs?search={quote_plus(query)}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 career-portfolio-project"})
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
        for job in payload.get("jobs", []):
            title = job.get("title", "")
            description = strip_html(job.get("description", ""))
            content = f"{title} {description}".lower()
            title_lower = title.lower()
            eligible_title = any(term in title_lower for term in ["intern", "internship", "analyst", "associate", "coordinator", "assistant"])
            senior_title = any(term in title_lower for term in ["senior", "manager", "director", "head of", "lead", "architect", "mid/senior"])
            if not eligible_title or (senior_title and "intern" not in title_lower):
                continue
            jobs.append({
                "company": job.get("company_name", "Remotive"),
                "role": title,
                "category": job.get("category", "Remote job"),
                "description": f"{title} {description}",
                "published": job.get("publication_date", ""),
                "link": job.get("url", ""),
                "query": f"Remotive: {query}",
            })
    return jobs


def write_report(rows):
    ranked = []
    for row in rows:
        fit_score, hits = score(row["description"])
        ranked.append({**row, "fit_score": fit_score, "hits": hits})
    ranked.sort(key=lambda row: row["fit_score"], reverse=True)

    OUTPUT.parent.mkdir(exist_ok=True)
    lines = [
        "# JobFit Report",
        "",
        "## Ranked opportunities",
        "",
        "| Rank | Company | Role | Fit score | Keyword evidence | Next action |",
        "| ---: | --- | --- | ---: | --- | --- |",
    ]
    for idx, row in enumerate(ranked, start=1):
        evidence = ", ".join(sorted(row["hits"])) or "No strong keyword match"
        next_action = "Tailor resume and apply" if row["fit_score"] >= 15 else "Use as stretch or skill-gap target"
        lines.append(f"| {idx} | {row['company']} | {row['role']} | {row['fit_score']} | {evidence} | {next_action} |")

    lines.extend([
        "",
        "## Improvement ideas",
        "",
        "1. Add a real job description parser that reads pasted postings.",
        "2. Add missing-keyword suggestions for each role.",
        "3. Export a weekly application tracker CSV.",
        "4. Connect the score to resume bullet variants.",
    ])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def write_live_report(rows):
    ranked = []
    for row in rows:
        fit_score, hits = score(row["description"])
        ranked.append({**row, "fit_score": fit_score, "hits": hits})
    ranked.sort(key=lambda row: row["fit_score"], reverse=True)

    LIVE_OUTPUT.parent.mkdir(exist_ok=True)
    lines = [
        "# Live JobFit Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "Sources: Remotive public jobs API plus Yahoo/Google News RSS search feeds for internship and career-opportunity terms",
        "",
        "## Ranked live leads",
        "",
        "| Rank | Fit score | Source | Published | Lead | Keyword evidence | Next action |",
        "| ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for idx, row in enumerate(ranked[:25], start=1):
        evidence = ", ".join(sorted(row["hits"])) or "No strong keyword match"
        next_action = "Open and verify application page" if row["fit_score"] >= 10 else "Monitor only"
        title = row["role"].replace("|", "\\|")
        lines.append(f"| {idx} | {row['fit_score']} | {row['company']} | {row['published']} | [{title}]({row['link']}) | {evidence} | {next_action} |")

    lines.extend([
        "",
        "## Recruiter-search notes",
        "",
        "1. Live news leads are not guaranteed application pages; verify each link before applying.",
        "2. Prioritize roles mentioning analytics, SQL, Python, business, security, product, or systems.",
        "3. During the academic year, treat full-time internships as Summer 2027 pipeline items, not semester commitments.",
    ])
    LIVE_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        live_rows = load_live_leads()
        write_live_report(live_rows)
        print(f"Wrote {LIVE_OUTPUT}")
    except Exception as exc:
        print(f"Live news fetch failed; using sample job fallback. Reason: {exc}")
        write_report(load_jobs())
        print(f"Wrote {OUTPUT}")
