#!/usr/bin/env python3
"""
AEGIS-TJ1 Cognitive AI Engine Unit Tests
========================================
DO-178C DAL C Structural Unit Tests for advanced neural systems.
"""

import ctypes
import os
import pytest
import numpy as np

# Load library
lib_path = "./libfadec.dylib"
if not os.path.exists(lib_path):
    raise FileNotFoundError(f"FADEC library not found at {lib_path}. Run make first.")
lib = ctypes.CDLL(lib_path)

class AI_Advisory_Telemetry(ctypes.Structure):
    _fields_ = [
        ("compressor_degradation", ctypes.c_float),
        ("turbine_wear", ctypes.c_float),
        ("bayesian_surge_risk", ctypes.c_float),
        ("anomaly_score", ctypes.c_float),
        ("confidence_interval", ctypes.c_float),
    ]

class BayesianSurge_State(ctypes.Structure):
    _fields_ = [
        ("prior_surge_prob", ctypes.c_float),
        ("system_noise_var", ctypes.c_float),
        ("observation_noise_var", ctypes.c_float),
    ]

class DigitalTwin_State(ctypes.Structure):
    _fields_ = [
        ("est_compressor_eff", ctypes.c_float),
        ("est_turbine_eff", ctypes.c_float),
        ("learning_rate", ctypes.c_float),
        ("residual_history", ctypes.c_float * 5),
        ("residual_index", ctypes.c_uint32),
    ]

class CognitiveState(ctypes.Structure):
    _fields_ = [
        ("surge_estimator", BayesianSurge_State),
        ("digital_twin", DigitalTwin_State),
        ("telemetry", AI_Advisory_Telemetry),
    ]

# Declare function signatures
lib.cognitive_engine_init.argtypes = [ctypes.POINTER(CognitiveState)]
lib.cognitive_engine_init.restype = None

lib.cognitive_digital_twin_step.argtypes = [
    ctypes.POINTER(CognitiveState),
    ctypes.c_float,
    ctypes.c_float,
    ctypes.c_float,
    ctypes.c_float,
    ctypes.c_float,
]
lib.cognitive_digital_twin_step.restype = None

lib.cognitive_bayesian_surge_estimate.argtypes = [
    ctypes.POINTER(CognitiveState),
    ctypes.c_float,
    ctypes.c_float,
    ctypes.c_float,
]
lib.cognitive_bayesian_surge_estimate.restype = None

def test_cognitive_engine_init():
    state = CognitiveState()
    lib.cognitive_engine_init(ctypes.byref(state))
    
    assert state.telemetry.compressor_degradation == 0.0
    assert state.telemetry.turbine_wear == 0.0
    assert state.telemetry.bayesian_surge_risk == pytest.approx(0.01)
    assert state.telemetry.anomaly_score == 0.0
    assert state.telemetry.confidence_interval == 1.0
    
    assert state.surge_estimator.prior_surge_prob == pytest.approx(0.01)
    assert state.digital_twin.est_compressor_eff == 1.0
    assert state.digital_twin.est_turbine_eff == 1.0
    assert state.digital_twin.learning_rate == pytest.approx(0.002)

def test_cognitive_digital_twin():
    state = CognitiveState()
    lib.cognitive_engine_init(ctypes.byref(state))
    
    # expected egt is ~ (300 + 50 * 12.5) * 0.72 = ~666 K. Let's pass measured egt = 800 K (positive residual)
    lib.cognitive_digital_twin_step(ctypes.byref(state), 5.0, 300.0, 800.0, 50.0, 0.1)
    
    assert state.telemetry.compressor_degradation > 0.0
    assert state.telemetry.anomaly_score > 0.0
    assert state.telemetry.confidence_interval < 1.0

def test_cognitive_bayesian_surge():
    state = CognitiveState()
    lib.cognitive_engine_init(ctypes.byref(state))
    
    # Case 1: Low variance, low deceleration -> prior should stay low
    lib.cognitive_bayesian_surge_estimate(ctypes.byref(state), 0.001, 0.0, 0.10)
    assert state.telemetry.bayesian_surge_risk == pytest.approx(0.01)
    
    # Case 2: High variance, high negative deceleration -> probability of surge should rise
    for _ in range(25):
        lib.cognitive_bayesian_surge_estimate(ctypes.byref(state), 0.08, -6000.0, 0.10)
        
    assert state.telemetry.bayesian_surge_risk > 0.50
    assert 0.01 <= state.telemetry.bayesian_surge_risk <= 0.99001
