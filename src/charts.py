"""Charts for the README. Reads outputs/ (run run_analysis.py and scenarios.py first).

Run:  python src/charts.py
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from db import ROOT

OUT = ROOT / "outputs"
CH = OUT / "charts"

INK, MUTED, GRID = "#17243A", "#5B6577", "#E4E6EA"
ACCENT, CONTEXT, NEG = "#356AE6", "#B9BFC9", "#B4551B"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 160,
})


def title(ax, t, sub=None):
    ax.set_title(t, loc="left", fontsize=12, fontweight="bold", color=INK, pad=22 if sub else 10)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=MUTED)


def whale_curve():
    d = pd.read_csv(OUT / "03_merchant_profitability.csv").sort_values("contribution_2_eur", ascending=False)
    cum = d.contribution_2_eur.cumsum() / d.contribution_2_eur.sum() * 100
    x = np.arange(1, len(d) + 1)
    peak_i = int(cum.values.argmax())
    n_loss = int((d.contribution_2_eur < 0).sum())
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(x, cum.values, color=ACCENT, lw=2)
    ax.axhline(100, color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.axvspan(peak_i + 1, len(d), color=NEG, alpha=0.07, lw=0)
    for n in (20, 50):
        ax.plot(n, cum.values[n - 1], "o", ms=6, color=ACCENT, mec="white", mew=1.5)
        ax.annotate(f"Top {n}: {cum.values[n - 1]:.0f}%", (n, cum.values[n - 1]),
                    xytext=(10, -14), textcoords="offset points", fontsize=9)
    ax.annotate(f"Peak {cum.values[peak_i]:.1f}% at merchant {peak_i + 1}",
                (peak_i + 1, cum.values[peak_i]), xytext=(-20, 12), textcoords="offset points",
                fontsize=9, ha="right")
    ax.text(len(d) - 4, 30, f"{n_loss} merchants lose money\n(mostly SMB retail)", ha="right",
            fontsize=9, color=NEG)
    ax.set_xlim(0, len(d) + 5)
    ax.set_ylim(0, 110)
    ax.set_xlabel("Merchants, ranked by 2025 contribution")
    ax.set_ylabel("Cumulative share of contribution (%)")
    title(ax, "A few merchants earn most of the profit; the tail gives some back",
          "Cumulative contribution after cost to serve, 2025 (synthetic data)")
    fig.tight_layout()
    fig.savefig(CH / "whale_curve.png")
    plt.close(fig)


def share_tpv_vs_contribution():
    d = pd.read_csv(OUT / "02_segment_growth_vs_margin.csv")
    d["tpv_share"] = d.tpv_2025_m / d.tpv_2025_m.sum() * 100
    d["cm_share"] = d.contribution_2025_m / d.contribution_2025_m.sum() * 100
    d = d.sort_values("tpv_share")
    y = np.arange(len(d))
    h = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh(y + h / 2 + 0.01, d.tpv_share, h, color=CONTEXT, label="Share of TPV")
    ax.barh(y - h / 2 - 0.01, d.cm_share, h, color=ACCENT, label="Share of contribution")
    for yi, a, b in zip(y, d.tpv_share, d.cm_share):
        ax.text(a + 1, yi + h / 2, f"{a:.0f}%", va="center", fontsize=9, color=MUTED)
        ax.text(b + 1, yi - h / 2, f"{b:.0f}%", va="center", fontsize=9, color=INK)
    ax.set_yticks(y, d.segment)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 80)
    ax.set_xlabel("% of total, 2025")
    ax.legend(loc="lower right", frameon=False)
    title(ax, "Volume and profit come from different places",
          "Share of 2025 TPV vs share of contribution after cost to serve (synthetic data)")
    fig.tight_layout()
    fig.savefig(CH / "segment_share_tpv_vs_contribution.png")
    plt.close(fig)


def volume_vs_take_rate():
    d = pd.read_csv(OUT / "06_monthly_trend.csv")
    d["month"] = pd.to_datetime(d.month)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.2), sharex=True, gridspec_kw={"hspace": 0.45})
    a1.bar(d.month, d.tpv_m / 1000, width=20, color=CONTEXT)
    a1.set_ylabel("TPV (EUR bn)")
    title(a1, "Volume keeps growing...", "Monthly TPV, Jan 2024 - Dec 2025 (synthetic data)")
    a2.plot(d.month, d.take_rate_bps, color=ACCENT, lw=2)
    a2.set_ylabel("Take rate (bps)")
    a2.set_ylim(20, 42)
    first, last = d.iloc[0], d.iloc[-1]
    a2.annotate(f"{first.take_rate_bps:.1f}", (first.month, first.take_rate_bps), xytext=(0, 8),
                textcoords="offset points", fontsize=9)
    a2.annotate(f"{last.take_rate_bps:.1f}", (last.month, last.take_rate_bps), xytext=(-8, -16),
                textcoords="offset points", fontsize=9, ha="right")
    title(a2, "...while each euro earns less", "Net revenue / TPV, basis points")
    fig.savefig(CH / "volume_vs_take_rate.png", bbox_inches="tight")
    plt.close(fig)


def enterprise_grid():
    g = pd.read_csv(OUT / "scenario_enterprise_grid.csv", index_col=0) / 1e6
    lim = np.abs(g.values).max()
    cmap = LinearSegmentedColormap.from_list("div", [NEG, "#F4F4F2", ACCENT])
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.imshow(g.values, cmap=cmap, vmin=-lim, vmax=lim, aspect="auto")
    for i in range(g.shape[0]):
        for j in range(g.shape[1]):
            v = g.values[i, j]
            ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=9,
                    color="white" if abs(v) > lim * 0.6 else INK)
    ax.set_xticks(range(g.shape[1]), g.columns)
    ax.set_yticks(range(g.shape[0]), g.index)
    ax.set_xlabel("Volume growth")
    ax.set_ylabel("Take-rate cut")
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    title(ax, "Enterprise: how much volume pays for a price cut?",
          "Change in annual contribution vs 2025, EUR m (synthetic data)")
    fig.tight_layout()
    fig.savefig(CH / "enterprise_volume_vs_price.png")
    plt.close(fig)


def payment_methods():
    d = pd.read_csv(OUT / "05_payment_method.csv")
    d25 = d[d.year == 2025].set_index("payment_method")
    d24 = d[d.year == 2024].set_index("payment_method")
    names = {"debit_card": "Debit card", "credit_card": "Credit card", "digital_wallet": "Digital wallet",
             "local_bank": "Local bank payment", "bnpl": "Buy now, pay later"}
    order = d25.contribution_1_bps.sort_values().index
    fig, ax = plt.subplots(figsize=(8, 3.8))
    y = np.arange(len(order))
    colors = [NEG if m == "bnpl" else ACCENT for m in order]
    ax.barh(y, d25.contribution_1_bps[order], 0.55, color=colors)
    for yi, m in zip(y, order):
        s24, s25 = d24.share_of_tpv_pct[m], d25.share_of_tpv_pct[m]
        ax.text(d25.contribution_1_bps[m] + 0.5, yi,
                f"{d25.contribution_1_bps[m]:.0f} bps   ·   share of TPV {s24:.0f}% → {s25:.0f}%",
                va="center", fontsize=9)
    ax.set_yticks(y, [names[m] for m in order])
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 48)
    ax.set_xlabel("Contribution per euro of TPV, 2025 (bps, before cost to serve)")
    title(ax, "The fastest-growing method earns the least",
          "Contribution per euro by payment method, and its share of TPV 2024 → 2025 (synthetic data)")
    fig.tight_layout()
    fig.savefig(CH / "payment_methods.png")
    plt.close(fig)


def main():
    CH.mkdir(parents=True, exist_ok=True)
    whale_curve()
    share_tpv_vs_contribution()
    volume_vs_take_rate()
    enterprise_grid()
    payment_methods()
    print("charts written to", CH)


if __name__ == "__main__":
    main()
