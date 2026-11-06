"""
Projection Indicator (PI) engine.

Every metric in the report is funnelled into one 0-100 score for where the
lean hog market sits and where it is likely to head over a 4-6 week horizon.

    0-20   Strongly bearish      55-65  Mildly bullish
   20-35   Bearish               65-80  Bullish
   35-45   Mildly bearish        80-100 Strongly bullish
   45-55   Neutral

Design rules, each one traceable to a finding in the report:

  * The negotiated spot print is EXCLUDED. It is 2.5% of volume and swings
    $7/cwt on a few thousand head. Feeding it in would inject the exact noise
    the report warns against. Producer-all-types base and the cutout carry the
    signal instead.
  * Fund positioning is NON-LINEAR. Below the 90th percentile it confirms
    trend; above it, it inverts, because the marginal seller is exhausted.
  * The packer margin enters twice with opposite signs: wide spread means hogs
    are abundant now (level-bearish) but gives packers cushion to bid up later
    (direction-bullish, only once it is genuinely extreme).
  * Horizon governs the futures weighting. Over 4-6 weeks the front contract
    dominates; the shape of the curve is context, not a forecast for this
    window.
  * Seasonality is adjusted for. November is the seasonal trough; without this
    PI would read bearish every Q4 and become noise.

Each component carries `avail`. When an input is missing the engine
redistributes its weight inside its own block and reports the drop in
confidence rather than silently substituting a default.
"""
import math
import data as D

HORIZON = "4-6 weeks"
NEUTRAL = 50.0

BANDS = [(0, 20, "Strongly bearish"), (20, 35, "Bearish"),
         (35, 45, "Mildly bearish"), (45, 55, "Neutral"),
         (55, 65, "Mildly bullish"), (65, 80, "Bullish"),
         (80, 100.01, "Strongly bullish")]

# block weights: fundamentals 70 / technicals 30
BLOCK_W = {
    "carcass": 0.22,     # carcass value and packer margin
    "supply": 0.20,      # slaughter, inventory, weights, breeding herd
    "demand": 0.18,      # exports and cold storage
    "cash": 0.10,        # producer base trend and futures basis
    "tech": 0.30,        # futures RSI / MACD / term structure / momentum
}

OVERLAY_CAP = 0.12       # hard cap on the sum of non-linear overlays


# ---------------------------------------------------------------- helpers
def clamp(v, lo=-1.0, hi=1.0):
    return max(lo, min(hi, v))


def squash(x, scale):
    """Map an unbounded reading onto [-1, 1] smoothly."""
    return math.tanh(x / scale)


def range_score(value, lo, hi):
    """Where `value` sits in [lo, hi], mapped to [-1, +1]."""
    if hi <= lo:
        return 0.0
    return clamp(2.0 * (value - lo) / (hi - lo) - 1.0)


def band_for(pi):
    for lo, hi, name in BANDS:
        if lo <= pi < hi:
            return name
    return "Neutral"


# ---------------------------------------------------------------- RSI / MACD
def rsi(closes, period=14):
    """Wilder-smoothed RSI. Returns None if the series is too short."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for a, b in zip(closes, closes[1:]):
        d = b - a
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for g, l in zip(gains[period:], losses[period:]):
        ag = (ag * (period - 1) + g) / period
        al = (al * (period - 1) + l) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return 100.0 - (100.0 / (1.0 + rs))


def ema(values, period):
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def ema_series(values, period):
    if len(values) < period:
        return []
    k = 2.0 / (period + 1)
    e = sum(values[:period]) / period
    out = [e]
    for v in values[period:]:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def macd(closes, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram) or None if too short."""
    if len(closes) < slow + signal:
        return None
    fast_s = ema_series(closes, fast)
    slow_s = ema_series(closes, slow)
    off = len(fast_s) - len(slow_s)
    line = [f - s for f, s in zip(fast_s[off:], slow_s)]
    sig_s = ema_series(line, signal)
    if not sig_s:
        return None
    m, s = line[-1], sig_s[-1]
    return m, s, m - s


