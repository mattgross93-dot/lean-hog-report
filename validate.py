"""
Freshness gate and market-day detection for the scheduled daily run.

Two jobs:

  1. Decide whether the target date was a CME trading day at all. Weekends and
     exchange holidays are not market days, so the run exits without sending.
  2. Grade every metric against its own expected refresh cadence and report
     which ones are fresh, stale or missing.

The point is that a run which could not verify today's cutout says so on the
front page instead of silently reprinting yesterday's number as today's.
"""
import datetime as dt
import data as D

# How old a metric may be, in calendar days, relative to the target date,
# before it is called stale. Set from each series' real publication cadence.
MAX_AGE = {
    "NEGOTIATED": 1, "PRODUCER_ALL": 2, "CUTOUT": 1, "FUTURES": 0,
    "LH_INDEX": 4, "SLAUGHTER": 3, "CARCASS_WT": 3, "FEED": 1,
    "BYPRODUCT": 10, "SOWS": 6, "FEEDER_PIGS": 10, "COT": 10,
    "EXPORTS": 12, "COLD_STORAGE": 45, "INVENTORY": 120,
}

# If any of these cannot be verified for the target date, the report is
# published with a prominent warning rather than presented as current.
CORE = ["CUTOUT", "FUTURES", "PRODUCER_ALL"]

LABEL = {
    "NEGOTIATED": "Negotiated base price", "PRODUCER_ALL": "Producer base, all types",
    "CUTOUT": "Pork carcass cutout", "FUTURES": "Lean hog futures",
    "LH_INDEX": "CME Lean Hog Index", "SLAUGHTER": "Daily slaughter",
    "CARCASS_WT": "Carcass weights", "FEED": "Corn & soybean meal",
    "BYPRODUCT": "By-product drop value", "SOWS": "Sow & boar prices",
    "FEEDER_PIGS": "SEW & feeder pigs", "COT": "COT positioning",
    "EXPORTS": "Pork exports", "COLD_STORAGE": "Cold storage",
    "INVENTORY": "Herd inventory",
}


# ------------------------------------------------------------ holidays
def _easter(year):
    """Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


def _nth_weekday(year, month, weekday, n):
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(weekday - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _last_weekday(year, month, weekday):
    d = (dt.date(year + (month == 12), (month % 12) + 1, 1)
         - dt.timedelta(days=1))
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d):
    """US rule: Saturday holidays observe Friday, Sunday observe Monday."""
    if d.weekday() == 5:
        return d - dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def cme_holidays(year):
    """CME Group full-closure holidays for livestock futures."""
    return {
        _observed(dt.date(year, 1, 1)),                 # New Year's Day
        _nth_weekday(year, 1, 0, 3),                    # MLK Day
        _nth_weekday(year, 2, 0, 3),                    # Presidents Day
        _easter(year) - dt.timedelta(days=2),           # Good Friday
        _last_weekday(year, 5, 0),                      # Memorial Day
        _observed(dt.date(year, 6, 19)),                # Juneteenth
        _observed(dt.date(year, 7, 4)),                 # Independence Day
        _nth_weekday(year, 9, 0, 1),                    # Labor Day
        _nth_weekday(year, 11, 3, 4),                   # Thanksgiving
        _observed(dt.date(year, 12, 25)),               # Christmas
    }


def is_market_day(d):
    """True when CME livestock futures traded a full session on `d`."""
    if d.weekday() >= 5:
        return False, "weekend"
    if d in cme_holidays(d.year):
        return False, "CME holiday"
    return True, "market day"


# ------------------------------------------------------------ freshness
def _asof(block):
    v = getattr(D, block, None)
    if isinstance(v, dict):
        return v.get("asof") or v.get("latest_asof")
    return None


def _parse(s):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def freshness(target):
    """Grade every metric against its cadence. Returns a list of rows."""
    rows = []
    for block, max_age in MAX_AGE.items():
        asof = _asof(block)
        d = _parse(asof)
        if d is None:
            rows.append({"block": block, "label": LABEL.get(block, block),
                         "asof": asof or "unknown", "age": None,
                         "max_age": max_age, "state": "MISSING",
                         "core": block in CORE})
            continue
        age = (target - d).days
        state = "FRESH" if age <= max_age else "STALE"
        rows.append({"block": block, "label": LABEL.get(block, block),
                     "asof": str(d), "age": age, "max_age": max_age,
                     "state": state, "core": block in CORE})
    return rows


def verdict(target=None):
    """Full pre-flight check for a scheduled run."""
    target = target or dt.date.today()
    market, why = is_market_day(target)
    rows = freshness(target)
    stale = [r for r in rows if r["state"] != "FRESH"]
    core_bad = [r for r in stale if r["core"]]

    if not market:
        action = "SKIP"
        note = f"{target} is not a market day ({why}). No report sent."
    elif core_bad:
        action = "SEND_FLAGGED"
        note = ("Core data could not be verified for this session: "
                + ", ".join(r["label"] for r in core_bad)
                + ". Report sent with a prominent staleness warning.")
    elif stale:
        action = "SEND_FLAGGED"
        note = ("Secondary series carried forward: "
                + ", ".join(r["label"] for r in stale)
                + ". Each is stamped with its real as-of date.")
    else:
        action = "SEND"
        note = "All series verified for this session."

    return {"target": str(target), "market_day": market, "why": why,
            "action": action, "note": note, "rows": rows,
            "stale": stale, "core_bad": core_bad,
            "fresh_count": len(rows) - len(stale), "total": len(rows)}


if __name__ == "__main__":
    import sys
    t = _parse(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    v = verdict(t)
    print(f"\ntarget {v['target']}  |  {v['why']}  |  action {v['action']}")
    print(f"{v['note']}\n")
    for r in v["rows"]:
        age = "-" if r["age"] is None else f"{r['age']}d"
        tag = "*" if r["core"] else " "
        print(f"  {tag} {r['state']:<8s} {r['label']:<28s} as of {r['asof']:<12s} "
              f"age {age:<5s} limit {r['max_age']}d")
    print(f"\n  {v['fresh_count']}/{v['total']} series fresh")
