"""
Chart generation for the Lean Hog Market Report.

House style:
  * all text black and bold, sized for print
  * rounded bars, shaded within the bar (light at top, deeper at the base)
    rather than carrying a drop shadow around the outside
  * direction is colour-coded literally: an increase is green, a decrease is red
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter
import os
import data as D

OUT = "/home/claude/hogreport/charts"
# Fresh containers start without this directory; savefig will not create it.
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ palette
BLACK = "#000000"
GRID = "#d4d9de"
AXIS = "#6b7681"

UP = "#2e7d4f"          # an increase
DOWN = "#c0392b"        # a decrease
FLAT = "#7c8894"

BLUE = "#2d5f8a"
TEAL = "#2f7d7d"
AMBER = "#bf8a26"
PLUM = "#6b4a6e"
GREY = "#aab3bc"

# Vertical shading applied inside each bar: lifted at the top, deepened at the
# base. No drop shadow is drawn around the bar.
GRAD_LIGHT = 0.26
GRAD_DARK = 0.22


def _grad_img(color, n=256, light=GRAD_LIGHT, dark=GRAD_DARK):
    """A top-to-bottom ramp from a lifted tint to a deepened shade."""
    rgb = np.array(to_rgb(color), dtype=float)
    top = rgb + (1.0 - rgb) * light
    bot = rgb * (1.0 - dark)
    t = np.linspace(0.0, 1.0, n).reshape(n, 1, 1)
    img = (1.0 - t) * top.reshape(1, 1, 3) + t * bot.reshape(1, 1, 3)
    return np.clip(img, 0.0, 1.0)


def _shade(ax, patch, color, extent, zorder):
    """Clip a vertical gradient to the rounded bar outline."""
    im = ax.imshow(_grad_img(color), extent=extent, aspect="auto",
                   origin="upper", zorder=zorder + 0.05,
                   interpolation="bilinear")
    im.set_clip_path(patch)
    return im

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "font.weight": "bold",
    "text.color": BLACK,
    "font.size": 11,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 1.0,
    "axes.labelcolor": BLACK,
    "axes.labelweight": "bold",
    "axes.titlecolor": BLACK,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "xtick.color": BLACK,
    "ytick.color": BLACK,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 10.5,
    "legend.frameon": False,
    "legend.labelcolor": BLACK,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


# ------------------------------------------------------------------ helpers
def _bold_ticks(ax):
    for lbl in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
        lbl.set_fontweight("bold")
        lbl.set_color(BLACK)


def _clean(ax, ygrid=True, left=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if not left:
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
    for s in ("left", "bottom"):
        if ax.spines[s].get_visible():
            ax.spines[s].set_color(AXIS)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
    _bold_ticks(ax)


def _money(ax, dec=0):
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"${v:,.{dec}f}"))


def _aspect(ax):
    """Data-space aspect so rounded corners stay circular on screen.

    Magnitude only: on an inverted axis (invert_yaxis) the signed ratio goes
    negative, which flips the corner arcs and carves the cap inward.
    """
    ax.figure.canvas.draw()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    bb = ax.get_window_extent()
    xs = abs(x1 - x0) / bb.width
    ys = abs(y1 - y0) / bb.height
    return ys / xs


def vbars(ax, xs, heights, width, colors, round_frac=0.34, bottom=0.0):
    """Vertical rounded bars, shaded top-to-bottom inside the bar."""
    asp = _aspect(ax)
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    if not isinstance(colors, (list, tuple)):
        colors = [colors] * len(xs)
    for x, h, c in zip(xs, heights, colors):
        if h == 0:
            continue
        r = width * round_frac
        # keep the corner radius from exceeding the bar
        r = min(r, abs(h) / (2.2 * asp)) if h else r
        iw = max(width - 2 * r, 1e-9)
        ih = max(abs(h) - 2 * r * asp, 1e-9)
        y0 = bottom + r * asp if h > 0 else bottom + h + r * asp
        p = FancyBboxPatch((x - width / 2 + r, y0), iw, ih,
                           boxstyle=f"round,pad={r},rounding_size={r}",
                           mutation_aspect=asp, linewidth=0,
                           facecolor=c, zorder=3)
        ax.add_patch(p)
        lo, hi = (bottom, bottom + h) if h > 0 else (bottom + h, bottom)
        _shade(ax, p, c, (x - width / 2, x + width / 2, lo, hi), 3)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)


def hbars(ax, ys, lengths, thick, colors, round_frac=0.46, left=0.0):
    """Horizontal pill bars (fully rounded caps), shaded inside the bar.

    round_frac stays just under 0.5: at exactly half the bar thickness the
    corner arcs meet and overlap, which carves a notch out of the cap.
    """
    asp = _aspect(ax)
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    if not isinstance(colors, (list, tuple)):
        colors = [colors] * len(ys)
    for y, L, c in zip(ys, lengths, colors):
        if L == 0:
            continue
        r = (thick / asp) * min(round_frac, 0.46)
        r = min(r, abs(L) / 2.2)
        iw = max(abs(L) - 2 * r, 1e-9)
        ih = max(thick - 2 * r * asp, 1e-9)
        x_lo = min(left, left + L)          # negative L runs leftward
        x_hi = max(left, left + L)
        p = FancyBboxPatch((x_lo + r, y - thick / 2 + r * asp), iw, ih,
                           boxstyle=f"round,pad={r},rounding_size={r}",
                           mutation_aspect=asp, linewidth=0,
                           facecolor=c, zorder=3)
        ax.add_patch(p)
        _shade(ax, p, c, (x_lo, x_hi, y - thick / 2, y + thick / 2), 3)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)


def group_pos(i, n, width, gap):
    """Centre positions for n bars in group i, separated by `gap`."""
    total = n * width + (n - 1) * gap
    start = i - total / 2 + width / 2
    return [start + k * (width + gap) for k in range(n)]


def _dir_color(cur, prev):
    if cur > prev:
        return UP
    if cur < prev:
        return DOWN
    return FLAT


def _save(fig, name):
    path = f"{OUT}/{name}.png"
    fig.savefig(path, dpi=int(__import__("os").environ.get("CHART_DPI", 150)), bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def _note(ax, txt):
    ax.text(0.0, -0.30, txt, transform=ax.transAxes, fontsize=9,
            color=BLACK, fontweight="bold", va="top")


# ------------------------------------------------------------------ 1
def price_divergence():
    fig, ax = plt.subplots(figsize=(7.1, 2.95))

    axis = ["Oct 23", "Nov 2", "Nov 3", "Nov 4"]
    all_pts = {"Oct 23": 71.54, "Nov 2": 66.91, "Nov 3": 66.15}
    neg_pts = {"Nov 2": 56.30, "Nov 3": 48.76, "Nov 4": 41.85}

    ax.set_xlim(-0.45, 3.55)
    ax.set_ylim(28, 82)

    ax.plot([axis.index(k) for k in all_pts], list(all_pts.values()),
            "-o", color=BLUE, lw=3.0, ms=9,
            label="All purchase types (producer sold)", zorder=4)
    ax.plot([axis.index(k) for k in neg_pts], list(neg_pts.values()),
            "-o", color=DOWN, lw=3.0, ms=9,
            label="Negotiated / spot only", zorder=4)

    ax.axhline(D.NEGOTIATED["roll5"], color=FLAT, ls=(0, (5, 4)), lw=1.6, zorder=2)
    ax.text(3.50, D.NEGOTIATED["roll5"] + 1.4,
            f"5-day avg  ${D.NEGOTIATED['roll5']:.2f}",
            color=BLACK, fontsize=10, fontweight="bold",
            va="bottom", ha="right")

    for k, v in neg_pts.items():
        ax.annotate(f"${v:,.2f}", (axis.index(k), v),
                    textcoords="offset points", xytext=(0, -20),
                    ha="center", fontsize=11.5, color=BLACK, fontweight="bold")
    for k, v in all_pts.items():
        ax.annotate(f"${v:,.2f}", (axis.index(k), v),
                    textcoords="offset points", xytext=(0, 13),
                    ha="center", fontsize=11.5, color=BLACK, fontweight="bold")

    ax.set_xticks(range(len(axis)))
    ax.set_xticklabels(axis)
    ax.set_ylabel("$/cwt carcass")
    ax.set_title("Negotiated spot has broken away from what producers receive",
                 pad=12)
    _money(ax)
    _clean(ax)
    ax.legend(loc="lower left", ncol=1)
    return _save(fig, "price_divergence")


# ------------------------------------------------------------------ 2
def purchase_mix():
    rows = D.PURCHASE_TYPES["rows"]
    _WRAP = {
        "Negotiated": "Negotiated",
        "Other market formula": "Other market\nformula",
        "Swine or pork mkt formula": "Swine/pork\nmkt formula",
        "Other purchase arrangement": "Other purchase\narrangement",
    }
    _SHORT = {
        "Negotiated": "Neg.",
        "Other market formula": "OMF",
        "Swine or pork mkt formula": "SPMF",
        "Other purchase arrangement": "OPA",
    }
    labels = [_WRAP.get(r[0], r[0]) for r in rows]
    shorts = [_SHORT.get(r[0], r[0][:5]) for r in rows]
    heads = [r[1] for r in rows]
    prices = [r[2] for r in rows]
    total = sum(heads)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.1, 2.85),
                                 gridspec_kw={"width_ratios": [1.5, 1],
                                              "wspace": 0.55})

    _pal = [DOWN, BLUE, TEAL, AXIS]
    cols = [_pal[i % len(_pal)] for i in range(len(rows))]

    y = list(range(len(labels)))
    a1.set_ylim(-0.7, len(labels) - 0.3)
    a1.set_xlim(0, max(heads) * 1.80)
    a1.invert_yaxis()
    hbars(a1, y, heads, 0.34, cols)
    a1.set_yticks(y)
    a1.set_yticklabels(labels, fontsize=10)
    a1.set_xlabel("head, plant delivered")
    a1.set_title("Volume by purchase type", pad=10)
    for i, h in enumerate(heads):
        a1.text(h + total * 0.055, i, f"{h:,}   {h/total*100:.1f}%",
                va="center", fontsize=10, color=BLACK, fontweight="bold")
    a1.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v/1000:.0f}k"))
    a1.xaxis.grid(True, color=GRID, lw=0.8)
    a1.set_axisbelow(True)
    for s in ("top", "right", "left"):
        a1.spines[s].set_visible(False)
    a1.spines["bottom"].set_color(AXIS)
    a1.tick_params(axis="y", length=0)
    _bold_ticks(a1)

    a2.set_xlim(-0.62, len(prices) - 0.38)
    a2.set_ylim(0, max(prices) * 1.32)
    vbars(a2, list(range(len(prices))), prices, 0.48, cols)
    a2.set_xticks(list(range(len(prices))))
    a2.set_xticklabels(shorts)
    a2.set_ylabel("$/cwt")
    a2.set_title("Base price paid", pad=10)
    for i, p in enumerate(prices):
        a2.text(i, p + max(prices) * 0.05, f"{p:,.2f}",
                ha="center", fontsize=9.5, color=BLACK, fontweight="bold")
    _money(a2)
    _clean(a2)
    return _save(fig, "purchase_mix")


# ------------------------------------------------------------------ 3
def cutout_and_spread():
    """Carcass cutout trend beside the packer gross-margin proxy."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.1, 2.65),
                                 gridspec_kw={"wspace": 0.40})

    s = D.CUTOUT["series"]
    vals = [x[1] for x in s]
    a1.set_xlim(-0.62, len(s) - 0.38)
    a1.set_ylim(0, max(vals) * 1.26)
    vbars(a1, list(range(len(s))), vals, 0.46,
          [FLAT, _dir_color(vals[1], vals[0])])
    a1.set_xticks(list(range(len(s))))
    a1.set_xticklabels([x[0] for x in s])
    for i, v in enumerate(vals):
        a1.text(i, v + max(vals) * 0.045, f"${v:,.2f}", ha="center",
                fontsize=12, color=BLACK, fontweight="bold")
    a1.set_ylabel("$/cwt")
    a1.set_title("Carcass cutout", pad=10)
    _money(a1)
    _clean(a1)

    pts = [("Nov 2", 72.28, 56.30), ("Nov 3", 72.43, 48.76)]
    labels = [p[0] for p in pts]
    spread = [p[1] - p[2] for p in pts]
    a2.set_xlim(-0.62, len(labels) - 0.38)
    a2.set_ylim(0, max(spread) * 1.30)
    vbars(a2, list(range(len(labels))), spread, 0.46,
          [FLAT, _dir_color(spread[1], spread[0])])
    a2.set_xticks(list(range(len(labels))))
    a2.set_xticklabels(labels)
    for i, v in enumerate(spread):
        a2.text(i, v + max(spread) * 0.05, f"${v:,.2f}", ha="center",
                fontsize=12, color=BLACK, fontweight="bold")
    a2.set_ylabel("$/cwt")
    a2.set_title("Cutout less negotiated base", pad=10)
    _money(a2)
    _clean(a2)
    return _save(fig, "cutout_spread")


