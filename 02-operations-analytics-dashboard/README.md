# Operations Analytics Decision Dashboard

Business analytics project focused on logistics and transportation performance. It is designed to fit Kelley DLT, BI internships, product analytics, and operations analyst roles.

## Business question

Which warehouse lanes are underperforming, and what operational actions should leadership take first?

## What this demonstrates

- Cleaning shipment records
- Defining KPIs: on-time rate, average delay, cost per shipment, damage rate
- SQL-style business analysis
- Executive communication through a concise recommendation memo

## Run

```bash
python src/analyze.py
```

The script now pulls current Yahoo News RSS results for logistics, transportation, warehousing, freight, and supply-chain risk topics. It writes a live report to `outputs/live_logistics_news_report.md`.

If the live fetch fails, it falls back to `data/sample_shipments.csv` and writes the original KPI summary to `outputs/kpi_report.md`.

## Resume bullet draft

Built an operations analytics dashboard prototype using shipment-level data to identify underperforming logistics lanes, define KPI logic, and translate Python/SQL analysis into executive recommendations.
