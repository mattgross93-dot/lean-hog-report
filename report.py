"""Builds the US Lean Hog Market Report PDF."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, Image, KeepTogether,
                                PageBreak, Flowable)
import os
import data as D
import charts as C
import pi as PI
import validate as V
import datetime as _dt

PAGE_W, PAGE_H = letter
M = 0.58 * inch
CONTENT_W = PAGE_W - 2 * M

INK = colors.HexColor("#000000")
BODY = colors.HexColor("#1b2430")
SOFT = colors.HexColor("#5b6773")
RULE = colors.HexColor("#cdd4da")
BAND = colors.HexColor("#1f3347")
BANDLT = colors.HexColor("#2d5f8a")
UP = colors.HexColor("#2e7d4f")
DOWN = colors.HexColor("#c0392b")
FLAT = colors.HexColor("#5b6773")
CARD = colors.HexColor("#f4f6f8")
CARDLN = colors.HexColor("#dde3e8")
# Callout boxes: light blue wash with a deeper blue spine.
WARN = colors.HexColor("#e9f1f9")
WARNLN = colors.HexColor("#3f7cab")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "US_Lean_Hog_Market_Report.pdf")


def _fmt_day(asof):
    """'2026-11-06' -> 'Nov 6'. Returns the input unchanged if unparseable."""
    try:
        return _dt.date.fromisoformat(str(asof)[:10]).strftime("%b %-d")
    except Exception:
        return str(asof)


def _fmt_long(asof):
    try:
        return _dt.date.fromisoformat(str(asof)[:10]).strftime("%B %-d %Y")
    except Exception:
        return str(asof)


def _nonneg_head():
    return sum(r[1] for r in D.PURCHASE_TYPES["rows"]
               if not r[0].lower().startswith("negotiated"))


def _neg_gap():
    return D.PRODUCER_ALL["value"] - D.NEGOTIATED["value"]


def _spread_now():
    return D.CUTOUT["value"] - D.PRODUCER_ALL["value"]


def _spread_prior():
    pa = D.PRODUCER_ALL
    pp = pa["series"][-2][1] if len(pa.get("series", [])) > 1 else pa["value"]
    return D.CUTOUT.get("prior", D.CUTOUT["value"]) - pp


def _move_word(chg):
    if chg > 0:
        return "up"
    if chg < 0:
        return "down"
    return "unchanged at"


def _formula_price():
    """Base price of the cutout-linked formula row in PURCHASE_TYPES."""
    for label, _head, price, _note in D.PURCHASE_TYPES["rows"]:
        if "pork mkt formula" in label or "pork market formula" in label:
            return price
    return D.PURCHASE_TYPES["rows"][-1][2]


# --------------------------------------------------------------- styles
def hx(c):
    return "#" + c.hexval()[2:]


def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.4, leading=13.2,
                textColor=BODY, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)


ST = {
    "h1": S("h1", fontName="Helvetica-Bold", fontSize=19, leading=22,
            textColor=INK, spaceAfter=2),
    "sub": S("sub", fontSize=10, leading=13, textColor=SOFT),
    "h2": S("h2", fontName="Helvetica-Bold", fontSize=13.5, leading=16,
            textColor=INK, spaceBefore=2, spaceAfter=3),
    "h3": S("h3", fontName="Helvetica-Bold", fontSize=10.6, leading=13,
            textColor=INK, spaceBefore=5, spaceAfter=2),
    "body": S("body"),
    "bodyb": S("bodyb", fontName="Helvetica-Bold"),
    "small": S("small", fontSize=8.2, leading=11, textColor=SOFT),
    "smallb": S("smallb", fontSize=8.2, leading=11, textColor=BODY,
                fontName="Helvetica-Bold"),
    "cap": S("cap", fontSize=8.0, leading=10.5, textColor=SOFT),
    "kpi_lbl": S("kpi_lbl", fontName="Helvetica-Bold", fontSize=7.4, leading=9,
                 textColor=SOFT),
    "kpi_val": S("kpi_val", fontName="Helvetica-Bold", fontSize=16.5,
                 leading=18.5, textColor=INK),
    "kpi_cad": S("kpi_cad", fontSize=7.6, leading=9.5, textColor=SOFT),
    "th": S("th", fontName="Helvetica-Bold", fontSize=8.4, leading=10.5,
            textColor=colors.white),
    "td": S("td", fontSize=8.6, leading=11),
    "tdb": S("tdb", fontSize=8.6, leading=11, fontName="Helvetica-Bold"),
    "tdr": S("tdr", fontSize=8.6, leading=11, alignment=TA_RIGHT),
    "tdrb": S("tdrb", fontSize=8.6, leading=11, alignment=TA_RIGHT,
              fontName="Helvetica-Bold"),
}


class Rule(Flowable):
    def __init__(self, w, thick=1.4, color=BANDLT, space=4):
        self.w, self.thick, self.color, self.space = w, thick, color, space
        self.height = thick + space

    def wrap(self, *a):
        return (self.w, self.height)

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thick)
        self.canv.line(0, self.space, self.w, self.space)


def section(title, note=None):
    out = [Paragraph(title, ST["h2"]), Rule(CONTENT_W)]
    if note:
        out.append(Paragraph(note, ST["cap"]))
        out.append(Spacer(1, 3))
    return out


def chart(path, width=6.55 * inch, cap=None):
    img = Image(path)
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = min(width, CONTENT_W)
    img.drawHeight = img.drawWidth * ratio
    img.hAlign = "CENTER"
    out = [img]
    if cap:
        out.append(Spacer(1, 2))
        out.append(Paragraph(cap, ST["cap"]))
    return out


def money(v, dec=2, cur="$"):
    return f"{cur}{v:,.{dec}f}"


def delta_str(v, dec=2, pct=False, unit=""):
    sign = "+" if v > 0 else ""
    suffix = "%" if pct else unit
    return f"{sign}{v:,.{dec}f}{suffix}"


def delta_col(v):
    return UP if v > 0 else (DOWN if v < 0 else FLAT)


# --------------------------------------------------------------- KPI card
def kpi_card(label, value, delta=None, delta_txt=None, cad=None, note=None):
    rows = [[Paragraph(label.upper(), ST["kpi_lbl"])],
            [Paragraph(value, ST["kpi_val"])]]
    line3 = []
    if delta_txt is not None:
        c = delta_col(delta if delta is not None else 0)
        line3.append(f'<font color="{hx(c)}"><b>{delta_txt}</b></font>')
    if cad:
        line3.append(f'<font color="#7b8894">{cad}</font>')
    if note:
        line3.append(f'<font color="#7b8894">{note}</font>')
    rows.append([Paragraph("&nbsp;&nbsp;".join(line3), ST["kpi_cad"])
                 if line3 else Paragraph("", ST["kpi_cad"])])

    t = Table(rows, colWidths=[CONTENT_W / 4 - 7])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (0, 0), 7),
        ("BOTTOMPADDING", (0, 0), (0, 0), 1),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (0, 1), 1),
        ("TOPPADDING", (0, 2), (0, 2), 0),
        ("BOTTOMPADDING", (0, 2), (0, 2), 7),
        ("BACKGROUND", (0, 0), (-1, -1), CARD),
        ("BOX", (0, 0), (-1, -1), 0.7, CARDLN),
        ("LINEBEFORE", (0, 0), (0, -1), 2.6, BANDLT),
    ]))
    return t


def kpi_grid(cards, cols=4):
    rows = [cards[i:i + cols] for i in range(0, len(cards), cols)]
    for r in rows:
        while len(r) < cols:
            r.append("")
    t = Table(rows, colWidths=[CONTENT_W / cols] * cols)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# --------------------------------------------------------------- tables
def data_table(header, rows, widths, aligns=None, zebra=True,
               compact=False):
    head = [Paragraph(h, ST["th"]) for h in header]
    body = []
    for r in rows:
        cells = []
        for j, cell in enumerate(r):
            if isinstance(cell, Paragraph):
                cells.append(cell)
            else:
                st = ST["tdr"] if (aligns and aligns[j] == "r") else ST["td"]
                cells.append(Paragraph(str(cell), st))
        body.append(cells)
    t = Table([head] + body, colWidths=widths, repeatRows=1)
    pad = 2.6 if compact else 4.5
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BAND),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
    ]
    if zebra:
        for i in range(1, len(body) + 1):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i),
                              colors.HexColor("#f7f9fa")))
    t.setStyle(TableStyle(style))
    return t


def callout(title, text, tone="warn"):
    # Both tones share the light blue treatment so every note matches.
    bg, ln = (WARN, WARNLN) if tone == "warn" else (WARN, WARNLN)
    inner = [[Paragraph(f"<b>{title}</b>", S("ct", fontName="Helvetica-Bold",
                                             fontSize=9.8, leading=12.5,
                                             textColor=INK))],
             [Paragraph(text, S("cb", fontSize=9.0, leading=12.4,
                                textColor=BODY))]]
    t = Table(inner, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ln),
        ("BOX", (0, 0), (-1, -1), 0.6, ln),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (0, 0), 7),
        ("BOTTOMPADDING", (0, 0), (0, 0), 1),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (0, 1), 8),
    ]))
    # a callout split across a page break reads as two broken boxes
    return KeepTogether([t])


def two_up(left_flow, right_flow, gap=14):
    w = (CONTENT_W - gap) / 2
    t = Table([[left_flow, "", right_flow]], colWidths=[w, gap, w])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def half_chart(path):
    w = (CONTENT_W - 14) / 2
    img = Image(path)
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = w
    img.drawHeight = w * ratio
    return img


# --------------------------------------------------------------- page deco
def page_deco(canv, doc):
    canv.saveState()
    # header band
    canv.setFillColor(BAND)
    canv.rect(0, PAGE_H - 30, PAGE_W, 30, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 9)
    canv.drawString(M, PAGE_H - 19.5, "US LEAN HOG MARKET REPORT")
    canv.setFont("Helvetica", 8.4)
    canv.drawRightString(PAGE_W - M, PAGE_H - 19.5,
                         f"Compiled {D.REPORT_DATE}")
    # footer
    canv.setStrokeColor(RULE)
    canv.setLineWidth(0.6)
    canv.line(M, 30, PAGE_W - M, 30)
    canv.setFillColor(SOFT)
    canv.setFont("Helvetica", 7.4)
    canv.drawString(M, 20, "Sources: USDA AMS / NASS / FAS, CFTC, CBOT. "
                           "Figures carry individual as-of dates — see "
                           "Data Sources page.")
    canv.setFont("Helvetica-Bold", 7.4)
    canv.drawRightString(PAGE_W - M, 20, f"Page {doc.page}")
    canv.restoreState()


def build():
    C.build_all()
    _res = PI.compute()
    C.pi_gauge(_res["pi"], _res["band"])
    C.pi_history_forecast(PI.history(), PI.forecast(_res), _res["pi"])
    C.pi_waterfall(_res)
    doc = BaseDocTemplate(OUT, pagesize=letter,
                          leftMargin=M, rightMargin=M,
                          topMargin=M + 20, bottomMargin=M,
                          title="US Lean Hog Market Report",
                          author="Prepared for Matthew")
    frame = Frame(M, M, CONTENT_W, PAGE_H - M - (M + 20) - 4, id="main")
    doc.addPageTemplates([PageTemplate(id="std", frames=[frame],
                                       onPage=page_deco)])
    doc.build(story())


# =============================================================== CONTENT
def story():
    pages = [page_one, page_pi, page_price, page_price_table, page_thin_market,
             page_breeding, page_feed, page_supply, page_exports,
             page_cot, page_drivers, page_sources]
    # No forced break between the cover and the PI breakdown: the freshness
    # banner changes the cover's height from day to day, so letting those two
    # flow together keeps the document from stranding a near-empty page.
    flow_after = {0}
    s = []
    for i, fn in enumerate(pages):
        s += fn()
        if i < len(pages) - 1 and i not in flow_after:
            s.append(PageBreak())
        elif i in flow_after:
            s.append(Spacer(1, 12))
    return s


# --------------------------------------------------------------- page 1
def page_one():
    s = []
    s.append(Paragraph("US Lean Hog Market Report", ST["h1"]))
    s.append(Paragraph(
        "Daily price, supply, demand and positioning briefing &nbsp;|&nbsp; "
        f"Compiled {D.REPORT_DATE} &nbsp;|&nbsp; "
        f"USD with CAD at {D.FX_USDCAD:.4f}", ST["sub"]))
    s.append(Spacer(1, 8))

    vd = V.verdict(V._parse(D.REPORT_DATE) or _dt.date.today())
    if vd["action"] != "SEND":
        bad = vd["core_bad"] or vd["stale"]
        names = ", ".join(r["label"] + f" ({r['asof']})" for r in bad[:6])
        sev = ("Core data not verified for this session"
               if vd["core_bad"] else "Some series carried forward")
        s.append(callout(
            f"Data freshness \u2014 {sev}",
            f"{vd['fresh_count']} of {vd['total']} series were confirmed for "
            f"{vd['target']}. Carried forward: {names}. Every figure in this "
            f"report is stamped with its own as-of date, and PI reports reduced "
            f"data completeness rather than filling gaps. Treat anything dated "
            f"before {vd['target']} as the last published value, not today's.",
            tone="warn"))
        s.append(Spacer(1, 9))

    neg = D.NEGOTIATED
    cut = D.CUTOUT
    _pa = D.PRODUCER_ALL
    spread = cut["value"] - _pa["value"]
    _cut_prior = cut.get("prior", cut["value"])
    _pa_prior = (_pa["series"][-2][1] if len(_pa.get("series", [])) > 1
                 else _pa["value"])
    spread_prior = _cut_prior - _pa_prior
    _pa_chg = _pa["value"] - _pa_prior
    _d_neg = _fmt_day(neg["asof"])
    _d_pa = _fmt_day(_pa["asof"])
    _d_cut = _fmt_day(cut["asof"])
    sow = D.sow_weighted_avg()
    feed_cwt = D.feed_cost_per_cwt()

    cards = [
        kpi_card("Negotiated base price", money(neg["value"]),
                 delta=neg["chg"], delta_txt=delta_str(neg["chg"]),
                 cad=f"C{money(D.cad(neg['value']))}", note=f"/cwt &middot; {_d_neg}"),
        kpi_card("Producer base, all types", money(D.PRODUCER_ALL["value"]),
                 delta=_pa_chg, delta_txt=delta_str(_pa_chg),
                 cad=f"C{money(D.cad(D.PRODUCER_ALL['value']))}",
                 note=f"/cwt &middot; {_d_pa}"),
        kpi_card("Pork carcass cutout", money(cut["value"]),
                 delta=cut["chg"], delta_txt=delta_str(cut["chg"]),
                 cad=f"C{money(D.cad(cut['value']))}", note=f"/cwt &middot; {_d_cut}"),
        kpi_card("Packer margin proxy", money(spread),
                 delta=spread - spread_prior,
                 delta_txt=delta_str(spread - spread_prior),
                 cad=f"C{money(D.cad(spread))}", note=f"/cwt &middot; {_d_cut}"),
        kpi_card("SEW 10-12 lb, cash", money(22.35),
                 cad=f"C{money(D.cad(22.35))}", note="per head &middot; weekly"),
        kpi_card("Sow price, wtd avg", money(sow),
                 cad=f"C{money(D.cad(sow))}", note="/cwt live &middot; Oct 19"),
        kpi_card("Est. feed cost", money(feed_cwt),
                 cad=f"C{money(D.cad(feed_cwt))}", note="/cwt carcass"),
        kpi_card("Fund net short", f"{abs(D.COT['mm_net']):,}",
                 delta=1, delta_txt="near record",
                 note="contracts &middot; Oct 27"),
    ]
    s.append(kpi_grid(cards))
    s.append(Spacer(1, 2))

    cards2 = [
        kpi_card("Dec corn", money(D.FEED["corn"]["value"]),
                 delta=0.0175, delta_txt=delta_str(0.0175),
                 cad=f"C{money(D.cad(D.FEED['corn']['value']))}", note="/bu"),
        kpi_card("Dec soybean meal", money(D.FEED["sbm"]["value"], 2),
                 delta=0.60, delta_txt=delta_str(0.60),
                 cad=f"C{money(D.cad(D.FEED['sbm']['value']))}", note="/ton"),
        kpi_card("Frozen pork stocks", f"{D.COLD_STORAGE['total_pork']:,.1f}M",
                 delta=D.COLD_STORAGE["yoy_pct"],
                 delta_txt=delta_str(D.COLD_STORAGE["yoy_pct"], 1, pct=True) + " YoY",
                 note="lb &middot; Sep 30"),
        kpi_card("Breeding herd", "5.875M",
                 delta=-1.0, delta_txt="-1.0% YoY",
                 note="head &middot; Sep 1"),
    ]
    s.append(kpi_grid(cards2))
    s.append(Spacer(1, 7))

    s += pi_panel()
    s.append(Spacer(1, 11))

    s += section("Where the market stands")
    s.append(Paragraph(
        "The negotiated cash market has fallen apart over the past two weeks. The "
        "national negotiated base price printed "
        f"<b>{money(neg['value'])}/cwt</b> on {_d_neg}, "
        f"{'up' if neg['chg'] >= 0 else 'down'} "
        f"<b>{money(abs(neg['chg']))}</b> on the day and roughly <b>$25/cwt</b> "
        "below where the same series traded in mid-October. The five-day rolling "
        f"average sits at {money(neg['roll5'])}. "
        "Critically, the break is <b>not</b> matched by the wider market: "
        "producer-sold hogs across all purchase types still based at "
        f"<b>{money(D.PRODUCER_ALL['value'])}/cwt</b> on {_d_pa}, and formula "
        f"hogs on {_fmt_day(D.PURCHASE_TYPES['asof'])} based at "
        f"{money(_formula_price())}. The negotiated print covers roughly "
        f"<b>{D.negotiated_share_pct():.1f}%</b> of plant-delivered volume on "
        "that day.",
        ST["body"]))
    s.append(Spacer(1, 5))
    s.append(Paragraph(
        f"Meanwhile the pork cutout printed <b>{money(cut['value'])}/cwt</b> on "
        f"{_d_cut}, {_move_word(cut['chg'])} {money(abs(cut['chg']))} on the day. "
        "The result is a cutout-to-base spread "
        f"of <b>{money(spread)}/cwt</b>, "
        f"{'up' if spread >= spread_prior else 'down'} from "
        f"{money(spread_prior)} the session before — packer gross margin on the "
        "producer-sold base. On the supply "
        "side, every market hog weight class ran 1.5-1.6% below a year ago on "
        "September 1 and the breeding herd is the smallest for that date since "
        "2013, which does not support a cash break of this size. Frozen stocks "
        "at 9% above year-ago and a near-record fund short are the genuinely "
        "bearish points.",
        ST["body"]))
    s.append(Spacer(1, 7))

    s.append(callout(
        "Read this before acting on the headline number",
        f"A {money(neg['value'])} negotiated base price does not mean hogs are "
        f"worth {money(neg['value'])}. That print came off "
        f"{neg['head']:,} head — a sliver of one plant-day of spot trade — "
        f"while {_nonneg_head():,} head moved the same day on formula and "
        "contract terms, tens of dollars higher. Thin negotiated volume plus "
        "USDA confidentiality "
        "suppression makes this series extremely jumpy. Use the all-purchase-type "
        "base price for valuation and the negotiated series only as a directional "
        "signal.", tone="warn"))
    return s


# --------------------------------------------------------------- PI panel
def pi_panel():
    res = PI.compute()
    fc = PI.forecast(res)
    s = section("Projection Indicator (PI)",
                f"The whole report plus the three nearest futures contracts, "
                f"resolved into one score. Horizon {res['horizon']}.")
    s += chart(f"{C.OUT}/pi_gauge.png", width=5.9 * inch)
    s.append(Spacer(1, 1))
    s.append(Paragraph(
        f"<b>PI {res['pi']:.1f} &mdash; {res['band']}.</b> Fundamentals sit "
        f"marginally below what the futures curve already prices. "
        f"Market-implied base {money(fc['implied'])}/cwt; PI tilts it to "
        f"<b>{money(fc['centre'])}</b>, 60% band {money(fc['lo'])}"
        f"&ndash;{money(fc['hi'])}. Data completeness "
        f"{res['completeness']*100:.0f}%. Full breakdown overleaf.",
        ST["body"]))
    return s



def page_pi():
    res = PI.compute()
    fc = PI.forecast(res)
    s = section("Projection Indicator \u2014 how the number is built",
                "PI resolves the whole report into one 0-100 score. 50 is "
                "neutral. Blocks are weighted 70% fundamentals, 30% futures "
                "technicals.")
    s += chart(f"{C.OUT}/pi_waterfall.png")
    s.append(Spacer(1, 4))
    s.append(Paragraph(
        "Each bar is that block's contribution in PI points. Hollow markers on "
        "the track overleaf mark dates where one or more inputs were carried "
        "forward rather than separately verified.", ST["cap"]))
    s.append(Spacer(1, 9))

    s += section("Track and projection")
    s += chart(f"{C.OUT}/pi_forecast.png")
    s.append(Spacer(1, 4))
    s.append(Paragraph(
        f"PI is read <b>against the market's own forecast</b>, not in a vacuum. "
        f"The December contract is itself a forecast of the cash index at "
        f"expiry; the producer base runs about "
        f"{money(abs(fc['offset']))}/cwt under that index, which gives a "
        f"market-implied base of {money(fc['implied'])}. PI then says whether "
        f"the fundamentals agree. At {res['pi']:.1f} it leans "
        f"{abs(fc['tilt_pct']):.1f}% below that pricing &mdash; broad agreement "
        f"with the curve, with a mild bearish lean.", ST["body"]))
    s.append(PageBreak())
    s += section("Component audit",
                 "Every input, its weight, its normalised score and the PI "
                 "points it contributed. Nothing is hidden inside the formula.")
    rows = []
    for key, b in res["blocks"].items():
        rows.append([
            Paragraph(f"<b>{b['label']}</b>", ST["td"]),
            Paragraph(f"<b>{b['weight']:.2f}</b>", ST["tdrb"]),
            Paragraph(f"<b>{b['score']:+.2f}</b>", ST["tdrb"]),
            Paragraph(f"<b>{b['contrib']*50:+.1f} pts</b>", ST["tdrb"]),
        ])
        for c in b["components"]:
            mark = "" if c.avail else " <font color=\"#c0392b\">[no data]</font>"
            rows.append([
                Paragraph(f"&nbsp;&nbsp;&nbsp;{c.label}{mark}<br/>"
                          f"<font size=7 color=\"#5b6773\">{c.detail}</font>",
                          ST["td"]),
                Paragraph(f"{c.weight:.2f}", ST["tdr"]),
                Paragraph(f"{c.score:+.2f}" if c.avail else "\u2014", ST["tdr"]),
                Paragraph("", ST["tdr"]),
            ])
    for name, k, _d in res["overlays"]:
        pretty = {"cot_extreme": "Overlay: fund positioning at extreme",
                  "seasonal": "Overlay: seasonal adjustment",
                  "margin_reversion": "Overlay: margin mean reversion"}.get(name, name)
        rows.append([Paragraph(f"<b>{pretty}</b>", ST["td"]),
                     Paragraph("capped", ST["tdr"]),
                     Paragraph(f"{k:+.3f}", ST["tdr"]),
                     Paragraph(f"<b>{k*50:+.1f} pts</b>", ST["tdrb"])])
    rows.append([Paragraph("<b>PROJECTION INDICATOR</b>", ST["tdb"]),
                 Paragraph("", ST["tdr"]), Paragraph("", ST["tdr"]),
                 Paragraph(f"<b>{res['pi']:.1f}</b>", ST["tdrb"])])
    s.append(data_table(
        ["Block / component", "Weight", "Score", "PI points"], rows,
        widths=[4.05 * inch, 0.72 * inch, 0.70 * inch, 0.90 * inch],
        aligns=["l", "r", "r", "r"], zebra=False, compact=True))
    s.append(PageBreak())
    s += section("PI method and limits")
    for txt in [
        "<b>Scale.</b> 0-100, 50 neutral. Each component is normalised to "
        "[-1, +1], weighted inside its block, and the blocks combined 70% "
        "fundamentals / 30% futures technicals. PI = 50 + 50 x the weighted sum.",
        "<b>The negotiated price is excluded by design.</b> It is 2.5% of "
        "volume and moves $7/cwt on a few thousand head. Including it would "
        "inject the exact noise this report warns against. Packer margin is "
        "therefore measured as cutout less the all-purchase-type base, not "
        "less the negotiated print.",
        "<b>Fund positioning is non-linear.</b> Below the 90th percentile it "
        "confirms trend. Above it, it inverts and becomes contrarian, because "
        "the marginal seller is exhausted. A linear term would read maximally "
        "bearish at precisely the point squeeze risk is highest.",
        "<b>Horizon governs the futures weighting.</b> Over 4-6 weeks the front "
        "contract dominates (60/25/15 across Dec, Feb, Apr). The steep contango "
        "out to spring says the dislocation is seen as temporary, but that is "
        "context for a later horizon, not a forecast for this one, so it carries "
        "only 10% of the technical block.",
        "<b>Missing inputs are not substituted.</b> When a component has no "
        "data its weight is redistributed inside its own block and the loss of "
        "confidence is reported. RSI and MACD are fully implemented and "
        "validated against reference series, but need 30 and 60 sessions "
        "respectively; only 10 dated December sessions could be verified, so "
        "both are currently inactive and the technical block runs at 30% data.",
        "<b>What PI is not.</b> Until there is enough history to backtest "
        "against, PI is a structured opinion rather than a validated model. Its "
        "value is that it is explicit, consistent and auditable - the table "
        "above shows exactly what moved it. It does not carry a measured hit "
        "rate, and the 60% band is a judgement, not a measured confidence "
        "interval.",
    ]:
        s.append(Paragraph(txt, ST["body"]))
        s.append(Spacer(1, 5))
    s.append(Spacer(1, 4))
    s += watch_block()
    return s


def watch_block():
    s = []
    s.append(Spacer(1, 11))

    s += section("What to watch next")
    rows = [
        [Paragraph("<b>Nov 6</b>", ST["td"]),
         Paragraph("CFTC Commitments of Traders", ST["td"]),
         Paragraph("Weekly", ST["td"]),
         Paragraph("Did funds add to a near-record short, or start covering?",
                   ST["td"])],
        [Paragraph("<b>Thursdays</b>", ST["td"]),
         Paragraph("FAS weekly export sales", ST["td"]),
         Paragraph("Weekly", ST["td"]),
         Paragraph("Mexican ham demand is the cutout's main support.", ST["td"])],
        [Paragraph("<b>~Nov 24</b>", ST["td"]),
         Paragraph("NASS Cold Storage, Oct 31 stocks", ST["td"]),
         Paragraph("Monthly", ST["td"]),
         Paragraph("Stocks already +9% YoY; another build confirms demand "
                   "weakness.", ST["td"])],
        [Paragraph("<b>Late Dec</b>", ST["td"]),
         Paragraph("NASS Quarterly Hogs and Pigs", ST["td"]),
         Paragraph("Quarterly", ST["td"]),
         Paragraph("Sets the forward supply map through mid-2027.", ST["td"])],
        [Paragraph("<b>Daily</b>", ST["td"]),
         Paragraph("Negotiated head count", ST["td"]),
         Paragraph("Daily", ST["td"]),
         Paragraph("Under ~6,000 head, treat the print as noise.", ST["td"])],
    ]
    s.append(data_table(
        ["When", "Release", "Frequency", "Why it matters right now"], rows,
        widths=[0.92 * inch, 1.90 * inch, 0.80 * inch, 3.23 * inch]))
    return s


# --------------------------------------------------------------- page 3
def page_price():
    s = []
    s += section("Lean hog price complex",
                 "National negotiated base price vs producer-sold base across all "
                 "purchase types, carcass basis.")
    s += chart(f"{C.OUT}/price_divergence.png")
    s.append(Spacer(1, 4))
    s.append(Paragraph(
        "The blue line is what producers were paid across every purchase "
        "arrangement; the red line is the thin spot market that sets the headline. "
        "They moved together until the final week of October, then separated "
        f"sharply; the gap stands at <b>{money(_neg_gap())}/cwt</b>. A divergence "
        "of that size is a market-structure event, not a demand event.",
        ST["body"]))
    s.append(Spacer(1, 9))

    s += section("Cutout and packer margin")
    s += chart(f"{C.OUT}/cutout_spread.png")
    s.append(Spacer(1, 5))
    s.append(Paragraph(
        "Carcass value and the hog bid have pulled apart, so the swing lands in "
        "packer margin. The cutout-to-base spread moved from "
        f"{money(_spread_prior())} to <b>{money(_spread_now())}/cwt</b> on the "
        "latest session. On a 215 lb carcass that is "
        f"<b>{money(D.revenue_per_head(_spread_now()))} per head</b> of gross "
        "margin between the hog and the box.", ST["body"]))
    return s


# --------------------------------------------------------------- page 3
def page_price_table():
    s = []
    s += section("Price reference table")
    neg, cut = D.NEGOTIATED, D.CUTOUT
    rows = [
        [Paragraph("<b>Negotiated base price</b>", ST["td"]),
         Paragraph(money(neg["value"]), ST["tdrb"]),
         Paragraph(money(D.cad(neg["value"])), ST["tdr"]),
         Paragraph(f'<font color="{hx(DOWN)}"><b>'
                   f'{delta_str(neg["chg"])}</b></font>', ST["tdr"]),
         Paragraph(f"{money(neg['low'])} – {money(neg['high'])}", ST["tdr"]),
         Paragraph(neg["asof"], ST["td"])],
        [Paragraph("Negotiated, 5-day rolling", ST["td"]),
         Paragraph(money(neg["roll5"]), ST["tdrb"]),
         Paragraph(money(D.cad(neg["roll5"])), ST["tdr"]),
         Paragraph("—", ST["tdr"]), Paragraph("—", ST["tdr"]),
         Paragraph(neg["asof"], ST["td"])],
        [Paragraph("<b>Producer base, all types</b>", ST["td"]),
         Paragraph(money(D.PRODUCER_ALL["value"]), ST["tdrb"]),
         Paragraph(money(D.cad(D.PRODUCER_ALL["value"])), ST["tdr"]),
         Paragraph(f'<font color="{hx(DOWN)}"><b>-0.76</b></font>',
                   ST["tdr"]),
         Paragraph("—", ST["tdr"]),
         Paragraph(D.PRODUCER_ALL["asof"], ST["td"])],
        [Paragraph("<b>Pork carcass cutout</b>", ST["td"]),
         Paragraph(money(cut["value"]), ST["tdrb"]),
         Paragraph(money(D.cad(cut["value"])), ST["tdr"]),
         Paragraph(f'<font color="{hx(UP)}"><b>'
                   f'{delta_str(cut["chg"])}</b></font>', ST["tdr"]),
         Paragraph("—", ST["tdr"]),
         Paragraph(cut["asof"], ST["td"])],
        [Paragraph("Cutout less negotiated base", ST["td"]),
         Paragraph(money(cut["value"] - 48.76), ST["tdrb"]),
         Paragraph(money(D.cad(cut["value"] - 48.76)), ST["tdr"]),
         Paragraph(f'<font color="{hx(UP)}"><b>+7.69</b></font>',
                   ST["tdr"]),
         Paragraph("—", ST["tdr"]),
         Paragraph(cut["asof"], ST["td"])],
        [Paragraph("By-product drop value", ST["td"]),
         Paragraph(money(D.BYPRODUCT["value"]), ST["tdrb"]),
         Paragraph(money(D.cad(D.BYPRODUCT["value"])), ST["tdr"]),
         Paragraph(f'<font color="{hx(DOWN)}"><b>-0.09</b></font>',
                   ST["tdr"]),
         Paragraph("—", ST["tdr"]),
         Paragraph(D.BYPRODUCT["asof"], ST["td"])],
        [Paragraph("CME Lean Hog Index", ST["td"]),
         Paragraph(money(D.COT["cme_index"]), ST["tdrb"]),
         Paragraph(money(D.cad(D.COT["cme_index"])), ST["tdr"]),
         Paragraph("—", ST["tdr"]), Paragraph("—", ST["tdr"]),
         Paragraph(D.COT["cme_index_asof"], ST["td"])],
    ]
    s.append(data_table(
        ["Measure ($/cwt carcass)", "USD", "CAD", "Change", "Day's range",
         "As of"],
        rows,
        widths=[1.85 * inch, 0.78 * inch, 0.78 * inch, 0.72 * inch,
                1.25 * inch, 0.92 * inch],
        aligns=["l", "r", "r", "r", "r", "l"]))
    s.append(Spacer(1, 11))

    s += section("Primal values")
    s += chart(f"{C.OUT}/primals.png")
    s.append(Spacer(1, 5))
    s.append(Paragraph(
        "Picnic led higher (+$6.16) while rib gave back $9.35. Ham — the "
        "primal that matters most into the December holiday window — was "
        "essentially unchanged at $64.30. With the cutout flat and hams steady, "
        "there is no carcass-value justification for the cash break.", ST["body"]))
    s.append(Spacer(1, 8))

    rows = []
    for name, cur_v, prv_v in D.CUTOUT["primals"]:
        ch = cur_v - prv_v
        col = hx(UP) if ch > 0 else (hx(DOWN) if ch < 0 else hx(FLAT))
        rows.append([
            Paragraph(f"<b>{name}</b>", ST["td"]),
            Paragraph(money(prv_v), ST["tdr"]),
            Paragraph(money(cur_v), ST["tdrb"]),
            Paragraph(f'<font color="{col}"><b>{delta_str(ch)}</b></font>',
                      ST["tdr"]),
            Paragraph(f'<font color="{col}"><b>{ch/prv_v*100:+.1f}%</b></font>',
                      ST["tdr"]),
            Paragraph(money(D.cad(cur_v)), ST["tdr"]),
        ])
    s.append(data_table(
        ["Primal ($/cwt)", "Nov 2", "Nov 3", "Change", "%", "CAD Nov 3"],
        rows,
        widths=[1.50 * inch, 0.88 * inch, 0.88 * inch, 0.88 * inch,
                0.72 * inch, 0.98 * inch],
        aligns=["l", "r", "r", "r", "r", "r"]))
    return s


# --------------------------------------------------------------- page 3
def page_thin_market():
    s = []
    s += section("How thin the negotiated market really is",
                 "Plant-delivered purchases, barrows and gilts, carcass basis, "
                 f"{_fmt_long(D.PURCHASE_TYPES['asof'])}.")
    s += chart(f"{C.OUT}/purchase_mix.png")
    s.append(Spacer(1, 6))

    rows = []
    tot_head = sum(r[1] for r in D.PURCHASE_TYPES["rows"])
    for label, head, price, note in D.PURCHASE_TYPES["rows"]:
        rows.append([
            Paragraph(f"<b>{label}</b>", ST["td"]),
            Paragraph(note, ST["td"]),
            Paragraph(f"{head:,}", ST["tdr"]),
            Paragraph(f"{head/tot_head*100:.1f}%", ST["tdr"]),
            Paragraph(money(price), ST["tdrb"]),
            Paragraph(money(D.cad(price)), ST["tdr"]),
            Paragraph(money(D.revenue_per_head(price)), ST["tdr"]),
        ])
    s.append(data_table(
        ["Purchase type", "Basis", "Head", "Share", "Base $/cwt",
         "CAD $/cwt", "$/head*"],
        rows,
        widths=[1.42 * inch, 0.95 * inch, 0.78 * inch, 0.55 * inch,
                0.85 * inch, 0.85 * inch, 0.80 * inch],
        aligns=["l", "l", "r", "r", "r", "r", "r"]))
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        "* Gross carcass revenue per head at a 215 lb carcass, before premiums, "
        "sort loss and deductions.", ST["cap"]))
    s.append(Spacer(1, 10))
    s.append(callout(
        f"What the {money(_neg_gap())}/cwt gap is worth per head",
        "At a 215 lb carcass, the difference between the negotiated print "
        f"({money(D.NEGOTIATED['value'])}) and the all-purchase-type base "
        f"({money(D.PRODUCER_ALL['value'])}) is "
        f"<b>{money(D.revenue_per_head(_neg_gap()))} per "
        f"head</b> — roughly C{money(D.cad(D.revenue_per_head(_neg_gap())))}. "
        "That gap is the single most important "
        "number on this page, and it is the reason the headline price should "
        "never be used on its own to value a load.", tone="warn"))
    return s


# --------------------------------------------------------------- page 5
def page_breeding():
    s = []
    s += section("Breeding stock and replacement pigs")
    s.append(two_up(half_chart(f"{C.OUT}/sows.png"),
                    half_chart(f"{C.OUT}/weans.png")))
    s.append(Spacer(1, 6))

    rows = []
    for cls, wtd, wt, head, lo, hi in D.SOWS["classes"]:
        rows.append([
            Paragraph(f"<b>{cls} lb</b>", ST["td"]),
            Paragraph(f"{head:,}", ST["tdr"]),
            Paragraph(f"{wt}", ST["tdr"]),
            Paragraph(money(wtd), ST["tdrb"]),
            Paragraph(f"{money(lo)} – {money(hi)}", ST["tdr"]),
            Paragraph(money(wtd * wt / 100), ST["tdr"]),
        ])
    rows.append([
        Paragraph("<b>Weighted average</b>", ST["tdb"]),
        Paragraph(f"<b>{D.SOWS['total_head']:,}</b>", ST["tdrb"]),
        Paragraph("", ST["tdr"]),
        Paragraph(f"<b>{money(D.sow_weighted_avg())}</b>", ST["tdrb"]),
        Paragraph("", ST["tdr"]),
        Paragraph("", ST["tdr"]),
    ])
    s.append(data_table(
        ["Sow weight class", "Head", "Avg wt", "Wtd avg $/cwt",
         "Range $/cwt", "Est. $/head"],
        rows,
        widths=[1.45 * inch, 0.85 * inch, 0.80 * inch, 1.15 * inch,
                1.55 * inch, 0.95 * inch],
        aligns=["l", "r", "r", "r", "r", "r"]))
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        f"National negotiated sows, live basis, {D.SOWS['asof']}. "
        f"{D.SOWS['canada_origin_head']:,} head of the day's sow and boar volume "
        "originated in Canada. Cash SEW pigs at $22.35/head sit $15.71 below the "
        "formula price of $38.06 — the spot replacement-pig market is as weak "
        "as the spot hog market.", ST["cap"]))
    return s


# --------------------------------------------------------------- page 6
def page_feed():
    s = []
    s += section("Feed costs")
    s += chart(f"{C.OUT}/feed.png")
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        "Note: value axes are truncated to show day-to-day movement; both series "
        "moved less than 1.5% across the three sessions.", ST["cap"]))
    s.append(Spacer(1, 6))

    m = D.FEED["model"]
    fh = D.feed_cost_per_head()
    fc = D.feed_cost_per_cwt()
    rows = [
        [Paragraph("Corn", ST["td"]),
         Paragraph(f"{m['corn_bu_per_head']} bu/head", ST["tdr"]),
         Paragraph(money(D.FEED["corn"]["value"]) + "/bu", ST["tdr"]),
         Paragraph(money(m["corn_bu_per_head"] * D.FEED["corn"]["value"]), ST["tdrb"]),
         Paragraph(money(D.cad(m["corn_bu_per_head"] * D.FEED["corn"]["value"])), ST["tdr"])],
        [Paragraph("Soybean meal", ST["td"]),
         Paragraph(f"{m['sbm_ton_per_head']} ton/head", ST["tdr"]),
         Paragraph(money(D.FEED["sbm"]["value"]) + "/ton", ST["tdr"]),
         Paragraph(money(m["sbm_ton_per_head"] * D.FEED["sbm"]["value"]), ST["tdrb"]),
         Paragraph(money(D.cad(m["sbm_ton_per_head"] * D.FEED["sbm"]["value"])), ST["tdr"])],
        [Paragraph("<b>Feed cost per head</b>", ST["tdb"]),
         Paragraph("", ST["tdr"]), Paragraph("", ST["tdr"]),
         Paragraph(f"<b>{money(fh)}</b>", ST["tdrb"]),
         Paragraph(f"<b>{money(D.cad(fh))}</b>", ST["tdrb"])],
        [Paragraph("<b>Feed cost per cwt carcass</b>", ST["tdb"]),
         Paragraph("215 lb carcass", ST["tdr"]), Paragraph("", ST["tdr"]),
         Paragraph(f"<b>{money(fc)}</b>", ST["tdrb"]),
         Paragraph(f"<b>{money(D.cad(fc))}</b>", ST["tdrb"])],
    ]
    s.append(data_table(
        ["Input", "Rate", "Price", "USD", "CAD"], rows,
        widths=[2.0 * inch, 1.35 * inch, 1.30 * inch, 1.05 * inch, 1.05 * inch],
        aligns=["l", "r", "r", "r", "r"]))
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        "Feed model assumes 9.5 bu corn and 90 lb soybean meal per market hog to a "
        "215 lb carcass, priced off December futures. Substitute your own rates "
        "and basis for a site-specific number; this is a market benchmark, not a "
        "ration cost.", ST["cap"]))
    s.append(Spacer(1, 11))
    s += slaughter_block()
    return s


# --------------------------------------------------------------- page 5
def page_supply():
    s = []
    s += section("Herd inventory and cold storage")
    s.append(two_up(half_chart(f"{C.OUT}/inventory.png"),
                    half_chart(f"{C.OUT}/coldstorage.png")))
    s.append(Spacer(1, 7))

    rows = []
    for lbl, y26, y25, pct in [(r[0], r[1], r[2], r[3]) for r in D.INVENTORY["rows"]]:
        c = UP if pct > 0 else DOWN
        rows.append([
            Paragraph(f"<b>{lbl}</b>", ST["td"]),
            Paragraph(f"{y25:,}", ST["tdr"]),
            Paragraph(f"{y26:,}", ST["tdrb"]),
            Paragraph(f'<font color="{hx(c)}"><b>{pct:+.1f}%</b></font>',
                      ST["tdr"]),
            Paragraph("", ST["td"]),
        ])
    for lbl, y26, y25, pct, window in D.INVENTORY["weight_classes"]:
        c = UP if pct > 0 else DOWN
        rows.append([
            Paragraph(f"&nbsp;&nbsp;{lbl}", ST["td"]),
            Paragraph(f"{y25:,}", ST["tdr"]),
            Paragraph(f"{y26:,}", ST["tdrb"]),
            Paragraph(f'<font color="{hx(c)}"><b>{pct:+.1f}%</b></font>',
                      ST["tdr"]),
            Paragraph(window, ST["td"]),
        ])
    s.append(data_table(
        ["Inventory class (1,000 head)", "Sep 1 2025", "Sep 1 2026", "YoY",
         "Reaches market"],
        rows,
        widths=[2.05 * inch, 0.95 * inch, 0.95 * inch, 0.70 * inch, 1.60 * inch],
        aligns=["l", "r", "r", "r", "l"]))
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        f"{D.INVENTORY['notes']} Next Quarterly Hogs and Pigs: "
        f"{D.INVENTORY['next_release']}.", ST["cap"]))
    return s


def slaughter_block():
    s = []
    s += section("Slaughter and carcass weights")
    sl = D.SLAUGHTER
    rows = [
        [Paragraph("Daily slaughter under FIS (est.)", ST["td"]),
         Paragraph(f"{sl['today_est']:,}", ST["tdrb"]),
         Paragraph(f"{sl['week_ago_est']:,}", ST["tdr"]),
         Paragraph(f"{sl['year_ago_act']:,}", ST["tdr"]),
         Paragraph(f'<font color="{hx(UP)}"><b>'
                   f'{(sl["today_est"]/sl["year_ago_act"]-1)*100:+.1f}%</b></font>',
                   ST["tdr"])],
        [Paragraph("Week to date", ST["td"]),
         Paragraph(f"{sl['wtd_est']:,}", ST["tdrb"]),
         Paragraph(f"{sl['wtd_prior_week']:,}", ST["tdr"]),
         Paragraph(f"{sl['wtd_year_ago']:,}", ST["tdr"]),
         Paragraph(f'<font color="{hx(UP)}"><b>'
                   f'{(sl["wtd_est"]/sl["wtd_year_ago"]-1)*100:+.1f}%</b></font>',
                   ST["tdr"])],
        [Paragraph("Saturday kill (est.)", ST["td"]),
         Paragraph(f"{sl['sat_est']:,}", ST["tdrb"]),
         Paragraph("110,000", ST["tdr"]),
         Paragraph("183,456", ST["tdr"]),
         Paragraph(f'<font color="{hx(UP)}"><b>+10.1%</b></font>',
                   ST["tdr"])],
    ]
    s.append(data_table(
        ["Slaughter (head)", "Current", "Week ago", "Year ago", "vs year ago"],
        rows,
        widths=[2.25 * inch, 1.05 * inch, 1.00 * inch, 1.00 * inch, 0.95 * inch],
        aligns=["l", "r", "r", "r", "r"]))
    s.append(Spacer(1, 6))

    cw = D.CARCASS_WT
    rows = [[Paragraph("Negotiated", ST["td"]),
             Paragraph(f"{cw['negotiated']:.2f}", ST["tdrb"]),
             Paragraph("Swine/pork formula", ST["td"]),
             Paragraph(f"{cw['spmf']:.2f}", ST["tdrb"])],
            [Paragraph("Other market formula", ST["td"]),
             Paragraph(f"{cw['omf']:.2f}", ST["tdrb"]),
             Paragraph("Other arrangement", ST["td"]),
             Paragraph(f"{cw['opa']:.2f}", ST["tdrb"])],
            [Paragraph("Combined", ST["td"]),
             Paragraph(f"{cw['combined']:.2f}", ST["tdrb"]),
             Paragraph("Packer owned", ST["td"]),
             Paragraph(f"{cw['packer_owned']:.2f}", ST["tdrb"])]]
    s.append(data_table(
        ["Average carcass weight", "lb", "Average carcass weight", "lb"], rows,
        widths=[1.95 * inch, 0.85 * inch, 1.95 * inch, 0.85 * inch],
        aligns=["l", "r", "l", "r"]))
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        "Carcass weight is the quiet supply variable: across a 2.4 million head "
        "week, a two-pound rise adds roughly 4.8 million lb of pork with no extra "
        "hogs. Negotiated hogs are running 6 lb heavier than packer-owned.",
        ST["cap"]))
    return s


# --------------------------------------------------------------- page 6
def page_exports():
    s = []
    s += section("Export demand",
                 f"USDA FAS weekly export sales, pork muscle cuts. "
                 f"As of {D.EXPORTS['asof']}.")
    s += chart(f"{C.OUT}/exports.png")
    s.append(Spacer(1, 5))
    e = D.EXPORTS
    s.append(Paragraph(
        f"Net sales of <b>{e['net_sales_mt']:,} MT</b> ran {e['net_sales_wow_pct']}% "
        f"above the prior week but {abs(e['net_sales_vs_4wk_pct'])}% below the "
        f"four-week average. Shipments of <b>{e['shipments_mt']:,} MT</b> were "
        f"{e['shipments_wow_pct']}% higher on the week. Mexico remains the volume "
        "anchor, taking nearly half of all physical shipments; China bought in two "
        "consecutive weeks, which matters because Chinese participation has been "
        "intermittent under current tariff conditions. Roughly "
        f"{e['share_of_production_pct']}% of US pork production moves to export, so "
        "a sustained shift in Mexican or Chinese buying feeds directly into the "
        "cutout within two to three weeks.", ST["body"]))
    s.append(Spacer(1, 10))
    s.append(callout(
        "Why exports belong on the first page of any hog report",
        "Export demand is the largest single swing factor in US pork disappearance "
        "and the one least visible in daily cash prices. A quarter to a third of "
        "production leaves the country, and it leaves as specific cuts — hams "
        "and picnics to Mexico, variety meats to Asia. When Mexico steps back, the "
        "ham primal has nowhere domestic to go at the same value, and the cutout "
        "follows it down within two to three weeks. Watch the Thursday FAS release "
        "as a leading indicator of the following fortnight's cutout, not as a "
        "same-week price driver.", tone="plain"))
    return s


# --------------------------------------------------------------- page 9
def page_cot():
    s = []
    s += section("Speculative positioning",
                 f"CFTC Commitments of Traders, Lean Hogs. Positions as of "
                 f"{D.COT['asof']}, released {D.COT['released']}. "
                 f"Next release {D.COT['next_release']}.")
    s += chart(f"{C.OUT}/cot.png")
    s.append(Spacer(1, 6))

    c = D.COT
    rows = [
        [Paragraph("Managed money long", ST["td"]),
         Paragraph(f"{c['mm_long']:,}", ST["tdrb"]),
         Paragraph(f"${D.contract_notional(c['mm_long'])/1e9:,.2f}B", ST["tdr"]),
         Paragraph("long exposure", ST["td"])],
        [Paragraph("Managed money short", ST["td"]),
         Paragraph(f"{c['mm_short']:,}", ST["tdrb"]),
         Paragraph(f"${D.contract_notional(c['mm_short'])/1e9:,.2f}B", ST["tdr"]),
         Paragraph("short exposure", ST["td"])],
        [Paragraph("<b>Managed money net</b>", ST["tdb"]),
         Paragraph(f"<b>{c['mm_net']:,}</b>", ST["tdrb"]),
         Paragraph(f"<b>${abs(D.contract_notional(c['mm_net']))/1e9:,.2f}B</b>",
                   ST["tdrb"]),
         Paragraph("<b>net SHORT</b>", ST["tdb"])],
        [Paragraph("Large speculators net (legacy)", ST["td"]),
         Paragraph(f"{c['large_spec_net']:,}", ST["tdrb"]),
         Paragraph(f"${abs(D.contract_notional(c['large_spec_net']))/1e9:,.2f}B",
                   ST["tdr"]),
         Paragraph("net SHORT", ST["td"])],
        [Paragraph("Futures + options net (reported)", ST["td"]),
         Paragraph(f"{c['futopt_net_reported']:,}", ST["tdrb"]),
         Paragraph("—", ST["tdr"]),
         Paragraph("separate series", ST["td"])],
    ]
    s.append(data_table(
        ["Position", "Contracts", "Est. notional", "Direction"], rows,
        widths=[2.45 * inch, 1.15 * inch, 1.30 * inch, 1.35 * inch],
        aligns=["l", "r", "r", "l"]))
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        f"Notional estimated at the CME Lean Hog Index of {money(c['cme_index'])}/cwt "
        f"({c['cme_index_asof']}) against a 40,000 lb contract. The futures-only "
        "disaggregated series and the futures-plus-options series are reported "
        "separately and do not reconcile to each other — both are shown rather "
        "than blended.", ST["cap"]))
    s.append(Spacer(1, 7))
    s.append(callout(
        "Positioning risk cuts both ways",
        f"{c['pct_rank_note']} A short base of {c['mm_short']:,} contracts against "
        "a contracting herd is the classic setup for a short-covering rally on any "
        "bullish surprise — a strong Hogs and Pigs number, a Chinese buying "
        "run, or a disease headline. Funds do not set the cash price, but they "
        "drive futures, and futures set the formula contracts that price two "
        "thirds of all hogs.", tone="warn"))
    return s


# --------------------------------------------------------------- page 7
def page_drivers():
    s = []
    s += section("What actually moves the lean hog base price",
                 "Ranked by influence on the daily print, with the series to watch "
                 "for each.")

    drivers = [
        ("1", "Pork carcass cutout value",
         "The strongest daily driver. Packers bid for hogs against the carcass "
         "value they expect to realise, so the base price tracks the cutout with a "
         "one-to-three day lag. The gap between them is packer gross margin, and it "
         "widens whenever hogs are plentiful relative to kill capacity. Ham and "
         "belly carry outsized weight seasonally — ham into the Q4 holiday "
         "window, belly through the summer BLT run.",
         "LM_PK602 daily, LM_PK600/601 morning"),
        ("2", "Slaughter capacity utilisation",
         "When the weekly kill runs at or near industry capacity, packers have no "
         "need to bid up for the marginal hog and the negotiated price sags. When "
         "supply falls below capacity, plants compete and cash firms. Saturday kill "
         "volume is the cleanest marginal signal — a large Saturday means "
         "packers are chasing hogs.",
         "SJ_LS710 daily, weekly FI slaughter"),
        ("3", "Negotiated market thinness and MPR confidentiality",
         "Only about 2-5% of hogs trade negotiated, yet that price anchors the "
         "formula contracts that price the other 95%. A few thousand head can move "
         "the reported base $5-7/cwt. Mandatory Price Reporting confidentiality "
         "rules suppress regional prints when too few packers report, which removes "
         "exactly the comparison points needed to sanity-check an outlier. This is "
         "structural fragility, not market information.",
         "LM_HG218 head counts alongside price"),
        ("4", "Managed money positioning",
         "Funds do not transact cash hogs, but they move futures, and futures feed "
         "both the Other Market Formula contracts and producer hedging behaviour. "
         "Extreme net short positioning raises the probability of a violent "
         "short-covering rally and tends to exaggerate moves in both directions.",
         "CFTC COT weekly, Friday 3:30pm ET"),
        ("5", "Export demand, Mexico and China above all",
         "Roughly a quarter to a third of US pork production is exported. Mexico "
         "absorbs hams and shoulders in volume; China is the swing buyer and the "
         "one most sensitive to tariffs; Japan and Korea pay premiums for specific "
         "cuts. One heavy week of Mexican ham buying can lift the ham primal and "
         "pull the whole cutout with it.",
         "FAS weekly export sales, Thursday"),
        ("6", "Frozen stocks and cold storage",
         "Monthly, and a demand-side drag when heavy. Large belly and ham "
         "inventories mean product the trade could not move fresh, which caps "
         "primal values until it clears. Current pork stocks 9% above year-ago is "
         "one of the few genuinely bearish fundamentals in this market.",
         "NASS Cold Storage, ~22nd-25th monthly"),
        ("7", "Herd inventory and the forward supply map",
         "Quarterly, and the best forward view available. The 180 lb-and-over class "
         "is the next four to six weeks of kill; the under-50 lb class is five to "
         "six months out; the breeding herd sets supply ten to twelve months "
         "forward. Read it as a calendar, not a snapshot.",
         "NASS Quarterly Hogs and Pigs"),
        ("8", "Average carcass weight",
         "The variable most often missed. Weight gains add tonnage without adding "
         "hogs, and heavier carcasses in a falling market usually mean producers "
         "are holding back — which builds a backlog that has to clear later.",
         "LM_HG201 weight distribution"),
        ("9", "Feed costs",
         "Slow-moving. Corn and soybean meal do not move the daily base price; they "
         "set the producer's floor and shape expansion decisions ten to twelve "
         "months out. Cheap corn encourages herd retention, which produces more "
         "hogs and lower prices a year later. This is a cycle driver, not a daily "
         "one.",
         "CBOT settlements, AMS cash grain"),
        ("10", "Seasonality",
         "The base price typically peaks in June and July and troughs in November "
         "and December. Q4 weakness is normal and expected; the question is always "
         "magnitude against the five-year pattern, never direction.",
         "Five-year average overlays"),
        ("11", "By-product drop value",
         "Small but real. Packers add hide, offal and rendering value to the "
         "carcass when calculating what they can pay. Currently $5.01/cwt.",
         "Weekly USDA by-product drop value"),
        ("12", "Disease, trade and macro shocks",
         "Low probability, high magnitude. PRRS and PEDv seasonal losses, ASF "
         "headlines anywhere in the world, tariff announcements, and dollar "
         "strength that suppresses export competitiveness. For a Canadian producer "
         "selling into the US, a weaker CAD amplifies USD returns on the way back.",
         "News flow, FX, FAS trade notices"),
    ]

    rows = []
    for rank, title, text, watch in drivers:
        rows.append([
            Paragraph(f'<font color="#2d5f8a"><b>{rank}</b></font>',
                      S("rk", fontName="Helvetica-Bold", fontSize=13,
                        leading=15, alignment=TA_CENTER)),
            Paragraph(f"<b>{title}</b><br/><font size=8.8>{text}</font>",
                      S("dv", fontSize=9.4, leading=12.4)),
            Paragraph(f"<i>{watch}</i>", S("wt", fontSize=7.8, leading=10,
                                           textColor=SOFT)),
        ])
    t = Table(rows, colWidths=[0.34 * inch, 5.08 * inch, 1.48 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
    ]))
    s.append(t)
    return s


# --------------------------------------------------------------- page 8
def page_sources():
    s = []
    s += section("Data sources, as-of dates and release calendar",
                 "Every metric in this report carries its own as-of date. Nothing "
                 "here is a same-day figure across the board — the underlying "
                 "series run on different clocks.")

    items = [
        ("Negotiated base price", D.NEGOTIATED["asof"], "Daily, ~2:00pm CT",
         "LM_HG218"),
        ("Producer base, all types", D.PRODUCER_ALL["asof"], "Daily, prior day",
         "LM_HG201"),
        ("Pork cutout and primals", D.CUTOUT["asof"], "Twice daily",
         "LM_PK602"),
        ("Sow and boar prices", D.SOWS["asof"], "Daily, prior day", "LM_HG234"),
        ("SEW and feeder pigs", D.FEEDER_PIGS["asof"], "Weekly", "AMS 2810"),
        ("Daily slaughter", D.SLAUGHTER["asof"], "Daily", "SJ_LS710"),
        ("Carcass weights", D.CARCASS_WT["asof"], "Daily, prior day", "LM_HG215"),
        ("Corn and soybean meal", D.FEED["asof"], "Daily settlement", "CBOT"),
        ("Pork exports", D.EXPORTS["asof"], "Weekly, Thursday", "FAS"),
        ("COT positioning", D.COT["asof"], "Weekly, Friday", "CFTC"),
        ("Cold storage", D.COLD_STORAGE["asof"], "Monthly, ~22nd-25th",
         "NASS Cold Storage"),
        ("Herd inventory", D.INVENTORY["asof"], "Quarterly", "NASS Hogs & Pigs"),
        ("Lean hog futures, 3 contracts", D.FUTURES["asof"],
         "Daily settlement", "CME"),
        ("CME Lean Hog Index", D.LH_INDEX["latest_asof"], "Daily", "CME"),
        ("USD/CAD", D.FX_ASOF, "Daily", "FX reference"),
    ]
    rows = [[Paragraph(f"<b>{a}</b>", ST["td"]), Paragraph(b, ST["td"]),
             Paragraph(c, ST["td"]), Paragraph(d, ST["td"])] for a, b, c, d in items]
    s.append(data_table(
        ["Metric", "As of", "Release frequency", "USDA / source report"],
        rows,
        widths=[1.95 * inch, 1.25 * inch, 1.55 * inch, 1.55 * inch]))
    s.append(Spacer(1, 10))

    s += section("Freshness at build time",
                 "How each series graded against its own expected refresh "
                 "cadence when this report was generated.")
    vd = V.verdict(V._parse(D.REPORT_DATE) or _dt.date.today())
    frows = []
    for r in vd["rows"]:
        col = {"FRESH": hx(UP), "STALE": hx(DOWN), "MISSING": hx(DOWN)}[r["state"]]
        age = "\u2014" if r["age"] is None else f"{r['age']}d"
        frows.append([
            Paragraph(("<b>*</b> " if r["core"] else "") + r["label"], ST["td"]),
            Paragraph(f'<font color="{col}"><b>{r["state"]}</b></font>', ST["td"]),
            Paragraph(r["asof"], ST["td"]),
            Paragraph(age, ST["tdr"]),
            Paragraph(f"{r['max_age']}d", ST["tdr"]),
        ])
    s.append(data_table(
        ["Series", "State", "As of", "Age", "Limit"], frows,
        widths=[2.35 * inch, 0.85 * inch, 1.05 * inch, 0.60 * inch, 0.60 * inch],
        aligns=["l", "l", "l", "r", "r"], compact=True))
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        f"* marks a core series. {vd['fresh_count']} of {vd['total']} fresh. "
        f"{vd['note']}", ST["cap"]))
    s.append(Spacer(1, 10))

    s += section("Build notes and known gaps")
    s.append(callout(
        "Historical depth — the one thing this sample does not yet carry",
        "You asked for ten years of history on each series. The figures in this "
        "report are verified against USDA source documents, but the trend charts "
        "are built on the live snapshot window only, because a decade of daily "
        "history has to come from the AMS Datamart API "
        "(mpr.datamart.ams.usda.gov) and NASS QuickStats rather than from the "
        "published PDFs. Those endpoints return full history in JSON and are the "
        "right foundation for the scheduled build. No historical values have been "
        "estimated or filled in to make a chart look complete — where a "
        "series is short, the chart shows only what was verified.", tone="warn"))
    s.append(Spacer(1, 8))

    s.append(callout(
        "What it takes to switch RSI and MACD on",
        "Ten dated December-contract settlements were verified and are carried "
        "in the dataset. That is enough for term structure and momentum but not "
        "for the oscillators: RSI(14) needs 30 sessions and MACD(12,26,9) needs "
        "60. Both are fully implemented and validated against reference series "
        "— RSI reproduces Wilder's worked example to within 0.07 — so they "
        "activate automatically once a daily settlement feed for HEZ26, HEG27 "
        "and HEJ27 is connected. Until then the technical block runs at 30% "
        "data and PI reports that openly rather than substituting a default. "
        "Note that a front-month continuous series cannot be used as a "
        "substitute: on 9 October the expiring October contract settled $75.05 "
        "while December settled $67.825, so splicing the two would fabricate a "
        "7-point crash that never happened.", tone="warn"))
    s.append(Spacer(1, 8))

    s.append(Paragraph("Method and conventions", ST["h3"]))
    for txt in [
        "<b>Currency.</b> All primary figures are USD as USDA publishes them. CAD "
        f"equivalents use {D.FX_USDCAD:.4f} and are shown on headline metrics only. "
        "The FX rate needs a live source in the scheduled build.",
        "<b>Derived values.</b> The sow weighted average, feed cost per head and "
        "per cwt, cutout-to-base spread, revenue per head and COT notional values "
        "are calculated in this report, not published by USDA. Each states its "
        "assumptions where it appears.",
        "<b>Cold storage 2025 comparisons.</b> Where a prior-year monthly value is "
        "shown, it is back-calculated from the published year-over-year percentage "
        "rather than read directly, and is labelled as such.",
        "<b>Series that do not reconcile.</b> The CFTC futures-only and "
        "futures-plus-options series report different net positions for the same "
        "Tuesday. Both appear; neither is blended into a single number.",
        "<b>Source priority.</b> Figures were taken from USDA source documents "
        "wherever the document could be read directly. Several commercial "
        "aggregators republishing these reports were found to mis-parse the AMS "
        "table layouts — one reported the cutout at $183.77 against a true "
        "$72.43 — so aggregator figures were not used for any price in this "
        "report.",
    ]:
        s.append(Paragraph(txt, ST["body"]))
        s.append(Spacer(1, 4))

    s.append(Spacer(1, 6))
    s.append(Paragraph("Primary sources", ST["h3"]))
    for key, (name, url) in D.SOURCES.items():
        s.append(Paragraph(
            f'<b>{name}</b><br/><font color="#5b6773">{url}</font>',
            S("src", fontSize=8.2, leading=10.5)))
        s.append(Spacer(1, 3))
    return s


if __name__ == "__main__":
    build()
    print("built", OUT)
