"""
DO-178C Software Safety Coverage Tests
"""

import pytest
from ai.models.flight_envelope import FlightEnvelope

def test_flight_envelope_boundary_safety():
    envelope = FlightEnvelope()

    # 1. Test extreme boundary conditions
    # Standard sea level: safe
    is_safe, details = envelope.check_envelope(altitude_ft=0.0, mach=0.0)
    assert is_safe

    # Extremely high altitude: unsafe
    is_safe, details = envelope.check_envelope(altitude_ft=65000.0, mach=0.0)
    assert not is_safe
    assert "Altitude" in details

    # Super-sonic speeds beyond structural limits: unsafe
    is_safe, details = envelope.check_envelope(altitude_ft=10000.0, mach=3.5)
    assert not is_safe
    assert "Mach" in details or "pressure" in details

def test_envelope_limit_derating():
    envelope = FlightEnvelope()

    # Check derating at extreme ram air temperatures (high Mach)
    limits_sl = envelope.get_limits(altitude_ft=0.0, mach=0.0)
    limits_mach = envelope.get_limits(altitude_ft=0.0, mach=1.8)

    # High Mach speeds must trigger a derating of max rotor speed and lower EGT limit
    assert limits_mach["max_n1_speed_pct"] < limits_sl["max_n1_speed_pct"]
    assert limits_mach["max_egt_kelvin"] < limits_sl["max_egt_kelvin"]
