"""
Pytest Verification Suite for DO-178C DAL A Safety Contracts
===========================================================
Verifies Safety Kernel STT transitions, EKF Covariance Positivity,
Latching Fallback thresholds, and oblivious memory write checks.

Proprietary — AEGIS-TF1 Systems Development Group
"""

import ctypes
import pytest
import os
import sys

# Setup absolute import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the ctypes structures
from tests.safety.run_massive_validation import (
    FADEC_State, HAL_SensorReadings, HAL_ActuatorCommands, SafetyMonitorState
)

lib_path = "./libfadec.dylib"
if not os.path.exists(lib_path):
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "libfadec.dylib")

lib = ctypes.CDLL(lib_path)

# Declare EKF PD argtypes for robust passing
lib.mbc_ekf_is_positive_definite.argtypes = [ctypes.POINTER((ctypes.c_double * 3) * 3)]
lib.mbc_ekf_is_positive_definite.restype = ctypes.c_bool

# Declare Safety Monitor argtypes/restype
lib.safety_monitor_init.argtypes = [ctypes.POINTER(SafetyMonitorState)]
lib.safety_monitor_init.restype = None

lib.safety_monitor_process_stt.argtypes = [
    ctypes.POINTER(SafetyMonitorState),
    ctypes.POINTER(HAL_SensorReadings),
    ctypes.c_uint32,
    ctypes.c_double,
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_double
]
lib.safety_monitor_process_stt.restype = ctypes.c_int

# Enums mappings from C headers
SAFETY_STATE_NORMAL = 0
SAFETY_STATE_DEGRADED = 1
SAFETY_STATE_LIMIT_ONLY = 2
SAFETY_STATE_EMERGENCY_SHUTDOWN = 3

VERDICT_PASS = 0
VERDICT_INHIBIT_WF = 1
VERDICT_EMERGENCY_SHUTDOWN = 2

def test_ekf_covariance_positivity_proof():
    """Verifies that mbc_ekf_is_positive_definite correctly validates matrices using Sylvester's criterion"""
    # 1. Setup positive definite matrix (Identity)
    P_good = ((ctypes.c_double * 3) * 3)(
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0)
    )
    assert lib.mbc_ekf_is_positive_definite(ctypes.byref(P_good)) is True

    # 2. Setup non-positive definite matrix (negative diagonal)
    P_bad_diagonal = ((ctypes.c_double * 3) * 3)(
        (-1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0)
    )
    assert lib.mbc_ekf_is_positive_definite(ctypes.byref(P_bad_diagonal)) is False

    # 3. Setup non-positive definite matrix (fails 2x2 minor check: det = 1 - 2 = -1)
    P_bad_minor = ((ctypes.c_double * 3) * 3)(
        (1.0, 1.414, 0.0),
        (1.414, 1.0, 0.0),
        (0.0, 0.0, 1.0)
    )
    assert lib.mbc_ekf_is_positive_definite(ctypes.byref(P_bad_minor)) is False

