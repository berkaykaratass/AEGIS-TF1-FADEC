#!/usr/bin/env python3
"""
FADEC Version 9.0 Advanced Subsystem Verification Tests
======================================================
DO-178C DAL A Structural Unit Tests for v9.0 components.
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

# --- 1. Ctypes Structures ---

class MBC_State(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_double * 3),
        ("P", (ctypes.c_double * 3) * 3),
        ("Q", (ctypes.c_double * 3) * 3),
        ("R", (ctypes.c_double * 2) * 2),
        ("estimated_t41_k", ctypes.c_double),
        ("estimated_stall_margin", ctypes.c_double),
        ("fallback_active", ctypes.c_bool),
        ("consecutive_failures", ctypes.c_uint32),
    ]

class ActuatorLoop_State(ctypes.Structure):
    _fields_ = [
        ("prev_error", ctypes.c_double),
        ("integral", ctypes.c_double),
        ("coil_a_current_ma", ctypes.c_double),
        ("coil_b_current_ma", ctypes.c_double),
        ("measured_position_pct", ctypes.c_double),
        ("fault_bits", ctypes.c_uint32),
    ]

class Watermark_State(ctypes.Structure):
    _fields_ = [
        ("last_injected_noise", ctypes.c_double),
        ("correlation_sum", ctypes.c_double),
        ("correlation_count", ctypes.c_uint32),
        ("alarm_triggered", ctypes.c_bool),
        ("prev_n1", ctypes.c_double),
        ("logistic_state", ctypes.c_double),
        ("filtered_noise", ctypes.c_double),
    ]

class CreepState(ctypes.Structure):
    _fields_ = [
        ("accumulated_damage", ctypes.c_double),
        ("creep_rate", ctypes.c_double),
        ("life_degradation_index", ctypes.c_double),
    ]

class ACC_State(ctypes.Structure):
    _fields_ = [
        ("rotor_thermal_growth_mm", ctypes.c_double),
        ("casing_thermal_growth_mm", ctypes.c_double),
        ("tip_clearance_mm", ctypes.c_double),
        ("acc_valve_cmd_pct", ctypes.c_double),
        ("rotor_temp_k", ctypes.c_double),
        ("casing_temp_k", ctypes.c_double),
    ]

# --- 2. Function Signatures ---

lib.mbc_init.argtypes = [ctypes.POINTER(MBC_State)]
lib.mbc_init.restype = None

lib.mbc_ekf_step.argtypes = [
    ctypes.POINTER(MBC_State),
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_bool,
    ctypes.c_double,
    ctypes.c_bool,
    ctypes.c_double,
]
lib.mbc_ekf_step.restype = None

lib.actuator_loop_init.argtypes = [ctypes.POINTER(ActuatorLoop_State)]
lib.actuator_loop_init.restype = None

lib.actuator_loop_close.argtypes = [
    ctypes.POINTER(ActuatorLoop_State),
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_double,
    ctypes.POINTER(ctypes.c_double),
]
lib.actuator_loop_close.restype = None

lib.watermark_init.argtypes = [ctypes.POINTER(Watermark_State)]
lib.watermark_init.restype = None

lib.watermark_inject.argtypes = [
    ctypes.POINTER(Watermark_State),
    ctypes.c_double,
    ctypes.c_uint64,
]
lib.watermark_inject.restype = ctypes.c_double

lib.watermark_verify.argtypes = [
    ctypes.POINTER(Watermark_State),
    ctypes.c_double,
    ctypes.c_uint64,
]
lib.watermark_verify.restype = None

lib.creep_governor_init.argtypes = [ctypes.POINTER(CreepState)]
lib.creep_governor_init.restype = None

lib.creep_governor_step.argtypes = [
    ctypes.POINTER(CreepState),
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_double,
]
lib.creep_governor_step.restype = None

lib.acc_init.argtypes = [ctypes.POINTER(ACC_State)]
lib.acc_init.restype = None

lib.acc_control_step.argtypes = [
    ctypes.POINTER(ACC_State),
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_double,
]
lib.acc_control_step.restype = None

# --- 3. Unit Tests ---

def test_mbc_ekf():
    state = MBC_State()
    lib.mbc_init(ctypes.byref(state))
    
    assert state.x[0] == 0.0
    assert state.x[1] == 288.15
    assert state.x[2] == 0.35
    
    # Run EKF step with non-zero inputs and measurements
    lib.mbc_ekf_step(ctypes.byref(state), 40.0, 10.0, 30000.0, True, 4.5, True, 0.01)
    
    # Estimates should update toward measurements
    assert state.x[0] > 0.0
    assert state.x[1] > 288.15
    assert state.estimated_t41_k > 288.15
    assert 0.0 <= state.estimated_stall_margin <= 1.0

def test_actuator_loop():
    state = ActuatorLoop_State()
    lib.actuator_loop_init(ctypes.byref(state))
    
    coil_ma = ctypes.c_double(0.0)
    # Command = 50.0%, LVDT feedback = 3.5 V (which is (3.5/7.0)*100 = 50.0% -> error is 0.0)
    lib.actuator_loop_close(ctypes.byref(state), 50.0, 3.5, 0.0005, ctypes.byref(coil_ma))
    
    assert state.measured_position_pct == pytest.approx(50.0)
    assert coil_ma.value == pytest.approx(0.0)
    assert state.fault_bits == 0
    
    # Check LVDT fault bounds
    lib.actuator_loop_close(ctypes.byref(state), 50.0, 9.0, 0.0005, ctypes.byref(coil_ma))
    assert (state.fault_bits & 0x04) != 0

def test_cyber_watermark():
    state = Watermark_State()
    lib.watermark_init(ctypes.byref(state))
    
    # Test injection of pseudo-random noise
    cmd1 = lib.watermark_inject(ctypes.byref(state), 50.0, 1)
    cmd2 = lib.watermark_inject(ctypes.byref(state), 50.0, 2)
    
    assert cmd1 != 50.0
    assert cmd1 != cmd2
    
    # Test correlation and verify alarm triggers if correlation drops
    # Feed flat speed (no correlation to injected noise) for 105 samples
    state.prev_n1 = 30000.0
    for i in range(1, 105):
        lib.watermark_inject(ctypes.byref(state), 50.0, i)
        lib.watermark_verify(ctypes.byref(state), 30000.0, i)
        
    assert state.alarm_triggered is True

def test_creep_governor():
    state = CreepState()
    lib.creep_governor_init(ctypes.byref(state))
    
    # Run with high temp and stress -> should accumulate creep damage
    lib.creep_governor_step(ctypes.byref(state), 1400.0, 8e8, 10.0)
    
    assert state.creep_rate > 0.0
    assert state.accumulated_damage > 0.0
    assert state.life_degradation_index == state.accumulated_damage

def test_active_clearance():
    state = ACC_State()
    lib.acc_init(ctypes.byref(state))
    
    assert state.tip_clearance_mm == 1.5
    
    # Run ACC step under high thermal conditions -> blade expands, clearance drops, valve opens
    lib.acc_control_step(ctypes.byref(state), 1200.0, 30000.0, 1.0)
    
    assert state.tip_clearance_mm < 1.5
    assert state.acc_valve_cmd_pct > 0.0