# ------------------------------------------------------------------ 4
def primals_chart():
    pr = D.CUTOUT["primals"]
    names = [p[0] for p in pr]
    cur = [p[1] for p in pr]
    prv = [p[2] for p in pr]
    x = list(range(len(names)))
    w, g = 0.30, 0.10

    fig, ax = plt.subplots(figsize=(7.1, 2.65))
    top = max(max(cur), max(prv))
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.set_ylim(0, top * 1.44)
    left = [group_pos(i, 2, w, g)[0] for i in x]
    right = [group_pos(i, 2, w, g)[1] for i in x]
    vbars(ax, left, prv, w, GREY)
    vbars(ax, right, cur, w,
          [_dir_color(c, p) for c, p in zip(cur, prv)])
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=11.5)
    ax.set_ylabel("$/cwt")
    ax.set_title("Primal values  —  Nov 3 labelled", pad=10)
    # label sits above the taller bar of the pair so it never covers either one
    for i, c in enumerate(cur):
        ax.text(right[i], max(c, prv[i]) + top * 0.045, f"{c:,.1f}",
                ha="center", fontsize=10, color=BLACK, fontweight="bold")
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none")
               for c in (GREY, UP, DOWN)]
    ax.legend(handles, ["Nov 2", "Nov 3 higher", "Nov 3 lower"],
              loc="upper left", ncol=1, fontsize=9.5, handlelength=1.1)
    _money(ax)
    _clean(ax)
    return _save(fig, "primals")


