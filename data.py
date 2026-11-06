"""
Lean Hog Market Report - data layer.

Every figure carries its own `asof` date and `src` key so the report can show
per-metric staleness. In the scheduled version, each block below is replaced by
a live pull from the endpoint named in SOURCES.
"""

REPORT_DATE = "2026-11-05"
FX_USDCAD = 1.3850          # USD -> CAD. Approximate; needs live pull.
FX_ASOF = "2026-11-05 (approx.)"

# ---------------------------------------------------------------- sources
SOURCES = {
    "LM_HG218": ("USDA AMS Daily Direct Prior Day Hog Report (LM_HG218)",
                 "ams.usda.gov/mnreports/ams_3458.pdf"),
    "LM_HG201": ("USDA AMS National Daily Direct Prior Day Slaughtered Swine (LM_HG201)",
                 "mymarketnews.ams.usda.gov/viewreport/2872"),
    "LM_PK602": ("USDA AMS National Daily Pork Report FOB Plant, PM (LM_PK602)",
                 "ams.usda.gov/mnreports/ams_2498.pdf"),
    "LM_HG234": ("USDA AMS Daily Direct Prior Day Sow and Boar Report (LM_HG234)",
                 "ams.usda.gov/mnreports/ams_3452.pdf"),
    "AMS2810":  ("USDA AMS US Direct Delivered Feeder Pig Summary (AMS 2810)",
                 "ams.usda.gov/mnreports/lsddhps.pdf"),
    "SJ_LS710": ("USDA AMS Daily Hog Slaughter Under FIS (SJ_LS710)",
                 "ams.usda.gov/mnreports/lsddhps.pdf"),
    "COLDSTOR": ("USDA NASS Cold Storage",
                 "nass.usda.gov/Publications/Todays_Reports/reports/cost1026.pdf"),
    "HOGSPIGS": ("USDA NASS Quarterly Hogs and Pigs",
                 "nass.usda.gov/Newsroom/Executive_Briefings/2026/09-24-2026.pdf"),
    "FAS":      ("USDA FAS Weekly Export Sales (pork muscle cuts)",
                 "apps.fas.usda.gov/export-sales/pork.htm"),
    "CFTC":     ("CFTC Commitments of Traders, Lean Hogs (code 054642)",
                 "cftc.gov/MarketReports/CommitmentsofTraders"),
    "CBOT":     ("CBOT settlements via AMS Daily Grain Reports",
                 "ams.usda.gov/mnreports/ams_3046.pdf"),
    "CME":      ("CME Lean Hog futures & Lean Hog Index (HEZ26/HEG27/HEJ27)",
                 "cmegroup.com; settlements cross-checked across Investing.com, "
                 "FXEmpire, Farmbucks, TradingEconomics and daily CME wire "
                 "reports"),
}

# ---------------------------------------------------------------- prices
# Negotiated national weighted average, carcass basis (LM_HG218 family).
# Only ~2-3% of hogs trade here, but it anchors formula contracts.
NEGOTIATED = {
    "asof": "2026-11-04", "src": "LM_HG218",
    "value": 41.85, "prior": 45.35, "chg": -3.50,
    "low": 40.00, "high": 55.00,
    "roll5": 47.94,
    "head": 5368,
    "series": [("Nov 2", 56.30), ("Nov 3", 48.76), ("Nov 4", 41.85)],
    "mid_oct_ref": (67.0, 72.0),
}

# Producer-sold ALL purchase types, carcass base (LM_HG201 family).
# This is much closer to what producers actually receive.
PRODUCER_ALL = {
    "asof": "2026-11-03", "src": "LM_HG201",
    "value": 66.15, "net": None, "head": 235706,
    "series": [("Oct 23", 71.54), ("Nov 2", 66.91), ("Nov 3", 66.15)],
}

# Purchase-type breakdown, plant-delivered Nov 4 (LM_HG218).
PURCHASE_TYPES = {
    "asof": "2026-11-04", "src": "LM_HG218",
    "rows": [
        # label,                      head,    price,  note
        ("Negotiated",                 5368,   41.85, "spot / cash"),
        ("Swine or pork mkt formula", 146524,  61.06, "cutout-linked"),
        ("Other purchase arrangement", 65867,  65.26, "fixed / window"),
    ],
}

