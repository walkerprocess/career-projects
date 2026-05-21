-- KPI summary by lane and carrier.
-- This file mirrors the Python logic and is ready to adapt to SQLite, Postgres, or BigQuery.

WITH shipment_metrics AS (
  SELECT
    origin,
    destination,
    carrier,
    units,
    cost_usd,
    promised_days,
    actual_days,
    CASE WHEN actual_days <= promised_days THEN 1 ELSE 0 END AS on_time_flag,
    CASE WHEN damaged = 'true' THEN 1 ELSE 0 END AS damaged_flag,
    actual_days - promised_days AS delay_days
  FROM shipments
)
SELECT
  origin,
  destination,
  carrier,
  COUNT(*) AS shipments,
  SUM(units) AS units,
  ROUND(AVG(cost_usd), 2) AS avg_cost,
  ROUND(AVG(cost_usd * 1.0 / units), 2) AS cost_per_unit,
  ROUND(AVG(on_time_flag) * 100, 1) AS on_time_rate_pct,
  ROUND(AVG(delay_days), 2) AS avg_delay_days,
  ROUND(AVG(damaged_flag) * 100, 1) AS damage_rate_pct
FROM shipment_metrics
GROUP BY origin, destination, carrier
ORDER BY on_time_rate_pct ASC, cost_per_unit DESC;