def test_safety_monitor_stt_transitions():
    """Verifies formal STT transitions and priority encoding logic"""
    smon = FADEC_State().safety_monitor
    lib.safety_monitor_init(ctypes.byref(smon))
    assert smon.current_state == SAFETY_STATE_NORMAL

    sensors = HAL_SensorReadings(
        n1_rpm=15000.0,
        n1_rpm_sensor_1=15000.0,
        n1_rpm_sensor_2=15000.0,
        egt_kelvin=600.0,
        p3_bar=1.013,
        p2_bar=1.013,
        t2_kelvin=288.15,
        vibration_g=0.5,
        fuel_flow_kgs=0.1,
        ehd_voltage_kv=0.0
    )
    
    safe_wf = ctypes.c_double(0.0)

    # 1. Trigger single sensor failure CBIT event (0x02: speed sensor 1 fail)
    # Target state: DEGRADED. Target verdict: PASS.
    verdict = lib.safety_monitor_process_stt(
        ctypes.byref(smon),
        ctypes.byref(sensors),
        0x02,  # CBIT single sensor fail
        20.0,  # requested fuel flow
        ctypes.byref(safe_wf),
        0.001  # dt
    )
    assert smon.current_state == SAFETY_STATE_DEGRADED
    assert verdict == VERDICT_PASS
    assert safe_wf.value == 20.0

    # 2. Trigger assertion failure CBIT event (0x80: assertion fail)
    # Target state: LIMIT_ONLY. Target verdict: INHIBIT_WF (clamps fuel to safe limits).
    verdict = lib.safety_monitor_process_stt(
        ctypes.byref(smon),
        ctypes.byref(sensors),
        0x80,  # CBIT assertion fail
        45.0,  # requested fuel flow (above clamp threshold)
        ctypes.byref(safe_wf),
        0.001
    )
    assert smon.current_state == SAFETY_STATE_LIMIT_ONLY
    assert verdict == VERDICT_INHIBIT_WF
    assert safe_wf.value == 25.0  # Clamped to 25.0%

    # 3. Trigger physical breach event (overspeed)
    # Target state: EMERGENCY_SHUTDOWN. Target verdict: EMERGENCY_SHUTDOWN (fuel cut).
    sensors.n1_rpm = 112000.0  # Limit is 105,000 RPM
    verdict = lib.safety_monitor_process_stt(
        ctypes.byref(smon),
        ctypes.byref(sensors),
        0x00,
        20.0,
        ctypes.byref(safe_wf),
        0.001
    )
    assert smon.current_state == SAFETY_STATE_EMERGENCY_SHUTDOWN
    assert verdict == VERDICT_EMERGENCY_SHUTDOWN
    assert safe_wf.value == 0.0  # Cut fuel immediately

def test_ekf_latching_fallback():
    """Verifies EKF latching fallback after 50 consecutive ticks of divergence"""
    state = FADEC_State()
    lib.fadec_init(ctypes.byref(state))
    assert state.mbc_state.fallback_active is False
    
    # Setup realistic sensor measurements
    sensors = HAL_SensorReadings(
        n1_rpm=15000.0,
        n1_rpm_sensor_1=35000.0,  # Huge mismatch to trigger Mahalanobis gating failure
        n1_rpm_sensor_2=35000.0,
        egt_kelvin=600.0,
        p3_bar=1.013,
        p2_bar=1.013,
        t2_kelvin=288.15,
        vibration_g=0.5,
        fuel_flow_kgs=0.1,
        ehd_voltage_kv=0.0
    )
    actuators = HAL_ActuatorCommands()
    
    # Execute 49 ticks - fallback should not latch yet
    for _ in range(49):
        lib.fadec_control_step(ctypes.byref(state), ctypes.byref(sensors), ctypes.byref(actuators))
    
    assert state.mbc_state.fallback_active is False
    
    # Tick 50 - fallback must latch active
    lib.fadec_control_step(ctypes.byref(state), ctypes.byref(sensors), ctypes.byref(actuators))
    assert state.mbc_state.fallback_active is True
    
    # Verify that once latched, it remains active even if sensor recovers
    sensors.n1_rpm_sensor_1 = 15000.0
    sensors.n1_rpm_sensor_2 = 15000.0
    lib.fadec_control_step(ctypes.byref(state), ctypes.byref(sensors), ctypes.byref(actuators))
    assert state.mbc_state.fallback_active is True

def test_mpu_partition_access():
    """Verifies that memory partition policies are enforced obliviously via fadec_write_memory"""
    # Allowed: Control partition writing to Control address
    assert lib.fadec_write_memory(1, 0x00010000, 42) == 0

    # Allowed: Safety partition reading Control (mock read operations allowed under write rules)
    assert lib.fadec_write_memory(2, 0x00050000, 42) == 0

    # Prohibited: Advisory partition attempting write access to Control memory space
    assert lib.fadec_write_memory(3, 0x00010000, 42) == -3
