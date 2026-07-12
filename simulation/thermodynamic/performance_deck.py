"""
AEGIS-TJ1 Turbojet — Performance Deck
======================================

Runs the BraytonCycleSimulator for three operating modes derived from
CAD-measured geometry and preliminary aero sizing:

    1. Idle   (Rölanti)  – 60 % N1, ground static
    2. Takeoff (Kalkış)  – 100 % N1, sea-level static
    3. Cruise  (Seyir)   – 95 % N1, FL350, Mach 0.80

Station numbering follows SAE ARP 755A:
    0  Ambient
    2  Compressor inlet  (after diffuser / intake)
    3  Compressor exit
    4  Combustor exit  / turbine inlet
    5  Turbine exit    / nozzle inlet
    9  Nozzle exit     / exhaust

All quantities in SI unless otherwise noted.

Copyright (c) 2026 AEGIS Propulsion Programme.
"""

from __future__ import annotations

import sys
import os
import numpy as np

# ── Import the cycle solver ────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brayton_sim import BraytonCycleSimulator


# ═══════════════════════════════════════════════════════════════════════
#  AEGIS-TJ1 design constants (from CAD geometry)
# ═══════════════════════════════════════════════════════════════════════
FAN_INLET_TIP_RADIUS = 0.11475        # m  (114.75 mm)
COMPRESSOR_EXIT_TIP_RADIUS = 0.0663   # m  (66.3 mm)
HUB_TO_TIP_RATIO = 0.45               # –
A_INLET = np.pi * FAN_INLET_TIP_RADIUS**2  # ≈ 0.04138 m²
N_COMPRESSOR_STAGES = 6               # –
OPR_DESIGN = 12.0                     # –  overall pressure ratio
T4_MAX_DESIGN = 1600.0                # K  turbine-inlet temperature
DESIGN_RPM = 35_000                   # rpm
ETA_C_POLY = 0.85                     # –  compressor polytropic eff.
ETA_T_POLY = 0.90                     # –  turbine polytropic eff.
ETA_B = 0.98                          # –  combustor efficiency
ETA_N = 0.95                          # –  nozzle efficiency

# ── Thermodynamic constants ──
CP_AIR = 1005.0    # J/(kg·K)
CP_GAS = 1148.0    # J/(kg·K)
GAMMA_AIR = 1.4
GAMMA_GAS = 1.33
R_AIR = 287.05     # J/(kg·K)


# ═══════════════════════════════════════════════════════════════════════
#  Operating-mode definitions
# ═══════════════════════════════════════════════════════════════════════
OPERATING_MODES: dict[str, dict] = {
    "Idle": {
        "label_tr": "Rölanti",
        "N1_fraction": 0.60,
        "T_amb": 288.15,       # K   (ISA sea-level)
        "P_amb": 101_325.0,    # Pa
        "M_flight": 0.0,
        "r_p": OPR_DESIGN * 0.60**2,   # 4.32
        "T4": 1100.0,          # K
        "mdot": 12.0,          # kg/s  (60 % of design)
    },
    "Takeoff": {
        "label_tr": "Kalkış",
        "N1_fraction": 1.00,
        "T_amb": 288.15,
        "P_amb": 101_325.0,
        "M_flight": 0.0,
        "r_p": OPR_DESIGN,     # 12.0
        "T4": T4_MAX_DESIGN,   # 1600 K
        "mdot": 20.0,          # kg/s  (based on inlet area)
    },
    "Cruise": {
        "label_tr": "Seyir",
        "N1_fraction": 0.95,
        "T_amb": 218.8,        # K   (FL350, ISA)
        "P_amb": 23_842.0,     # Pa
        "M_flight": 0.80,
        "r_p": OPR_DESIGN * 0.95**2,   # 10.83
        "T4": 1500.0,          # K
        "mdot": 8.0,           # kg/s  (reduced at altitude)
    },
}

STATION_LABELS = ["0", "2", "3", "4", "5", "9"]


# ═══════════════════════════════════════════════════════════════════════
#  Core analysis function
# ═══════════════════════════════════════════════════════════════════════
def run_performance_deck() -> dict[str, dict]:
    """
    Run the Brayton-cycle analysis for every operating mode defined in
    ``OPERATING_MODES``.

    Returns
    -------
    results : dict[str, dict]
        Keyed by mode name.  Each value dict contains the raw cycle
        output **plus** the following derived quantities:

        * ``mdot``        – mass-flow rate  [kg/s]
        * ``F_gross``     – gross thrust  [N]
        * ``F_gross_kN``  – gross thrust  [kN]
        * ``W_shaft_kW``  – compressor shaft power  [kW]
        * ``V_e``         – exhaust velocity  [m/s]
        * ``TSFC_hr``     – TSFC in  kg/(N·h)
        * ``s``           – specific entropy array  [J/(kg·K)]
        * ``v``           – specific volume array  [m³/kg]
    """
    sim = BraytonCycleSimulator(
        gamma_a=GAMMA_AIR,
        gamma_g=GAMMA_GAS,
        cp_a=CP_AIR,
        cp_g=CP_GAS,
        eta_b=ETA_B,
        eta_c=ETA_C_POLY,
        eta_t=ETA_T_POLY,
        eta_n=ETA_N,
    )

    results: dict[str, dict] = {}

    for mode_name, cfg in OPERATING_MODES.items():
        # ── Run core cycle ──────────────────────────────────────────
        cycle = sim.compute_cycle(
            T_amb=cfg["T_amb"],
            P_amb=cfg["P_amb"],
            M_flight=cfg["M_flight"],
            r_p=cfg["r_p"],
            T4_max=cfg["T4"],
        )

        mdot = cfg["mdot"]

        # ── Derived quantities ──────────────────────────────────────
        F_specific = cycle["F_specific"]             # N·s/kg
        F_gross = mdot * F_specific                   # N
        TSFC_hr = cycle["TSFC"] * 3600.0              # kg/(N·h)
        V_e = cycle["V"][-1]                          # m/s  (station 9)

        # Compressor shaft work  →  power
        T_t2 = cycle["T_t"][1]
        T_t3 = cycle["T_t"][2]
        W_shaft_kW = mdot * CP_AIR * (T_t3 - T_t2) / 1000.0  # kW

        # ── T-s / P-v diagram data ──────────────────────────────────
        s, _ = sim.generate_ts_diagram(cycle)
        v, _ = sim.generate_pv_diagram(cycle)

        # ── Pack results ────────────────────────────────────────────
        cycle.update({
            "mode":       mode_name,
            "label_tr":   cfg["label_tr"],
            "N1_pct":     cfg["N1_fraction"] * 100.0,
            "mdot":       mdot,
            "F_gross":    F_gross,
            "F_gross_kN": F_gross / 1000.0,
            "W_shaft_kW": W_shaft_kW,
            "V_e":        V_e,
            "TSFC_hr":    TSFC_hr,
            "s":          s,
            "v":          v,
        })

        results[mode_name] = cycle

    return results