# Pork carcass cutout and primals (LM_PK602).
CUTOUT = {
    "asof": "2026-11-03", "src": "LM_PK602",
    "value": 72.43, "prior": 72.28, "chg": 0.15,
    "loads": 283.61, "loads_prior": 310.84,
    "series": [("Nov 2", 72.28), ("Nov 3", 72.43)],
    "primals": [
        # name,     Nov 3,  Nov 2
        ("Loin",     74.64,  75.65),
        ("Butt",     94.73,  95.50),
        ("Picnic",   57.92,  51.76),
        ("Rib",     125.15, 134.50),
        ("Ham",      64.30,  64.43),
        ("Belly",    75.96,  74.12),
    ],
}

BYPRODUCT = {"asof": "2026-10-23", "src": "AMS2810", "value": 5.01, "chg": -0.09}

# Sow prices, national negotiated, live basis, by weight class (LM_HG234).
SOWS = {
    "asof": "2026-10-19", "src": "LM_HG234",
    "classes": [
        # class,      wtd avg, avg wt, head,  low,   high
        ("300-399",   60.73,   365,    1067,  30.00, 73.75),
        ("400-449",   62.78,   421,     580,  30.00, 76.69),
        ("450-499",   68.27,   475,     308,  48.00, 76.69),
        ("500-549",   71.82,   526,    1886,  62.12, 76.69),
        ("550/up",    72.00,   588,     667,  48.00, 76.75),
    ],
    "total_head": 4508,
    "canada_origin_head": 865,
}

# Early-wean and feeder pigs (AMS 2810), weekly.
FEEDER_PIGS = {
    "asof": "2026-10-23", "src": "AMS2810",
    "rows": [
        # label,              formula, cash,  composite
        ("SEW 10-12 lb",       38.06,  22.35, 26.01),
        ("Feeder pig 40 lb",   44.90,  None,  44.90),
    ],
}

# ---------------------------------------------------------------- feed
FEED = {
    "asof": "2026-11-04", "src": "CBOT",
    "corn": {"value": 4.4425, "prior": 4.4250, "contract": "Dec 26",
             "series": [("Nov 2", 4.4825), ("Nov 3", 4.4250), ("Nov 4", 4.4425)]},
    "sbm":  {"value": 318.60, "prior": 318.00, "contract": "Dec 26",
             "series": [("Nov 2", 319.60), ("Nov 3", 318.00), ("Nov 4", 318.60)]},
    "iowa_cash_corn": {"value": 4.06, "asof": "2026-11-02"},
    # Feed-cost model assumptions, stated so they can be overridden.
    "model": {"corn_bu_per_head": 9.5, "sbm_ton_per_head": 0.045,
              "carcass_lb": 215},
}

# ---------------------------------------------------------------- supply
SLAUGHTER = {
    "asof": "2026-10-23", "src": "SJ_LS710",
    "today_est": 462000, "sat_est": 202000,
    "week_ago_est": 472000, "year_ago_act": 458593,
    "wtd_est": 2413000, "wtd_prior_week": 2443000, "wtd_year_ago": 2393263,
    "sched_peak": (465110, "2026-11-03"),
}

CARCASS_WT = {
    "asof": "2026-11-04", "src": "LM_HG201",
    "negotiated": 224.09, "spmf": 218.53, "omf": 220.51,
    "opa": 219.70, "combined": 220.06, "packer_owned": 217.20,
}

# Quarterly Hogs and Pigs, Sept 1 (thousand head).
INVENTORY = {
    "asof": "2026-09-01", "src": "HOGSPIGS", "released": "2026-09-24",
    "next_release": "late December 2026",
    "rows": [
        # label,            2026,    2025,   pct_chg
        ("All hogs & pigs", 74302,  75438,  -1.5),
        ("Kept for breeding", 5875,  5936,  -1.0),
        ("Market hogs",     68427,  69502,  -1.5),
    ],
    "weight_classes": [
        # class,        2026,   2025,  pct, comes to market
        ("Under 50 lb", 21866, 22211, -1.6, "Jan-Feb 2027"),
        ("50-119 lb",   19976, 20283, -1.5, "Dec 26-Jan 27"),
        ("120-179 lb",  14142, 14358, -1.5, "Nov-Dec 2026"),
        ("180 lb +",    12443, 12650, -1.6, "Sep-mid Oct 2026"),
    ],
    "notes": "Smallest September breeding herd since 2013; fewest sows farrowing since 2002.",
}

