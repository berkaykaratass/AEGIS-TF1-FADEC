"""
AEGIS-TJ1 Parasitic Power Budget Analysis
==========================================

Computes the parasitic electrical power budget for the AEGIS-TJ1 single-spool
turbojet engine across three operating modes (Idle, Takeoff, Cruise).

Power source:  AGB-mounted generator driven from the engine main shaft.
Consumers:     AI-FADEC processors, qEEG neuromorphic sensors, actuators,
               EHD plasma flow-control actuators, bus electronics, and
               auxiliary cooling / monitoring loads.

All values in SI (Watts) unless noted.

Reference:     AEGIS-TJ1 ECD-PWR-001 Rev B
Copyright (c)  2026 AEGIS-TF1 Systems Development Group.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")          # headless backend – safe for CI / remote
import matplotlib.pyplot as plt
from matplotlib.sankey import Sankey
from collections import OrderedDict

# ───────────────────────────────────────────────────────────────────────
#  OUTPUT DIRECTORY
# ───────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ───────────────────────────────────────────────────────────────────────
#  POWER SOURCE SPECIFICATIONS
# ───────────────────────────────────────────────────────────────────────
SHAFT_POWER_TAKEOFF_W   = 120_000.0          # 120 kW mechanical (Takeoff)
AGB_EXTRACTION_RATIO    = 0.042              # 4.2 % of shaft power
GENERATOR_RATED_W       = 5_000.0            # 5.0 kW electrical
GENERATOR_EFFICIENCY    = 0.92               # η_gen
AGB_GEAR_MESH_EFF       = 0.97               # η_agb
WIRING_LOSS_FRACTION    = 0.08               # 8 % wiring / conversion losses

# Mechanical accessory loads per mode (parasitic drag)
LUBE_OIL_PUMP_LOAD_W = {
    "Idle": 400.0,
    "Takeoff": 1200.0,
    "Cruise": 900.0,
}

FUEL_PUMP_LOAD_W = {
    "Idle": 500.0,
    "Takeoff": 1500.0,
    "Cruise": 1100.0,
}

# Shaft power per operating mode (approx.)
SHAFT_POWER_MODE = {
    "Idle":    0.35 * SHAFT_POWER_TAKEOFF_W,   # 42 kW
    "Takeoff": 1.00 * SHAFT_POWER_TAKEOFF_W,   # 120 kW
    "Cruise":  0.70 * SHAFT_POWER_TAKEOFF_W,   # 84 kW
}

# Generator available electrical output per mode
# P_gen = min(P_shaft × AGB_ratio × η_agb × η_gen, Rated)
def generator_output_w(mode: str) -> float:
    """Net electrical power available from the AGB generator [W]."""
    p_shaft = SHAFT_POWER_MODE[mode]
    p_gen_max = p_shaft * AGB_EXTRACTION_RATIO * AGB_GEAR_MESH_EFF * GENERATOR_EFFICIENCY
    return min(p_gen_max, GENERATOR_RATED_W)

# ───────────────────────────────────────────────────────────────────────
#  CONSUMER DATABASE
# ───────────────────────────────────────────────────────────────────────
#  Each consumer:
#    name, category, continuous_W, peak_W, duty_pct (0-1), DAL,
#    mode_active = dict  {mode: True/False}
#
#  "category" is one of:
#       "FADEC Core", "Sensors", "Actuators", "EHD Plasma", "Auxiliary"

CONSUMERS = [
    # ── FADEC Core ──────────────────────────────────────────────────
    {
        "id": 1,
        "name": "AI-FADEC Primary Processor",
        "category": "FADEC Core",
        "cont_w": 140.0,
        "peak_w": 180.0,
        "duty": 1.00,
        "dal": "A",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 2,
        "name": "AI-FADEC Redundant Processor",
        "category": "FADEC Core",
        "cont_w": 140.0,
        "peak_w": 180.0,
        "duty": 1.00,
        "dal": "A",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    # ── Sensors ─────────────────────────────────────────────────────
    {
        "id": 3,
        "name": "qEEG Neuromorphic Sensor #1 (Front Brg)",
        "category": "Sensors",
        "cont_w": 15.0,
        "peak_w": 22.0,
        "duty": 1.00,
        "dal": "B",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 4,
        "name": "qEEG Neuromorphic Sensor #2 (Mid Spool)",
        "category": "Sensors",
        "cont_w": 15.0,
        "peak_w": 22.0,
        "duty": 1.00,
        "dal": "B",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 5,
        "name": "qEEG Neuromorphic Sensor #3 (Rear Brg)",
        "category": "Sensors",
        "cont_w": 15.0,
        "peak_w": 22.0,
        "duty": 1.00,
        "dal": "B",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 6,
        "name": "EGT Thermocouple Sig. Cond. (12×)",
        "category": "Sensors",
        "cont_w": 36.0,
        "peak_w": 36.0,
        "duty": 1.00,
        "dal": "A",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 7,
        "name": "N1 Speed Sensor + Conditioning",
        "category": "Sensors",
        "cont_w": 8.0,
        "peak_w": 8.0,
        "duty": 1.00,
        "dal": "A",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    # ── Actuators ───────────────────────────────────────────────────
    {
        "id": 8,
        "name": "Fuel Metering Valve Actuator",
        "category": "Actuators",
        "cont_w": 85.0,
        "peak_w": 150.0,
        "duty": 0.60,          # variable – use 60 % average
        "dal": "A",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 9,
        "name": "Compressor IGV Actuator (Hyd.)",
        "category": "Actuators",
        "cont_w": 60.0,
        "peak_w": 120.0,
        "duty": 0.40,          # variable – use 40 % average
        "dal": "B",
        "modes": {"Idle": False, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 10,
        "name": "Starter/Generator Ctrl. Elec.",
        "category": "Actuators",
        "cont_w": 25.0,
        "peak_w": 45.0,
        "duty": 0.10,          # startup only
        "dal": "C",
        "modes": {"Idle": True, "Takeoff": False, "Cruise": False},
    },
    # ── EHD Plasma ──────────────────────────────────────────────────
    {
        "id": 11,
        "name": "EHD Plasma Actuator – Inlet",
        "category": "EHD Plasma",
        "cont_w": 800.0,
        "peak_w": 1600.0,
        "duty": 0.50,          # pulsed 50 %
        "dal": "C",
        "modes": {"Idle": False, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 12,
        "name": "EHD Plasma Actuator – Nozzle",
        "category": "EHD Plasma",
        "cont_w": 800.0,
        "peak_w": 1600.0,
        "duty": 0.50,          # pulsed 50 %
        "dal": "C",
        "modes": {"Idle": False, "Takeoff": True, "Cruise": True},
    },
    # ── Auxiliary ────────────────────────────────────────────────────
    {
        "id": 13,
        "name": "MIL-STD-1553B Bus I/F Units (2×)",
        "category": "Auxiliary",
        "cont_w": 12.0,
        "peak_w": 12.0,
        "duty": 1.00,
        "dal": "A",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 14,
        "name": "Databus Encryption Module",
        "category": "Auxiliary",
        "cont_w": 18.0,
        "peak_w": 25.0,
        "duty": 1.00,
        "dal": "A",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 15,
        "name": "LED Status / Health Monitor",
        "category": "Auxiliary",
        "cont_w": 5.0,
        "peak_w": 5.0,
        "duty": 1.00,
        "dal": "D",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 16,
        "name": "Alternator Cooling Pump",
        "category": "Auxiliary",
        "cont_w": 35.0,
        "peak_w": 35.0,
        "duty": 1.00,
        "dal": "C",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
    {
        "id": 17,
        "name": "FADEC Cooling Fan",
        "category": "Auxiliary",
        "cont_w": 30.0,
        "peak_w": 30.0,
        "duty": 1.00,
        "dal": "B",
        "modes": {"Idle": True, "Takeoff": True, "Cruise": True},
    },
]

CATEGORIES = ["FADEC Core", "Sensors", "Actuators", "EHD Plasma", "Auxiliary"]
MODES = ["Idle", "Takeoff", "Cruise"]

# ───────────────────────────────────────────────────────────────────────
#  ANALYSIS FUNCTIONS
# ───────────────────────────────────────────────────────────────────────

def compute_mode_power(mode: str):
    """
    Compute continuous and peak power demand for a given operating mode.

    Returns
    -------
    cont_total : float   – total continuous demand (incl. wiring losses) [W]
    peak_total : float   – total peak demand (incl. wiring losses) [W]
    cat_cont   : dict    – continuous demand by category [W]
    cat_peak   : dict    – peak demand by category [W]
    consumer_details : list of dicts with per-consumer breakdown
    """
    cat_cont = {c: 0.0 for c in CATEGORIES}
    cat_peak = {c: 0.0 for c in CATEGORIES}
    consumer_details = []

    for c in CONSUMERS:
        active = c["modes"].get(mode, False)
        if not active:
            consumer_details.append({
                "id": c["id"], "name": c["name"],
                "category": c["category"],
                "cont_w": 0.0, "peak_w": 0.0, "active": False,
            })
            continue

        cont = c["cont_w"]
        peak = c["peak_w"]
        cat_cont[c["category"]] += cont
        cat_peak[c["category"]] += peak
        consumer_details.append({
            "id": c["id"], "name": c["name"],
            "category": c["category"],
            "cont_w": cont, "peak_w": peak, "active": True,
        })

    # Sum before losses
    raw_cont = sum(cat_cont.values())
    raw_peak = sum(cat_peak.values())

    # Wiring / conversion losses (8 %)
    wiring_cont = raw_cont * WIRING_LOSS_FRACTION
    wiring_peak = raw_peak * WIRING_LOSS_FRACTION

    cont_total = raw_cont + wiring_cont
    peak_total = raw_peak + wiring_peak

    # Add wiring loss to category dict for completeness
    cat_cont["Wiring Losses"] = wiring_cont
    cat_peak["Wiring Losses"] = wiring_peak

    return cont_total, peak_total, cat_cont, cat_peak, consumer_details


def full_analysis():
    """Run budget analysis for every mode.  Returns structured dict."""
    results = OrderedDict()
    for mode in MODES:
        gen_w = generator_output_w(mode)
        cont, peak, cat_c, cat_p, details = compute_mode_power(mode)
        margin_cont = gen_w - cont
        margin_peak = gen_w - peak
        sf_cont = gen_w / cont if cont > 0 else float("inf")
        sf_peak = gen_w / peak if peak > 0 else float("inf")

        # Accessory mechanical loads
        p_lube = LUBE_OIL_PUMP_LOAD_W[mode]
        p_fuel = FUEL_PUMP_LOAD_W[mode]
        p_gen_mech = gen_w / GENERATOR_EFFICIENCY
        p_friction = (p_gen_mech + p_lube + p_fuel) * ((1.0 - AGB_GEAR_MESH_EFF) / AGB_GEAR_MESH_EFF)
        p_total_mech = p_gen_mech + p_lube + p_fuel + p_friction

        results[mode] = {
            "generator_w": gen_w,
            "shaft_w": SHAFT_POWER_MODE[mode],
            "cont_total": cont,
            "peak_total": peak,
            "margin_cont": margin_cont,
            "margin_peak": margin_peak,
            "safety_factor_cont": sf_cont,
            "safety_factor_peak": sf_peak,
            "cat_cont": cat_c,
            "cat_peak": cat_p,
            "details": details,
            # Mechanical parasitic loads
            "lube_pump_mech_w": p_lube,
            "fuel_pump_mech_w": p_fuel,
            "agb_friction_mech_w": p_friction,
            "total_parasitic_mech_w": p_total_mech,
        }
    return results


# ───────────────────────────────────────────────────────────────────────
#  CONSOLE REPORT
# ───────────────────────────────────────────────────────────────────────

def print_report(results):
    """Print formatted analysis tables to stdout."""
    line = "=" * 92
    thin = "-" * 92

    print("\n" + line)
    print("  AEGIS-TJ1  PARASITIC POWER BUDGET ANALYSIS")
    print("  Document: ECD-PWR-001 Rev B        Date: 2026-06-20")
    print(line)

    # ── Power Source ──
    print("\n  POWER SOURCE")
    print(thin)
    print(f"  Engine shaft power (Takeoff):  {SHAFT_POWER_TAKEOFF_W/1e3:>8.1f} kW")
    print(f"  AGB extraction ratio:          {AGB_EXTRACTION_RATIO*100:>8.1f} %")
    print(f"  AGB gear mesh efficiency:      {AGB_GEAR_MESH_EFF*100:>8.1f} %")
    print(f"  Generator efficiency:          {GENERATOR_EFFICIENCY*100:>8.1f} %")
    print(f"  Generator rated output:        {GENERATOR_RATED_W:>8.1f} W")
    print(f"  Wiring / conversion losses:    {WIRING_LOSS_FRACTION*100:>8.1f} %")

    for mode in MODES:
        gen_w = generator_output_w(mode)
        print(f"\n  Generator output ({mode:>7s}):    {gen_w:>8.1f} W"
              f"  (shaft {SHAFT_POWER_MODE[mode]/1e3:.0f} kW)")

    # ── Mechanical Accessory Loads ──
    print("\n\n  AGB MECHANICAL ACCESSORY LOADS & GEARBOX FRICTION")
    print(thin)
    print(f"  {'Mode':<10s}  {'Lube Pump [W]':>15s}  {'Fuel Pump [W]':>15s}  {'AGB Friction [W]':>18s}  {'Total Mech [W]':>15s}")
    print(thin)
    for mode in MODES:
        r = results[mode]
        print(f"  {mode:<10s}  {r['lube_pump_mech_w']:>15.1f}  {r['fuel_pump_mech_w']:>15.1f}  {r['agb_friction_mech_w']:>18.1f}  {r['total_parasitic_mech_w']:>15.1f}")

    # ── Consumer Table ──
    print("\n\n  CONSUMER POWER DEMAND BY OPERATING MODE")
    print(thin)
    hdr = f"  {'#':>2s}  {'Consumer':<40s}"
    for m in MODES:
        hdr += f"  {'C/'+m:>8s}  {'P/'+m:>8s}"
    print(hdr)
    print(thin)

    for idx, c in enumerate(CONSUMERS):
        row = f"  {c['id']:>2d}  {c['name']:<40s}"
        for m in MODES:
            r = results[m]
            d = r["details"][idx]
            row += f"  {d['cont_w']:>8.1f}  {d['peak_w']:>8.1f}"
        print(row)

    # Wiring losses row
    row = f"  {'18':>2s}  {'Wiring/Conversion Losses (8%)':<40s}"
    for m in MODES:
        r = results[m]
        row += f"  {r['cat_cont']['Wiring Losses']:>8.1f}  {r['cat_peak']['Wiring Losses']:>8.1f}"
    print(row)
    print(thin)

    # Totals
    row_c = f"  {'':>2s}  {'TOTAL CONTINUOUS':<40s}"
    row_p = f"  {'':>2s}  {'TOTAL PEAK':<40s}"
    for m in MODES:
        r = results[m]
        row_c += f"  {r['cont_total']:>8.1f}  {'':>8s}"
        row_p += f"  {'':>8s}  {r['peak_total']:>8.1f}"
    print(row_c)
    print(row_p)
    print(thin)

    # ── Category summary ──
    print("\n\n  CATEGORY BREAKDOWN BY MODE [W]")
    print(thin)
    hdr2 = f"  {'Category':<20s}"
    for m in MODES:
        hdr2 += f"  {'C/'+m:>8s}  {'P/'+m:>8s}"
    print(hdr2)
    print(thin)
    for cat in CATEGORIES + ["Wiring Losses"]:
        row = f"  {cat:<20s}"
        for m in MODES:
            row += f"  {results[m]['cat_cont'].get(cat,0):>8.1f}  {results[m]['cat_peak'].get(cat,0):>8.1f}"
        print(row)
    print(thin)

    # ── Margin ──
    print("\n\n  MARGIN ANALYSIS")
    print(thin)
    print(f"  {'Mode':<10s}  {'Gen [W]':>10s}  {'Cont [W]':>10s}  {'Peak [W]':>10s}"
          f"  {'Margin_C':>10s}  {'Margin_P':>10s}  {'SF_C':>8s}  {'SF_P':>8s}  {'Verdict':>10s}")
    print(thin)
    for m in MODES:
        r = results[m]
        verdict = "PASS" if r["safety_factor_peak"] >= 1.0 else "** FAIL **"
        print(f"  {m:<10s}"
              f"  {r['generator_w']:>10.1f}"
              f"  {r['cont_total']:>10.1f}"
              f"  {r['peak_total']:>10.1f}"
              f"  {r['margin_cont']:>+10.1f}"
              f"  {r['margin_peak']:>+10.1f}"
              f"  {r['safety_factor_cont']:>8.2f}"
              f"  {r['safety_factor_peak']:>8.2f}"
              f"  {verdict:>10s}")
    print(thin)

    # Overall pass/fail
    min_sf = min(results[m]["safety_factor_peak"] for m in MODES)
    overall = "PASS" if min_sf >= 1.0 else "FAIL"
    print(f"\n  Overall minimum peak safety factor: {min_sf:.2f}  →  {overall}")
    print(line + "\n")


# ───────────────────────────────────────────────────────────────────────
#  PLOT 1 – SANKEY / WATERFALL  (Power Flow)
# ───────────────────────────────────────────────────────────────────────

def plot_sankey(results, filepath: str):
    """
    Waterfall-style stacked bar chart showing power flow from shaft
    through AGB and generator to each consumer category (Takeoff mode).
    """
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(14, 8), dpi=200)

    mode = "Takeoff"
    r = results[mode]

    # Build waterfall stages
    shaft_w   = r["shaft_w"]
    agb_in    = shaft_w * AGB_EXTRACTION_RATIO
    agb_loss  = agb_in * (1 - AGB_GEAR_MESH_EFF)
    agb_out   = agb_in - agb_loss
    gen_loss  = agb_out * (1 - GENERATOR_EFFICIENCY)
    gen_out   = r["generator_w"]

    # Consumer categories (no wiring in this breakdown yet)
    cat_cont = {k: v for k, v in r["cat_cont"].items() if k != "Wiring Losses"}
    wiring   = r["cat_cont"]["Wiring Losses"]

    labels = []
    values = []
    colors = []

    # Stages
    stages = [
        ("Shaft Power\n(AGB Extract)", agb_in,  "#00bfff"),
        ("AGB Gear Loss",            -agb_loss, "#ff4444"),
        ("Generator Loss",           -gen_loss, "#ff6666"),
        ("Generator Output",          gen_out,  "#00e676"),
    ]

    # Consumer sinks (negative = consumed)
    cat_colors = {
        "FADEC Core":  "#ffab40",
        "Sensors":     "#7c4dff",
        "Actuators":   "#ff5252",
        "EHD Plasma":  "#18ffff",
        "Auxiliary":   "#eeff41",
    }
    for cat in CATEGORIES:
        cw = cat_cont.get(cat, 0)
        if cw > 0:
            stages.append((cat, -cw, cat_colors[cat]))
    stages.append(("Wiring Losses", -wiring, "#ff8a80"))

    # Compute waterfall
    cumulative = 0
    bottoms = []
    heights = []
    bar_labels = []
    bar_colors = []
    for label, val, col in stages:
        if val >= 0:
            bottoms.append(cumulative)
            heights.append(val)
            cumulative += val
        else:
            cumulative += val        # subtract
            bottoms.append(cumulative)
            heights.append(abs(val))
        bar_labels.append(label)
        bar_colors.append(col)

    x = np.arange(len(bar_labels))
    bars = ax.bar(x, heights, bottom=bottoms, color=bar_colors,
                  edgecolor="white", linewidth=0.6, width=0.65)

    # Value annotations
    for i, (b, h) in enumerate(zip(bottoms, heights)):
        val_w = stages[i][1]
        txt = f"{abs(val_w):.0f} W"
        y_pos = b + h / 2
        ax.text(i, y_pos, txt, ha="center", va="center",
                fontsize=8, fontweight="bold", color="white")

    # Connector lines
    for i in range(len(x) - 1):
        y_connect = bottoms[i] + heights[i] if stages[i][1] >= 0 else bottoms[i]
        ax.plot([x[i] + 0.325, x[i + 1] - 0.325],
                [y_connect, y_connect],
                color="gray", linewidth=0.8, linestyle="--")

    ax.set_xticks(x)
    ax.set_xticklabels(bar_labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("Power  [W]", fontsize=11)
    ax.set_title("AEGIS-TJ1  Power Flow Waterfall  —  Takeoff Mode",
                 fontsize=14, fontweight="bold", pad=15)
    ax.grid(axis="y", alpha=0.25)
    ax.set_xlim(-0.6, len(x) - 0.4)

    # Remaining margin annotation
    margin = r["margin_cont"]
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.annotate(f"Remaining margin: {margin:+.0f} W",
                xy=(len(x) - 1, bottoms[-1]),
                xytext=(len(x) - 1.8, bottoms[-1] + max(heights) * 0.15),
                fontsize=10, color="#76ff03",
                arrowprops=dict(arrowstyle="->", color="#76ff03"),
                fontweight="bold")

    fig.tight_layout()
    fig.savefig(filepath, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved: {filepath}")


# ───────────────────────────────────────────────────────────────────────
#  PLOT 2 – STACKED BAR  (Category Breakdown by Mode)
# ───────────────────────────────────────────────────────────────────────

def plot_breakdown(results, filepath: str):
    """Stacked bar chart of continuous power by category for each mode."""
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(14, 8), dpi=200)

    cat_colors = {
        "FADEC Core":    "#ffab40",
        "Sensors":       "#7c4dff",
        "Actuators":     "#ff5252",
        "EHD Plasma":    "#18ffff",
        "Auxiliary":     "#eeff41",
        "Wiring Losses": "#ff8a80",
    }

    all_cats = CATEGORIES + ["Wiring Losses"]
    x = np.arange(len(MODES))
    width = 0.35

    # Continuous bars
    bot_c = np.zeros(len(MODES))
    bot_p = np.zeros(len(MODES))
    for cat in all_cats:
        vals_c = [results[m]["cat_cont"].get(cat, 0) for m in MODES]
        vals_p = [results[m]["cat_peak"].get(cat, 0) for m in MODES]
        ax.bar(x - width / 2, vals_c, width, bottom=bot_c,
               label=cat + " (Cont.)" if cat == all_cats[0] else cat,
               color=cat_colors[cat], edgecolor="white", linewidth=0.4)
        ax.bar(x + width / 2, vals_p, width, bottom=bot_p,
               color=cat_colors[cat], edgecolor="white", linewidth=0.4,
               alpha=0.55, hatch="//")
        bot_c += np.array(vals_c)
        bot_p += np.array(vals_p)

    # Generator capacity line
    gen_vals = [generator_output_w(m) for m in MODES]
    ax.plot(x - width / 2, gen_vals, "s--", color="#76ff03",
            markersize=8, linewidth=2, label="Generator Capacity")
    ax.plot(x + width / 2, gen_vals, "s--", color="#76ff03",
            markersize=8, linewidth=2)

    # Total labels
    for i, m in enumerate(MODES):
        ax.text(i - width / 2, bot_c[i] + 40, f"{bot_c[i]:.0f} W",
                ha="center", va="bottom", fontsize=9, fontweight="bold",
                color="white")
        ax.text(i + width / 2, bot_p[i] + 40, f"{bot_p[i]:.0f} W",
                ha="center", va="bottom", fontsize=9, fontweight="bold",
                color="#aaaaaa")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}\n(Cont. | Peak)" for m in MODES], fontsize=11)
    ax.set_ylabel("Power Demand  [W]", fontsize=12)
    ax.set_title("AEGIS-TJ1  Power Consumption Breakdown by Category & Mode",
                 fontsize=14, fontweight="bold", pad=15)
    ax.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.6)
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    fig.savefig(filepath, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved: {filepath}")


# ───────────────────────────────────────────────────────────────────────
#  PLOT 3 – POWER MARGIN CHART
# ───────────────────────────────────────────────────────────────────────

def plot_margin(results, filepath: str):
    """Bar chart of available vs consumed power with safety-margin line."""
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(14, 8), dpi=200)

    x = np.arange(len(MODES))
    width = 0.25

    gen_vals  = [results[m]["generator_w"]  for m in MODES]
    cont_vals = [results[m]["cont_total"]   for m in MODES]
    peak_vals = [results[m]["peak_total"]   for m in MODES]

    b1 = ax.bar(x - width, gen_vals,  width, label="Generator Output",
                color="#00e676", edgecolor="white", linewidth=0.6)
    b2 = ax.bar(x,          cont_vals, width, label="Continuous Demand",
                color="#ffab40", edgecolor="white", linewidth=0.6)
    b3 = ax.bar(x + width,  peak_vals, width, label="Peak Demand",
                color="#ff5252", edgecolor="white", linewidth=0.6)

    # Value labels
    for bars in [b1, b2, b3]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 30,
                    f"{h:.0f}", ha="center", va="bottom",
                    fontsize=9, fontweight="bold", color="white")

    # Minimum safety margin threshold line (SF = 1.0 → generator = demand)
    # We show generator rated output as reference and a 20% derating line
    ax.axhline(GENERATOR_RATED_W, color="#76ff03", linewidth=1.5,
               linestyle="-", alpha=0.8, label="Generator Rated (5000 W)")
    ax.axhline(GENERATOR_RATED_W * 0.80, color="#ff1744", linewidth=2,
               linestyle="--", label="Min. Margin Threshold (80%)")

    # Safety factor annotations
    for i, m in enumerate(MODES):
        sf = results[m]["safety_factor_peak"]
        color = "#76ff03" if sf >= 1.0 else "#ff1744"
        ax.text(i, max(gen_vals[i], peak_vals[i]) + 180,
                f"SF_peak = {sf:.2f}",
                ha="center", fontsize=10, fontweight="bold", color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(MODES, fontsize=12)
    ax.set_ylabel("Power  [W]", fontsize=12)
    ax.set_title("AEGIS-TJ1  Power Margin Analysis by Operating Mode",
                 fontsize=14, fontweight="bold", pad=15)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.6)
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(max(gen_vals), max(peak_vals)) * 1.25)

    fig.tight_layout()
    fig.savefig(filepath, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved: {filepath}")


# ───────────────────────────────────────────────────────────────────────
#  MAIN
# ───────────────────────────────────────────────────────────────────────

def main():
    print("\n  ▸ Running AEGIS-TJ1 Parasitic Power Budget Analysis …")
    results = full_analysis()
    print_report(results)

    # Generate plots
    print("  ▸ Generating plots …\n")
    plot_sankey(results,    os.path.join(OUTPUT_DIR, "power_sankey.png"))
    plot_breakdown(results, os.path.join(OUTPUT_DIR, "power_breakdown.png"))
    plot_margin(results,    os.path.join(OUTPUT_DIR, "power_margin.png"))

    print("\n  ▸ All outputs saved to:", OUTPUT_DIR)
    print("  ▸ Analysis complete.\n")
    return results


if __name__ == "__main__":
    results = main()
