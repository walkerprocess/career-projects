import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const inputPath = process.argv[2] || path.join(root, "outputs", "latest", "stock_signal_results.json");
const outputPath = process.argv[3] || path.join(root, "outputs", "latest", "stock_signal_report.xlsx");
const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));

const wb = Workbook.create();
const dashboard = wb.worksheets.add("Dashboard");
const top = wb.worksheets.add("Top Signals");
const portfolio = wb.worksheets.add("Portfolio Outlook");
const news = wb.worksheets.add("News Signals");
const methodology = wb.worksheets.add("Methodology");
const checks = wb.worksheets.add("Checks");

const colors = {
  navy: "#17202F",
  blue: "#2563EB",
  teal: "#0F766E",
  amber: "#F59E0B",
  red: "#DC2626",
  paleBlue: "#EEF3F8",
  paleGreen: "#EAF7F2",
  paleRed: "#FDECEC",
  border: "#D9E0EA",
  white: "#FFFFFF",
  muted: "#687386",
};

function setTitle(sheet, title, subtitle) {
  sheet.showGridLines = false;
  sheet.getRange("A1:H1").merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format = {
    fill: colors.navy,
    font: { bold: true, color: colors.white, size: 18 },
  };
  sheet.getRange("A2:H2").merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A2").format = {
    fill: colors.paleBlue,
    font: { color: colors.muted, italic: true },
  };
}

function writeHeader(range) {
  range.format = {
    fill: colors.navy,
    font: { bold: true, color: colors.white },
  };
}

function pct(value) {
  return typeof value === "number" ? value : 0;
}

function signalFill(signal) {
  if (signal === "Strong Watchlist") return colors.paleGreen;
  if (signal === "Watchlist") return "#F4FAEE";
  if (signal === "Neutral") return "#FFF8E8";
  return colors.paleRed;
}

const rankings = payload.rankings || [];
const portfolioRows = payload.portfolio || [];
const newsRows = payload.news || [];
const top10 = rankings.slice(0, 10);
const watchlistCount = rankings.filter(r => r.signal === "Strong Watchlist" || r.signal === "Watchlist").length;
const avoidCount = rankings.filter(r => r.signal === "Avoid / High Risk").length;
const avgScore = rankings.length ? rankings.reduce((sum, r) => sum + Number(r.score || 0), 0) / rankings.length : 0;

setTitle(dashboard, "Stock Signal Dashboard", `As of ${payload.as_of}. Educational quantitative screen only, not financial advice.`);
dashboard.getRange("A4:D4").values = [["Universe", "Watchlist", "Avoid / High Risk", "Avg Score"]];
writeHeader(dashboard.getRange("A4:D4"));
dashboard.getRange("A5:D5").values = [[rankings.length, watchlistCount, avoidCount, avgScore]];
dashboard.getRange("A5:D5").format = { font: { bold: true, size: 16 } };
dashboard.getRange("D5").format.numberFormat = "0.0";

dashboard.getRange("A7:H7").values = [["Rank", "Ticker", "Company", "Score", "Signal", "20D Expected", "Low Case", "High Case"]];
writeHeader(dashboard.getRange("A7:H7"));
dashboard.getRange(`A8:H${7 + top10.length}`).values = top10.map((r, i) => [
  i + 1,
  r.symbol,
  r.name,
  r.score,
  r.signal,
  pct(r.expected_20d),
  pct(r.expected_low_20d),
  pct(r.expected_high_20d),
]);
dashboard.getRange(`D8:D${7 + top10.length}`).format.numberFormat = "0.0";
dashboard.getRange(`F8:H${7 + top10.length}`).format.numberFormat = "0.0%";
for (let i = 0; i < top10.length; i++) {
  dashboard.getRange(`E${8 + i}`).format = { fill: signalFill(top10[i].signal) };
}

