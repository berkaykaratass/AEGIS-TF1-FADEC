#!/usr/bin/env python3
"""
Station-Based Transient Gas Path Model Verification Suite
=========================================================

Validates flow continuity algebraic matching, quasi-1D thermodynamic station parameters,
and off-design parameter shifts (ISA day temp deviation).

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import pytest
import numpy as np
import math
from ai.models.adaptive_mpc import NonlinearStateSpace

def test_thermodynamic_station_matching():
    """Verify that temperature and pressure match physical engine station constraints (Brayton cycle)."""
    model = NonlinearStateSpace()
    
    # State: [N1_rad, N2_rad, T_t4, P3]
    state = np.array([30000.0 * np.pi / 30.0, 32000.0 * np.pi / 30.0, 1600.0, 101325.0 * 12.0], dtype=np.float32)
    inputs = [0.15, 0.0, 15.0] # Wf, V_ehd, theta_vane
    
    # Run one step of derivatives to populate stations
    model.derivatives(state, inputs)
    
    # 1. Verification of Station 2 (Inlet) vs Station 3 (Compressor Exit)
    # Compression must increase temperature and pressure
    assert model.stations[3]["P"] > model.stations[2]["P"]
    assert model.stations[3]["T"] > model.stations[2]["T"]
    
    # 2. Verification of Station 4 (Combustor Exit / Turbine Inlet)
    # Combustion must increase temperature at the cost of a minor pressure drop (4% burner loss)
    assert model.stations[4]["T"] > model.stations[3]["T"]
    assert model.stations[4]["P"] < model.stations[3]["P"] # P4 = P3 * 0.96
    
    # 3. Verification of Station 5 (Turbine Exit) vs Nozzle (Station 9)
    # Turbine expansion must drop temperature and pressure to drive the spools
    assert model.stations[5]["T"] < model.stations[4]["T"]
    assert model.stations[5]["P"] < model.stations[4]["P"]
    
    # Nozzle exit pressure must equal ambient pressure
    assert math.isclose(model.stations[9]["P"], model.P_amb)
    assert 0.0 <= model.stations[9]["Mach"] <= 1.0

def test_flow_continuity_matching():
    """Verify that the Newton-Raphson map matching solver enforces flow continuity (W_in = W_out)."""
    model = NonlinearStateSpace()
    
    state = np.array([30000.0 * np.pi / 30.0, 32000.0 * np.pi / 30.0, 1600.0, 101325.0 * 10.0], dtype=np.float32)
    inputs = [0.12, 0.0, 15.0]
    
    model.derivatives(state, inputs)
    
    # Fuel flow Wf = 0.12
    W3 = model.stations[3]["W"]
    W4 = model.stations[4]["W"]
    
    # Flow continuity check: W4 (turbine inlet flow) must equal W3 (compressor exit flow) + Wf
    assert math.isclose(W4, W3 + 0.12, rel_tol=1e-3)

def test_isa_off_design_parameter_shifts():
    """Verify that ambient day temperature deviations deform compressor corrected speeds and surge margin."""
    model = NonlinearStateSpace()
    
    # Nominal Day (delta_T_day = 0 K)
    state = np.array([30000.0 * np.pi / 30.0, 32000.0 * np.pi / 30.0, 1600.0, 101325.0 * 11.0], dtype=np.float32)
    inputs = [0.12, 0.0, 15.0]
    
    model.delta_T_day = 0.0
    model.derivatives(state, inputs)
    p3_nominal = model.stations[3]["P"]
    
    # Hot Day (delta_T_day = +15 K)
    model.delta_T_day = 15.0
    model.derivatives(state, inputs)
    p3_hot = model.stations[3]["P"]
    
    # On a hot day, air is less dense; compressor discharge pressure P3 must drop for the same speed
    assert p3_hot < p3_nominal, f"P3 hot day ({p3_hot}) should be lower than nominal day ({p3_nominal})"
