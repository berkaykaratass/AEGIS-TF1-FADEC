"""
Unit Tests for Telemetry Verification, Seeding, Immutability and O(1) Seek API
=============================================================================
Verifies structured golden profiles, MAPE scoring, deterministic random seeds,
Strict replay immutability, and O(1) frame seeking index constraints.

Proprietary — AEGIS-TF1 Systems Development Group
"""

import pytest
import json
import os
from fastapi.testclient import TestClient
from simulation.digital_twin.twin_api import app, simulator, GoldenReferenceVerifier

client = TestClient(app)

def test_deterministic_seeding_reproducibility():
    """Verifies that applying the same seed results in identical sensor noise streams."""
    simulator.reset()
    
    # 1. Run first time with Seed A
    simulator.apply_seed(12345)
    simulator.reset()
    simulator.state[0] = 30000.0 * 3.14159 / 30.0 # set N1 speed
    simulator.step_1ms()
    vib_run1 = simulator.sensors.vibration_g
    egt_run1 = simulator.sensors.egt_kelvin
    
    # 2. Run second time with different seed (Seed B) -> should deviate
    simulator.apply_seed(67890)
    simulator.reset()
    simulator.state[0] = 30000.0 * 3.14159 / 30.0
    simulator.step_1ms()
    vib_run2 = simulator.sensors.vibration_g
    
    # 3. Reset seed back to Seed A -> should match run 1 exactly
    simulator.apply_seed(12345)
    simulator.reset()
    simulator.state[0] = 30000.0 * 3.14159 / 30.0
    simulator.step_1ms()
    vib_run3 = simulator.sensors.vibration_g
    egt_run3 = simulator.sensors.egt_kelvin
    
    assert vib_run1 != vib_run2
    assert vib_run1 == vib_run3
    assert egt_run1 == egt_run3

def test_strict_replay_immutability():
    """Verifies that sending command writes is rejected (HTTP 403) when replay mode is active."""
    simulator.reset()
    simulator.replay_mode = True
    
    # Attempt throttle command change
    response = client.post("/api/twin/command", json={"throttle_pla": 50.0, "altitude_ft": 1000.0, "mach": 0.1})
    assert response.status_code == 403
    assert "Replay Mode" in response.json()["detail"]
    
    # Attempt cyber fault injection
    response = client.post("/api/twin/inject-fault", json={"fault_type": "cyber", "enable": True})
    assert response.status_code == 403
    
    # Attempt fault matrix update
    response = client.post("/api/twin/fault-matrix", json={"sensor_stuck": {"n1": 20000.0}})
    assert response.status_code == 403
    
    # Disable replay and verify write is allowed
    simulator.replay_mode = False
    response = client.post("/api/twin/command", json={"throttle_pla": 50.0, "altitude_ft": 1000.0, "mach": 0.1})
    assert response.status_code == 200

def test_o1_replay_seek_indexing():
    """Verifies O(1) seek indexing correctly slices timestamps and clamps boundaries."""
    simulator.reset()
    simulator.replay_mode = True
    
    # Mock replay data: 100 frames (1.0 second duration total)
    mock_frames = []
    for i in range(100):
        mock_frames.append({
            "sim_time": round(i * 0.01, 2),
            "n1_rpm": 15000.0 + i * 100.0,
            "egt": 600.0 + i * 2.0,
            "running": True
        })
    simulator.replay_log = mock_frames
    
    # Seek to 0.45 seconds -> Frame index 45
    response = client.post("/api/twin/replay/seek", json={"seek_time_sec": 0.45})
    assert response.status_code == 200
    assert response.json()["index"] == 45
    assert simulator.replay_index == 45
    assert simulator.t_simulated == 0.45
    assert simulator.latest_telemetry["n1_rpm"] == 15000.0 + 45 * 100.0
    
    # Seek out of bounds (negative time) -> clamp to 0
    response = client.post("/api/twin/replay/seek", json={"seek_time_sec": -2.0})
    assert response.json()["index"] == 0
    
    # Seek out of bounds (high time) -> clamp to 99
    response = client.post("/api/twin/replay/seek", json={"seek_time_sec": 10.0})
    assert response.json()["index"] == 99

def test_golden_reference_validation_engine():
    """Verifies that the verifier correctly calculates MAPE regression scores and checks event bounds."""
    # Setup baseline golden reference profile
    profile = {
        "scenario": "Nominal Climb",
        "signals": {
            "n1_rpm": {"tol_pct": 0.3},
            "egt": {"tol_abs": 2.0}
        },
        "events": [
            {"time": 2.0, "type": "THROTTLE_CHANGE"}
        ]
    }
    
    golden_log = [
        {"sim_time": 0.0, "n1_rpm": 20000.0, "egt": 600.0},
        {"sim_time": 1.0, "n1_rpm": 22000.0, "egt": 650.0},
        {"sim_time": 2.0, "n1_rpm": 25000.0, "egt": 700.0}
    ]
    
    # 1. Test nominal run matching baseline exactly
    run_log_exact = {
        "metadata": {"scenario": "Nominal Climb"},
        "events": [{"time": 2.0, "type": "THROTTLE_CHANGE"}],
        "telemetry": golden_log
    }
    report = GoldenReferenceVerifier.validate(run_log_exact, golden_log, profile)
    assert report["verdict"] == "PASS"
    assert report["overall_score_pct"] == 100.0
    assert report["signals"]["n1_rpm"]["score_pct"] == 100.0
    assert report["signals"]["egt"]["verdict"] == "PASS"
    assert report["events_status"] == "1/1 PASS"
    
    # 2. Test deviant run exceeding tolerance limits
    deviant_log = [
        {"sim_time": 0.0, "n1_rpm": 20000.0, "egt": 600.0},
        {"sim_time": 1.0, "n1_rpm": 22000.0, "egt": 650.0},
        {"sim_time": 2.0, "n1_rpm": 25000.0, "egt": 705.0} # EGT error is 5.0 K (tolerance is 2.0 K)
    ]
    run_log_deviant = {
        "metadata": {"scenario": "Nominal Climb"},
        "events": [{"time": 2.0, "type": "THROTTLE_CHANGE"}],
        "telemetry": deviant_log
    }
    report_deviant = GoldenReferenceVerifier.validate(run_log_deviant, golden_log, profile)
    assert report_deviant["signals"]["egt"]["verdict"] == "FAIL"
    assert report_deviant["signals"]["egt"]["max_error"] == 5.0
    assert report_deviant["verdict"] == "FAIL" # overall fails due to EGT breach