dashboard.getRange("J7:K7").values = [["Ticker", "Score"]];
dashboard.getRange(`J8:K${7 + top10.length}`).values = top10.map(r => [r.symbol, r.score]);
const scoreChart = dashboard.charts.add("bar", dashboard.getRange(`J7:K${7 + top10.length}`));
scoreChart.title = "Top 10 Signal Scores";
scoreChart.hasLegend = false;
scoreChart.setPosition("J2", "Q18");
dashboard.getRange("A20:H23").merge();
dashboard.getRange("A20").values = [[payload.disclaimer]];
dashboard.getRange("A20").format = { fill: "#FFF8E8", font: { color: colors.navy, italic: true }, wrapText: true };

setTitle(top, "Ranked Stock Signals", "Direct algorithm using price trend, momentum, news buzz, sentiment, volume, volatility, and drawdown risk.");
const topHeaders = [
  "Rank", "Ticker", "Company", "Price", "Score", "Signal", "Daily", "5D", "20D", "60D",
  "20D Expected", "Low Case", "High Case", "Vol 20D", "Volume Ratio", "News Count", "News Sentiment", "Top News"
];
top.getRange("A4:R4").values = [topHeaders];
writeHeader(top.getRange("A4:R4"));
top.getRange(`A5:R${4 + rankings.length}`).values = rankings.map((r, i) => [
  i + 1, r.symbol, r.name, r.price, r.score, r.signal, r.daily_return, r.return_5d, r.return_20d, r.return_60d,
  r.expected_20d, r.expected_low_20d, r.expected_high_20d, r.volatility_20d, r.volume_ratio, r.news_count, r.news_sentiment, r.top_news
]);
top.getRange(`D5:E${4 + rankings.length}`).format.numberFormat = "0.00";
top.getRange(`G5:N${4 + rankings.length}`).format.numberFormat = "0.0%";
top.getRange(`O5:O${4 + rankings.length}`).format.numberFormat = "0.00x";
top.getRange("R:R").format = { wrapText: true };
top.freezePanes.freezeRows(4);

setTitle(portfolio, "Portfolio Outlook", "Uses portfolio_input.csv. Shares and average cost can be zero for watch-only tickers.");
const portfolioHeaders = [
  "Ticker", "Company", "Shares", "Avg Cost", "Price", "Market Value", "Cost Basis", "Unrealized $",
  "Unrealized %", "Score", "Signal", "20D Expected", "Low Case", "High Case", "Notes", "Top News"
];
portfolio.getRange("A4:P4").values = [portfolioHeaders];
writeHeader(portfolio.getRange("A4:P4"));
if (portfolioRows.length) {
  portfolio.getRange(`A5:P${4 + portfolioRows.length}`).values = portfolioRows.map(r => [
    r.symbol, r.name, r.shares, r.avg_cost, r.price, r.market_value, r.cost_basis, r.unrealized_gain_loss,
    r.unrealized_gain_loss_pct, r.score, r.signal, r.expected_20d, r.expected_low_20d, r.expected_high_20d,
    r.notes, r.top_news
  ]);
  portfolio.getRange(`D5:H${4 + portfolioRows.length}`).format.numberFormat = "$#,##0.00;[Red]($#,##0.00);-";
  portfolio.getRange(`I5:I${4 + portfolioRows.length}`).format.numberFormat = "0.0%;[Red](0.0%);-";
  portfolio.getRange(`L5:N${4 + portfolioRows.length}`).format.numberFormat = "0.0%";
  portfolio.getRange("P:P").format = { wrapText: true };
} else {
  portfolio.getRange("A5:P5").merge();
  portfolio.getRange("A5").values = [["No portfolio rows found. Edit portfolio_input.csv to add holdings or watch-only tickers."]];
}
portfolio.freezePanes.freezeRows(4);