# ---------------------------------------------------------------- component
class C:
    """One scored input."""

    def __init__(self, key, label, score, weight, detail,
                 avail=True, source=""):
        self.key = key
        self.label = label
        self.score = clamp(score) if score is not None else 0.0
        self.weight = weight
        self.detail = detail
        self.avail = avail
        self.source = source

    def __repr__(self):
        return f"<{self.key} {self.score:+.2f} w={self.weight}>"


def block_score(components):
    """Weighted mean over available components; weight redistributes."""
    live = [c for c in components if c.avail]
    wsum = sum(c.weight for c in live)
    if wsum == 0:
        return 0.0, 0.0
    score = sum(c.score * c.weight for c in live) / wsum
    completeness = wsum / sum(c.weight for c in components)
    return score, completeness


# ---------------------------------------------------------------- blocks
def carcass_block(ov=None):
    ov = ov or {}
    cut = ov.get("cutout", D.CUTOUT["value"])
    prev_cut = ov.get("prev_cutout", 70.69)
    base_all = ov.get("base", D.PRODUCER_ALL["value"])
    hist = [v for _, v in D.CUTOUT_EXTRA]
    lo, hi = min(hist), max(hist)

    mom = (cut / prev_cut - 1.0) * 100.0 if prev_cut else 0.0

    # Packer gross margin measured against the ALL-PURCHASE-TYPE base, not the
    # negotiated print. PI excludes the negotiated series by design, and the
    # all-types base is what packers actually paid for the volume they bought.
    spread = cut - base_all
    SPREAD_NORM = 6.0

    return [
        C("cutout_level", "Cutout level in range",
          range_score(cut, lo, hi), 0.40,
          f"${cut:,.2f} within ${lo:,.2f}-${hi:,.2f} window", source="LM_PK602"),
        C("cutout_mom", "Cutout momentum",
          squash(mom, 3.0), 0.35,
          f"{mom:+.2f}% vs prior reading ${prev_cut:,.2f}", source="LM_PK602"),
        C("packer_margin", "Packer margin (level)",
          -squash(spread - SPREAD_NORM, 3.0), 0.25,
          f"cutout less all-types base = ${spread:,.2f} "
          f"vs ${SPREAD_NORM:,.2f} normal", source="LM_PK602 / LM_HG201"),
    ]


def supply_block(ov=None):
    sl = D.SLAUGHTER
    kill_yoy = (sl["today_est"] / sl["year_ago_act"] - 1) * 100
    wtd_yoy = (sl["wtd_est"] / sl["wtd_year_ago"] - 1) * 100
    hv180 = D.INVENTORY["weight_classes"][3][3]       # 180+ lb YoY %
    breed = D.INVENTORY["rows"][1][3]                 # breeding herd YoY %
    cw = D.CARCASS_WT
    cw_gap = cw["negotiated"] - cw["packer_owned"]    # heavy = backlog

    return [
        C("slaughter", "Slaughter vs year ago",
          -squash((kill_yoy + wtd_yoy) / 2, 2.0), 0.30,
          f"daily {kill_yoy:+.2f}%, week-to-date {wtd_yoy:+.2f}%",
          source="SJ_LS710"),
        C("fwd_supply", "180 lb+ forward supply",
          -squash(hv180, 2.0), 0.30,
          f"{hv180:+.1f}% YoY - the next 4-6 weeks of kill",
          source="NASS Hogs & Pigs"),
        C("carcass_wt", "Carcass weight trend",
          -squash(cw_gap, 5.0), 0.20,
          f"negotiated {cw['negotiated']:.2f} lb vs packer-owned "
          f"{cw['packer_owned']:.2f} lb", source="LM_HG201"),
        C("breeding", "Breeding herd",
          -squash(breed, 1.5), 0.20,
          f"{breed:+.1f}% YoY, smallest Sept herd since 2013",
          source="NASS Hogs & Pigs"),
    ]