# Cold storage, total pork, million lb. 2025 points derived from published YoY %.
COLD_STORAGE = {
    "asof": "2026-09-30", "src": "COLDSTOR", "released": "2026-10-23",
    "next_release": "approx. 2026-11-24 (Oct 31 stocks)",
    "total_pork": 427.8, "mom_pct": -1.0, "yoy_pct": 9.0,
    "beef": 400.0, "beef_mom": -1.0, "beef_yoy": -1.0,
    "series_2026": [("Jun", 455.0), ("Jul", 439.4), ("Aug", 436.3), ("Sep", 427.8)],
    "series_2025_derived": [("Jun", None), ("Jul", 404.6), ("Aug", 389.6), ("Sep", 392.5)],
    "bellies_jul": 35.9,
}

# ---------------------------------------------------------------- demand
EXPORTS = {
    "asof": "mid-October 2026", "src": "FAS",
    "net_sales_mt": 22000, "net_sales_wow_pct": 27, "net_sales_vs_4wk_pct": -14,
    "shipments_mt": 29400, "shipments_wow_pct": 26, "shipments_vs_4wk_pct": 13,
    "net_sales_by_dest": [("Japan", 6600), ("Mexico", 6200), ("China", 3000),
                          ("Colombia", 1400), ("Canada", 1300)],
    "shipments_by_dest": [("Mexico", 14500), ("Japan", 4100), ("China", 2800),
                          ("South Korea", 1900), ("Canada", 1700)],
    "share_of_production_pct": "25-30",
}

# CFTC Commitments of Traders, Lean Hogs.
COT = {
    "asof": "2026-10-27", "src": "CFTC", "released": "2026-10-30",
    "next_release": "2026-11-06",
    "mm_long": 71391, "mm_short": 123037, "mm_net": -51646,
    "mm_net_prior": -56479,
    "large_spec_net": -82361,
    "futopt_net_reported": -47109, "futopt_wow": -5976,
    "cme_index": 67.30, "cme_index_asof": "2026-10-28",
    "contract_lb": 40000,
    "pct_rank_note": "Managed money net position sits above only ~1% of the last 156 weeks.",
}


# ---------------------------------------------------------------- derived
def cad(usd):
    return usd * FX_USDCAD


def feed_cost_per_head():
    m = FEED["model"]
    return (m["corn_bu_per_head"] * FEED["corn"]["value"]
            + m["sbm_ton_per_head"] * FEED["sbm"]["value"])


def feed_cost_per_cwt():
    return feed_cost_per_head() / (FEED["model"]["carcass_lb"] / 100.0)


def sow_weighted_avg():
    tot_v = sum(c[1] * c[3] for c in SOWS["classes"])
    tot_h = sum(c[3] for c in SOWS["classes"])
    return tot_v / tot_h


def cutout_base_spread():
    """Packer gross-margin proxy: cutout less negotiated base, same-week."""
    return CUTOUT["value"] - NEGOTIATED["series"][1][1]   # Nov 3 vs Nov 3


def contract_notional(contracts, index=None):
    idx = index if index is not None else COT["cme_index"]
    return contracts * COT["contract_lb"] * (idx / 100.0)


def revenue_per_head(price_cwt):
    return price_cwt * (FEED["model"]["carcass_lb"] / 100.0)


def negotiated_share_pct():
    rows = PURCHASE_TYPES["rows"]
    tot = sum(r[1] for r in rows)
    return rows[0][1] / tot * 100.0