# ------------------------------------------------------------------ 5
def sow_prices():
    cls = D.SOWS["classes"]
    names = [c[0] for c in cls]
    vals = [c[1] for c in cls]
    lows = [c[4] for c in cls]
    highs = [c[5] for c in cls]

    fig, ax = plt.subplots(figsize=(3.5, 2.85))
    x = list(range(len(names)))
    ax.set_xlim(-0.7, len(names) - 0.3)
    ax.set_ylim(20, 92)
    for i in x:
        ax.plot([i, i], [lows[i], highs[i]], color=GRID, lw=9,
                solid_capstyle="round", zorder=1)
    ax.scatter(x, vals, color=PLUM, s=95, zorder=4, linewidths=0)
    for i, v in enumerate(vals):
        ax.annotate(f"{v:,.0f}", (i, v), textcoords="offset points",
                    xytext=(0, 13), ha="center", fontsize=10.5,
                    color=BLACK, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=9.5, rotation=30, ha="right")
    ax.set_ylabel("$/cwt live")
    ax.set_title("Sow price by weight class", pad=10)
    _money(ax)
    _clean(ax)
    return _save(fig, "sows")


# ------------------------------------------------------------------ 6
def wean_prices():
    rows = D.FEEDER_PIGS["rows"]
    labels = ["SEW\n10-12 lb", "Feeder pig\n40 lb"]
    form = [r[1] for r in rows]
    cash = [r[2] if r[2] is not None else 0 for r in rows]
    comp = [r[3] for r in rows]

    fig, ax = plt.subplots(figsize=(3.5, 2.85))
    x = list(range(len(labels)))
    w, g = 0.21, 0.07
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylim(0, 60)
    pos = [group_pos(i, 3, w, g) for i in x]
    vbars(ax, [p[0] for p in pos], form, w, BLUE)
    vbars(ax, [p[1] for p in pos], cash, w, DOWN)
    vbars(ax, [p[2] for p in pos], comp, w, TEAL)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("$ per head")
    ax.set_title("Early-wean & feeder pigs", pad=10)
    for i in x:
        for px, v in zip(pos[i], (form[i], cash[i], comp[i])):
            if v:
                ax.text(px, v + 1.8, f"{v:,.0f}", ha="center",
                        fontsize=9.5, color=BLACK, fontweight="bold")
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none")
               for c in (BLUE, DOWN, TEAL)]
    ax.legend(handles, ["Formula", "Cash", "Composite"],
              loc="upper center", ncol=3, fontsize=9,
              handlelength=1.1, columnspacing=1.0,
              bbox_to_anchor=(0.5, 1.0))
    _money(ax)
    _clean(ax)
    return _save(fig, "weans")


