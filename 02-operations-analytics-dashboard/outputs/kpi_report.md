# Operations KPI Report

## Executive finding
The first lane to investigate is **Detroit -> Atlanta / RoadRunner** because it has the weakest on-time rate and a high cost per unit.

## KPI table

| Lane | Carrier | Shipments | Units | Avg cost | Cost/unit | On-time | Avg delay | Damage |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Detroit -> Atlanta | RoadRunner | 1 | 100 | $1600 | $16.00 | 0% | 3.0 | 100% |
| Detroit -> Atlanta | SwiftPath | 1 | 110 | $1510 | $13.73 | 0% | 1.0 | 0% |
| Chicago -> Atlanta | BlueLine | 1 | 120 | $1410 | $11.75 | 0% | 3.0 | 100% |
| Chicago -> Atlanta | SwiftPath | 1 | 130 | $1375 | $10.58 | 0% | 1.0 | 0% |
| Chicago -> Atlanta | RoadRunner | 1 | 140 | $1320 | $9.43 | 0% | 2.0 | 0% |
| Columbus -> Indianapolis | BlueLine | 1 | 220 | $880 | $4.00 | 0% | 1.0 | 0% |
| Detroit -> Indianapolis | BlueLine | 1 | 250 | $820 | $3.28 | 0% | 1.0 | 0% |
| Columbus -> Atlanta | SwiftPath | 1 | 95 | $1280 | $13.47 | 100% | 0.0 | 0% |
| Chicago -> Indianapolis | RoadRunner | 1 | 180 | $940 | $5.22 | 100% | 0.0 | 0% |
| Chicago -> Indianapolis | BlueLine | 1 | 210 | $970 | $4.62 | 100% | 0.0 | 0% |
| Columbus -> Indianapolis | RoadRunner | 1 | 240 | $900 | $3.75 | 100% | 0.0 | 0% |
| Detroit -> Indianapolis | RoadRunner | 1 | 260 | $790 | $3.04 | 100% | 0.0 | 0% |

## Recommended actions

1. Audit late Atlanta lanes and separate carrier performance from route complexity.
2. Compare cost per unit against promised-day reliability before renewing carrier allocation.
3. Add weekly exception reporting for damaged shipments and delay spikes.