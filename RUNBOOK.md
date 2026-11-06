# Daily run procedure

This is the instruction set for the scheduled agent. Follow it in order.
Everything the report needs lives in `daily.json`; the Python never reaches the
network, so **gathering the data is your job**, not the script's.

---

## 0. Check the date first

```bash
python3 validate.py            # or: python3 validate.py YYYY-MM-DD
```

If it reports `action SKIP`, the target was a weekend or a CME holiday.
**Stop. Send nothing.** This is a normal outcome, not a failure.

---

## 1. Gather today's figures

Update the keys below in `daily.json`. Set each block's `asof` to the real
publication date of the figure you found — **never to today's date just because
you ran today**. The freshness gate depends on those dates being truthful, and a
carried-forward number labelled as current is the one failure mode that matters.

### Core (the report is flagged if these cannot be confirmed)

| Block | What to update | Where it comes from |
|---|---|---|
| `CUTOUT` | `value`, `prior`, `chg`, `loads`, `primals`, `asof` | USDA AMS Daily Pork Report FOB Plant PM (LM_PK602) |
| `FUTURES` | `latest` prices for Dec/Feb/Apr, `curve` snapshot, append to `dec26`/`feb27`/`apr27`, `asof` | CME settlements |
| `PRODUCER_ALL` | `value`, `head`, append to `series`, `asof` | USDA AMS LM_HG201 |

### Daily

| Block | Notes |
|---|---|
| `NEGOTIATED` | `value`, `chg`, `roll5`, `head`, `low`, `high`. Reported but deliberately **excluded from PI**. |
| `PURCHASE_TYPES` | `rows` — head count and price per purchase type. Drives the thin-market analysis. |
| `SLAUGHTER` | daily estimate, week-to-date, year-ago |
| `CARCASS_WT` | by purchase type |
| `FEED` | Dec corn and soybean meal settlements |
| `FX_USDCAD` | needs a live rate; currently hardcoded |

### Weekly

`COT` (Friday, positions as of Tuesday) · `EXPORTS` (Thursday, FAS) ·
`FEEDER_PIGS` (SEW 10-12 lb) · `SOWS`

### Monthly / quarterly

`COLD_STORAGE` (~22nd-25th) · `INVENTORY` (quarterly Hogs & Pigs) ·
`BYPRODUCT`

---

## 2. Source notes — read these, they cost real time to learn

**The AMS `mnreports/*.pdf` endpoints serve stale snapshots.** On 5 Nov 2026 they
returned files dated 20 and 23 Oct. Always check the report date printed inside
the document against what you expected. Prefer
`mymarketnews.ams.usda.gov` or the Datamart API where you can reach them.

**Commercial aggregators mis-parse the AMS table layouts.** One published the
cutout at `$183.77` against a true `$72.43`, apparently by summing columns.
**Cross-check every price against a second source** before writing it in. If two
sources disagree materially, treat the figure as unverified and let the gate
flag it rather than picking one.

**Never splice a front-month continuous futures series.** On 9 Oct 2026 the
expiring October contract settled `$75.05` while December settled `$67.825`.
A continuous series spliced across that roll fabricates a 7-point crash.
Each contract keeps its own history in `daily.json`.

**Sources that worked**, roughly in order of reliability:
CME settlements via FXEmpire / Investing.com / Farmbucks (all three agreed on
5 Nov) · ThePigSite daily CME wire reports (good for dated cutout and index) ·
Brownfield and Yahoo ag wires · TradingEconomics (front-month only; its
"1 month" change splices contracts, so do not use it for momentum).

---

## 3. Build

```bash
python3 build.py
```

- exit `0` — PDF built, `run_status.json` has the subject line and summary
- exit `10` — not a market day, send nothing
- exit `1` — build failed, read the traceback in `run_status.json`

---

## 4. Send

Read `run_status.json` and email `US_Lean_Hog_Market_Report.pdf` using the
`subject` and `summary` it provides.

Append to the body when `stale` is non-empty, so the reader knows before they
open the PDF:

> Data note: N of 15 series were confirmed for this session. Carried forward:
> &lt;list&gt;. Each figure in the report carries its own as-of date.

---

## 5. Appending to the futures history

Each run appends one dated close per contract to `dec26`, `feb27`, `apr27` as
`[date, close, derived]`. Set `derived` to `true` when the close was
back-calculated from a published daily change rather than read directly.

**This is what eventually switches RSI and MACD on.** Both are implemented and
validated; they activate automatically once `dec26` reaches 30 entries (RSI) and
60 (MACD). Until then the technical block runs on term structure and momentum
only, at reduced weight, and PI reports the shortfall rather than guessing.
Do not pad the series to reach the threshold sooner.
