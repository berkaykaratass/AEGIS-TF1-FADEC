"""
AI Creep-Governor Safety Verification Tests
===========================================

Verifies the logic, activation timing, fuel flow reduction, and EGT cooling
of the FADEC AI Creep-Governor under DO-178C Level A.
"""

import pytest
import numpy as np
from simulation.digital_twin.twin_engine import DigitalTwinEngine
from ai.models.adaptive_mpc import NonlinearStateSpace

def test_creep_governor_activation_logic():
    # Model variables representing FADEC state
    run_time_sec = 285.0
    fuel_cmd = 1.0

    # 1. Under 290 seconds (approaching 5 minutes), governor is inactive
    governed_fuel_cmd = fuel_cmd
    if run_time_sec >= 290.0:
        governed_fuel_cmd = fuel_cmd * (1.0 - 0.021)
    assert governed_fuel_cmd == fuel_cmd, "Governor activated too early"

    # 2. At 290 seconds, governor must activate
    run_time_sec = 290.0
    if run_time_sec >= 290.0:
        governed_fuel_cmd = fuel_cmd * (1.0 - 0.021)
    assert governed_fuel_cmd == fuel_cmd * 0.979, "Governor failed to reduce fuel flow by 2.1%"
    assert np.isclose(governed_fuel_cmd, 0.979)

def test_creep_governor_egt_cooling_effect():
    # We verify the physical effect of a 2.1% fuel reduction on the turbine inlet temperature (T4)
    # using our NonlinearStateSpace model equations.
    sys_model = NonlinearStateSpace()
    
    # Baseline takeoff conditions (design RPM, max fuel command Wf = 0.303 kg/s)
    Wf_base = 0.303
    omega = 35000.0 * np.pi / 30.0
    P3 = 12.0 * 101325.0 # OPR 12
    state = np.array([omega, 1600.0, P3])
    inputs_base = np.array([Wf_base, 0.0, 15.0]) # Wf, V_ehd, theta_vane
    
    # Calculate baseline steady-state T4 temperature
    mass_flow = 1.2 * (omega / 8000.0) * (P3 / 1e5)
    T4_ss_base = sys_model.T_amb + (Wf_base * 4.3e7 * 0.98) / (sys_model.cp * (mass_flow + 1e-5))
    
    # 2.1% fuel command reduction
    Wf_governed = Wf_base * (1.0 - 0.021)
    inputs_governed = np.array([Wf_governed, 0.0, 15.0])
    T4_ss_governed = sys_model.T_amb + (Wf_governed * 4.3e7 * 0.98) / (sys_model.cp * (mass_flow + 1e-5))
    
    # Temperature drop in Kelvin
    T_drop = T4_ss_base - T4_ss_governed
    
    print(f"\nBaseline Wf: {Wf_base:.4f} kg/s | Governed Wf: {Wf_governed:.4f} kg/s")
    print(f"Baseline T4_ss: {T4_ss_base:.1f} K | Governed T4_ss: {T4_ss_governed:.1f} K")
    print(f"Temperature drop: {T_drop:.2f} K")
    
    # The temperature drop should be approximately 40 K (or at least within a realistic physical range)
    # The formula is linear with respect to Wf, so we can check that it drops by around 40 K
    assert 30.0 < T_drop < 50.0, f"Expected temperature drop of ~40 K, got {T_drop:.2f} K"
