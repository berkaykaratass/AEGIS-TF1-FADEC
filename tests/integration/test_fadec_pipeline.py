"""
FADEC Integration Pipeline Tests
"""

import pytest
from simulation.digital_twin.twin_engine import DigitalTwinEngine
from simulation.digital_twin.telemetry_ingester import TelemetryIngester

def test_closed_loop_twin_pipeline():
    # Initialize components
    twin = DigitalTwinEngine(dt=0.02)
    ingester = TelemetryIngester(buffer_size=100)

    # Simulate 5 steps of engine throttle increase
    for i in range(5):
        inputs = [0.005, 0.0, 15.0]  # [fuel_flow_cmd, EHD_voltage, vane_angle]
        
        # 1. Propagate digital twin state
        twin.predict(inputs)
        state = twin.get_state()
        
        assert state["n1_rpm"] > 0
        assert state["egt"] > 0
        
        # 2. Ingest telemetry frame
        frame = {
            "n1_rpm": state["n1_rpm"],
            "egt_kelvin": state["egt"],
            "p3_bar": state["p3_bar"],
            "p2_bar": 1.013,
            "t2_kelvin": 288.15,
            "vibration_g": 0.8,
            "fuel_flow_kgs": 0.005,
            "ehd_voltage_kv": 0.0,
            "timestamp": float(i) * 0.02
        }
        
        is_valid, faults = ingester.ingest_frame(frame)
        assert is_valid
        assert len(faults) == 0

    # Verify statistical tracking
    stats = ingester.calculate_rolling_statistics(window_size=5)
    assert "n1_rpm" in stats
    assert stats["n1_rpm"]["mean"] > 1000.0
