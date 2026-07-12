"""
AEGIS-TJ1 Turbojet — Thermodynamic Diagram Generator
======================================================

Imports the performance deck and produces four publication-quality plots:

    1. T-s diagram        (all 3 operating modes overlaid)
    2. P-v diagram        (all 3 operating modes overlaid)
    3. Station bar chart  (Takeoff mode detail)
    4. Performance table  (cross-mode comparison)

Outputs are saved as 200 DPI PNGs in
    simulation/thermodynamic/outputs/

Copyright (c) 2026 AEGIS Propulsion Programme.
"""

from __future__ import annotations

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless backend — must precede pyplot import
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

# ── Ensure the package is importable from any CWD ──────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from performance_deck import run_performance_deck, STATION_LABELS, print_results

# ═══════════════════════════════════════════════════════════════════════
#  Constants / style
# ═══════════════════════════════════════════════════════════════════════
OUTPUT_DIR = os.path.join(_THIS_DIR, "outputs")
DPI = 200

MODE_STYLE: dict[str, dict] = {
    "Idle":    {"color": "#00e5ff", "marker": "s", "label": "Idle (Rölanti) — 60 % N1"},
    "Takeoff": {"color": "#ff5252", "marker": "D", "label": "Takeoff (Kalkış) — 100 % N1"},
    "Cruise":  {"color": "#69f0ae", "marker": "o", "label": "Cruise (Seyir) — 95 % N1"},
}


def _setup_style() -> None:
    """Activate dark aerospace theme."""
    plt.style.use("dark_background")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 13,
        "legend.fontsize": 10,
        "figure.facecolor": "#0d1117",
        "axes.facecolor": "#161b22",
        "axes.edgecolor": "#30363d",
        "grid.color": "#30363d",
        "grid.alpha": 0.5,
    })


