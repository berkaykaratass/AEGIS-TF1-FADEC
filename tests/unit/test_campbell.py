"""
AEGIS-TJ1 Campbell Diagram — Unit Tests
========================================

Validates the correctness of the Finite Element rotor dynamics model,
matrix assemblies, eigenvalue solver, and critical speed identification.

Run with:
    pytest tests/unit/test_campbell.py -v
"""

import sys
import os
import pytest
import numpy as np

# Ensure the rotor_dynamics package is importable regardless of CWD
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "simulation", "rotor_dynamics"))

from simulation.rotor_dynamics.campbell_diagram import (
    Material, ShaftSection, Disk, Bearing, RotorFEM, find_critical_speeds
)

@pytest.fixture(scope="module")
def sample_rotor():
    # Construct standard AEGIS-TJ1 rotor model as defined in campbell_diagram.py
    mat = Material("Inconel 718", E=205e9, rho=8190, nu=0.29)
    shaft = ShaftSection(D_outer=0.035, D_inner=0.025)
    
    # 20 elements
    model = RotorFEM(
        shaft_length=0.540,
        x_start=-0.065,
        material=mat,
        section=shaft,
        n_elements=20,
        disks=[Disk("Fan/Compressor", x_pos=0.060, mass=4.5, Ip=0.025, Id=0.013),
               Disk("Turbine", x_pos=0.300, mass=3.8, Ip=0.018, Id=0.010)],
        bearings=[Bearing("Front Ball Brg", x_pos=-0.065, kxx=5e7, kyy=5e7, cxx=500, cyy=500),
                  Bearing("Rear Roller Brg", x_pos=0.385, kxx=8e7, kyy=8e7, cxx=800, cyy=800)]
    )
    return model

class TestRotorAssembly:
    def test_matrix_dimensions(self, sample_rotor):
        """Verify assembled global matrices are square and size corresponds to 84 DOFs (21 nodes * 4 DOFs/node)."""
        n_dof = 84
        assert sample_rotor.M_global.shape == (n_dof, n_dof), "Mass matrix M_global has incorrect shape"
        assert sample_rotor.K_global.shape == (n_dof, n_dof), "Stiffness matrix K_global has incorrect shape"
        assert sample_rotor.G_global.shape == (n_dof, n_dof), "Gyroscopic matrix G_global has incorrect shape"
        
    def test_symmetry(self, sample_rotor):
        """Verify mass and stiffness matrices are symmetric, and gyroscopic matrix is skew-symmetric."""
        M = sample_rotor.M_global
        K = sample_rotor.K_global
        G = sample_rotor.G_global
        
        # Check symmetry
        np.testing.assert_allclose(M, M.T, atol=1e-7, err_msg="M_global matrix is not symmetric")
        np.testing.assert_allclose(K, K.T, atol=1e-7, err_msg="K_global matrix is not symmetric")
        
        # Check skew-symmetry for G
        np.testing.assert_allclose(G, -G.T, atol=1e-7, err_msg="G_global matrix is not skew-symmetric")

class TestEigenvalueSolver:
    def test_frequencies_at_zero_rpm(self, sample_rotor):
        """Verify that natural frequencies at 0 RPM are positive, real, and forward/backward modes are degenerate (equal)."""
        eigvals, _ = sample_rotor.solve_eigenvalues(0.0)
        freqs, zetas, _ = sample_rotor.extract_natural_frequencies(eigvals, n_modes=6)
        
        # Frequencies should be sorted, let's look at the first 10 frequencies (which occur in pairs of equal values for symmetric rotor)
        assert len(freqs) > 0
        assert np.all(freqs >= 0.0)
        
        # At 0 RPM, FW and BW should be degenerate (first two modes should be equal)
        np.testing.assert_allclose(freqs[0], freqs[1], rtol=1e-3)
        np.testing.assert_allclose(freqs[2], freqs[3], rtol=1e-3)

    def test_gyroscopic_split(self, sample_rotor):
        """Verify that at high spin speeds, gyroscopic effects split the degenerate natural frequencies into forward (higher) and backward (lower) whirl modes."""
        # 35,000 RPM (design speed)
        omega_spin = 35000 * 2.0 * np.pi / 60.0
        eigvals, _ = sample_rotor.solve_eigenvalues(omega_spin)
        freqs, zetas, _ = sample_rotor.extract_natural_frequencies(eigvals, n_modes=6)
        
        # The degeneracy should be broken (freqs[0] != freqs[1])
        # In sorted list, they are not necessarily sorted by paired mode but by magnitude of frequency
        # For split modes, one frequency increases (FW) and one decreases (BW)
        # So they won't be equal anymore
        assert abs(freqs[1] - freqs[0]) > 1.0, f"No gyroscopic splitting detected: {freqs[0]} vs {freqs[1]}"

class TestCriticalSpeeds:
    def test_find_critical_speeds(self):
        """Test critical speed interpolation with mock data."""
        rpm_range = np.array([0, 10000, 20000, 30000, 40000])
        # A mock mode frequency that starts at 150 Hz and increases to 250 Hz due to gyros
        mode_freqs = np.array([150.0, 175.0, 200.0, 225.0, 250.0])
        
        # Synchronous 1x line is RPM / 60.0 Hz
        # At 0 RPM: sync=0, mode=150
        # At 12000 RPM: sync=200, mode=180
        # Intersection occurs where mode_freq = RPM / 60
        classified = {"FW1": mode_freqs}
        
        criticals = find_critical_speeds(rpm_range, classified, sync_order=1.0)
        
        assert len(criticals) == 1
        crit = criticals[0]
        assert crit["mode"] == "FW1"
        assert 10000 < crit["rpm"] < 20000
        np.testing.assert_allclose(crit["freq_hz"], crit["rpm"] / 60.0, rtol=1e-4)
