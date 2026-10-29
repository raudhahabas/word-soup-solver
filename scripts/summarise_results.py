"""Summarise the 100-grid benchmark (results/batch_100) and draw the headline figure.

Writes results/summary.csv and figures/policy_comparison.png.

    pip install -e ".[analysis]"
    python scripts/summarise_results.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
POLICIES = {"random": "Random", "greedy1": "Greedy-1", "greedy2": "Greedy-2", "greedy3": "Greedy-3", "hybrid": "Hybrid"}
COLORS = {"random": "#868e96", "greedy1": "#1c7ed6", "greedy2": "#0ca678", "greedy3": "#7048e8", "hybrid": "#e8590c"}
BONUS = 500


def load(policy: str) -> pd.DataFrame:
    df = pd.read_csv(RESULTS / "batch_100" / f"{policy}.csv")
    df["cleared"] = df["cleared"].astype(int)
    if "total_score_with_bonus" in df:
        df["score_with_bonus"] = df["total_score_with_bonus"]
        df["score_no_bonus"] = df["scoreNoBonus"]
    else:
        # In random.csv and hybrid.csv the "scoreNoBonus" column already includes
        # the +500 clear bonus (see results/README.md), so take it back off here.
        df["score_with_bonus"] = df["scoreNoBonus"]
        df["score_no_bonus"] = df["scoreNoBonus"] - BONUS * df["cleared"]

    if "runtime_sec" in df:
        df["runtime"] = df["runtime_sec"]
    else:
        rt = pd.read_csv(RESULTS / "runtime" / f"{policy}.csv")
        df = df.merge(rt[["grid", "runtime_sec"]].rename(columns={"runtime_sec": "runtime"}), on="grid")
    return df


def main() -> None:
    rows = []
    for key, name in POLICIES.items():
        df = load(key)
        rows.append({
            "policy": name,
            "grids": len(df),
            "clear_rate": df["cleared"].mean(),
            "mean_score_with_bonus": df["score_with_bonus"].mean(),
            "mean_score_no_bonus": df["score_no_bonus"].mean(),
            "mean_runtime_sec": df["runtime"].mean(),
        })
    summary = pd.DataFrame(rows)
    summary.round(3).to_csv(RESULTS / "summary.csv", index=False)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    names = list(POLICIES.values())
    colors = list(COLORS.values())
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))

    ax = axes[0]
    bars = ax.bar(names, summary["clear_rate"] * 100, color=colors)
    ax.bar_label(bars, labels=[f"{v:.0%}" for v in summary["clear_rate"]], padding=3)
    ax.set_title("Boards cleared")
    ax.set_ylabel("% of 100 random 12×9 grids")
    ax.set_ylim(0, 100)

    ax = axes[1]
    ax.bar(names, summary["mean_score_no_bonus"], color=colors)
    bars = ax.bar(names, summary["mean_score_with_bonus"] - summary["mean_score_no_bonus"],
                  bottom=summary["mean_score_no_bonus"], color=colors, alpha=0.4, hatch="//", edgecolor="white")
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in summary["mean_score_with_bonus"]], padding=3)
    ax.set_title("Mean score (hatched = clear bonus)")
    ax.set_ylim(0, summary["mean_score_with_bonus"].max() * 1.15)

    ax = axes[2]
    bars = ax.bar(names, summary["mean_runtime_sec"], color=colors)
    ax.bar_label(bars, labels=[f"{v:.1f}s" if v >= 1 else f"{v:.2f}s" for v in summary["mean_runtime_sec"]], padding=3)
    ax.set_yscale("log")
    ax.set_title("Thinking time per game (log scale)")
    ax.set_ylabel("seconds")

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=9)
    fig.tight_layout()
    out = ROOT / "figures" / "policy_comparison.png"
    fig.savefig(out, dpi=160)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