# ═══════════════════════════════════════════════════════════════════════
#  Pretty-print helpers
# ═══════════════════════════════════════════════════════════════════════
def _hr(width: int = 100) -> str:
    return "─" * width


def print_results(results: dict[str, dict]) -> None:
    """Print formatted performance tables to stdout."""

    print()
    print("=" * 100)
    print("  AEGIS-TJ1 TURBOJET ENGINE — THERMODYNAMIC PERFORMANCE DECK")
    print("=" * 100)

    for mode_name, r in results.items():
        print(f"\n{_hr()}")
        print(f"  MODE: {mode_name.upper()} ({r['label_tr']})  —  N1 = {r['N1_pct']:.0f} %")
        print(_hr())

        # Station table
        print(f"\n  {'Station':>10s}  {'T_t [K]':>12s}  {'P_t [kPa]':>12s}  {'V [m/s]':>12s}")
        print(f"  {'─'*10}  {'─'*12}  {'─'*12}  {'─'*12}")
        for i, lbl in enumerate(STATION_LABELS):
            print(
                f"  {lbl:>10s}  {r['T_t'][i]:12.2f}  "
                f"{r['P_t'][i]/1000.0:12.3f}  {r['V'][i]:12.2f}"
            )

        # Scalar metrics
        print()
        print(f"  {'Mass flow rate':.<40s} {r['mdot']:>10.2f} kg/s")
        print(f"  {'Fuel-air ratio (f)':.<40s} {r['f']:>10.5f}")
        print(f"  {'Specific thrust (F_sp)':.<40s} {r['F_specific']:>10.2f} N·s/kg")
        print(f"  {'Gross thrust (F_gross)':.<40s} {r['F_gross']:>10.1f} N  ({r['F_gross_kN']:.2f} kN)")
        print(f"  {'TSFC':.<40s} {r['TSFC_hr']:>10.5f} kg/(N·h)")
        print(f"  {'Exhaust velocity (V_e)':.<40s} {r['V_e']:>10.2f} m/s")
        print(f"  {'Shaft power (W_shaft)':.<40s} {r['W_shaft_kW']:>10.1f} kW")
        print(f"  {'Thermal efficiency':.<40s} {r['eta_thermal']:>10.4f}  ({r['eta_thermal']*100:.2f} %)")
        print(f"  {'Propulsive efficiency':.<40s} {r['eta_propulsive']:>10.4f}  ({r['eta_propulsive']*100:.2f} %)")
        print(f"  {'Overall efficiency':.<40s} {r['eta_overall']:>10.4f}  ({r['eta_overall']*100:.2f} %)")

    # ── Cross-mode comparison ───────────────────────────────────────
    modes = list(results.keys())
    print(f"\n{'=' * 100}")
    print("  CROSS-MODE COMPARISON")
    print(f"{'=' * 100}")
    header = f"  {'Metric':.<35s}" + "".join(f"  {m:>18s}" for m in modes)
    print(header)
    print(f"  {'─'*35}" + "  " + "  ".join("─" * 18 for _ in modes))

    rows = [
        ("F_specific [N·s/kg]",  "F_specific", "{:>18.2f}"),
        ("F_gross [kN]",         "F_gross_kN", "{:>18.2f}"),
        ("TSFC [kg/(N·h)]",     "TSFC_hr",    "{:>18.5f}"),
        ("V_e [m/s]",           "V_e",        "{:>18.2f}"),
        ("η_th",                "eta_thermal","{:>18.4f}"),
        ("η_prop",              "eta_propulsive","{:>18.4f}"),
        ("η_overall",           "eta_overall", "{:>18.4f}"),
        ("mdot [kg/s]",         "mdot",       "{:>18.2f}"),
        ("W_shaft [kW]",        "W_shaft_kW", "{:>18.1f}"),
    ]
    for label, key, fmt in rows:
        line = f"  {label:.<35s}"
        for m in modes:
            line += "  " + fmt.format(results[m][key])
        print(line)

    print(f"\n{'=' * 100}\n")


# ═══════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    results = run_performance_deck()
    print_results(results)
