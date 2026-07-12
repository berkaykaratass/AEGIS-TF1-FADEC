"""
Surge Predictor GRU & CBF Unit Tests
"""

import os
import numpy as np
from ai.models.surge_predictor import SurgePredictor, CompressorEnvironment

def test_environment_reset_step():
    env = CompressorEnvironment()
    state = env.reset()
    assert len(state) == 7
    assert not env.is_surged
    
    # Take step
    next_state, reward, done, _ = env.step(action_fuel_adj=0.1)
    assert len(next_state) == 7
    assert isinstance(reward, float)

def test_predictor_forward():
    predictor = SurgePredictor(input_dim=7, hidden_dim=16, output_dim=2)
    predictor.reset_hidden()
    dummy_input = np.random.randn(7)
    
    out = predictor.predict(dummy_input)
    assert len(out) == 2
    assert 0.0 <= out[0] <= 1.0  # probability sigmoid bounded
    assert -1.0 <= out[1] <= 1.0 # adjustment tanh bounded
    
    # Verify hidden state update
    assert not np.allclose(predictor.h, 0.0)

def test_cbf_safety_filter():
    predictor = SurgePredictor()
    
    # Case 1: Safe commands within boundaries
    Wf_safe = predictor.apply_cbf_filter(Wf_cmd=0.5, n1=30000.0, n2=35000.0, delta_tip=0.00030)
    assert np.isclose(Wf_safe, 0.5)
    
    # Case 2: Lean blow-out protection (minimum limit)
    Wf_safe = predictor.apply_cbf_filter(Wf_cmd=0.005, n1=15000.0, n2=15000.0, delta_tip=0.00045)
    assert Wf_safe >= 0.02
    
    # Case 3: Spool shear protection (|N2 - N1| > 80,000)
    Wf_safe = predictor.apply_cbf_filter(Wf_cmd=1.0, n1=10000.0, n2=100000.0, delta_tip=0.00020)
    assert Wf_safe < 1.0
    
    # Case 4: Tip clearance emergency safety cut-off (delta_tip <= 80 microns)
    Wf_safe = predictor.apply_cbf_filter(Wf_cmd=1.0, n1=30000.0, n2=35000.0, delta_tip=0.00005)
    assert Wf_safe <= 0.96