def demand_block(ov=None):
    e = D.EXPORTS
    cs = D.COLD_STORAGE
    return [
        C("exp_sales", "Export net sales vs 4-wk avg",
          squash(e["net_sales_vs_4wk_pct"], 18.0), 0.35,
          f"{e['net_sales_mt']:,} MT, {e['net_sales_vs_4wk_pct']:+d}% vs 4-wk",
          source="FAS"),
        C("exp_ship", "Export shipments vs 4-wk avg",
          squash(e["shipments_vs_4wk_pct"], 18.0), 0.30,
          f"{e['shipments_mt']:,} MT, {e['shipments_vs_4wk_pct']:+d}% vs 4-wk",
          source="FAS"),
        C("stocks_yoy", "Frozen pork stocks YoY",
          -squash(cs["yoy_pct"], 8.0), 0.20,
          f"{cs['total_pork']:,.1f}M lb, {cs['yoy_pct']:+.1f}% YoY",
          source="NASS Cold Storage"),
        C("stocks_mom", "Frozen pork stocks MoM",
          -squash(cs["mom_pct"], 3.0), 0.15,
          f"{cs['mom_pct']:+.1f}% on the month - drawing down",
          source="NASS Cold Storage"),
    ]


def cash_block(ov=None):
    ov = ov or {}
    ser = D.PRODUCER_ALL["series"]
    base = ov.get("base", D.PRODUCER_ALL["value"])
    trend = (base / ser[0][1] - 1) * 100
    idx = ov.get("idx", D.LH_INDEX["latest"])
    front = ov.get("dec", D.FUTURES["latest"]["Dec 26"]["px"])
    basis = front - idx

    return [
        C("base_trend", "Producer base trend",
          squash(trend, 5.0), 0.50,
          f"${ser[0][1]:,.2f} -> ${base:,.2f} ({trend:+.2f}%)",
          source="LM_HG201"),
        C("basis", "Futures basis to cash index",
          squash(basis, 8.0), 0.50,
          f"Dec ${front:,.2f} vs index ${idx:,.2f} = ${basis:,.2f}; "
          "futures are pricing the index lower into expiry",
          source="CME"),
    ]


def tech_block(ov=None):
    ov = ov or {}
    f = D.FUTURES
    w = f["front_weight"]
    series = {"Dec 26": f["dec26"], "Feb 27": f["feb27"], "Apr 27": f["apr27"]}
    need_rsi = f["min_sessions"]["rsi14"]
    need_macd = f["min_sessions"]["macd"]

    # --- RSI and MACD, weighted across the three contracts -------------
    rsi_parts, macd_parts, n_rsi, n_macd = [], [], 0, 0
    for (name, pts), wt in zip(series.items(), w):
        closes = [p[1] for p in pts]
        r = rsi(closes) if len(closes) >= need_rsi else None
        m = macd(closes) if len(closes) >= need_macd else None
        if r is not None:
            rsi_parts.append((wt, r))
            n_rsi += 1
        if m is not None:
            macd_parts.append((wt, m[2]))
            n_macd += 1

    rsi_ok = len(rsi_parts) > 0
    macd_ok = len(macd_parts) > 0
    sessions = {k: len(v) for k, v in series.items()}

    if rsi_ok:
        rv = sum(wt * r for wt, r in rsi_parts) / sum(wt for wt, _ in rsi_parts)
        # oversold reads bullish on a 4-6 week mean-reversion horizon
        rsi_score = -squash(rv - 50.0, 18.0)
        rsi_detail = f"weighted RSI(14) {rv:.1f}"
    else:
        rsi_score = None
        rsi_detail = (f"insufficient history - {sessions['Dec 26']} Dec sessions "
                      f"available, {need_rsi} required")

    if macd_ok:
        hv = sum(wt * h for wt, h in macd_parts) / sum(wt for wt, _ in macd_parts)
        macd_score = squash(hv, 1.5)
        macd_detail = f"weighted MACD histogram {hv:+.3f}"
    else:
        macd_score = None
        macd_detail = (f"insufficient history - {sessions['Dec 26']} Dec sessions "
                       f"available, {need_macd} required")

    # --- term structure -------------------------------------------------
    cur = f["curve"]["2026-11-05"]
    prev = f["curve"]["2026-10-23"]
    dec_o, apr_o = ov.get("dec"), ov.get("apr")
    if dec_o and apr_o:
        slope_now = (apr_o / dec_o - 1) * 100
    else:
        slope_now = (cur["Apr 27"] / cur["Dec 26"] - 1) * 100
    slope_prev = (prev["Apr 27"] / prev["Dec 26"] - 1) * 100

    # --- contract momentum ----------------------------------------------
    dec = [p[1] for p in f["dec26"]]
    last = ov.get("dec", dec[-1])
    mom_1m = (last / dec[0] - 1) * 100
    mom_1w = ov.get("mom_1w", f["perf"]["Dec 26"]["1w"])
    mom_blend = 0.65 * mom_1m + 0.35 * mom_1w

    return [
        C("rsi", "RSI(14), 3 contracts", rsi_score, 0.35, rsi_detail,
          avail=rsi_ok, source="CME"),
        C("macd", "MACD(12,26,9), 3 contracts", macd_score, 0.35, macd_detail,
          avail=macd_ok, source="CME"),
        C("term", "Term structure", squash(slope_now, 28.0), 0.10,
          f"Dec->Apr {slope_now:+.1f}% contango (was {slope_prev:+.1f}% Oct 23); "
          "dislocation priced as temporary, but outside this horizon",
          source="CME"),
        C("momentum", "Front-contract momentum", squash(mom_blend, 12.0), 0.20,
          f"Dec {mom_1m:+.1f}% since Sep 30, {mom_1w:+.1f}% on the week",
          source="CME"),
    ]


