"""
Generate Pareto front plot from experiment results.

Usage: uv run python plot.py
Output: pareto_plot.png
"""

import csv
import json
import os

import matplotlib.pyplot as plt
import numpy as np

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "results.tsv")
PARETO_FILE = os.path.join(os.path.dirname(__file__), "pareto.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "pareto_plot.png")


def load_results():
    """Load all experiments from results.tsv."""
    experiments = []
    with open(RESULTS_FILE, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                gbw = float(row["gbw_hz"])
                power = float(row["power_mw"])
                status = row.get("status", "").strip()
                experiments.append({
                    "gbw_hz": gbw,
                    "power_mw": power,
                    "status": status,
                })
            except (ValueError, KeyError):
                continue
    return experiments


def load_pareto():
    """Load final Pareto front from pareto.json."""
    if not os.path.exists(PARETO_FILE):
        return []
    with open(PARETO_FILE, "r") as f:
        front = json.load(f)
    return [{"gbw_hz": p["gbw_hz"], "power_mw": p["power_w"] * 1000} for p in front]


def plot(experiments, pareto):
    fig, ax = plt.subplots(figsize=(10, 7))

    # All experiments as trajectory
    gbw_all = [e["gbw_hz"] / 1e6 for e in experiments]
    pwr_all = [e["power_mw"] * 1000 for e in experiments]  # mW -> μW

    # Trajectory line (order of experiments)
    ax.plot(gbw_all, pwr_all, color="#cccccc", linewidth=0.8, zorder=1)

    # Scatter: color by status
    for i, e in enumerate(experiments):
        gbw = e["gbw_hz"] / 1e6
        pwr = e["power_mw"] * 1000
        if e["status"] == "crash":
            color, marker, size = "#ff4444", "x", 40
        elif e["status"] == "discard":
            color, marker, size = "#aaaaaa", "o", 25
        else:
            color, marker, size = "#4488cc", "o", 30
        ax.scatter(gbw, pwr, c=color, marker=marker, s=size, zorder=2, alpha=0.7)
        # Label experiment number
        ax.annotate(str(i + 1), (gbw, pwr), fontsize=5, ha="center", va="bottom",
                    xytext=(0, 3), textcoords="offset points", color="#666666")

    # Pareto front
    if pareto:
        pareto_sorted = sorted(pareto, key=lambda p: p["gbw_hz"])
        gbw_p = [p["gbw_hz"] / 1e6 for p in pareto_sorted]
        pwr_p = [p["power_mw"] * 1000 for p in pareto_sorted]

        ax.plot(gbw_p, pwr_p, color="#ff6600", linewidth=2, zorder=4, label="Pareto front")
        ax.scatter(gbw_p, pwr_p, c="#ff6600", s=80, zorder=5, edgecolors="black",
                   linewidths=0.8, marker="D")

    # Labels and formatting
    ax.set_xlabel("GBW (MHz)", fontsize=12)
    ax.set_ylabel("Power (μW)", fontsize=12)
    ax.set_title("Two-Stage Op-Amp: GBW vs Power — 100 Experiments", fontsize=14)
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    # Custom legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color="#cccccc", linewidth=0.8, label="Trajectory"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#4488cc",
               markersize=7, label="Keep"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#aaaaaa",
               markersize=7, label="Discard"),
        Line2D([0], [0], marker="x", color="#ff4444", markersize=7, label="Crash"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#ff6600",
               markeredgecolor="black", markersize=7, label="Pareto front"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=9)

    plt.tight_layout()
    plt.savefig(OUTPUT_FILE, dpi=200)
    print(f"Plot saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    experiments = load_results()
    pareto = load_pareto()
    print(f"Loaded {len(experiments)} experiments, {len(pareto)} Pareto points")
    plot(experiments, pareto)
