"""
AEGIS-TJ1 Performance Deck — Unit Tests
========================================

Validates physical plausibility of the three operating modes
(Idle, Takeoff, Cruise) produced by `performance_deck.py`.

Run with:
    pytest tests/unit/test_performance_deck.py -v
"""

import sys
import os
import pytest

# Ensure the thermodynamic package is importable regardless of CWD
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "simulation", "thermodynamic"))

from simulation.thermodynamic.performance_deck import run_performance_deck


# ── Fixture: run the deck once for all tests ─────────────────────────
@pytest.fixture(scope="module")
def results():
    """Run the performance deck and cache results for the module."""
    return run_performance_deck()


# ═══════════════════════════════════════════════════════════════════════
#  1. Takeoff specific thrust > 500 N·s/kg
# ═══════════════════════════════════════════════════════════════════════
class TestTakeoffThrust:
    def test_specific_thrust_above_500(self, results):
        """Takeoff F_specific should exceed 500 N·s/kg for a turbojet
        with OPR 12 and T4 = 1600 K at SLS conditions."""
        F_sp = results["Takeoff"]["F_specific"]
        assert F_sp > 500.0, (
            f"Takeoff F_specific = {F_sp:.2f} N·s/kg, expected > 500"
        )


# ═══════════════════════════════════════════════════════════════════════
#  2. All efficiencies between 0 and 1
# ═══════════════════════════════════════════════════════════════════════
class TestEfficiencyBounds:
    @pytest.mark.parametrize("mode", ["Idle", "Takeoff", "Cruise"])
    def test_thermal_efficiency_bounds(self, results, mode):
        eta = results[mode]["eta_thermal"]
        assert 0.0 < eta < 1.0, (
            f"{mode} η_thermal = {eta:.4f}, out of (0, 1)"
        )

    @pytest.mark.parametrize("mode", ["Idle", "Takeoff", "Cruise"])
    def test_propulsive_efficiency_bounds(self, results, mode):
        eta = results[mode]["eta_propulsive"]
        # Propulsive efficiency is 0 for static (V_0=0) cases — allow >= 0
        assert 0.0 <= eta <= 1.0, (
            f"{mode} η_propulsive = {eta:.4f}, out of [0, 1]"
        )

    @pytest.mark.parametrize("mode", ["Idle", "Takeoff", "Cruise"])
    def test_overall_efficiency_bounds(self, results, mode):
        eta = results[mode]["eta_overall"]
        assert 0.0 <= eta <= 1.0, (
            f"{mode} η_overall = {eta:.4f}, out of [0, 1]"
        )


# ═══════════════════════════════════════════════════════════════════════
#  3. Cruise T3 < T4
# ═══════════════════════════════════════════════════════════════════════
class TestCruiseTemperatureOrder:
    def test_T3_less_than_T4(self, results):
        """Compressor exit temperature must be below turbine inlet
        temperature — otherwise there is nothing for the combustor
        to add."""
        T_t = results["Cruise"]["T_t"]
        T3, T4 = T_t[2], T_t[3]
        assert T3 < T4, (
            f"Cruise T3 = {T3:.1f} K >= T4 = {T4:.1f} K — unphysical"
        )


# ═══════════════════════════════════════════════════════════════════════
#  4. Idle thrust < Takeoff thrust
# ═══════════════════════════════════════════════════════════════════════
class TestCrossModeThrust:
    def test_idle_lower_than_takeoff(self, results):
        """Idle gross thrust must be strictly less than Takeoff."""
        F_idle = results["Idle"]["F_gross"]
        F_to = results["Takeoff"]["F_gross"]
        assert F_idle < F_to, (
            f"Idle F_gross = {F_idle:.1f} N >= Takeoff = {F_to:.1f} N"
        )

    def test_idle_specific_thrust_lower(self, results):
        """Even on a per-unit-mass basis, idle should produce less
        specific thrust than takeoff."""
        assert results["Idle"]["F_specific"] < results["Takeoff"]["F_specific"]


# ═══════════════════════════════════════════════════════════════════════
#  5. Monotonically increasing temperatures through compression
# ═══════════════════════════════════════════════════════════════════════
class TestCompressionMonotonicity:
    @pytest.mark.parametrize("mode", ["Idle", "Takeoff", "Cruise"])
    def test_temperature_increases_through_compression(self, results, mode):
        """T at station 0 <= T at station 2 <= T at station 3.
        (Station 2 equals station 0 for M=0 cases, so allow <=.)"""
        T_t = results[mode]["T_t"]
        T0, T2, T3 = T_t[0], T_t[1], T_t[2]
        assert T0 <= T2, (
            f"{mode}: T0={T0:.1f} > T2={T2:.1f} — diffuser should not cool"
        )
        assert T2 < T3, (
            f"{mode}: T2={T2:.1f} >= T3={T3:.1f} — compressor must raise temperature"
        )

    @pytest.mark.parametrize("mode", ["Idle", "Takeoff", "Cruise"])
    def test_pressure_increases_through_compression(self, results, mode):
        """P at station 0 <= P at station 2 <= P at station 3."""
        P_t = results[mode]["P_t"]
        P0, P2, P3 = P_t[0], P_t[1], P_t[2]
        assert P0 <= P2, f"{mode}: P0={P0:.0f} > P2={P2:.0f}"
        assert P2 < P3, f"{mode}: P2={P2:.0f} >= P3={P3:.0f}"