# ================================================================ FUTURES
# CME Lean Hog futures. Settlements are $/cwt carcass (quoted as cents/lb).
# `curve` entries are dated full-chain snapshots; `dec26`/`feb27`/`apr27`
# hold the dated points verified for each contract.
# derived=True marks a close back-calculated from a published daily change.
FUTURES = {
    "asof": "2026-11-05", "src": "CME",
    "contracts": ["Dec 26 (HEZ26)", "Feb 27 (HEG27)", "Apr 27 (HEJ27)"],
    "front_weight": [0.60, 0.25, 0.15],      # 4-6 week horizon: front dominates

    "latest": {
        "Dec 26": {"px": 55.10, "chg": -2.45, "pct": -4.26,
                   "oi": 145427, "vol": 41870, "lo": 54.225, "hi": 56.825},
        "Feb 27": {"px": 60.18, "chg": -2.13, "pct": -3.41, "oi": 76937},
        "Apr 27": {"px": 67.13, "chg": -1.20, "pct": -1.76, "oi": 46839},
    },

    # full-chain snapshots, for term-structure slope and how it is changing
    "curve": {
        "2026-10-23": {"Dec 26": 65.575, "Feb 27": 67.625, "Apr 27": 72.675,
                       "May 27": 78.575, "Jun 27": 87.700, "Jul 27": 90.300,
                       "Aug 27": 90.625, "Oct 27": 78.075, "Dec 27": 71.750},
        "2026-11-04": {"Dec 26": 57.55, "Feb 27": 62.30, "Apr 27": 68.33,
                       "May 27": 74.95, "Jun 27": 83.93, "Jul 27": 87.15,
                       "Aug 27": 88.10, "Oct 27": 77.35, "Dec 27": 70.95},
        "2026-11-05": {"Dec 26": 55.10, "Feb 27": 60.18, "Apr 27": 67.13,
                       "May 27": 73.98, "Jun 27": 83.05},
    },

    # dated closes per contract (date, close, derived?)
    "dec26": [("2026-09-30", 69.43, True), ("2026-10-09", 67.825, False),
              ("2026-10-12", 68.375, True), ("2026-10-13", 68.025, False),
              ("2026-10-23", 65.575, False), ("2026-10-28", 58.600, True),
              ("2026-10-29", 59.825, False), ("2026-11-03", 58.600, True),
              ("2026-11-04", 57.550, False), ("2026-11-05", 55.100, False)],
    "feb27": [("2026-10-09", 69.250, False), ("2026-10-23", 67.625, False),
              ("2026-10-29", 64.725, False), ("2026-11-03", 63.530, True),
              ("2026-11-04", 62.300, False), ("2026-11-05", 60.180, False)],
    "apr27": [("2026-10-23", 72.675, False), ("2026-11-03", 69.380, True),
              ("2026-11-04", 68.330, False), ("2026-11-05", 67.130, False)],

    # front-month continuous, Oct-2026 contract (ends at its roll) - kept for
    # reference only. NOT splice-safe with the Dec series: on 09 Oct the Oct
    # contract settled 75.05 while Dec settled 67.825, a 7.2-point gap.
    "front_continuous_oct_contract": [
        ("2026-09-10", 83.15), ("2026-09-11", 81.53), ("2026-09-14", 79.60),
        ("2026-09-15", 79.07), ("2026-09-16", 78.68), ("2026-09-17", 78.90),
        ("2026-09-18", 78.10), ("2026-09-21", 78.15), ("2026-09-22", 79.28),
        ("2026-09-23", 79.88), ("2026-09-24", 79.20), ("2026-09-25", 78.22),
        ("2026-09-28", 78.25), ("2026-09-29", 79.38), ("2026-09-30", 78.72),
        ("2026-10-01", 77.50), ("2026-10-02", 77.88), ("2026-10-05", 77.85),
        ("2026-10-06", 77.93), ("2026-10-07", 76.93), ("2026-10-08", 75.82),
        ("2026-10-09", 75.05)],

    "perf": {"Dec 26": {"1d": -4.26, "1w": -5.97, "ytd": -35.25, "1y": -31.06}},
    "min_sessions": {"rsi14": 30, "macd": 60},
}

# CME Lean Hog Index history (cash index the Dec contract converges to)
LH_INDEX = {
    "src": "CME",
    "points": [("2026-10-07", 78.41), ("2026-10-28", 67.30),
               ("2026-10-29", 68.30)],
    "latest": 68.30, "latest_asof": "2026-10-29",
    "note": "lowest since January 2024",
}

# extra dated cutout points picked up during futures research
CUTOUT_EXTRA = [("2026-10-13", 80.68), ("2026-10-29", 70.69),
                ("2026-11-02", 72.28), ("2026-11-03", 72.43)]


# ================================================================ OVERLAY
# daily.json carries every value that changes between runs. The scheduled
# job rewrites that file from freshly gathered figures; this module then
# loads it over the literals above, so nothing in the report code needs to
# know whether a number came from the file or the defaults below it.
# Lists replace tuples on the JSON round-trip, which all consumers tolerate
# because every access is positional.
def _load_daily(path=None):
    import json
    import os
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "daily.json")
    if not os.path.exists(p):
        return {"loaded": False, "path": p, "blocks": 0}
    with open(p) as f:
        blob = json.load(f)
    g = globals()
    n = 0
    for k, v in blob.items():
        if k in g:
            g[k] = v
            n += 1
    return {"loaded": True, "path": p, "blocks": n}


DAILY = _load_daily()