# ------------------------------------------------------------------ 7
def feed_chart():
    corn = D.FEED["corn"]["series"]
    sbm = D.FEED["sbm"]["series"]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.1, 2.65),
                                 gridspec_kw={"wspace": 0.42})

    for ax, series, title, unit, dec, lab_dec in (
        (a1, corn, "Dec corn", "$/bu", 2, 2),
        (a2, sbm, "Dec soybean meal", "$/ton", 0, 2),
    ):
        labels = [s[0] for s in series]
        vals = [s[1] for s in series]
        base = min(vals) * 0.985
        cols = [FLAT] + [_dir_color(vals[i], vals[i - 1])
                         for i in range(1, len(vals))]
        ax.set_xlim(-0.65, len(vals) - 0.35)
        ax.set_ylim(base, max(vals) + (max(vals) - base) * 0.42)
        vbars(ax, list(range(len(vals))), [v - base for v in vals],
              0.5, cols, bottom=base)
        ax.set_xticks(list(range(len(vals))))
        ax.set_xticklabels(labels)
        for i, v in enumerate(vals):
            ax.text(i, v + (max(vals) - base) * 0.07,
                    f"${v:,.{lab_dec}f}", ha="center", fontsize=11,
                    color=BLACK, fontweight="bold")
        ax.set_ylabel(unit)
        ax.set_title(title, pad=10)
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda v, p, d=dec: f"${v:,.{d}f}"))
        _clean(ax)
    return _save(fig, "feed")


