import argparse
import csv
import json
import math
import statistics
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
USER_AGENT = "Mozilla/5.0 BaselineStockSignal/1.0"


DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "AMD", "CRM",
    "ORCL", "ADBE", "NFLX", "PLTR", "NOW", "SNOW", "SHOP", "UBER", "PANW", "CRWD",
    "JPM", "BAC", "GS", "MS", "V", "MA", "AXP", "COIN", "SQ", "PYPL",
    "LLY", "NVO", "UNH", "JNJ", "MRK", "ABBV", "PFE", "TMO", "ISRG", "VRTX",
    "XOM", "CVX", "COP", "SLB", "NEE", "ENPH", "FSLR",
    "WMT", "COST", "HD", "NKE", "SBUX", "MCD", "DIS", "CMG", "LULU",
    "CAT", "GE", "BA", "LMT", "RTX", "DE", "UPS", "FDX",
    "SPY", "QQQ", "IWM", "DIA", "SMH", "XLK", "XLF", "XLE", "XLV", "XLY"
]


POSITIVE_TERMS = {
    "beat", "beats", "surge", "surges", "rally", "rises", "record", "upgrade", "upgraded",
    "bullish", "buy", "growth", "profit", "profits", "partnership", "contract", "strong",
    "outperform", "guidance", "raises", "raised", "launch", "ai", "demand", "expansion"
}

NEGATIVE_TERMS = {
    "miss", "misses", "falls", "fall", "decline", "declines", "downgrade", "downgraded",
    "bearish", "sell", "lawsuit", "probe", "investigation", "weak", "loss", "losses",
    "recall", "layoff", "cuts", "cut", "risk", "warning", "slumps", "drops", "fraud"
}

LOW_VALUE_NEWS_PHRASES = {
    "stock price, quote", "quote & chart", "stock price and quote", "technical analysis | trend",
    "stock holdings cut", "stock position", "buys new position", "boosts stock position"
}


def request_text(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def safe_float(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except Exception:
        return default


def pct_change(start: float, end: float) -> float:
    if not start:
        return 0.0
    return (end / start) - 1


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


def yahoo_chart(symbol: str, range_: str = "6mo") -> dict | None:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range={range_}&interval=1d&includePrePost=false"
    try:
        data = json.loads(request_text(url))
        result = data.get("chart", {}).get("result", [None])[0]
        if not result:
            return None
        quote = result["indicators"]["quote"][0]
        closes = [safe_float(v, None) for v in quote.get("close", [])]
        volumes = [safe_float(v, None) for v in quote.get("volume", [])]
        timestamps = result.get("timestamp", [])
        rows = [
            {"date": datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat(), "close": close, "volume": volume}
            for ts, close, volume in zip(timestamps, closes, volumes)
            if close is not None
        ]
        meta = result.get("meta", {})
        return {
            "symbol": symbol,
            "shortName": meta.get("shortName") or meta.get("symbol") or symbol,
            "currency": meta.get("currency", "USD"),
            "regularMarketPrice": safe_float(meta.get("regularMarketPrice"), rows[-1]["close"] if rows else 0),
            "rows": rows,
        }
    except Exception:
        return None


def google_news(symbol: str, company_name: str, limit: int = 8) -> list[dict]:
    query = f"{symbol} stock OR {company_name} when:7d"
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    })
    try:
        text = request_text(url)
        root = ET.fromstring(text)
        items = []
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", default="")
            lowered = title.lower()
            if any(phrase in lowered for phrase in LOW_VALUE_NEWS_PHRASES):
                continue
            source = item.findtext("source", default="Google News")
            link = item.findtext("link", default="")
            published = item.findtext("pubDate", default="")
            items.append({"symbol": symbol, "title": title, "source": source, "link": link, "published": published})
        return items
    except Exception:
        return []