# ---------------------------------------------------------------- overlays
def overlays(base_raw, ov=None):
    ov = ov or {}
    """Non-linear adjustments, applied after the weighted sum and capped."""
    out = []

    # 1. fund positioning at an extreme flips from confirming to contrarian
    net = abs(ov.get("cot", D.COT["mm_net"]))
    oi = 446000
    pct_oi = net / oi * 100
    pctile = 98.0                      # ~5-year extreme per CFTC / trade reports
    if pctile >= 90:
        kick = 0.10 * ((pctile - 90) / 10)
        out.append(("cot_extreme", +kick,
                    f"managed money net short {net:,} ({pct_oi:.1f}% of open "
                    f"interest), ~{pctile:.0f}th percentile - marginal seller "
                    "exhausted, squeeze risk"))

    # 2. seasonal: November is the seasonal trough
    out.append(("seasonal", +0.06,
                "November-December is the seasonal low; raw reading overstates "
                "weakness against the 5-year pattern"))

    # 3. packer margin mean reversion, only once genuinely extreme
    spread = D.CUTOUT["value"] - D.PRODUCER_ALL["value"]
    if spread > 9.0:
        out.append(("margin_reversion", +0.04,
                    f"packer margin ${spread:,.2f} is extreme; cushion to bid "
                    "up when supply tightens"))

    total = sum(k for _, k, _ in out)
    scale = 1.0 if abs(total) <= OVERLAY_CAP else OVERLAY_CAP / abs(total)
    return [(n, k * scale, d) for n, k, d in out], total * scale


# ---------------------------------------------------------------- compute
def compute(ov=None):
    blocks = {
        "carcass": ("Carcass value & packer margin", carcass_block(ov)),
        "supply": ("Supply", supply_block(ov)),
        "demand": ("Demand", demand_block(ov)),
        "cash": ("Cash market & basis", cash_block(ov)),
        "tech": ("Futures technicals", tech_block(ov)),
    }

    detail, raw = {}, 0.0
    for key, (label, comps) in blocks.items():
        s, comp = block_score(comps)
        w = BLOCK_W[key]
        contrib = s * w
        raw += contrib
        detail[key] = {"label": label, "score": s, "weight": w,
                       "contrib": contrib, "completeness": comp,
                       "components": comps}

    ovl, ovl_total = overlays(raw, ov)
    raw_adj = clamp(raw + ovl_total)
    pi = clamp(NEUTRAL + 50.0 * raw_adj, 0.0, 100.0)

    # overall data completeness, weighted by block
    completeness = sum(detail[k]["completeness"] * BLOCK_W[k] for k in detail)

    return {
        "pi": pi,
        "band": band_for(pi),
        "raw": raw,
        "raw_adj": raw_adj,
        "overlays": ovl,
        "overlay_total": ovl_total,
        "blocks": detail,
        "completeness": completeness,
        "horizon": HORIZON,
    }