# ------------------------------------------------------------------ 8
def inventory_chart():
    wc = D.INVENTORY["weight_classes"]
    names = ["<50 lb", "50-119", "120-179", "180+"]
    y26 = [v[1] / 1000 for v in wc]
    y25 = [v[2] / 1000 for v in wc]
    pct = [v[3] for v in wc]

    fig, ax = plt.subplots(figsize=(3.5, 2.85))
    x = list(range(len(names)))
    w, g = 0.30, 0.10
    ax.set_xlim(-0.62, len(names) - 0.38)
    ax.set_ylim(0, 30)
    left = [group_pos(i, 2, w, g)[0] for i in x]
    right = [group_pos(i, 2, w, g)[1] for i in x]
    vbars(ax, left, y25, w, GREY)
    vbars(ax, right, y26, w,
          [_dir_color(a, b) for a, b in zip(y26, y25)])
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=10)
    ax.set_ylabel("million head")
    ax.set_title("Market hogs by weight class", pad=10)
    for i, (v, p) in enumerate(zip(y26, pct)):
        ax.text(right[i], max(v, y25[i]) + 0.9, f"{p:+.1f}%", ha="center",
                fontsize=9, color=BLACK, fontweight="bold")
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none") for c in (GREY, DOWN)]
    ax.legend(handles, ["Sep 1 2025", "Sep 1 2026"], loc="upper right",
              ncol=1, fontsize=9, handlelength=1.1)
    _clean(ax)
    return _save(fig, "inventory")


