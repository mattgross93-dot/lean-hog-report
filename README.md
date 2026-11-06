# US Lean Hog Market Report

A print-ready daily briefing on the US lean hog market: price complex, supply,
demand, speculative positioning, and a composite **Projection Indicator (PI)**.

Built for Matthew — Canadian hog production, ISO weans finished in Iowa and
marketed through Smithfield.

## Running it

```bash
pip install -r requirements.txt
python3 build.py          # validates, builds, writes run_status.json
```

`build.py` exits `10` on non-market days and sends nothing.

## Layout

| File | Role |
|---|---|
| `daily.json` | **every value that changes between runs.** The only file a daily update needs to touch |
| `data.py` | static source definitions and derived helpers; loads `daily.json` over its defaults |
| `pi.py` | the Projection Indicator engine — normalisation, blocks, overlays, RSI, MACD |
| `charts.py` | all matplotlib figures in the report's house style |
| `report.py` | ReportLab document assembly |
| `validate.py` | market-day detection and the per-series freshness gate |
| `build.py` | entry point: validate → build → status |
| `RUNBOOK.md` | **the daily procedure, including source gotchas. Read before editing anything** |

## The Projection Indicator

Resolves every metric in the report into one 0-100 score for where the market
is heading over 4-6 weeks. 50 is neutral. Weighted 70% fundamentals, 30%
futures technicals.

Design decisions, each traceable to a finding in the report:

- **The negotiated spot price is excluded.** It is ~2.5% of plant-delivered
  volume and swings $7/cwt on a few thousand head. Packer margin is measured
  against the all-purchase-type base instead.
- **Fund positioning is non-linear.** Below the 90th percentile it confirms
  trend; above it, it inverts and turns contrarian, because the marginal seller
  is exhausted.
- **Horizon governs the futures weighting.** Over 4-6 weeks the front contract
  dominates (60/25/15 across Dec/Feb/Apr). Curve shape is context for a later
  horizon, not a forecast for this one.
- **Seasonality is adjusted for**, or PI would read bearish every Q4 and become
  noise.
- **Missing inputs are never substituted.** Weight redistributes inside the
  block and the confidence loss is reported on the face of the report.

PI is read *against the market's own forecast*: the front contract is itself a
forecast of the cash index at expiry, so PI says whether the fundamentals agree
with how futures are priced, not whether the market is "good" in a vacuum.

**PI is a structured opinion, not a validated model.** Until there is enough
history to backtest, it has no measured hit rate, and its 60% band is a
judgement rather than a confidence interval. Its value is that it is explicit
and auditable — the report shows every input, weight and score.

## Known gaps

- **RSI and MACD are inactive.** Both are implemented and validated (RSI
  reproduces Wilder's worked example to within 0.07), but need 30 and 60
  sessions of per-contract history. See `RUNBOOK.md` §5.
- **Trend charts are short.** Ten years of history needs the AMS Datamart API
  and NASS QuickStats rather than the published PDFs.
- **FX is hardcoded** and needs a live source.
