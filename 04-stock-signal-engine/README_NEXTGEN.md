# NextGen Stock Signal Engine

This is a replacement path for the older GPT-dependent stock recommendation project.

It does **not** use GPT for the scoring algorithm. It pulls market data and news, then computes an explainable quantitative score.

## What It Does

- Finds hot stocks from a broad U.S. equity/ETF universe
- Pulls Yahoo Finance chart data
- Pulls Google News RSS headlines
- Scores each ticker with a direct algorithm:
  - 60-day and 20-day trend
  - 5-day and 1-day momentum
  - price vs. moving averages
  - volume confirmation
  - headline buzz and keyword sentiment
  - volatility and drawdown risk penalty
- Accepts current holdings through `portfolio_input.csv`
- Creates CSV/JSON outputs for an Excel workbook builder

## Important Disclaimer

This is an educational screening tool, not financial advice. It does not guarantee returns and should not be treated as a buy/sell instruction.

## Run Data Collection

```powershell
python nextgen_stock_engine.py --portfolio portfolio_input.csv --limit 45
```

Optional extra tickers:

```powershell
python nextgen_stock_engine.py --symbols "AAPL,NVDA,TSLA" --portfolio portfolio_input.csv
```

## Portfolio Input

Edit `portfolio_input.csv`:

```csv
symbol,shares,avg_cost,notes
AAPL,10,185,example
NVDA,3,900,example
```

If you do not own shares yet, keep shares and average cost as `0`. The report will still analyze the ticker outlook.