# ------------------------------------------------------------------ 9
def cold_storage_chart():
    s26 = D.COLD_STORAGE["series_2026"]
    labels = [x[0] for x in s26]
    vals = [x[1] for x in s26]

    fig, ax = plt.subplots(figsize=(3.5, 2.85))
    x = list(range(len(labels)))
    base = 380
    cols = [FLAT] + [_dir_color(vals[i], vals[i - 1]) for i in range(1, len(vals))]
    ax.set_xlim(-0.62, len(labels) - 0.38)
    ax.set_ylim(base, 492)
    vbars(ax, x, [v - base for v in vals], 0.52, cols, bottom=base)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    for i, v in enumerate(vals):
        ax.text(i, v + 4.5, f"{v:,.0f}", ha="center", fontsize=11,
                color=BLACK, fontweight="bold")
    ax.set_ylabel("million lb")
    ax.set_title("Frozen pork in cold storage", pad=10)
    _clean(ax)
    return _save(fig, "coldstorage")


# ------------------------------------------------------------------ 10
def cot_chart():
    c = D.COT
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.1, 2.75),
                                 gridspec_kw={"width_ratios": [0.80, 1.20],
                                              "wspace": 0.78})

    vals = [c["mm_long"], c["mm_short"]]
    a1.set_xlim(-0.7, 1.7)
    a1.set_ylim(0, max(vals) * 1.30)
    vbars(a1, [0, 1], vals, 0.46, [UP, DOWN])
    a1.set_xticks([0, 1])
    a1.set_xticklabels(["Long", "Short"])
    a1.set_ylabel("contracts")
    a1.set_title("Managed money gross positions", pad=10)
    for i, v in enumerate(vals):
        a1.text(i, v + max(vals) * 0.045, f"{v:,}", ha="center",
                fontsize=12, color=BLACK, fontweight="bold")
    a1.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v/1000:.0f}k"))
    _clean(a1)

    nets = [("Managed money\nprior week", abs(c["mm_net_prior"])),
            ("Managed money\nOct 27", abs(c["mm_net"])),
            ("Large speculators\nOct 27", abs(c["large_spec_net"]))]
    nv = [n[1] for n in nets]
    y = list(range(len(nets)))
    a2.set_ylim(-0.72, len(nets) - 0.28)
    a2.set_xlim(0, max(nv) * 1.50)
    a2.invert_yaxis()
    hbars(a2, y, nv, 0.34, [FLAT, DOWN, "#8a3b30"])
    a2.set_yticks(y)
    a2.set_yticklabels([n[0] for n in nets], fontsize=9.5)
    a2.set_xlabel("contracts net SHORT")
    a2.set_title("Net short positioning", pad=10)
    for i, v in enumerate(nv):
        a2.text(v + max(nv) * 0.045, i, f"{v:,}", va="center",
                fontsize=10.5, color=BLACK, fontweight="bold")
    a2.set_xticks([0, 40000, 80000])
    a2.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v/1000:.0f}k"))
    a2.xaxis.grid(True, color=GRID, lw=0.8)
    a2.set_axisbelow(True)
    for s in ("top", "right", "left"):
        a2.spines[s].set_visible(False)
    a2.spines["bottom"].set_color(AXIS)
    a2.tick_params(axis="y", length=0)
    _bold_ticks(a2)
    return _save(fig, "cot")


# ------------------------------------------------------------------ 11
def exports_chart():
    e = D.EXPORTS
    ns = dict(e["net_sales_by_dest"])
    sh = dict(e["shipments_by_dest"])
    dests = ["Mexico", "Japan", "China", "S. Korea", "Colombia", "Canada"]
    key = {"S. Korea": "South Korea"}
    nsv = [ns.get(key.get(d, d), 0) for d in dests]
    shv = [sh.get(key.get(d, d), 0) for d in dests]

    fig, ax = plt.subplots(figsize=(7.1, 3.1))
    y = list(range(len(dests)))
    t, g = 0.26, 0.09
    ax.set_ylim(-0.7, len(dests) - 0.3)
    ax.set_xlim(0, 18600)
    ax.invert_yaxis()
    pos = [group_pos(i, 2, t, g) for i in y]
    hbars(ax, [p[0] for p in pos], nsv, t, BLUE)
    hbars(ax, [p[1] for p in pos], shv, t, TEAL)
    ax.set_yticks(y)
    ax.set_yticklabels(dests, fontsize=11.5)
    ax.set_xlabel("metric tons")
    ax.set_title("Weekly pork export sales & shipments by destination", pad=10)
    for i in y:
        if nsv[i]:
            ax.text(nsv[i] + 440, pos[i][0], f"{nsv[i]:,}", va="center",
                    fontsize=10, color=BLACK, fontweight="bold")
        if shv[i]:
            ax.text(shv[i] + 440, pos[i][1], f"{shv[i]:,}", va="center",
                    fontsize=10, color=BLACK, fontweight="bold")
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none") for c in (BLUE, TEAL)]
    ax.legend(handles, ["Net sales", "Shipments"], loc="lower right", ncol=1,
              fontsize=10.5, handlelength=1.1)
    ax.set_xticks([0, 5000, 10000, 15000])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v/1000:.0f}k"))
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(axis="y", length=0)
    _bold_ticks(ax)
    return _save(fig, "exports")


