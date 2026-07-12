"""
AEGIS-TJ1 Parasitic Power Budget — Unit Tests
==============================================

Validates energy balance, power consumer totals, generator capacity scaling,
and safety factor calculations under multiple engine operating modes.

Run with:
    pytest tests/unit/test_power_budget.py -v
"""

import sys
import os
import pytest

# Ensure the power_budget package is importable regardless of CWD
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "simulation", "power_budget"))

from simulation.power_budget.power_budget import (
    generator_output_w, compute_mode_power, full_analysis
)

@pytest.fixture(scope="module")
def analysis_results():
    """Run full analysis and cache results for tests."""
    return full_analysis()

class TestGeneratorScaling:
    @pytest.mark.parametrize("mode", ["Idle", "Takeoff", "Cruise"])
    def test_generator_outputs_positive(self, mode):
        """Verify generator output is positive and scales with shaft speed/power."""
        output = generator_output_w(mode)
        assert output > 0.0, f"Generator output for {mode} is non-positive: {output}"
        
    def test_generator_speed_scaling(self):
        """Verify generator output: Idle < Cruise < Takeoff (corresponding to RPM scaling)."""
        p_idle = generator_output_w("Idle")
        p_cruise = generator_output_w("Cruise")
        p_takeoff = generator_output_w("Takeoff")
        
        assert p_idle < p_cruise, "Generator Idle output should be less than Cruise"
        assert p_cruise < p_takeoff, "Generator Cruise output should be less than Takeoff"

class TestModePowerCalculations:
    @pytest.mark.parametrize("mode", ["Idle", "Takeoff", "Cruise"])
    def test_power_totals_structure(self, mode):
        """Verify mode power calculation dictionary structure and positivity."""
        cont, peak, cat_cont, cat_peak, details = compute_mode_power(mode)
        assert cont > 0
        assert peak > 0
        assert isinstance(cat_cont, dict)
        assert isinstance(cat_peak, dict)
        assert len(details) > 0
        
    @pytest.mark.parametrize("mode", ["Idle", "Takeoff", "Cruise"])
    def test_continuous_less_than_peak(self, mode):
        """Verify continuous power is strictly less than peak power."""
        cont, peak, _, _, _ = compute_mode_power(mode)
        assert cont < peak, (
            f"{mode}: Total continuous {cont}W >= peak {peak}W"
        )

class TestFullAnalysis:
    def test_analysis_verdict(self, analysis_results):
        """Verify full analysis runs and has expected keys for each mode."""
        for mode in ["Idle", "Takeoff", "Cruise"]:
            assert mode in analysis_results
            res = analysis_results[mode]
            assert "generator_w" in res
            assert "cont_total" in res
            assert "peak_total" in res
            assert "margin_cont" in res
            assert "margin_peak" in res
            assert "safety_factor_cont" in res
            assert "safety_factor_peak" in res
            
    def test_safety_factor_math(self, analysis_results):
        """Verify that safety factor equals generator output divided by demand."""
        for mode in ["Idle", "Takeoff", "Cruise"]:
            res = analysis_results[mode]
            gen = res["generator_w"]
            peak = res["peak_total"]
            expected_sf = gen / peak
            assert abs(res["safety_factor_peak"] - expected_sf) < 1e-4, (
                f"{mode}: calculated SF_peak {res['safety_factor_peak']} != expected {expected_sf}"
            )
            
    def test_cruise_failure_verdict(self, analysis_results):
        """Verify that Cruise peak power safety factor is less than 1.0 (fails)."""
        assert analysis_results["Cruise"]["safety_factor_peak"] < 1.0
