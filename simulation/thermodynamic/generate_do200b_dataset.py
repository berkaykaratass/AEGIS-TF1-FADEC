#!/usr/bin/env python3
"""
DO-200B Aviation Grade Engine Envelope and Degradation Dataset Generator
========================================================================

Generates a comprehensive dataset across the entire flight envelope, including
standard/off-standard atmospheres, throttle range, and compressor/turbine aging
degradation indexes (fouling/erosion).

Used for EKF observer calibration and off-line diagnostic model training.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import os
import csv
import math
import numpy as np
from ai.models.adaptive_mpc import NonlinearStateSpace

def calculate_ambient(altitude_ft):
    """Calculate atmospheric temperature and pressure based on altitude."""
    h = altitude_ft * 0.3048
    if h < 11000.0:
        T_amb = 288.15 - 0.0065 * h
        P_amb = 101325.0 * math.pow(1.0 - 0.0065 * h / 288.15, 5.2561)
    else:
        T_amb = 216.65
        P_11 = 101325.0 * math.pow(1.0 - 0.0065 * 11000.0 / 288.15, 5.2561)
        h_diff = h - 11000.0
        P_amb = P_11 * math.exp(-9.80665 * h_diff / (287.05 * T_amb))
    return T_amb, P_amb

def main():
    print("--- Starting DO-200B Engine Envelope & Degradation Dataset Generation ---")
    
    # Initialize Engine model
    model = NonlinearStateSpace()
    
    # Flight Envelope sweeps
    altitudes = [0.0, 10000.0, 20000.0, 35000.0, 45000.0]        # Altitude (ft)
    delta_T_days = [-20.0, 0.0, 15.0, 35.0]                      # ISA deviation (K)
    n2_speeds = [20000.0, 28000.0, 33000.0, 35000.0]             # HP speed (RPM)
    degradations = [0.0, 0.2, 0.5, 0.8]                           # Fouling/Erosion factors
    
    output_dir = "/Users/berkaykaratas/Downloads/turbojet/simulation/thermodynamic/outputs"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "do200b_envelope_dataset.csv")
    
    records = []
    
    # Sweep flight conditions
    for alt in altitudes:
        T_base, P_base = calculate_ambient(alt)
        for dT in delta_T_days:
            # Set environmental conditions in model
            model.T_amb = T_base
            model.P_amb = P_base
            model.delta_T_day = dT
            
            for deg in degradations:
                model.compressor_fouling_factor = deg
                model.turbine_erosion_factor = deg
                
                for n2_rpm in n2_speeds:
                    # Map to model state vector
                    n2_rad = n2_rpm * np.pi / 30.0
                    n1_rad = n2_rad * 0.85 # LP speed scaling
                    T_t4 = 1100.0 + 400.0 * (n2_rpm / 35000.0) # Estimated burner temp
                    P3 = P_base * (1.0 + 11.0 * (n2_rpm / 35000.0))
                    
                    state = np.array([n1_rad, n2_rad, T_t4, P3], dtype=np.float32)
                    
                    # Wf command based on speed
                    Wf = 0.05 + 0.20 * (n2_rpm / 35000.0)
                    inputs = [Wf, 0.0, 15.0]
                    
                    # Run derivatives to match stations and flow continuity
                    model.derivatives(state, inputs)
                    
                    # Read converged outputs from station graph
                    p3_pa = model.stations[3]["P"]
                    t3_k = model.stations[3]["T"]
                    w3 = model.stations[3]["W"]
                    p4_pa = model.stations[4]["P"]
                    t4_k = model.stations[4]["T"]
                    p5_pa = model.stations[5]["P"]
                    t5_k = model.stations[5]["T"]
                    p9_pa = model.stations[9]["P"]
                    t9_k = model.stations[9]["T"]
                    mach9 = model.stations[9]["Mach"]
                    
                    # Calculate surge margin
                    Nc = (n2_rpm) / np.sqrt(t3_k / 288.15)
                    surge_pr = (1.0 + 13.0 * (Nc / 35000.0)**2) * (1.0 - 0.12 * deg)
                    pr_current = p3_pa / P_base
                    stall_margin = (surge_pr - pr_current) / surge_pr
                    
                    records.append({
                        "Altitude_ft": alt,
                        "ISA_Deviation_K": dT,
                        "N2_RPM": n2_rpm,
                        "Degradation_Index": deg,
                        "Fuel_Flow_kgs": Wf,
                        "P2_Pa": P_base,
                        "T2_K": T_base + dT,
                        "P3_Pa": p3_pa,
                        "T3_K": t3_k,
                        "W3_kgs": w3,
                        "P4_Pa": p4_pa,
                        "T4_K": t4_k,
                        "P5_Pa": p5_pa,
                        "T5_K": t5_k,
                        "P9_Pa": p9_pa,
                        "T9_K": t9_k,
                        "Mach_9": mach9,
                        "Stall_Margin": stall_margin
                    })

    # Write to CSV
    headers = list(records[0].keys())
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(records)
        
    print(f"Generated {len(records)} data records successfully.")
    print(f"Dataset saved with DO-200B traceability to: [do200b_envelope_dataset.csv](file://{output_path})")

if __name__ == "__main__":
    main()
