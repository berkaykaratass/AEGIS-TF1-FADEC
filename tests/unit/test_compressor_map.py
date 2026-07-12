"""
Compressor Simulator Unit Tests
"""

import pytest
from simulation.thermodynamic.compressor_sim import CompressorSimulator

def test_compressor_lookup_normal():
    sim = CompressorSimulator()
    
    # Normal operating point: 80% speed, 12 kg/s flow
    pr, eff, is_surge = sim.lookup_performance(speed_pct=80.0, flow=12.0)
    
    assert pr > 1.0
    assert 0.5 < eff < 0.95
    assert not is_surge

def test_compressor_surge_detection():
    sim = CompressorSimulator()
    
    # Low flow at high speed triggers surge
    pr, eff, is_surge = sim.lookup_performance(speed_pct=90.0, flow=5.0)
    assert is_surge

def test_surge_margin():
    sim = CompressorSimulator()
    sm = sim.compute_surge_margin(speed_pct=80.0, flow_op=12.0, pr_op=5.5)
    assert sm > 0.0
