"""
Single entry point for a scheduled run.

    python3 build.py [YYYY-MM-DD]

Order of operations:

  1. Decide whether the target date was a CME market day. If not, stop and
     write a SKIP status. Nothing is emailed on weekends or exchange holidays.
  2. Grade every series for freshness.
  3. Build charts and the PDF.
  4. Write run_status.json, which carries everything the calling agent needs
     to compose the email: PI and its band, the forecast, what is stale, and
     a ready-to-send subject line and summary.

Exit codes
  0  report built and ready to send
  10 not a market day, nothing to send (not an error)
  1  build failed
"""
import datetime as dt
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PDF = os.path.join(HERE, "US_Lean_Hog_Market_Report.pdf")
STATUS = os.path.join(HERE, "run_status.json")


def write_status(obj):
    with open(STATUS, "w") as f:
        json.dump(obj, f, indent=2)
    return obj


def main():
    import data as D
    import validate as V

    target = (V._parse(sys.argv[1]) if len(sys.argv) > 1
              else V._parse(D.REPORT_DATE) or dt.date.today())
    vd = V.verdict(target)

    if vd["action"] == "SKIP":
        print(f"SKIP  {vd['target']}  {vd['note']}")
        write_status({"action": "SKIP", "target": vd["target"],
                      "why": vd["why"], "note": vd["note"], "pdf": None})
        return 10

    import pi as PIM
    import report as R

    res = PIM.compute()
    fc = PIM.forecast(res)

    R.build()
    if not os.path.exists(PDF):
        print("FAIL  pdf was not produced")
        write_status({"action": "FAIL", "target": vd["target"],
                      "note": "pdf not produced"})
        return 1

    size = os.path.getsize(PDF)
    arrow = "lower" if res["pi"] < 50 else "higher"
    stale = [r["label"] for r in vd["stale"]]

    subject = (f"Lean Hog Report {vd['target']} - PI {res['pi']:.1f} "
               f"{res['band']}")

    summary = (
        f"PI {res['pi']:.1f} ({res['band']}), {res['horizon']} horizon.\n"
        f"Negotiated base {D.NEGOTIATED['value']:.2f}/cwt, "
        f"producer base all types {D.PRODUCER_ALL['value']:.2f}, "
        f"cutout {D.CUTOUT['value']:.2f}.\n"
        f"Dec futures {D.FUTURES['latest']['Dec 26']['px']:.2f}. "
        f"Market-implied base {fc['implied']:.2f}; PI centre {fc['centre']:.2f} "
        f"(band {fc['lo']:.2f}-{fc['hi']:.2f}).\n"
        f"Fundamentals read {arrow} than the futures curve.\n"
        f"Data: {vd['fresh_count']}/{vd['total']} series fresh."
        + (f" Carried forward: {', '.join(stale)}." if stale else "")
    )

    out = {
        "action": vd["action"], "target": vd["target"],
        "pdf": PDF, "pdf_bytes": size,
        "pi": round(res["pi"], 1), "band": res["band"],
        "completeness": round(res["completeness"], 3),
        "forecast": {k: round(v, 2) for k, v in fc.items()
                     if isinstance(v, (int, float))},
        "stale": stale, "core_bad": [r["label"] for r in vd["core_bad"]],
        "fresh_count": vd["fresh_count"], "total": vd["total"],
        "subject": subject, "summary": summary,
        "blocks": {k: round(b["contrib"] * 50, 2)
                   for k, b in res["blocks"].items()},
    }
    write_status(out)
    print(f"OK    {vd['target']}  PI {res['pi']:.1f} {res['band']}  "
          f"{size/1024:.0f} KB  {vd['fresh_count']}/{vd['total']} fresh")
    print(f"      subject: {subject}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        write_status({"action": "FAIL", "error": traceback.format_exc()[-2000:]})
        sys.exit(1)
