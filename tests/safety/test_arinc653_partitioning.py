#!/usr/bin/env python3
"""
ARINC-653 Spatial & Temporal Partitioning Verification Suite
===========================================================

Validates the formal partition boundaries, memory zone isolation (Virtual MPU),
Health Monitor decision latency limits, and Byzantine lockout policies.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import os
import ctypes
import pytest

# Load FADEC C++ library
LIB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../libfadec.dylib"))
lib = ctypes.CDLL(LIB_PATH)

# ctypes structures matching rtos_tasks.h
class HM_Status(ctypes.Structure):
    _fields_ = [
        ("last_error", ctypes.c_int),
        ("last_faulty_partition", ctypes.c_uint32),
        ("alarm_triggered", ctypes.c_uint32),
        ("recovery_duration_us", ctypes.c_uint64)
    ]

# Mapped functions
lib.rtos_arinc_init.restype = ctypes.c_int
lib.rtos_arinc_configure_partition.argtypes = [ctypes.c_int, ctypes.c_uint64, ctypes.c_uint64]
lib.rtos_arinc_configure_partition.restype = ctypes.c_int
lib.rtos_arinc_create_task.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
lib.rtos_arinc_create_task.restype = ctypes.c_int
lib.rtos_arinc_verify_feasibility.restype = ctypes.c_bool
lib.rtos_arinc_run_tick.argtypes = [ctypes.c_uint64]
lib.rtos_arinc_run_tick.restype = ctypes.c_int
lib.rtos_arinc_write_memory.argtypes = [ctypes.c_int, ctypes.c_uint32, ctypes.c_uint32]
lib.rtos_arinc_write_memory.restype = ctypes.c_int
lib.rtos_arinc_get_partition_state.argtypes = [ctypes.c_int]
lib.rtos_arinc_get_partition_state.restype = ctypes.c_int
lib.rtos_arinc_get_hm_status.argtypes = [ctypes.POINTER(HM_Status)]

# Dummy task functions
@ctypes.CFUNCTYPE(None)
def dummy_fadec_task():
    pass

@ctypes.CFUNCTYPE(None)
def dummy_ai_task():
    pass

def test_arinc_schedule_feasibility():
    """Verify that schedule feasibility analysis detects overflows and overlaps."""
    lib.rtos_arinc_init()
    
    # Configure valid, non-overlapping partition windows
    lib.rtos_arinc_configure_partition(0, 0, 400)    # PARTITION_FADEC_CORE (0-400 us)
    lib.rtos_arinc_configure_partition(1, 400, 200)  # PARTITION_SAFETY_KERNEL (400-600 us)
    lib.rtos_arinc_configure_partition(2, 600, 200)  # PARTITION_AI_ADVISORY (600-800 us)
    lib.rtos_arinc_configure_partition(3, 800, 200)  # PARTITION_TEST_GROUND (800-1000 us)

    # Register tasks matching partition budgets
    lib.rtos_arinc_create_task(0, 0, 1000, 250, dummy_fadec_task) # FADEC task (250 us < 400 us slot)
    lib.rtos_arinc_create_task(1, 2, 1000, 150, dummy_ai_task)    # AI task (150 us < 200 us slot)

    assert lib.rtos_arinc_verify_feasibility() is True

    # Test failure: Overloading partition budget
    lib.rtos_arinc_create_task(2, 2, 1000, 300, dummy_ai_task) # AI total WCET = 150 + 300 = 450 us (> 200 us slot)
    assert lib.rtos_arinc_verify_feasibility() is False

def test_arinc_temporal_isolation_preemption():
    """Verify that task budget overrun triggers Health Monitor preemption and AI lockout."""
    lib.rtos_arinc_init()
    
    lib.rtos_arinc_configure_partition(0, 0, 400)    # FADEC
    lib.rtos_arinc_configure_partition(2, 600, 200)  # AI

    # Register FADEC task (normal) and AI task (budget overrun)
    lib.rtos_arinc_create_task(0, 0, 1000, 100, dummy_fadec_task)
    lib.rtos_arinc_create_task(1, 2, 1000, 500, dummy_ai_task) # 500 us WCET exceeds 200 us slot

    # Tick inside FADEC slot (0 to 400) -> should run FADEC task
    # Step scheduler by 100 us
    executed = lib.rtos_arinc_run_tick(100)
    assert executed == 1

    # Shift scheduler time to AI slot (at 600 us)
    for _ in range(5):
        lib.rtos_arinc_run_tick(100)

    # Tick inside AI slot -> should trigger budget overflow and lock out AI
    lib.rtos_arinc_run_tick(100)

    # Assert AI partition state is locked out
    ai_state = lib.rtos_arinc_get_partition_state(2)
    assert ai_state == 2  # PARTITION_STATE_LOCKED_OUT

    # Assert HM status caught the budget overflow
    hm = HM_Status()
    lib.rtos_arinc_get_hm_status(ctypes.byref(hm))
    assert hm.last_error == 0  # HM_ERROR_BUDGET_EXCEEDED
    assert hm.last_faulty_partition == 2

def test_arinc_spatial_isolation_mpu():
    """Verify that MPU page rules block unauthorized writes and trap violations."""
    lib.rtos_arinc_init()

    # Allowed: FADEC writing to control memory zone
    assert lib.rtos_arinc_write_memory(0, 0x00015000, 0xABC) == 0

    # Denied: AI attempting to write to FADEC control memory zone
    assert lib.rtos_arinc_write_memory(2, 0x00015000, 0xABC) == -1

    # Denied: Test partition attempting to write to Safety memory zone
    assert lib.rtos_arinc_write_memory(3, 0x00055000, 0xABC) == -1

    # Assert MPU violation was captured by HM
    hm = HM_Status()
    lib.rtos_arinc_get_hm_status(ctypes.byref(hm))
    assert hm.last_error == 1  # HM_ERROR_MPU_VIOLATION
    assert hm.last_faulty_partition == 3

def test_arinc_byzantine_fault_lockout_latency():
    """Verify that Health Monitor executes recovery actions inside the same minor frame (Reaction latency <= 1 MIF)."""
    lib.rtos_arinc_init()
    lib.rtos_arinc_configure_partition(3, 800, 200) # Test ground partition

    # Trigger MPU violation
    lib.rtos_arinc_write_memory(3, 0x00015000, 0xABC)

    # Check partition state is locked out instantly
    test_state = lib.rtos_arinc_get_partition_state(3)
    assert test_state == 2  # PARTITION_STATE_LOCKED_OUT

    # Check recovery duration is 0 (immediate resolution within the same execution frame)
    hm = HM_Status()
    lib.rtos_arinc_get_hm_status(ctypes.byref(hm))
    assert hm.recovery_duration_us <= 1000  # <= 1 MIF (1 ms)