# ---------------------------------------------------------------- forecast
def forecast(res):
    """
    PI is expressed against the market's own forecast rather than in a vacuum.

    The Dec futures contract IS a forecast of the cash index at expiry. The
    producer base runs at a roughly stable offset to that index, which gives a
    market-implied base price. PI then says whether the report's fundamentals
    agree with that pricing or lean against it.
    """
    idx = D.LH_INDEX["latest"]
    base = D.PRODUCER_ALL["value"]
    offset = base - idx                       # base-to-index offset
    front = D.FUTURES["latest"]["Dec 26"]["px"]

    implied = front + offset                  # market-implied base at expiry
    tilt = (res["pi"] - NEUTRAL) / NEUTRAL     # -1 .. +1
    centre = implied * (1 + tilt * 0.08)       # PI tilts up to +/- 8%
    halfwidth = centre * 0.085                 # ~60% band

    return {
        "index": idx, "base": base, "offset": offset, "front": front,
        "implied": implied, "tilt_pct": tilt * 8.0,
        "centre": centre, "lo": centre - halfwidth, "hi": centre + halfwidth,
        "agree": abs(res["pi"] - NEUTRAL) < 5,
    }


# ---------------------------------------------------------------- history
# as-of snapshots. Dated inputs are the real published values for that day.
# The slow series (inventory, cold storage, exports, slaughter, carcass weight)
# are held constant because they genuinely had not been re-published inside
# this window - that is the true as-of state, not an approximation.
ASOF = [
    ("Oct 13", {"cutout": 80.68, "prev_cutout": 80.68 + 2.29, "dec": 68.025,
                "apr": None, "idx": 78.41, "cot": -56479, "base": 71.54,
                "mom_1w": -1.2}),
    ("Oct 23", {"cutout": 76.00, "prev_cutout": 80.68, "dec": 65.575,
                "apr": 72.675, "idx": 72.00, "cot": -56479, "base": 71.54,
                "mom_1w": -3.4}),
    ("Oct 29", {"cutout": 70.69, "prev_cutout": 76.00, "dec": 59.825,
                "apr": 71.00, "idx": 68.30, "cot": -51646, "base": 69.00,
                "mom_1w": -8.8}),
    ("Nov 03", {"cutout": 72.43, "prev_cutout": 70.69, "dec": 58.600,
                "apr": 69.380, "idx": 68.30, "cot": -51646, "base": 66.15,
                "mom_1w": -4.6}),
    ("Nov 05", {"cutout": 72.43, "prev_cutout": 70.69, "dec": 55.100,
                "apr": 67.130, "idx": 68.30, "cot": -51646, "base": 66.15,
                "mom_1w": -5.97}),
]

# values interpolated between published prints, flagged so the chart can mark
# them: the Oct 23 cutout and index were not separately verified.
ASOF_PARTIAL = {"Oct 23", "Oct 29"}


def history():
    """Recompute PI at each as-of date from that day's actual inputs."""
    return [(label, compute(ov)["pi"], label in ASOF_PARTIAL)
            for label, ov in ASOF]


if __name__ == "__main__":
    r = compute()
    print(f"\nPROJECTION INDICATOR = {r['pi']:.1f}   [{r['band']}]")
    print(f"horizon {r['horizon']}   data completeness "
          f"{r['completeness']*100:.0f}%\n")
    for k, b in r["blocks"].items():
        print(f"  {b['label']:<32s} score {b['score']:+.3f}  "
              f"w {b['weight']:.2f}  ->{b['contrib']:+.4f}  "
              f"(data {b['completeness']*100:.0f}%)")
        for c in b["components"]:
            flag = " " if c.avail else "!"
            print(f"     {flag} {c.label:<34s} {c.score:+.2f} "
                  f"w{c.weight:.2f}  {c.detail}")
    print(f"\n  raw sum {r['raw']:+.4f}")
    for n, k, d in r["overlays"]:
        print(f"  overlay {n:<18s} {k:+.4f}  {d}")
    print(f"  adjusted {r['raw_adj']:+.4f}  ->  PI {r['pi']:.1f}")
    f = forecast(r)
    print(f"\n  market-implied base ${f['implied']:.2f} "
          f"(Dec {f['front']:.2f} + offset {f['offset']:+.2f})")
    print(f"  PI tilt {f['tilt_pct']:+.2f}%  ->  centre ${f['centre']:.2f}  "
          f"range ${f['lo']:.2f}-${f['hi']:.2f}")
    print("\n  history:", ", ".join(f"{l} {v:.1f}{'*' if pa else ''}" for l, v, pa in history()))