def sentiment_from_titles(news_items: list[dict]) -> tuple[float, int, int]:
    positive = 0
    negative = 0
    for item in news_items:
        words = set("".join(ch.lower() if ch.isalnum() else " " for ch in item.get("title", "")).split())
        positive += len(words & POSITIVE_TERMS)
        negative += len(words & NEGATIVE_TERMS)
    raw = positive - negative
    score = clamp(raw / 6, -1, 1)
    return score, positive, negative


def analyze_symbol(symbol: str) -> tuple[dict | None, list[dict]]:
    chart = yahoo_chart(symbol)
    if not chart or len(chart["rows"]) < 35:
        return None, []

    rows = chart["rows"]
    closes = [row["close"] for row in rows]
    volumes = [row["volume"] for row in rows if row["volume"] is not None]
    latest = closes[-1]

    daily = pct_change(closes[-2], closes[-1]) if len(closes) >= 2 else 0
    ret_5 = pct_change(closes[-6], closes[-1]) if len(closes) >= 6 else 0
    ret_20 = pct_change(closes[-21], closes[-1]) if len(closes) >= 21 else 0
    ret_60 = pct_change(closes[-61], closes[-1]) if len(closes) >= 61 else pct_change(closes[0], closes[-1])
    sma_20 = mean(closes[-20:])
    sma_50 = mean(closes[-50:]) if len(closes) >= 50 else mean(closes)
    day_returns = [pct_change(closes[i - 1], closes[i]) for i in range(1, len(closes)) if closes[i - 1]]
    vol_20 = statistics.stdev(day_returns[-20:]) if len(day_returns) >= 20 else statistics.stdev(day_returns) if len(day_returns) > 2 else 0
    avg_vol_20 = mean(volumes[-20:])
    volume_ratio = (volumes[-1] / avg_vol_20) if volumes and avg_vol_20 else 1
    peak_60 = max(closes[-60:]) if len(closes) >= 60 else max(closes)
    drawdown_60 = (latest / peak_60) - 1 if peak_60 else 0

    news = google_news(symbol, chart["shortName"])
    sentiment, pos_terms, neg_terms = sentiment_from_titles(news)
    buzz = min(len(news), 10) / 10

    trend_score = (
        clamp(ret_60 / 0.30, -1, 1) * 15
        + clamp(ret_20 / 0.15, -1, 1) * 15
        + (6 if latest > sma_20 else -6)
        + (6 if latest > sma_50 else -6)
    )
    momentum_score = clamp(ret_5 / 0.08, -1, 1) * 8 + clamp(daily / 0.04, -1, 1) * 4
    news_score = buzz * 8 + sentiment * 6
    liquidity_score = clamp((volume_ratio - 0.8) / 1.2, -1, 1) * 5
    risk_penalty = clamp((vol_20 - 0.022) / 0.035, 0, 1) * 18 + abs(min(drawdown_60, 0)) * 25
    raw_total = 45 + trend_score + momentum_score + news_score + liquidity_score - risk_penalty
    total_score = round(clamp(raw_total, 0, 100), 1)

    expected_20d = clamp((0.40 * ret_20) + (0.20 * ret_60 / 3) + (0.025 * sentiment) + (0.015 * clamp(volume_ratio - 1, -1, 2)), -0.18, 0.22)
    expected_low = expected_20d - min(0.18, vol_20 * math.sqrt(20) * 0.75)
    expected_high = expected_20d + min(0.18, vol_20 * math.sqrt(20) * 0.75)

    if total_score >= 75:
        signal = "Strong Watchlist"
    elif total_score >= 62:
        signal = "Watchlist"
    elif total_score >= 45:
        signal = "Neutral"
    else:
        signal = "Avoid / High Risk"

    row = {
        "symbol": symbol,
        "name": chart["shortName"],
        "price": round(latest, 2),
        "currency": chart["currency"],
        "daily_return": daily,
        "return_5d": ret_5,
        "return_20d": ret_20,
        "return_60d": ret_60,
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2),
        "above_sma20": latest > sma_20,
        "above_sma50": latest > sma_50,
        "volatility_20d": vol_20,
        "volume_ratio": volume_ratio,
        "drawdown_60d": drawdown_60,
        "news_count": len(news),
        "news_sentiment": sentiment,
        "positive_terms": pos_terms,
        "negative_terms": neg_terms,
        "score": total_score,
        "signal": signal,
        "expected_20d": expected_20d,
        "expected_low_20d": expected_low,
        "expected_high_20d": expected_high,
        "top_news": " | ".join(item["title"] for item in news[:3]),
    }
    return row, news


