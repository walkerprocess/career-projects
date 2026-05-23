# Stock Signal Engine

This project screens U.S. stocks and ETFs using live market data plus recent news headlines. It replaces the older GPT-dependent recommendation logic with a direct, explainable scoring algorithm.

## What It Does

- Pulls Yahoo Finance daily chart data.
- Pulls recent Google News RSS headlines.
- Scores each ticker using:
  - 60-day and 20-day trend
  - 5-day and 1-day momentum
  - price vs. 20-day and 50-day moving averages
  - volume confirmation
  - news buzz and keyword sentiment
  - volatility and drawdown risk penalty
- Accepts current holdings from `portfolio_input.csv`.
- Generates CSV, JSON, and an Excel workbook report.

## Important Disclaimer

This is an educational quantitative screen only. It is not financial advice, not a buy/sell instruction, and not a guarantee of future returns. Always do your own research before making investment decisions.

## Portfolio Input

Edit `portfolio_input.csv`:

```csv
symbol,shares,avg_cost,notes
AAPL,10,185,example
NVDA,3,900,example
```

Set `shares` and `avg_cost` to `0` if you only want a watch-only outlook.

## Run

Collect live stock/news data:

```powershell
python nextgen_stock_engine.py --portfolio portfolio_input.csv --limit 45 --output-dir outputs\latest
```

Build the Excel workbook:

```powershell
node build_stock_workbook.mjs outputs\latest\stock_signal_results.json outputs\latest\stock_signal_report.xlsx
```

## Main Output

```text
outputs/latest/stock_signal_report.xlsx
```

Workbook tabs:

- `Dashboard`
- `Top Signals`
- `Portfolio Outlook`
- `News Signals`
- `Methodology`
- `Checks`

## Notes

The model intentionally avoids GPT for scoring. News sentiment is a simple keyword-based signal, which makes the result explainable but not perfect. The score is a screening tool, not a prediction engine.
