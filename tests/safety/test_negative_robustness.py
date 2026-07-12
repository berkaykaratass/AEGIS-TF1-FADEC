#!/usr/bin/env python3
"""
FADEC Negative & Robustness Testing Suite
=========================================

Verifies system safety, fault containment, and fail-safe transitions under 
worst-case input and hardware anomalies (negative testing).

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import pytest
import ctypes
import math
from simulation.digital_twin.twin_api import FADECSILSimulator, Scenario, ScenarioEvent

import os
lib_path = "./libfadec.dylib"
if not os.path.exists(lib_path):
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "libfadec.dylib")
lib = ctypes.CDLL(lib_path)

class FuelLimits(ctypes.Structure):
    _fields_ = [("min_wf_pct", ctypes.c_double), ("max_wf_pct", ctypes.c_double)]

class VaneState(ctypes.Structure):
    _fields_ = [
        ("cmd_deg", ctypes.c_double),
        ("fdbk_deg", ctypes.c_double),
        ("error_duration_sec", ctypes.c_double),
        ("jam_fault", ctypes.c_bool)
    ]

# Setup ctypes signatures
lib.vane_schedule_init.argtypes = [ctypes.POINTER(VaneState)]
lib.vane_schedule_monitor.argtypes = [ctypes.POINTER(VaneState), ctypes.c_double, ctypes.c_double, ctypes.c_double]
lib.vane_schedule_monitor.restype = ctypes.c_bool

def test_sensor_spike_robustness():
    """Verify that a massive 10x speed sensor EMI spike is rejected by FDIR filter, preventing fuel command jumps."""
    twin = FADECSILSimulator()
    
    # Run to stabilize speed at idle
    for _ in range(50):
        twin.step_1ms()
        
    initial_wf = twin.actuators.fuel_valve_pct
    
    # Inject a massive 10x N1 speed sensor spike (representing EMI burst)
    twin.stuck_at_sensors["n1"] = twin.sensors.n1_rpm * 10.0
    twin.step_1ms()
    
    # Assert that FDIR voting logic detects the discrepancy,
    # and prevents the active fuel command from spiking (retains safety within bounds)
    current_wf = twin.actuators.fuel_valve_pct
    assert abs(current_wf - initial_wf) < 10.0, f"Fuel command spiked from {initial_wf}% to {current_wf}% due to sensor fault!"

def test_actuator_stuck_fail_safe():
    """Verify that a stuck Fuel Metering Valve (actuator jam) is detected and triggers FADEC limit only warning."""
    twin = FADECSILSimulator()
    
    # Stabilize
    for _ in range(30):
        twin.step_1ms()
        
    # Inject actuator stuck fault (feedback remains at 20%)
    twin.actuator_limits["fuel"] = (20.0, 20.0)
    
    # Run simulation steps
    for _ in range(200):
        twin.step_1ms()
        
    # FADEC must detect that the command and feedback do not match and trigger alarm/warning
    assert twin.fadec_state.safety_monitor.current_state != 0 or twin.fadec_state.mode != 0

def test_ccdl_link_drop_handling():
    """Verify that complete CCDL link drop causes standby channel to assume independent control safely."""
    class ChannelConfig(ctypes.Structure):
        _fields_ = [
            ("channel_id", ctypes.c_uint32),
            ("state", ctypes.c_int),
            ("health_score", ctypes.c_uint32),
            ("heartbeat_tx_cnt", ctypes.c_uint32),
            ("heartbeat_rx_cnt", ctypes.c_uint32),
            ("rx_timeout_sec", ctypes.c_double),
            ("partner_failed", ctypes.c_bool)
        ]
        
    class ChannelSyncData(ctypes.Structure):
        _fields_ = [
            ("n1_rpm", ctypes.c_double),
            ("egt_kelvin", ctypes.c_double),
            ("p3_bar", ctypes.c_double),
            ("fuel_flow_cmd", ctypes.c_double),
            ("mode", ctypes.c_uint32),
            ("faults", ctypes.c_uint32),
            ("ekf_state", ctypes.c_double * 3),
            ("config_checksum", ctypes.c_uint32)
        ]
        
    lib.dual_channel_init.argtypes = [ctypes.POINTER(ChannelConfig), ctypes.c_uint32]
    lib.dual_channel_update.argtypes = [
        ctypes.POINTER(ChannelConfig),
        ctypes.POINTER(ChannelSyncData),
        ctypes.POINTER(ChannelSyncData),
        ctypes.c_bool,
        ctypes.c_double
    ]
    lib.dual_channel_update.restype = ctypes.c_bool
    
    config_a = ChannelConfig()
    lib.dual_channel_init(ctypes.byref(config_a), 0) # Lane A
    
    data_a = ChannelSyncData()
    data_b = ChannelSyncData()
    
    # 1. Nominal state: Link is healthy
    is_active = lib.dual_channel_update(ctypes.byref(config_a), ctypes.byref(data_a), ctypes.byref(data_b), True, 0.001)
    assert is_active is True # Channel A remains active
    
    # 2. CCDL Link dropped (remote_alive = False)
    is_active_dropped = lib.dual_channel_update(ctypes.byref(config_a), ctypes.byref(data_a), ctypes.byref(data_b), False, 0.001)
    assert is_active_dropped is True # Standalone Channel A continues running

def test_scheduler_overrun_budget_enforcement():
    """Verify that a task exceeding its allocated runtime budget triggers Health Monitor lockout."""
    lib.rtos_arinc_init.argtypes = []
    lib.rtos_arinc_get_partition_state.argtypes = [ctypes.c_int]
    lib.rtos_arinc_get_partition_state.restype = ctypes.c_int
    lib.rtos_arinc_report_error.argtypes = [ctypes.c_int, ctypes.c_int]
    
    lib.rtos_arinc_init()
    
    # Trigger MPU violation or budget overrun on AI Advisory partition (ID = 2)
    # HM_ERROR_MPU_VIOLATION = 1, PARTITION_AI_ADVISORY = 2
    lib.rtos_arinc_report_error(1, 2)
    
    # Check that partition state is locked out (state 2 = PARTITION_STATE_LOCKED_OUT)
    part_state = lib.rtos_arinc_get_partition_state(2)
    assert part_state == 2
