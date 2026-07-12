#!/usr/bin/env python3
"""
FADEC Version 4.0 Subsystem Verification Tests
==============================================
DO-178C DAL A Structural Unit Tests.
Verifies compliance with requirements REQ-FADEC-001 through REQ-FADEC-014.
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

# Ctypes structures
class StartSequence(ctypes.Structure):
    _fields_ = [
        ("state", ctypes.c_int),
        ("abort_reason", ctypes.c_int),
        ("time_in_state_sec", ctypes.c_double),
        ("total_start_time_sec", ctypes.c_double),
        ("igniter_on", ctypes.c_bool),
        ("starter_on", ctypes.c_bool),
        ("peak_egt_k", ctypes.c_double),
        ("egt_history", ctypes.c_double * 5),
    ]

class ThrustRatingConfig(ctypes.Structure):
    _fields_ = [
        ("rating", ctypes.c_int),
        ("flex_temp_k", ctypes.c_double),
        ("flex_enabled", ctypes.c_bool),
        ("max_n1_ref", ctypes.c_double),
    ]

class FuelLimits(ctypes.Structure):
    _fields_ = [
        ("min_wf_pct", ctypes.c_double),
        ("max_wf_pct", ctypes.c_double),
    ]

class VaneState(ctypes.Structure):
    _fields_ = [
        ("cmd_deg", ctypes.c_double),
        ("fdbk_deg", ctypes.c_double),
        ("error_duration_sec", ctypes.c_double),
        ("jam_fault", ctypes.c_bool),
    ]

class ChannelConfig(ctypes.Structure):
    _fields_ = [
        ("channel_id", ctypes.c_uint32),
        ("state", ctypes.c_int),
        ("health_score", ctypes.c_uint32),
        ("heartbeat_tx_cnt", ctypes.c_uint32),
        ("heartbeat_rx_cnt", ctypes.c_uint32),
        ("rx_timeout_sec", ctypes.c_double),
        ("partner_failed", ctypes.c_bool),
    ]

class ChannelSyncData(ctypes.Structure):
    _fields_ = [
        ("n1_rpm", ctypes.c_double),
        ("egt_kelvin", ctypes.c_double),
        ("fuel_flow_cmd", ctypes.c_double),
        ("mode", ctypes.c_uint32),
        ("faults", ctypes.c_uint32),
    ]

class ARINC429_Word(ctypes.Structure):
    _fields_ = [
        ("label", ctypes.c_uint8),
        ("sdi", ctypes.c_uint8),
        ("data", ctypes.c_uint32),
        ("ssm", ctypes.c_uint8),
        ("parity", ctypes.c_uint8),
    ]

class SafetyMonitorState(ctypes.Structure):
    _fields_ = [
        ("egt_overshoot_timer", ctypes.c_double),
        ("vibration_overshoot_timer", ctypes.c_double),
        ("trip_active", ctypes.c_bool),
        ("current_state", ctypes.c_int),
    ]

class SafetyVetoLatch(ctypes.Structure):
    _fields_ = [
        ("request_mask", ctypes.c_uint32),
        ("committed_latch", ctypes.c_uint32),
    ]

class FDIR_SensorState(ctypes.Structure):
    _fields_ = [
        ("speed_sensor_1_rpm", ctypes.c_double),
        ("speed_sensor_2_rpm", ctypes.c_double),
        ("s1_valid", ctypes.c_bool),
        ("s2_valid", ctypes.c_bool),
        ("disagreement_duration_sec", ctypes.c_double),
        ("dual_sensor_failure", ctypes.c_bool),
        ("synthetic_n1_rpm", ctypes.c_double),
        ("s1_fault_timer_sec", ctypes.c_double),
        ("s2_fault_timer_sec", ctypes.c_double),
        ("s1_recover_timer_sec", ctypes.c_double),
        ("s2_recover_timer_sec", ctypes.c_double),
        ("s1_confirmed_failed", ctypes.c_bool),
        ("s2_confirmed_failed", ctypes.c_bool),
    ]

class HAL_SensorReadings(ctypes.Structure):
    _fields_ = [
        ("n1_rpm", ctypes.c_double),
        ("n1_rpm_sensor_1", ctypes.c_double),
        ("n1_rpm_sensor_2", ctypes.c_double),
        ("egt_kelvin", ctypes.c_double),
        ("p3_bar", ctypes.c_double),
        ("p2_bar", ctypes.c_double),
        ("t2_kelvin", ctypes.c_double),
        ("vibration_g", ctypes.c_double),
        ("fuel_flow_kgs", ctypes.c_double),
        ("ehd_voltage_kv", ctypes.c_double),
    ]

# Setup Signatures
lib.engine_start_init.argtypes = [ctypes.POINTER(StartSequence)]
lib.engine_start_step.argtypes = [ctypes.POINTER(StartSequence), ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.POINTER(ctypes.c_double)]
lib.engine_start_step.restype = ctypes.c_int

lib.thrust_modes_init.argtypes = [ctypes.POINTER(ThrustRatingConfig)]
lib.thrust_modes_get_n1_limit.argtypes = [ctypes.POINTER(ThrustRatingConfig), ctypes.c_double, ctypes.c_double, ctypes.c_double]
lib.thrust_modes_get_n1_limit.restype = ctypes.c_double

lib.fuel_schedule_init.argtypes = []
lib.fuel_schedule_get_limits.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.POINTER(FuelLimits)]

lib.vane_schedule_init.argtypes = [ctypes.POINTER(VaneState)]
lib.vane_schedule_get_angle.argtypes = [ctypes.c_double, ctypes.c_double]
lib.vane_schedule_get_angle.restype = ctypes.c_double
lib.vane_schedule_monitor.argtypes = [ctypes.POINTER(VaneState), ctypes.c_double, ctypes.c_double, ctypes.c_double]
lib.vane_schedule_monitor.restype = ctypes.c_bool

lib.dual_channel_init.argtypes = [ctypes.POINTER(ChannelConfig), ctypes.c_uint32]
lib.dual_channel_calc_health.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
lib.dual_channel_calc_health.restype = ctypes.c_uint32
lib.dual_channel_update.argtypes = [ctypes.POINTER(ChannelConfig), ctypes.POINTER(ChannelSyncData), ctypes.POINTER(ChannelSyncData), ctypes.c_bool, ctypes.c_double]
lib.dual_channel_update.restype = ctypes.c_bool

lib.arinc429_pack.argtypes = [ctypes.POINTER(ARINC429_Word)]
lib.arinc429_pack.restype = ctypes.c_uint32
lib.arinc429_unpack.argtypes = [ctypes.c_uint32, ctypes.POINTER(ARINC429_Word)]
lib.arinc429_verify_parity.argtypes = [ctypes.c_uint32]
lib.arinc429_verify_parity.restype = ctypes.c_bool
lib.arinc429_encode_bnr.argtypes = [ctypes.c_double, ctypes.c_double]
lib.arinc429_encode_bnr.restype = ctypes.c_uint32
lib.arinc429_decode_bnr.argtypes = [ctypes.c_uint32, ctypes.c_double, ctypes.c_bool]
lib.arinc429_decode_bnr.restype = ctypes.c_double

lib.safety_monitor_init.argtypes = [ctypes.POINTER(SafetyMonitorState)]
lib.safety_monitor_process_stt.argtypes = [ctypes.POINTER(SafetyMonitorState), ctypes.POINTER(HAL_SensorReadings), ctypes.c_uint32, ctypes.c_double, ctypes.POINTER(ctypes.c_double), ctypes.c_double]
lib.safety_monitor_process_stt.restype = ctypes.c_int

lib.fdir_sensor_init.argtypes = [ctypes.POINTER(FDIR_SensorState)]
lib.fdir_sensor_vote_speed.argtypes = [
    ctypes.POINTER(FDIR_SensorState),
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_double,
    ctypes.POINTER(ctypes.c_double),
]
lib.fdir_sensor_vote_speed.restype = ctypes.c_bool

lib.triple_buffer_init.argtypes = [ctypes.c_void_p]
lib.triple_buffer_write.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint16]
lib.triple_buffer_write.restype = ctypes.c_bool
lib.triple_buffer_read.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint16]
lib.triple_buffer_read.restype = ctypes.c_bool


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TEST CASES
# ═══════════════════════════════════════════════════════════════════════════════

def test_engine_start_sequence():
    """Verifies REQ-FADEC-001, REQ-FADEC-002, REQ-FADEC-003: Startup, Hot-start & Hung-start protection."""
    seq = StartSequence()
    lib.engine_start_init(ctypes.byref(seq))
    assert seq.state == 0 # START_STATE_OFF
    
    fuel_cmd = ctypes.c_double(0.0)
    
    # Crank transition
    state = lib.engine_start_step(ctypes.byref(seq), 1000.0, 290.0, 0.001, ctypes.byref(fuel_cmd))
    assert state == 1 # START_STATE_CRANKING
    # Call another step in Cranking to let outputs settle
    state = lib.engine_start_step(ctypes.byref(seq), 1000.0, 290.0, 0.001, ctypes.byref(fuel_cmd))
    assert seq.starter_on is True
    assert seq.igniter_on is False
    
    # Ignition transition
    state = lib.engine_start_step(ctypes.byref(seq), 3000.0, 290.0, 0.001, ctypes.byref(fuel_cmd))
    assert state == 2 # START_STATE_IGNITION
    # Call another step in Ignition to let outputs settle
    state = lib.engine_start_step(ctypes.byref(seq), 3000.0, 290.0, 0.001, ctypes.byref(fuel_cmd))
    assert seq.igniter_on is True
    assert fuel_cmd.value == 8.5
    
    # Hot-start check (REQ-FADEC-002)
    state = lib.engine_start_step(ctypes.byref(seq), 3500.0, 1000.0, 0.001, ctypes.byref(fuel_cmd))
    assert state == 6 # START_STATE_ABORTED
    assert seq.abort_reason == 1 # START_ABORT_HOT_START
    assert fuel_cmd.value == 0.0
    
    # Hung-start check (REQ-FADEC-003)
    lib.engine_start_init(ctypes.byref(seq))
    # 1. Crank to Ignition
    lib.engine_start_step(ctypes.byref(seq), 3000.0, 290.0, 0.001, ctypes.byref(fuel_cmd))
    # 2. Trigger lightoff (EGT = 500 K > 480 K)
    lib.engine_start_step(ctypes.byref(seq), 3000.0, 500.0, 0.001, ctypes.byref(fuel_cmd))
    # 3. Transition through Lightoff state (needs > 2.0 seconds)
    lib.engine_start_step(ctypes.byref(seq), 3000.0, 500.0, 1.0, ctypes.byref(fuel_cmd))
    lib.engine_start_step(ctypes.byref(seq), 3000.0, 500.0, 1.1, ctypes.byref(fuel_cmd))
    # 4. Stay at sub-idle speed and run time to exceed 45 seconds
    for _ in range(460):
        state = lib.engine_start_step(ctypes.byref(seq), 3000.0, 500.0, 0.1, ctypes.byref(fuel_cmd))
    assert state == 6 # START_STATE_ABORTED
    assert seq.abort_reason == 2 # START_ABORT_HUNG_START


def test_thrust_ratings_and_flex():
    """Verifies REQ-FADEC-004, REQ-FADEC-005: Flat rating schedule and Flex temperature derating."""
    config = ThrustRatingConfig()
    lib.thrust_modes_init(ctypes.byref(config))
    assert config.max_n1_ref == 100000.0
    
    # Standard day, TOGA
    config.rating = 3 # RATING_TOGA
    n1_lim_std = lib.thrust_modes_get_n1_limit(ctypes.byref(config), 288.15, 1.013, 0.0)
    assert n1_lim_std == 100000.0
    
    # Hot day derate (REQ-FADEC-004)
    n1_lim_hot = lib.thrust_modes_get_n1_limit(ctypes.byref(config), 310.0, 1.013, 0.0)
    assert n1_lim_hot < 100000.0
    
    # Flex derate (REQ-FADEC-005)
    config.flex_enabled = True
    config.flex_temp_k = 325.0
    n1_lim_flex = lib.thrust_modes_get_n1_limit(ctypes.byref(config), 288.15, 1.013, 0.0)
    assert n1_lim_flex < n1_lim_hot
    assert n1_lim_flex == lib.thrust_modes_get_n1_limit(ctypes.byref(config), 325.0, 1.013, 0.0)


def test_fuel_schedule_limits():
    """Verifies REQ-FADEC-006: Fuel schedule bounds logic."""
    limits = FuelLimits()
    lib.fuel_schedule_init()
    
    # Idle speed limits: RPM = 15000, P3 = 2.0 bar, T2 = 288.15
    lib.fuel_schedule_get_limits(15000.0, 2.0, 288.15, ctypes.byref(limits))
    assert limits.min_wf_pct == 0.0
    assert limits.max_wf_pct > 0.0
    
    # High speed limits: RPM = 50000, P3 = 6.0 bar, T2 = 288.15
    lib.fuel_schedule_get_limits(50000.0, 6.0, 288.15, ctypes.byref(limits))
    assert limits.max_wf_pct > limits.min_wf_pct


def test_vane_schedule_and_jam():
    """Verifies REQ-FADEC-007, REQ-FADEC-008: Stator vane scheduling & Jam monitoring."""
    state = VaneState()
    lib.vane_schedule_init(ctypes.byref(state))
    assert state.jam_fault is False
    
    # Low speed corrected angle (fully closed)
    angle_low = lib.vane_schedule_get_angle(5000.0, 288.15)
    assert angle_low == 30.0
    
    # High speed corrected angle (fully open)
    angle_high = lib.vane_schedule_get_angle(95000.0, 288.15)
    assert angle_high == -15.0
    
    # Jam detection verification (REQ-FADEC-008)
    # Feed command is 30, feedback is 10 (disagreement is 20 deg)
    healthy = lib.vane_schedule_monitor(ctypes.byref(state), 30.0, 10.0, 0.1)
    assert healthy is True # not latched yet (only 100ms)
    
    # Disagree for another 400ms (total 500ms limit reached)
    healthy = lib.vane_schedule_monitor(ctypes.byref(state), 30.0, 10.0, 0.4)
    assert healthy is False
    assert state.jam_fault is True


def test_dual_channel_handover():
    """Verifies REQ-FADEC-009, REQ-FADEC-010: Channel health & Active/Standby synchronization handover."""
    local_cfg = ChannelConfig()
    lib.dual_channel_init(ctypes.byref(local_cfg), 1) # Channel B (boots as standby)
    assert local_cfg.state == 1 # CHANNEL_STATE_STANDBY
    
    # Check health calculation (REQ-FADEC-009)
    score_healthy = lib.dual_channel_calc_health(0, 0, 0)
    assert score_healthy == 100
    
    score_faulty = lib.dual_channel_calc_health(1, 1, 1)
    assert score_faulty == (100 - 25 - 40 - 15)
    
    # Test takeover when remote channel fails (REQ-FADEC-010)
    local_data = ChannelSyncData(n1_rpm=30000.0, egt_kelvin=600.0, fuel_flow_cmd=35.0, faults=0)
    remote_data = ChannelSyncData(n1_rpm=30000.0, egt_kelvin=600.0, fuel_flow_cmd=35.0, faults=1) # degraded remote
    
    # If remote partner fails / stops sending heartbeat (remote_alive = False)
    # Check if local B promotes to ACTIVE after timeout
    authority = lib.dual_channel_update(ctypes.byref(local_cfg), ctypes.byref(local_data), ctypes.byref(remote_data), False, 0.05)
    assert authority is False # not timeout yet
    
    authority = lib.dual_channel_update(ctypes.byref(local_cfg), ctypes.byref(local_data), ctypes.byref(remote_data), False, 0.06)
    assert authority is True
    assert local_cfg.state == 0 # CHANNEL_STATE_ACTIVE


def test_arinc429_transceiver():
    """Verifies REQ-FADEC-011, REQ-FADEC-012: ARINC 429 protocol pack, parity check, and BNR decoding."""
    # Build a word structure
    word = ARINC429_Word(label=100, sdi=1, data=12345, ssm=0, parity=0)
    
    packed = lib.arinc429_pack(ctypes.byref(word))
    assert lib.arinc429_verify_parity(packed) is True
    
    # Unpack and verify
    decoded = ARINC429_Word()
    lib.arinc429_unpack(packed, ctypes.byref(decoded))
    assert decoded.label == 100
    assert decoded.sdi == 1
    assert decoded.data == 12345
    assert decoded.ssm == 0
    
    # BNR encoding/decoding (REQ-FADEC-012)
    raw_val = 85.5
    encoded_bnr = lib.arinc429_encode_bnr(raw_val, 100.0)
    decoded_val = lib.arinc429_decode_bnr(encoded_bnr, 100.0, True)
    assert np.isclose(raw_val, decoded_val, atol=0.01)


def test_safety_monitor_range_checks():
    """Verifies REQ-FADEC-014: Safety monitor static range checks, veto latch, and cooldown."""
    smon = SafetyMonitorState()
    lib.safety_monitor_init(ctypes.byref(smon))
    assert smon.trip_active is False
    
    veto = SafetyVetoLatch.in_dll(lib, "hal_safety_veto")
    veto.request_mask = 0
    veto.committed_latch = 0
    
    sensors = HAL_SensorReadings(
        n1_rpm=30000.0,
        egt_kelvin=600.0,
        p3_bar=5.0,
        p2_bar=1.013,
        t2_kelvin=288.15,
        vibration_g=1.2,
        fuel_flow_kgs=0.1,
        ehd_voltage_kv=0.0
    )
    
    safe_wf = ctypes.c_double(50.0)
    
    # Step 1: Nominal region, no veto requested or committed
    verdict = lib.safety_monitor_process_stt(ctypes.byref(smon), ctypes.byref(sensors), 0, 50.0, ctypes.byref(safe_wf), 0.01)
    assert verdict == 0 # VERDICT_PASS
    assert smon.trip_active is False
    assert veto.request_mask == 0
    assert veto.committed_latch == 0
    
    # Step 2: Breach EGT redline limit (1050.0) but only for 10ms (limit is 20ms) -> no veto committed yet
    sensors.egt_kelvin = 1060.0
    verdict = lib.safety_monitor_process_stt(ctypes.byref(smon), ctypes.byref(sensors), 0, 50.0, ctypes.byref(safe_wf), 0.01)
    assert verdict == 0 # VERDICT_PASS
    assert smon.trip_active is False
    assert (veto.request_mask & 0x02) == 0  # VETO_REASON_OVERTEMP not requested yet
    
    # Step 3: Keep EGT overlimit for another 10ms (total 20ms) -> triggers overtemp veto request & latch!
    verdict = lib.safety_monitor_process_stt(ctypes.byref(smon), ctypes.byref(sensors), 0, 50.0, ctypes.byref(safe_wf), 0.01)
    assert verdict == 2 # VERDICT_EMERGENCY_SHUTDOWN
    assert smon.trip_active is True
    assert (veto.request_mask & 0x02) != 0
    assert (veto.committed_latch & 0x02) != 0
    assert safe_wf.value == 0.0
    
    # Step 4: Drop EGT below redline (e.g. 1000 K) but above cooldown threshold (950 K) -> request_mask clears, but committed_latch remains active (sticky cooldown)
    sensors.egt_kelvin = 1000.0
    verdict = lib.safety_monitor_process_stt(ctypes.byref(smon), ctypes.byref(sensors), 0, 50.0, ctypes.byref(safe_wf), 0.01)
    assert verdict == 2 # VERDICT_EMERGENCY_SHUTDOWN
    assert (veto.request_mask & 0x02) == 0
    assert (veto.committed_latch & 0x02) != 0 # still latched!
    
    # Step 5: Cool down below 950 K (e.g. 900 K) -> auto-clears the latch!
    sensors.egt_kelvin = 900.0
    verdict = lib.safety_monitor_process_stt(ctypes.byref(smon), ctypes.byref(sensors), 0, 50.0, ctypes.byref(safe_wf), 0.01)
    assert verdict == 0 # VERDICT_PASS
    assert smon.trip_active is False
    assert veto.request_mask == 0
    assert veto.committed_latch == 0

def test_triple_buffer_ipc():
    """Verifies REQ-FADEC-013: Lock-free atomic triple buffer operation."""
    class TripleBuffer(ctypes.Structure):
        _fields_ = [
            ("buffers", (ctypes.c_uint8 * 256) * 3),
            ("write_idx", ctypes.c_int),
            ("read_idx", ctypes.c_int),
            ("new_idx", ctypes.c_int),
        ]
    
    tb = TripleBuffer()
    lib.triple_buffer_init(ctypes.byref(tb))
    
    # Write data
    data_to_write = (ctypes.c_uint8 * 256)(*[i for i in range(10)])
    write_ok = lib.triple_buffer_write(ctypes.byref(tb), data_to_write, 10)
    assert write_ok is True
    
    # Read data
    data_read = (ctypes.c_uint8 * 256)()
    read_ok = lib.triple_buffer_read(ctypes.byref(tb), data_read, 10)
    assert read_ok is True
    
    # Check values
    for i in range(10):
         assert data_read[i] == i

def test_fdir_sensor_debounce():
    """Verifies FDIR 2.0 speed sensor fault debounce, glitch recovery, and sticky failures."""
    fdir = FDIR_SensorState()
    lib.fdir_sensor_init(ctypes.byref(fdir))
    assert fdir.s1_valid is True
    assert fdir.s2_valid is True
    assert fdir.dual_sensor_failure is False
    
    validated = ctypes.c_double(0.0)
    
    # Step 1: Inject sensor 1 out-of-bounds speed (e.g. -10.0 RPM) for 50 ms (limit is 100 ms) -> no failure committed yet
    for _ in range(5):
        allowed = lib.fdir_sensor_vote_speed(ctypes.byref(fdir), -10.0, 30000.0, 288.15, 1.013, 0.010, ctypes.byref(validated))
        assert allowed is True
        assert fdir.s1_valid is True
        assert fdir.s1_confirmed_failed is False
        
    # Step 2: Allow sensor 1 to recover (glitch recovery) -> resets fault timer
    allowed = lib.fdir_sensor_vote_speed(ctypes.byref(fdir), 30000.0, 30000.0, 288.15, 1.013, 0.010, ctypes.byref(validated))
    assert allowed is True
    assert fdir.s1_fault_timer_sec == 0.0
    
    # Step 3: Inject sustained out-of-bounds speed (-10.0 RPM) for 120 ms (12 steps of 10ms) -> commits sticky failure!
    for _ in range(12):
        allowed = lib.fdir_sensor_vote_speed(ctypes.byref(fdir), -10.0, 30000.0, 288.15, 1.013, 0.010, ctypes.byref(validated))
        
    assert fdir.s1_confirmed_failed is True
    assert fdir.s1_valid is False
    assert allowed is True # Reverted to single sensor 2 valid speed, closed loop still allowed
    
    # Step 4: Try to recover sensor 1 -> should fail because confirmed failures are sticky!
    allowed = lib.fdir_sensor_vote_speed(ctypes.byref(fdir), 30000.0, 30000.0, 288.15, 1.013, 0.010, ctypes.byref(validated))
    assert fdir.s1_confirmed_failed is True
    assert fdir.s1_valid is False
