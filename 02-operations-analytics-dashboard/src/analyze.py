from collections import defaultdict
from csv import DictReader
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "sample_shipments.csv"
OUTPUT = ROOT / "outputs" / "kpi_report.md"
LIVE_OUTPUT = ROOT / "outputs" / "live_logistics_news_report.md"

NEWS_QUERIES = [
    "supply chain logistics disruption United States",
    "warehouse automation logistics transportation",
    "freight rates trucking rail logistics",
    "port congestion shipping logistics",
]

RISK_TERMS = {
    "delay": 4,
    "delays": 4,
    "disruption": 5,
    "disruptions": 5,
    "strike": 5,
    "shortage": 4,
    "congestion": 4,
    "tariff": 3,
    "tariffs": 3,
    "cost": 2,
    "costs": 2,
    "automation": -2,
    "ai": -1,
    "efficiency": -2,
}


def load_rows():
    with DATA.open(newline="", encoding="utf-8") as file:
        return list(DictReader(file))


def fetch_yahoo_news(query, limit=12):
    xml = fetch_rss([
        f"https://news.search.yahoo.com/rss?p={quote_plus(query)}",
        f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en",
    ])
    root = ET.fromstring(xml)
    rows = []
    for item in root.findall("./channel/item")[:limit]:
        rows.append({
            "query": query,
            "title": text(item, "title"),
            "source": text(item, "source") or "Yahoo News",
            "published": text(item, "pubDate"),
            "link": text(item, "link"),
            "description": strip_html(text(item, "description")),
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


def score_article(article):
    content = f"{article['title']} {article['description']}".lower()
    hits = {term: weight for term, weight in RISK_TERMS.items() if re.search(rf"\b{re.escape(term)}\b", content)}
    return sum(hits.values()), hits


def live_news_report():
    articles = []
    for query in NEWS_QUERIES:
        articles.extend(fetch_yahoo_news(query))

    deduped = {}
    for article in articles:
        deduped.setdefault(article["link"] or article["title"], article)

    scored = []
    for article in deduped.values():
        risk_score, hits = score_article(article)
        scored.append({**article, "risk_score": risk_score, "hits": hits})
    scored.sort(key=lambda row: row["risk_score"], reverse=True)
    return scored


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        key = (row["origin"], row["destination"], row["carrier"])
        row["units"] = int(row["units"])
        row["cost_usd"] = float(row["cost_usd"])
        row["promised_days"] = int(row["promised_days"])
        row["actual_days"] = int(row["actual_days"])
        row["damaged_flag"] = row["damaged"].lower() == "true"
        row["on_time"] = row["actual_days"] <= row["promised_days"]
        row["delay_days"] = row["actual_days"] - row["promised_days"]
        groups[key].append(row)

    summary = []
    for (origin, destination, carrier), items in groups.items():
        shipments = len(items)
        units = sum(item["units"] for item in items)
        avg_cost = sum(item["cost_usd"] for item in items) / shipments
        cost_per_unit = sum(item["cost_usd"] for item in items) / units
        on_time_rate = sum(item["on_time"] for item in items) / shipments
        avg_delay = sum(item["delay_days"] for item in items) / shipments
        damage_rate = sum(item["damaged_flag"] for item in items) / shipments
        summary.append({
            "lane": f"{origin} -> {destination}",
            "carrier": carrier,
            "shipments": shipments,
            "units": units,
            "avg_cost": avg_cost,
            "cost_per_unit": cost_per_unit,
            "on_time_rate": on_time_rate,
            "avg_delay": avg_delay,
            "damage_rate": damage_rate,
        })
    return sorted(summary, key=lambda row: (row["on_time_rate"], -row["cost_per_unit"]))


def write_report(summary):
    OUTPUT.parent.mkdir(exist_ok=True)
    worst = summary[0]
    lines = [
        "# Operations KPI Report",
        "",
        "## Executive finding",
        f"The first lane to investigate is **{worst['lane']} / {worst['carrier']}** because it has the weakest on-time rate and a high cost per unit.",
        "",
        "## KPI table",
        "",
        "| Lane | Carrier | Shipments | Units | Avg cost | Cost/unit | On-time | Avg delay | Damage |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        lines.append(
            f"| {row['lane']} | {row['carrier']} | {row['shipments']} | {row['units']} | "
            f"${row['avg_cost']:.0f} | ${row['cost_per_unit']:.2f} | "
            f"{row['on_time_rate']:.0%} | {row['avg_delay']:.1f} | {row['damage_rate']:.0%} |"
        )
    lines.extend([
        "",
        "## Recommended actions",
        "",
        "1. Audit late Atlanta lanes and separate carrier performance from route complexity.",
        "2. Compare cost per unit against promised-day reliability before renewing carrier allocation.",
        "3. Add weekly exception reporting for damaged shipments and delay spikes.",
    ])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def write_live_report(articles):
    LIVE_OUTPUT.parent.mkdir(exist_ok=True)
    highest = articles[0] if articles else None
    lines = [
        "# Live Logistics News Risk Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "Source: Yahoo News RSS search feeds",
        "",
    ]
    if highest:
        lines.extend([
            "## Executive finding",
            f"The highest-scoring current logistics risk signal is **{highest['title']}** from {highest['source']}.",
            "",
        ])
    else:
        lines.extend(["## Executive finding", "No live news articles were retrieved.", ""])

    lines.extend([
        "## Ranked live signals",
        "",
        "| Rank | Risk score | Source | Published | Headline | Matched terms |",
        "| ---: | ---: | --- | --- | --- | --- |",
    ])
    for idx, article in enumerate(articles[:20], start=1):
        matched = ", ".join(sorted(article["hits"])) or "none"
        title = article["title"].replace("|", "\\|")
        lines.append(f"| {idx} | {article['risk_score']} | {article['source']} | {article['published']} | [{title}]({article['link']}) | {matched} |")

    lines.extend([
        "",
        "## Recommended operating actions",
        "",
        "1. Treat high-scoring disruption, strike, congestion, or delay articles as lane-risk prompts for weekly monitoring.",
        "2. Pair negative risk signals with automation/AI articles to identify where technology can reduce operational exposure.",
        "3. Convert the top 3 headlines into a short DLT networking question for a speaker or alumni conversation.",
    ])
    LIVE_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        live_articles = live_news_report()
        write_live_report(live_articles)
        print(f"Wrote {LIVE_OUTPUT}")
    except Exception as exc:
        print(f"Live news fetch failed; using sample shipment fallback. Reason: {exc}")
        write_report(summarize(load_rows()))
        print(f"Wrote {OUTPUT}")