def load_portfolio(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol or symbol == "SYMBOL":
                continue
            rows.append({
                "symbol": symbol,
                "shares": safe_float(row.get("shares")),
                "avg_cost": safe_float(row.get("avg_cost")),
                "notes": row.get("notes", ""),
            })
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="News and market-data stock signal engine. Not investment advice.")
    parser.add_argument("--portfolio", default=str(ROOT / "portfolio_input.csv"), help="CSV with symbol, shares, avg_cost, notes")
    parser.add_argument("--symbols", default="", help="Optional comma-separated extra symbols")
    parser.add_argument("--limit", type=int, default=45, help="Maximum universe symbols to analyze")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    portfolio = load_portfolio(Path(args.portfolio))
    portfolio_symbols = [row["symbol"] for row in portfolio]
    extra_symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    universe = []
    for symbol in portfolio_symbols + extra_symbols + DEFAULT_UNIVERSE:
        if symbol not in universe:
            universe.append(symbol)
    universe = universe[: max(args.limit, len(portfolio_symbols) + len(extra_symbols))]

    results = []
    news_rows = []
    for index, symbol in enumerate(universe, 1):
        print(f"[{index}/{len(universe)}] analyzing {symbol}")
        row, news = analyze_symbol(symbol)
        if row:
            results.append(row)
            news_rows.extend(news)
        time.sleep(0.12)

    results.sort(key=lambda item: item["score"], reverse=True)
    result_by_symbol = {row["symbol"]: row for row in results}
    portfolio_outlook = []
    for holding in portfolio:
        signal = result_by_symbol.get(holding["symbol"])
        if not signal:
            continue
        shares = holding["shares"]
        avg_cost = holding["avg_cost"]
        market_value = shares * signal["price"]
        cost_basis = shares * avg_cost if avg_cost else 0
        unrealized = market_value - cost_basis if cost_basis else 0
        unrealized_pct = unrealized / cost_basis if cost_basis else 0
        portfolio_outlook.append({
            **holding,
            "name": signal["name"],
            "price": signal["price"],
            "market_value": market_value,
            "cost_basis": cost_basis,
            "unrealized_gain_loss": unrealized,
            "unrealized_gain_loss_pct": unrealized_pct,
            "score": signal["score"],
            "signal": signal["signal"],
            "expected_20d": signal["expected_20d"],
            "expected_low_20d": signal["expected_low_20d"],
            "expected_high_20d": signal["expected_high_20d"],
            "top_news": signal["top_news"],
        })

    as_of = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "as_of": as_of,
        "disclaimer": "Quantitative educational screen only. Not financial advice, not a buy/sell instruction, and not a guarantee of future returns.",
        "universe": universe,
        "rankings": results,
        "portfolio": portfolio_outlook,
        "news": news_rows,
        "methodology": {
            "score_components": "Trend, recent momentum, news buzz/sentiment, volume confirmation, volatility/drawdown risk penalty.",
            "expected_20d": "Heuristic scenario estimate from 20d/60d returns, news sentiment, and volume confirmation. It is not a price target.",
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "stock_signal_results.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_csv(output_dir / "stock_rankings.csv", results, list(results[0].keys()) if results else ["symbol"])
    if portfolio_outlook:
        write_csv(output_dir / "portfolio_outlook.csv", portfolio_outlook, list(portfolio_outlook[0].keys()))
    write_csv(output_dir / "news_items.csv", news_rows, ["symbol", "title", "source", "link", "published"])
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