setTitle(news, "News Signals", "Recent Google News RSS items used for buzz and keyword sentiment.");
news.getRange("A4:E4").values = [["Ticker", "Title", "Source", "Published", "Link"]];
writeHeader(news.getRange("A4:E4"));
if (newsRows.length) {
  news.getRange(`A5:E${4 + newsRows.length}`).values = newsRows.map(r => [r.symbol, r.title, r.source, r.published, r.link]);
  news.getRange("B:B").format = { wrapText: true };
  news.getRange("E:E").format = { wrapText: true };
}
news.freezePanes.freezeRows(4);

setTitle(methodology, "Methodology", "The model is explainable and does not call GPT for scoring.");
methodology.getRange("A4:B13").values = [
  ["Item", "Explanation"],
  ["Purpose", "Rank stocks that are hot in price action and news while penalizing risk. This is an educational screen."],
  ["Trend", "60-day and 20-day returns plus price above/below 20-day and 50-day moving averages."],
  ["Momentum", "5-day and 1-day returns to capture short-term acceleration."],
  ["News", "Google News RSS item count and simple positive/negative keyword sentiment."],
  ["Volume", "Latest volume relative to 20-day average volume."],
  ["Risk", "20-day volatility and 60-day drawdown reduce the score."],
  ["Expected 20D", "Heuristic scenario estimate from momentum, sentiment, and volume. It is not a price target."],
  ["Signals", "Strong Watchlist >=75, Watchlist >=62, Neutral >=45, otherwise Avoid / High Risk."],
  ["Disclaimer", payload.disclaimer],
];
writeHeader(methodology.getRange("A4:B4"));
methodology.getRange("B:B").format = { wrapText: true };

setTitle(checks, "Checks", "Basic workbook/data integrity checks.");
checks.getRange("A4:E9").values = [
  ["Check", "Actual", "Expected", "Status", "Notes"],
  ["Ranking rows", rankings.length, "> 0", rankings.length > 0 ? "OK" : "FAIL", "Must have stock data."],
  ["News rows", newsRows.length, "> 0", newsRows.length > 0 ? "OK" : "WARN", "News API may fail or return sparse results."],
  ["Portfolio rows", portfolioRows.length, ">= 0", "OK", "Zero is acceptable if portfolio_input.csv is blank."],
  ["Score max", Math.max(...rankings.map(r => Number(r.score || 0))), "<= 100", Math.max(...rankings.map(r => Number(r.score || 0))) <= 100 ? "OK" : "FAIL", "Scores are clamped."],
  ["Score min", Math.min(...rankings.map(r => Number(r.score || 0))), ">= 0", Math.min(...rankings.map(r => Number(r.score || 0))) >= 0 ? "OK" : "FAIL", "Scores are clamped."],
];
writeHeader(checks.getRange("A4:E4"));

for (const sheet of [dashboard, top, portfolio, news, methodology, checks]) {
  sheet.getRange("A:Z").format.font = { name: "Aptos", size: 10 };
  sheet.getRange("A:Z").format.verticalAlignment = "Top";
  sheet.getRange("A:A").format.columnWidthPx = 88;
  sheet.getRange("B:B").format.columnWidthPx = 120;
  sheet.getRange("C:C").format.columnWidthPx = 220;
}
dashboard.getRange("C:C").format.columnWidthPx = 250;
dashboard.getRange("E:E").format.columnWidthPx = 140;
dashboard.getRange("F:H").format.columnWidthPx = 92;
top.getRange("R:R").format.columnWidthPx = 420;
portfolio.getRange("P:P").format.columnWidthPx = 420;
news.getRange("B:B").format.columnWidthPx = 420;
news.getRange("E:E").format.columnWidthPx = 360;
methodology.getRange("A:A").format.columnWidthPx = 160;
methodology.getRange("B:B").format.columnWidthPx = 620;

await fs.mkdir(path.dirname(outputPath), { recursive: true });

const preview = await wb.render({ sheetName: "Dashboard", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(path.join(path.dirname(outputPath), "stock_signal_dashboard_preview.png"), new Uint8Array(await preview.arrayBuffer()));

const errorScan = await wb.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errorScan.ndjson);

const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);
console.log(`Wrote ${outputPath}`);