def _ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
#  1. T-s Diagram
# ═══════════════════════════════════════════════════════════════════════
def plot_ts_diagram(results: dict[str, dict]) -> str:
    """Temperature–entropy diagram with all 3 modes overlaid."""
    fig, ax = plt.subplots(figsize=(14, 10))

    for mode_name, r in results.items():
        sty = MODE_STYLE[mode_name]
        s_arr = np.array(r["s"])
        T_arr = np.array(r["T_t"])

        # Closed-cycle visual: connect station 9 back to station 0
        s_plot = np.append(s_arr, s_arr[0])
        T_plot = np.append(T_arr, T_arr[0])

        ax.plot(s_plot, T_plot, color=sty["color"], linewidth=2.2,
                marker=sty["marker"], markersize=8, markeredgecolor="white",
                markeredgewidth=0.6, label=sty["label"], zorder=3)

        # Station annotations for Takeoff
        if mode_name == "Takeoff":
            offsets = [(15, -20), (15, -20), (15, 10), (15, 10), (15, -20), (-30, -20)]
            for i, lbl in enumerate(STATION_LABELS):
                ax.annotate(
                    f"Stn {lbl}",
                    xy=(s_arr[i], T_arr[i]),
                    xytext=offsets[i],
                    textcoords="offset points",
                    fontsize=9, fontweight="bold",
                    color=sty["color"],
                    arrowprops=dict(arrowstyle="->", color=sty["color"], lw=0.8),
                )

    ax.set_xlabel(r"Specific Entropy  $s$  [J/(kg·K)]")
    ax.set_ylabel(r"Total Temperature  $T_t$  [K]")
    ax.set_title("AEGIS-TJ1 — T–s Diagram (Brayton Cycle)", fontweight="bold", pad=12)
    ax.legend(loc="upper left", framealpha=0.7)
    ax.grid(True, which="major", linewidth=0.6)
    ax.grid(True, which="minor", linewidth=0.3, alpha=0.4)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())

    fpath = os.path.join(OUTPUT_DIR, "ts_diagram.png")
    fig.savefig(fpath, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved {fpath}")
    return fpath


# ═══════════════════════════════════════════════════════════════════════
#  2. P-v Diagram
# ═══════════════════════════════════════════════════════════════════════
def plot_pv_diagram(results: dict[str, dict]) -> str:
    """Pressure–volume diagram with all 3 modes overlaid."""
    fig, ax = plt.subplots(figsize=(14, 10))

    for mode_name, r in results.items():
        sty = MODE_STYLE[mode_name]
        v_arr = np.array(r["v"])
        P_arr = np.array(r["P_t"]) / 1000.0  # Pa → kPa

        # Closed-cycle visual
        v_plot = np.append(v_arr, v_arr[0])
        P_plot = np.append(P_arr, P_arr[0])

        ax.plot(v_plot, P_plot, color=sty["color"], linewidth=2.2,
                marker=sty["marker"], markersize=8, markeredgecolor="white",
                markeredgewidth=0.6, label=sty["label"], zorder=3)

    ax.set_xlabel(r"Specific Volume  $v$  [m³/kg]")
    ax.set_ylabel(r"Total Pressure  $P_t$  [kPa]")
    ax.set_title("AEGIS-TJ1 — P–v Diagram (Brayton Cycle)", fontweight="bold", pad=12)
    ax.legend(loc="upper right", framealpha=0.7)
    ax.grid(True, which="major", linewidth=0.6)
    ax.grid(True, which="minor", linewidth=0.3, alpha=0.4)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())

    fpath = os.path.join(OUTPUT_DIR, "pv_diagram.png")
    fig.savefig(fpath, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved {fpath}")
    return fpath


# ═══════════════════════════════════════════════════════════════════════
#  3. Station Performance Bar Chart (Takeoff)
# ═══════════════════════════════════════════════════════════════════════
def plot_station_chart(results: dict[str, dict]) -> str:
    """Grouped bar chart of T_t and P_t at each station for Takeoff."""
    r = results["Takeoff"]
    T = np.array(r["T_t"])
    P = np.array(r["P_t"]) / 1000.0  # kPa

    x = np.arange(len(STATION_LABELS))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(14, 10))

    bars_T = ax1.bar(x - width / 2, T, width,
                     color="#ff5252", alpha=0.85, label="Total Temperature  T_t [K]",
                     edgecolor="white", linewidth=0.5)
    ax1.set_ylabel(r"Total Temperature  $T_t$  [K]", color="#ff5252")
    ax1.tick_params(axis="y", labelcolor="#ff5252")

    # Value labels on temperature bars
    for bar, val in zip(bars_T, T):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
                 f"{val:.0f}", ha="center", va="bottom", fontsize=9,
                 color="#ff5252", fontweight="bold")

    ax2 = ax1.twinx()
    bars_P = ax2.bar(x + width / 2, P, width,
                     color="#448aff", alpha=0.85, label="Total Pressure  P_t [kPa]",
                     edgecolor="white", linewidth=0.5)
    ax2.set_ylabel(r"Total Pressure  $P_t$  [kPa]", color="#448aff")
    ax2.tick_params(axis="y", labelcolor="#448aff")

    # Value labels on pressure bars
    for bar, val in zip(bars_P, P):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 15,
                 f"{val:.1f}", ha="center", va="bottom", fontsize=9,
                 color="#448aff", fontweight="bold")

    ax1.set_xlabel("Engine Station")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Stn {l}" for l in STATION_LABELS])
    ax1.set_title("AEGIS-TJ1 — Station Thermodynamic Summary (Takeoff)",
                  fontweight="bold", pad=12)

    # Combined legend
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left",
               framealpha=0.7)
    ax1.grid(True, axis="y", linewidth=0.4, alpha=0.4)

    fpath = os.path.join(OUTPUT_DIR, "station_chart.png")
    fig.savefig(fpath, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved {fpath}")
    return fpath


# ═══════════════════════════════════════════════════════════════════════
#  4. Performance Comparison Table (rendered as figure)
# ═══════════════════════════════════════════════════════════════════════
def plot_performance_table(results: dict[str, dict]) -> str:
    """Matplotlib table comparing key metrics across modes."""
    modes = list(results.keys())

    row_labels = [
        "N1 [%]",
        "Mass Flow [kg/s]",
        "F_specific [N·s/kg]",
        "F_gross [kN]",
        "TSFC [kg/(N·h)]",
        "V_exhaust [m/s]",
        "W_shaft [kW]",
        "Fuel-Air Ratio",
        "η_thermal",
        "η_propulsive",
        "η_overall",
    ]

    cell_data: list[list[str]] = []
    for row_label in row_labels:
        row: list[str] = []
        for m in modes:
            r = results[m]
            if row_label == "N1 [%]":
                row.append(f"{r['N1_pct']:.0f}")
            elif row_label == "Mass Flow [kg/s]":
                row.append(f"{r['mdot']:.1f}")
            elif row_label == "F_specific [N·s/kg]":
                row.append(f"{r['F_specific']:.2f}")
            elif row_label == "F_gross [kN]":
                row.append(f"{r['F_gross_kN']:.2f}")
            elif row_label == "TSFC [kg/(N·h)]":
                row.append(f"{r['TSFC_hr']:.5f}")
            elif row_label == "V_exhaust [m/s]":
                row.append(f"{r['V_e']:.1f}")
            elif row_label == "W_shaft [kW]":
                row.append(f"{r['W_shaft_kW']:.1f}")
            elif row_label == "Fuel-Air Ratio":
                row.append(f"{r['f']:.5f}")
            elif row_label == "η_thermal":
                row.append(f"{r['eta_thermal']:.4f}")
            elif row_label == "η_propulsive":
                row.append(f"{r['eta_propulsive']:.4f}")
            elif row_label == "η_overall":
                row.append(f"{r['eta_overall']:.4f}")
        cell_data.append(row)

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.axis("off")
    ax.set_title("AEGIS-TJ1 — Performance Comparison Across Operating Modes",
                 fontweight="bold", fontsize=15, pad=20)

    col_labels = [f"{m}\n({results[m]['label_tr']})" for m in modes]

    table = ax.table(
        cellText=cell_data,
        rowLabels=row_labels,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 1.8)

    # Style cells
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#30363d")
        if row == 0:
            # Header row
            cell.set_facecolor("#1f6feb")
            cell.set_text_props(color="white", fontweight="bold")
        elif col == -1:
            # Row labels
            cell.set_facecolor("#21262d")
            cell.set_text_props(color="#c9d1d9", fontweight="bold", ha="right")
        else:
            cell.set_facecolor("#0d1117" if row % 2 == 0 else "#161b22")
            cell.set_text_props(color="#e6edf3")

    fpath = os.path.join(OUTPUT_DIR, "performance_table.png")
    fig.savefig(fpath, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved {fpath}")
    return fpath


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════
def main() -> None:
    _setup_style()
    _ensure_output_dir()

    print("\n" + "=" * 80)
    print("  AEGIS-TJ1 — Thermodynamic Diagram Generator")
    print("=" * 80)

    # ── Run performance analysis ─────────────────────────────────────
    print("\n  Running performance deck …")
    results = run_performance_deck()
    print_results(results)

    # ── Generate all diagrams ────────────────────────────────────────
    print("\n  Generating diagrams …\n")
    plot_ts_diagram(results)
    plot_pv_diagram(results)
    plot_station_chart(results)
    plot_performance_table(results)

    print(f"\n  All outputs saved to: {OUTPUT_DIR}/")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
