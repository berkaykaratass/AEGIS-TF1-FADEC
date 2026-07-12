"""
Brayton Cycle Simulator Unit Tests
"""

import pytest
from simulation.thermodynamic.brayton_sim import BraytonCycleSimulator

def test_brayton_simulator_normal():
    sim = BraytonCycleSimulator()
    # Test standard sea level flight conditions, Mach 0.5
    res = sim.compute_cycle(T_amb=288.15, P_amb=101325.0, M_flight=0.5, r_p=8.0, T4_max=950.0)

    assert "T_t" in res
    assert "P_t" in res
    assert "F_specific" in res
    assert res["F_specific"] > 0.0
    assert 0.0 < res["eta_thermal"] < 1.0
    assert 0.0 < res["eta_propulsive"] <= 1.0

def test_brayton_flameout_error():
    sim = BraytonCycleSimulator()
    # High ambient temp + low T4 max causing unphysical values
    with pytest.raises(ValueError):
        sim.compute_cycle(T_amb=400.0, P_amb=101325.0, M_flight=1.5, r_p=2.0, T4_max=300.0)