def build_all():
    return {
        "divergence": price_divergence(),
        "mix": purchase_mix(),
        "cutout_spread": cutout_and_spread(),
        "primals": primals_chart(),
        "sows": sow_prices(),
        "weans": wean_prices(),
        "feed": feed_chart(),
        "inventory": inventory_chart(),
        "coldstorage": cold_storage_chart(),
        "cot": cot_chart(),
        "exports": exports_chart(),
    }


if __name__ == "__main__":
    for k, v in build_all().items():
        print(k, v)


# ============================================================ PI charts
PI_BANDS = [
    (0, 20, "#8c2f22", "Strongly\nbearish"),
    (20, 35, "#b8452f", "Bearish"),
    (35, 45, "#c9793f", "Mildly\nbearish"),
    (45, 55, "#8d949b", "Neutral"),
    (55, 65, "#6d9668", "Mildly\nbullish"),
    (65, 80, "#44814f", "Bullish"),
    (80, 100, "#2d6138", "Strongly\nbullish"),
]


def pi_gauge(value, band_label):
    """Horizontal band gauge with a pointer at the current PI."""
    fig, ax = plt.subplots(figsize=(7.1, 1.18))
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.52, 1.34)

    for lo, hi, col, lbl in PI_BANDS:
        ax.add_patch(plt.Rectangle((lo, -0.1), hi - lo, 0.72,
                                   facecolor=col, edgecolor="white",
                                   linewidth=1.6, zorder=2))
        ax.text((lo + hi) / 2, 0.26, lbl, ha="center", va="center",
                fontsize=7.6, color="white", fontweight="bold", zorder=3)
        ax.text(lo, -0.26, f"{lo}", ha="center", va="top", fontsize=9,
                color=BLACK, fontweight="bold")
    ax.text(100, -0.26, "100", ha="center", va="top", fontsize=9,
            color=BLACK, fontweight="bold")

    # pointer
    ax.plot([value, value], [0.62, 0.95], color=BLACK, lw=2.6,
            solid_capstyle="round", zorder=5)
    ax.plot([value], [0.62], marker="v", ms=13, color=BLACK, zorder=6)
    ax.text(value, 1.04, f"PI  {value:.1f}", ha="center", va="bottom",
            fontsize=15, color=BLACK, fontweight="bold")

    ax.axis("off")
    return _save(fig, "pi_gauge")


def pi_history_forecast(hist, fc, current):
    """PI track to date beside the price forecast it implies."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.1, 3.0),
                                 gridspec_kw={"width_ratios": [1.02, 1],
                                              "wspace": 0.46})

    # ---- PI history
    labels = [h[0] for h in hist]
    vals = [h[1] for h in hist]
    partial = [h[2] for h in hist]
    x = list(range(len(vals)))
    a1.set_xlim(-0.4, len(vals) - 0.6)
    a1.set_ylim(28, 68)
    a1.axhspan(45, 55, color="#eef0f2", zorder=0)
    a1.axhline(50, color=FLAT, ls=(0, (4, 3)), lw=1.2, zorder=1)
    a1.text(len(vals) - 0.62, 50.7, "neutral", fontsize=8, color=BLACK,
            fontweight="bold", ha="right")
    a1.plot(x, vals, "-", color=BLUE, lw=2.6, zorder=3)
    for i, (v, p) in enumerate(zip(vals, partial)):
        a1.plot([i], [v], marker="o", ms=9, zorder=4,
                color="white" if p else BLUE,
                markeredgecolor=BLUE, markeredgewidth=2.4)
        a1.annotate(f"{v:.0f}", (i, v), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=10,
                    color=BLACK, fontweight="bold")
    a1.set_xticks(x)
    a1.set_xticklabels(labels, fontsize=9, rotation=28, ha="right")
    a1.set_ylabel("PI")
    a1.set_title("PI track", pad=9)
    _clean(a1)

    # ---- price forecast
    cur_base = fc["base"]
    items = [("Base\nnow", cur_base, BLUE),
             ("Futures\nimplied", fc["implied"], FLAT),
             ("PI\ncentre", fc["centre"], DOWN if fc["centre"] < cur_base else UP)]
    a2.set_xlim(-0.6, 2.95)
    a2.set_ylim(40, 80)
    vbars(a2, [0, 1, 2], [v - 40 for _, v, _ in items], 0.44,
          [c for _, _, c in items], bottom=40)

    # forecast range drawn BESIDE the PI bar, never across it
    wx = 2.62
    a2.plot([wx, wx], [fc["lo"], fc["hi"]], color=BLACK, lw=2.4,
            solid_capstyle="round", zorder=6)
    for yv in (fc["lo"], fc["hi"]):
        a2.plot([wx - 0.13, wx + 0.13], [yv, yv], color=BLACK, lw=2.4,
                zorder=6)
    # escaped dollars: an unescaped "$a - $b" is parsed as mathtext
    a2.text(wx, fc["hi"] + 1.6, f"\\${fc['lo']:,.0f}-\\${fc['hi']:,.0f}",
            ha="center", fontsize=8.5, color=BLACK, fontweight="bold")

    a2.set_xticks([0, 1, 2])
    a2.set_xticklabels([n for n, _, _ in items], fontsize=9)
    for i, (_, v, _) in enumerate(items):
        a2.text(i, v + 1.6, f"${v:,.2f}", ha="center", fontsize=9.5,
                color=BLACK, fontweight="bold")
    a2.set_ylabel("$/cwt base")
    a2.set_title(f"Projected base, {HORIZON_LBL}", pad=9)
    _money(a2)
    _clean(a2)
    return _save(fig, "pi_forecast")


HORIZON_LBL = "4-6 wk"


def pi_waterfall(res):
    """Block contributions and overlays, summing to the final PI."""
    blocks = res["blocks"]
    rows = [(b["label"], b["contrib"] * 50, b["completeness"])
            for b in blocks.values()]
    for name, k, _ in res["overlays"]:
        pretty = {"cot_extreme": "Fund positioning (extreme)",
                  "seasonal": "Seasonal adjustment",
                  "margin_reversion": "Margin mean reversion"}.get(name, name)
        rows.append((pretty, k * 50, 1.0))

    labels = [r[0] if r[2] >= 0.999 else f"{r[0]}  ({r[2]*100:.0f}% data)"
              for r in rows]
    vals = [r[1] for r in rows]
    comp = [r[2] for r in rows]

    fig, ax = plt.subplots(figsize=(7.1, 3.15))
    y = list(range(len(rows)))
    lim = max(abs(min(vals)), abs(max(vals))) * 1.35
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-0.75, len(rows) - 0.25)
    ax.invert_yaxis()

    cols = [UP if v > 0 else DOWN for v in vals]
    for i, v in enumerate(vals):
        hbars(ax, [i], [v], 0.44, [cols[i]], left=0.0)
    ax.axvline(0, color=AXIS, lw=1.4, zorder=5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.5)
    for i, (v, c) in enumerate(zip(vals, comp)):
        off = lim * 0.035
        ha = "left" if v > 0 else "right"
        tag = f"{v:+.1f}"
        ax.text(v + (off if v > 0 else -off), i, tag, va="center", ha=ha,
                fontsize=9.5, color=BLACK, fontweight="bold")
    ax.set_xlabel("PI points contributed")
    ax.set_title("What moved PI", pad=9)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(axis="y", length=0)
    _bold_ticks(ax)
    return _save(fig, "pi_waterfall")
