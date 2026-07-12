#!/usr/bin/env python3
"""
AEGIS-TJ1 Campbell Diagram — Rotor Critical Speed Analysis
===========================================================

Finite Element rotor dynamics modal analysis using Timoshenko beam elements
with gyroscopic coupling. Generates a Campbell diagram showing natural
frequency variation with rotor speed and identifies critical speeds.

Engine:  AEGIS-TJ1 Single-Spool Turbojet
Author:  Rotor Dynamics Analysis Module
Units:   SI throughout (m, kg, s, N, Pa, rad)

Reference Frames:
    X — axial (along shaft), Y/Z — lateral (transverse)
    Each node DOF: [y, θ_z, z, θ_y]  (two lateral translations + two rotations)

Method:
    1. Timoshenko beam FEM discretisation (20 elements)
    2. Lumped disk masses with polar & diametral inertia
    3. Bearing stiffness & damping at support nodes
    4. State-space eigenvalue problem at each spin speed Ω
    5. Eigenvalue tracking and mode sorting across speed range
"""

import os
import sys
import numpy as np
from scipy import linalg
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for headless runs
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES — Physical parameters
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Material:
    """Shaft material properties."""
    name: str
    E: float          # Young's modulus [Pa]
    rho: float        # Density [kg/m³]
    nu: float         # Poisson's ratio [-]

    @property
    def G(self) -> float:
        """Shear modulus [Pa]."""
        return self.E / (2.0 * (1.0 + self.nu))


@dataclass
class ShaftSection:
    """Hollow shaft cross-section geometry."""
    D_outer: float    # Outer diameter [m]
    D_inner: float    # Inner diameter [m]

    @property
    def A(self) -> float:
        """Cross-section area [m²]."""
        return np.pi / 4.0 * (self.D_outer**2 - self.D_inner**2)

    @property
    def I(self) -> float:
        """Second moment of area [m⁴]."""
        return np.pi / 64.0 * (self.D_outer**4 - self.D_inner**4)

    @property
    def Ip(self) -> float:
        """Polar second moment of area [m⁴]."""
        return 2.0 * self.I

    @property
    def kappa(self) -> float:
        """Timoshenko shear correction factor for hollow circular section."""
        r = self.D_inner / self.D_outer
        # Cowper (1966) formula for hollow circular cross-section
        nu = 0.29  # approximate
        return (6.0 * (1.0 + nu) * (1.0 + r**2)**2) / (
            (7.0 + 6.0 * nu) * (1.0 + r**2)**2 + (20.0 + 12.0 * nu) * r**2
        )


@dataclass
class Disk:
    """Rigid disk (lumped mass) attached to the shaft."""
    name: str
    x_pos: float      # Axial position [m]
    mass: float        # Mass [kg]
    Ip: float          # Polar moment of inertia [kg·m²]
    Id: float          # Diametral moment of inertia [kg·m²]
    node: int = -1     # Assigned FE node index (set during meshing)
    spool: str = "LP"  # "LP" or "HP"


@dataclass
class Bearing:
    """Isotropic bearing support."""
    name: str
    x_pos: float       # Axial position [m]
    kxx: float          # Direct stiffness in y [N/m]
    kyy: float          # Direct stiffness in z [N/m]
    cxx: float          # Direct damping in y [N·s/m]
    cyy: float          # Direct damping in z [N·s/m]
    node: int = -1      # Assigned FE node index (set during meshing)
    spool: str = "LP"   # "LP", "HP", or "IS" (inter-shaft)
    lp_node: int = -1   # for inter-shaft bearing
    hp_node: int = -1   # for inter-shaft bearing


# ═══════════════════════════════════════════════════════════════════════════════
# TIMOSHENKO BEAM ELEMENT MATRICES
# ═══════════════════════════════════════════════════════════════════════════════

def timoshenko_element_matrices(
    L: float, E: float, G_mod: float, rho: float,
    A: float, I_sec: float, Ip: float, kappa: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute 8×8 element mass, stiffness, and gyroscopic matrices for a
    Timoshenko beam element with 4 DOF per node: [y, θ_z, z, θ_y].

    The element is formulated in a single transverse plane and then
    assembled for two orthogonal planes with gyroscopic coupling.

    Parameters
    ----------
    L : float
        Element length [m].
    E : float
        Young's modulus [Pa].
    G_mod : float
        Shear modulus [Pa].
    rho : float
        Material density [kg/m³].
    A : float
        Cross-section area [m²].
    I_sec : float
        Second moment of area [m⁴].
    Ip : float
        Polar second moment of area [m⁴].
    kappa : float
        Timoshenko shear correction factor [-].

    Returns
    -------
    M_e : ndarray (8, 8)
        Element mass matrix (translational + rotary inertia).
    K_e : ndarray (8, 8)
        Element stiffness matrix.
    G_e : ndarray (8, 8)
        Element gyroscopic matrix (skew-symmetric).
    """
    # Shear deformation parameter
    phi = 12.0 * E * I_sec / (kappa * G_mod * A * L**2)

    denom = (1.0 + phi)**2

    # ─── Single-plane stiffness (4×4) ──────────────────────────────────
    coeff_k = E * I_sec / ((1.0 + phi) * L**3)
    K_plane = coeff_k * np.array([
        [ 12.0,       6.0*L,      -12.0,       6.0*L     ],
        [  6.0*L,    (4.0+phi)*L**2, -6.0*L, (2.0-phi)*L**2],
        [-12.0,      -6.0*L,       12.0,      -6.0*L     ],
        [  6.0*L,   (2.0-phi)*L**2, -6.0*L, (4.0+phi)*L**2],
    ])

    # ─── Single-plane consistent mass (4×4) ─────────────────────────
    # Translational mass
    coeff_mt = rho * A * L / (840.0 * denom)
    Mt_plane = coeff_mt * np.array([
        [312.0 + 588.0*phi + 280.0*phi**2,
         (44.0 + 77.0*phi + 35.0*phi**2)*L,
         108.0 + 252.0*phi + 140.0*phi**2,
         -(26.0 + 63.0*phi + 35.0*phi**2)*L],

        [(44.0 + 77.0*phi + 35.0*phi**2)*L,
         (8.0 + 14.0*phi + 7.0*phi**2)*L**2,
         (26.0 + 63.0*phi + 35.0*phi**2)*L,
         -(6.0 + 14.0*phi + 7.0*phi**2)*L**2],

        [108.0 + 252.0*phi + 140.0*phi**2,
         (26.0 + 63.0*phi + 35.0*phi**2)*L,
         312.0 + 588.0*phi + 280.0*phi**2,
         -(44.0 + 77.0*phi + 35.0*phi**2)*L],

        [-(26.0 + 63.0*phi + 35.0*phi**2)*L,
         -(6.0 + 14.0*phi + 7.0*phi**2)*L**2,
         -(44.0 + 77.0*phi + 35.0*phi**2)*L,
         (8.0 + 14.0*phi + 7.0*phi**2)*L**2],
    ])

    # Rotary inertia mass
    coeff_mr = rho * I_sec / (30.0 * L * denom)
    Mr_plane = coeff_mr * np.array([
        [ 36.0,          (3.0 - 15.0*phi)*L,  -36.0,          (3.0 - 15.0*phi)*L ],
        [(3.0 - 15.0*phi)*L, (4.0 + 5.0*phi + 10.0*phi**2)*L**2,
         -(3.0 - 15.0*phi)*L, (-1.0 - 5.0*phi + 5.0*phi**2)*L**2],
        [-36.0,         -(3.0 - 15.0*phi)*L,   36.0,         -(3.0 - 15.0*phi)*L ],
        [(3.0 - 15.0*phi)*L, (-1.0 - 5.0*phi + 5.0*phi**2)*L**2,
         -(3.0 - 15.0*phi)*L, (4.0 + 5.0*phi + 10.0*phi**2)*L**2],
    ])

    M_plane = Mt_plane + Mr_plane

    # ─── Single-plane gyroscopic (4×4, skew-symmetric part) ─────────
    # Gyroscopic matrix from rotary inertia of spinning shaft
    coeff_g = rho * Ip / (30.0 * L * denom)
    G_plane = coeff_g * np.array([
        [  0.0,         -36.0,           0.0,         (3.0 - 15.0*phi)*L ],
        [ 36.0,           0.0,         -(3.0 - 15.0*phi)*L, 0.0        ],
        [  0.0,          (3.0 - 15.0*phi)*L, 0.0,          -36.0       ],
        [-(3.0 - 15.0*phi)*L, 0.0,          36.0,           0.0        ],
    ])

    # Wait — let me redo this more carefully. For the coupled 2-plane problem
    # with DOF ordering [y1, θz1, z1, θy1, y2, θz2, z2, θy2] we need to
    # assemble the full 8×8 matrices properly.

    # DOF ordering per node: [y, θ_z, z, θ_y]
    # Node 1: indices 0,1,2,3
    # Node 2: indices 4,5,6,7

    # The y-plane (y, θ_z) uses indices [0,1,4,5]
    # The z-plane (z, θ_y) uses indices [2,3,6,7]  (note sign conventions)

    # ─── Assemble full 8×8 stiffness ───────────────────────────────────
    K_e = np.zeros((8, 8))
    # y-plane DOFs: [y1, θz1, y2, θz2] -> global [0,1,4,5]
    idx_y = [0, 1, 4, 5]
    # z-plane DOFs: [z1, θy1, z2, θy2] -> global [2,3,6,7]
    idx_z = [2, 3, 6, 7]

    # For z-plane, the sign of θ_y couples differently. The stiffness in
    # the z-plane has identical structure but with sign changes on the
    # rotation-translation coupling terms due to the right-hand rule.
    # However for an axi-symmetric shaft, K is identical in both planes
    # if we use the convention z, -θ_y (or equivalently z, θ_y with
    # appropriate sign adjustments in G).

    # We'll use: z-plane stiffness = K_plane but with θ sign flip
    # Actually for symmetric sections, K_z = K_y in terms of matrix structure.
    # The sign changes appear in the gyroscopic coupling.

    K_z = K_plane.copy()
    # Sign change for θ_y coupling (right-hand rule): z-θ_y has opposite
    # sign convention compared to y-θ_z.
    # K_z row/col sign flips for rotation DOFs:
    # Actually, using the formulation where DOF = [y, θ_z, z, θ_y],
    # the z-plane stiffness relating (z, θ_y) has the SAME form as
    # (y, θ_z) because the bending equations are symmetric.
    # The difference only appears in the gyroscopic matrix.

    for i_loc, i_glob in enumerate(idx_y):
        for j_loc, j_glob in enumerate(idx_y):
            K_e[i_glob, j_glob] += K_plane[i_loc, j_loc]

    for i_loc, i_glob in enumerate(idx_z):
        for j_loc, j_glob in enumerate(idx_z):
            K_e[i_glob, j_glob] += K_plane[i_loc, j_loc]

    # ─── Assemble full 8×8 mass ────────────────────────────────────────
    M_e = np.zeros((8, 8))

    for i_loc, i_glob in enumerate(idx_y):
        for j_loc, j_glob in enumerate(idx_y):
            M_e[i_glob, j_glob] += M_plane[i_loc, j_loc]

    for i_loc, i_glob in enumerate(idx_z):
        for j_loc, j_glob in enumerate(idx_z):
            M_e[i_glob, j_glob] += M_plane[i_loc, j_loc]

    # ─── Assemble full 8×8 gyroscopic ──────────────────────────────────
    # The gyroscopic matrix couples y-plane and z-plane.
    # For DOF [y, θ_z, z, θ_y], the gyroscopic matrix has the form:
    #   G_full = Ω * [ [0, G_yz], [-G_yz^T, 0] ]
    # where G_yz is the coupling between planes.
    #
    # Standard formulation (Nelson, 1980):
    # G couples (y, θz) with (z, θy) and vice versa.
    # The gyroscopic terms arise from Coriolis effects of spinning shaft.

    G_e = np.zeros((8, 8))

    # Gyroscopic coupling: the skew-symmetric matrix couples y-z planes
    # Using consistent gyroscopic matrix from Timoshenko beam:
    coeff_gyro = 2.0 * rho * Ip / (30.0 * L * denom)

    # Sub-matrix for gyroscopic coupling (relates y-DOFs to z-DOFs)
    G_sub = coeff_gyro * np.array([
        [ 0.0,           -36.0,           0.0,        -(3.0 - 15.0*phi)*L],
        [ 36.0,            0.0,          (3.0 - 15.0*phi)*L, 0.0],
        [ 0.0,           (3.0 - 15.0*phi)*L, 0.0,          -36.0],
        [-(3.0 - 15.0*phi)*L, 0.0,           36.0,           0.0],
    ])

    # Place gyroscopic coupling: y-DOFs ↔ z-DOFs
    # G[y_dofs, z_dofs] = G_sub
    # G[z_dofs, y_dofs] = -G_sub^T  (skew symmetry)
    for i_loc, i_glob in enumerate(idx_y):
        for j_loc, j_glob in enumerate(idx_z):
            G_e[i_glob, j_glob] += G_sub[i_loc, j_loc]
            G_e[j_glob, i_glob] -= G_sub[i_loc, j_loc]

    return M_e, K_e, G_e


# ═══════════════════════════════════════════════════════════════════════════════
# ROTOR SYSTEM ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════════

class RotorFEM:
    """
    Finite Element rotor dynamics model.

    Assembles global matrices for a single-shaft rotor with disks and
    bearings, then solves the damped gyroscopic eigenvalue problem across
    a range of spin speeds.
    """

    def __init__(
        self,
        shaft_length: float,
        x_start: float,
        material: Material,
        section: ShaftSection,
        n_elements: int,
        disks: List[Disk],
        bearings: List[Bearing],
        is_dual_spool: bool = False,
        lp_section: Optional[ShaftSection] = None,
        hp_section: Optional[ShaftSection] = None,
        hp_shaft_length: float = 0.200,
        hp_x_start: float = 0.080,
        n_elements_hp: Optional[int] = None,
    ):
        self.L_total = shaft_length
        self.x_start = x_start
        self.material = material
        self.section = section
        self.is_dual_spool = is_dual_spool
        
        self.n_elem_lp = n_elements
        self.n_nodes_lp = n_elements + 1
        self.node_x_lp = np.linspace(x_start, x_start + shaft_length, self.n_nodes_lp)
        self.elem_L_lp = shaft_length / n_elements
        
        self.dof_per_node = 4  # [y, θ_z, z, θ_y]
        
        if is_dual_spool:
            self.lp_section = lp_section if lp_section is not None else section
            self.hp_section = hp_section if hp_section is not None else ShaftSection(D_outer=0.050, D_inner=0.038)
            self.n_elem_hp = n_elements_hp if n_elements_hp is not None else n_elements
            self.n_nodes_hp = self.n_elem_hp + 1
            self.node_x_hp = np.linspace(hp_x_start, hp_x_start + hp_shaft_length, self.n_nodes_hp)
            self.elem_L_hp = hp_shaft_length / self.n_elem_hp
            self.n_nodes = self.n_nodes_lp + self.n_nodes_hp
        else:
            self.n_nodes = self.n_nodes_lp
            
        self.n_dof = self.n_nodes * self.dof_per_node
        self.disks = disks
        self.bearings = bearings

        # Assign disks and bearings to nearest nodes
        self._assign_nodes()

        # Assemble base matrices (speed-independent)
        self.M_global = None
        self.K_global = None
        self.G_global = None
        self.C_global = None
        self._assemble()

    def _assign_nodes(self):
        """Assign disks and bearings to nearest FE nodes."""
        if not self.is_dual_spool:
            for disk in self.disks:
                idx = np.argmin(np.abs(self.node_x_lp - disk.x_pos))
                disk.node = idx
                print(f"  Disk '{disk.name}' at x={disk.x_pos*1e3:.1f} mm "
                      f"→ Node {idx} (x={self.node_x_lp[idx]*1e3:.1f} mm)")

            for brg in self.bearings:
                idx = np.argmin(np.abs(self.node_x_lp - brg.x_pos))
                brg.node = idx
                print(f"  Bearing '{brg.name}' at x={brg.x_pos*1e3:.1f} mm "
                      f"→ Node {idx} (x={self.node_x_lp[idx]*1e3:.1f} mm)")
        else:
            for disk in self.disks:
                if disk.spool == "LP":
                    idx = np.argmin(np.abs(self.node_x_lp - disk.x_pos))
                    disk.node = idx
                    print(f"  LP Disk '{disk.name}' at x={disk.x_pos*1e3:.1f} mm → LP Node {idx} (x={self.node_x_lp[idx]*1e3:.1f} mm)")
                else:
                    idx = np.argmin(np.abs(self.node_x_hp - disk.x_pos))
                    disk.node = idx
                    print(f"  HP Disk '{disk.name}' at x={disk.x_pos*1e3:.1f} mm → HP Node {idx} (x={self.node_x_hp[idx]*1e3:.1f} mm)")

            for brg in self.bearings:
                if brg.spool == "LP":
                    idx = np.argmin(np.abs(self.node_x_lp - brg.x_pos))
                    brg.node = idx
                    print(f"  LP Bearing '{brg.name}' at x={brg.x_pos*1e3:.1f} mm → LP Node {idx} (x={self.node_x_lp[idx]*1e3:.1f} mm)")
                elif brg.spool == "HP":
                    idx = np.argmin(np.abs(self.node_x_hp - brg.x_pos))
                    brg.node = idx
                    print(f"  HP Bearing '{brg.name}' at x={brg.x_pos*1e3:.1f} mm → HP Node {idx} (x={self.node_x_hp[idx]*1e3:.1f} mm)")
                elif brg.spool == "IS":
                    lp_idx = np.argmin(np.abs(self.node_x_lp - brg.x_pos))
                    hp_idx = np.argmin(np.abs(self.node_x_hp - brg.x_pos))
                    brg.lp_node = lp_idx
                    brg.hp_node = hp_idx
                    print(f"  Inter-shaft Bearing '{brg.name}' at x={brg.x_pos*1e3:.1f} mm → LP Node {lp_idx}, HP Node {hp_idx}")

    def _assemble(self):
        """Assemble global M, K, G, C matrices."""
        n = self.n_dof
        M = np.zeros((n, n))
        K = np.zeros((n, n))
        C = np.zeros((n, n))
        
        G_lp = np.zeros((n, n))
        G_hp = np.zeros((n, n))

        mat = self.material
        sec_lp = self.section if not self.is_dual_spool else self.lp_section

        # ─── LP Shaft elements ───────────────────────────────────────────
        for e in range(self.n_elem_lp):
            Me, Ke, Ge = timoshenko_element_matrices(
                L=self.elem_L_lp,
                E=mat.E,
                G_mod=mat.G,
                rho=mat.rho,
                A=sec_lp.A,
                I_sec=sec_lp.I,
                Ip=sec_lp.Ip,
                kappa=sec_lp.kappa,
            )
            dof_start = e * self.dof_per_node
            idx = list(range(dof_start, dof_start + 8))

            for i_loc in range(8):
                for j_loc in range(8):
                    M[idx[i_loc], idx[j_loc]] += Me[i_loc, j_loc]
                    K[idx[i_loc], idx[j_loc]] += Ke[i_loc, j_loc]
                    G_lp[idx[i_loc], idx[j_loc]] += Ge[i_loc, j_loc]

        # ─── HP Shaft elements ───────────────────────────────────────────
        if self.is_dual_spool:
            sec_hp = self.hp_section
            for e in range(self.n_elem_hp):
                Me, Ke, Ge = timoshenko_element_matrices(
                    L=self.elem_L_hp,
                    E=mat.E,
                    G_mod=mat.G,
                    rho=mat.rho,
                    A=sec_hp.A,
                    I_sec=sec_hp.I,
                    Ip=sec_hp.Ip,
                    kappa=sec_hp.kappa,
                )
                dof_start = (self.n_nodes_lp + e) * self.dof_per_node
                idx = list(range(dof_start, dof_start + 8))

                for i_loc in range(8):
                    for j_loc in range(8):
                        M[idx[i_loc], idx[j_loc]] += Me[i_loc, j_loc]
                        K[idx[i_loc], idx[j_loc]] += Ke[i_loc, j_loc]
                        G_hp[idx[i_loc], idx[j_loc]] += Ge[i_loc, j_loc]

        # ─── Disk lumped masses ────────────────────────────────────────
        for disk in self.disks:
            nd = disk.node
            if self.is_dual_spool and disk.spool == "HP":
                i0 = (self.n_nodes_lp + nd) * self.dof_per_node
                G_target = G_hp
            else:
                i0 = nd * self.dof_per_node
                G_target = G_lp
                
            M[i0, i0] += disk.mass
            M[i0 + 1, i0 + 1] += disk.Id
            M[i0 + 2, i0 + 2] += disk.mass
            M[i0 + 3, i0 + 3] += disk.Id

            G_target[i0 + 1, i0 + 3] -= 2.0 * disk.Ip
            G_target[i0 + 3, i0 + 1] += 2.0 * disk.Ip

        # ─── Bearing stiffness and damping ─────────────────────────────
        for brg in self.bearings:
            if brg.spool == "LP":
                i0 = brg.node * self.dof_per_node
                K[i0, i0] += brg.kxx
                C[i0, i0] += brg.cxx
                K[i0 + 2, i0 + 2] += brg.kyy
                C[i0 + 2, i0 + 2] += brg.cyy
            elif brg.spool == "HP":
                i0 = (self.n_nodes_lp + brg.node) * self.dof_per_node
                K[i0, i0] += brg.kxx
                C[i0, i0] += brg.cxx
                K[i0 + 2, i0 + 2] += brg.kyy
                C[i0 + 2, i0 + 2] += brg.cyy
            elif brg.spool == "IS":
                i_lp = brg.lp_node * self.dof_per_node
                i_hp = (self.n_nodes_lp + brg.hp_node) * self.dof_per_node
                
                K[i_lp, i_lp] += brg.kxx
                K[i_hp, i_hp] += brg.kxx
                K[i_lp, i_hp] -= brg.kxx
                K[i_hp, i_lp] -= brg.kxx
                
                C[i_lp, i_lp] += brg.cxx
                C[i_hp, i_hp] += brg.cxx
                C[i_lp, i_hp] -= brg.cxx
                C[i_hp, i_lp] -= brg.cxx
                
                K[i_lp + 2, i_lp + 2] += brg.kyy
                K[i_hp + 2, i_hp + 2] += brg.kyy
                K[i_lp + 2, i_hp + 2] -= brg.kyy
                K[i_hp + 2, i_lp + 2] -= brg.kyy
                
                C[i_lp + 2, i_lp + 2] += brg.cyy
                C[i_hp + 2, i_hp + 2] += brg.cyy
                C[i_lp + 2, i_hp + 2] -= brg.cyy
                C[i_hp + 2, i_lp + 2] -= brg.cyy

        self.M_global = M
        self.K_global = K
        self.C_global = C
        if self.is_dual_spool:
            self.G_lp = G_lp
            self.G_hp = G_hp
        else:
            self.G_global = G_lp

        print(f"\n  Global matrices assembled: {n}×{n}  (LP: {self.n_nodes_lp} nodes, HP: {self.n_nodes_hp if self.is_dual_spool else 0} nodes)")

    def solve_eigenvalues(self, omega_spin: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Solve the damped gyroscopic eigenvalue problem at a given spin speed.
        """
        n = self.n_dof
        M = self.M_global
        K = self.K_global
        
        if self.is_dual_spool:
            # omega_spin is HP spool speed. LP spool speed is N1 = 0.65 * N2.
            G_total = 0.65 * omega_spin * self.G_lp + omega_spin * self.G_hp
        else:
            G_total = omega_spin * self.G_global
            
        C_total = self.C_global + G_total

        M_reg = M.copy()
        diag_min = np.min(np.abs(np.diag(M_reg)[np.diag(M_reg) != 0]))
        for i in range(n):
            if abs(M_reg[i, i]) < 1e-12 * diag_min:
                M_reg[i, i] = 1e-12 * diag_min

        M_inv = np.linalg.inv(M_reg)
        M_inv_K = M_inv @ K
        M_inv_C = M_inv @ C_total

        A_ss = np.zeros((2 * n, 2 * n))
        A_ss[:n, n:] = np.eye(n)
        A_ss[n:, :n] = -M_inv_K
        A_ss[n:, n:] = -M_inv_C

        eigvals, eigvecs = linalg.eig(A_ss)

        return eigvals, eigvecs

    def extract_natural_frequencies(
        self, eigvals: np.ndarray, n_modes: int = 6
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract natural frequencies and damping ratios from eigenvalues.

        Only keeps eigenvalues with positive imaginary part (forward
        direction in rotating frame), sorted by frequency.

        Parameters
        ----------
        eigvals : ndarray
            Complex eigenvalues from state-space solution.
        n_modes : int
            Number of modes to extract.

        Returns
        -------
        freqs_hz : ndarray
            Natural frequencies [Hz].
        damping_ratios : ndarray
            Modal damping ratios [-].
        eigvals_sorted : ndarray
            Sorted eigenvalues.
        """
        # Filter: keep eigenvalues with positive imaginary part
        mask = np.imag(eigvals) > 1.0  # above 1 rad/s to skip rigid body modes
        pos_eigvals = eigvals[mask]

        # Sort by imaginary part (frequency)
        sort_idx = np.argsort(np.imag(pos_eigvals))
        sorted_eig = pos_eigvals[sort_idx]

        # Take first n_modes
        n_take = min(n_modes, len(sorted_eig))
        selected = sorted_eig[:n_take]

        omega_d = np.abs(np.imag(selected))       # Damped natural freq [rad/s]
        sigma = np.real(selected)                  # Decay rate
        omega_n = np.sqrt(sigma**2 + omega_d**2)   # Undamped natural freq
        zeta = -sigma / omega_n                    # Damping ratio
        freqs_hz = omega_d / (2.0 * np.pi)

        return freqs_hz, zeta, selected

    def campbell_sweep(
        self, rpm_range: np.ndarray, n_modes: int = 6
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sweep through RPM range and compute natural frequencies at each speed.

        Parameters
        ----------
        rpm_range : ndarray
            Array of rotor speeds [RPM].
        n_modes : int
            Number of modes to track.

        Returns
        -------
        freq_map : ndarray (len(rpm_range), n_modes)
            Natural frequencies [Hz] at each speed.
        damp_map : ndarray (len(rpm_range), n_modes)
            Damping ratios at each speed.
        """
        n_speeds = len(rpm_range)
        freq_map = np.full((n_speeds, n_modes), np.nan)
        damp_map = np.full((n_speeds, n_modes), np.nan)

        print(f"\n  Campbell sweep: {n_speeds} speed points, "
              f"{n_modes} modes tracked")
        print(f"  {'RPM':>8s} | {'ω₁ [Hz]':>10s} | {'ω₂ [Hz]':>10s} | "
              f"{'ω₃ [Hz]':>10s} | {'ω₄ [Hz]':>10s} | {'ω₅ [Hz]':>10s} | "
              f"{'ω₆ [Hz]':>10s}")
        print("  " + "─" * 82)

        for i, rpm in enumerate(rpm_range):
            omega = rpm * 2.0 * np.pi / 60.0  # [rad/s]
            eigvals, _ = self.solve_eigenvalues(omega)
            freqs, zetas, _ = self.extract_natural_frequencies(eigvals, n_modes)

            n_found = len(freqs)
            freq_map[i, :n_found] = freqs[:n_found]
            damp_map[i, :n_found] = zetas[:n_found]

            if i % 15 == 0 or i == n_speeds - 1:
                freq_str = " | ".join(
                    f"{freq_map[i, j]:10.1f}" if not np.isnan(freq_map[i, j])
                    else f"{'—':>10s}"
                    for j in range(min(n_modes, 6))
                )
                print(f"  {rpm:8.0f} | {freq_str}")

        return freq_map, damp_map


# ═══════════════════════════════════════════════════════════════════════════════
# MODE CLASSIFICATION (Forward / Backward Whirl)
# ═══════════════════════════════════════════════════════════════════════════════

def classify_whirl(freq_map: np.ndarray, rpm_range: np.ndarray) -> dict:
    """
    Classify modes into Forward Whirl (FW) and Backward Whirl (BW).

    For a symmetric rotor, eigenvalues come in pairs. Modes that increase
    with speed are forward whirl; those that decrease are backward whirl.

    Parameters
    ----------
    freq_map : ndarray (n_speeds, n_modes)
        Natural frequencies at each speed.
    rpm_range : ndarray
        Rotor speeds [RPM].

    Returns
    -------
    classified : dict
        Keys like 'FW1', 'BW1', 'FW2', 'BW2', etc.
        Values are 1-D arrays of frequency [Hz] vs speed.
    """
    n_speeds, n_modes = freq_map.shape
    classified = {}

    # At zero speed, modes come in degenerate pairs.
    # As speed increases, each pair splits into FW (increasing) and BW (decreasing).
    # We'll look at the slope of frequency vs RPM to classify.

    # Use frequency at ~20% of speed range to determine slope
    i_low = max(1, n_speeds // 10)
    i_high = min(n_speeds - 1, n_speeds // 3)

    n_pairs = n_modes // 2
    for p in range(n_pairs):
        idx_a = 2 * p
        idx_b = 2 * p + 1

        if idx_b >= n_modes:
            break

        freq_a = freq_map[:, idx_a]
        freq_b = freq_map[:, idx_b]

        # Compute average slope
        slope_a = np.nanmean(np.diff(freq_a[i_low:i_high]))
        slope_b = np.nanmean(np.diff(freq_b[i_low:i_high]))

        # The one with higher slope is forward whirl
        if slope_a >= slope_b:
            classified[f"FW{p+1}"] = freq_a
            classified[f"BW{p+1}"] = freq_b
        else:
            classified[f"FW{p+1}"] = freq_b
            classified[f"BW{p+1}"] = freq_a

    return classified


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL SPEED FINDER
# ═══════════════════════════════════════════════════════════════════════════════

def find_critical_speeds(
    rpm_range: np.ndarray, classified: dict, sync_order: float = 1.0
) -> List[dict]:
    """
    Find intersections of natural frequency curves with synchronous line.

    The n× synchronous line is: f_sync = n × RPM / 60  [Hz]

    Parameters
    ----------
    rpm_range : ndarray
        Rotor speeds [RPM].
    classified : dict
        Classified whirl modes (from classify_whirl).
    sync_order : float
        Synchronous order (1.0 for 1×, 2.0 for 2×, etc.).

    Returns
    -------
    criticals : list of dict
        Each dict has 'mode', 'rpm', 'freq_hz', 'order'.
    """
    f_sync = sync_order * rpm_range / 60.0  # [Hz]
    criticals = []

    for mode_name, freqs in classified.items():
        # Find sign changes in (freq - f_sync)
        diff = freqs - f_sync
        valid = ~np.isnan(diff)

        for i in range(len(rpm_range) - 1):
            if valid[i] and valid[i + 1]:
                if diff[i] * diff[i + 1] < 0:
                    # Linear interpolation for crossing point
                    frac = abs(diff[i]) / (abs(diff[i]) + abs(diff[i + 1]))
                    rpm_crit = rpm_range[i] + frac * (rpm_range[i + 1] - rpm_range[i])
                    freq_crit = sync_order * rpm_crit / 60.0

                    criticals.append({
                        "mode": mode_name,
                        "rpm": rpm_crit,
                        "freq_hz": freq_crit,
                        "order": sync_order,
                    })

    # Sort by RPM
    criticals.sort(key=lambda c: c["rpm"])
    return criticals


# ═══════════════════════════════════════════════════════════════════════════════
# PLOTTING
# ═══════════════════════════════════════════════════════════════════════════════

def plot_campbell_diagram(
    rpm_range: np.ndarray,
    classified: dict,
    criticals_1x: List[dict],
    criticals_2x: List[dict],
    rpm_idle: float,
    rpm_max: float,
    output_path: str,
):
    """
    Generate publication-quality Campbell diagram.

    Parameters
    ----------
    rpm_range : ndarray
        Speed range [RPM].
    classified : dict
        Classified whirl modes.
    criticals_1x, criticals_2x : list of dict
        Critical speed intersections.
    rpm_idle, rpm_max : float
        Operating range bounds [RPM].
    output_path : str
        Path to save PNG.
    """
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(16, 10), dpi=200)

    # ─── Operating range band ──────────────────────────────────────────
    ax.axvspan(rpm_idle, rpm_max, alpha=0.12, color="#00ff88",
               label="Operating Range (21k–38.5k RPM)")

    # ─── Synchronous lines ─────────────────────────────────────────────
    f_1x = rpm_range / 60.0
    f_2x = 2.0 * rpm_range / 60.0
    ax.plot(rpm_range, f_1x, "--", color="#cccccc", linewidth=1.2,
            label="1× Synchronous", zorder=2)
    ax.plot(rpm_range, f_2x, "--", color="#888888", linewidth=1.0,
            label="2× Synchronous", zorder=2)

    # ─── Mode style definitions ────────────────────────────────────────
    style_map = {
        "FW1": {"color": "#3399ff", "ls": "-",  "lw": 2.2, "label": "1st Forward Whirl (FW1)"},
        "BW1": {"color": "#3399ff", "ls": "--", "lw": 1.8, "label": "1st Backward Whirl (BW1)"},
        "FW2": {"color": "#ff4444", "ls": "-",  "lw": 2.2, "label": "2nd Forward Whirl (FW2)"},
        "BW2": {"color": "#ff4444", "ls": "--", "lw": 1.8, "label": "2nd Backward Whirl (BW2)"},
        "FW3": {"color": "#44cc44", "ls": "-",  "lw": 2.0, "label": "3rd Forward Whirl (FW3)"},
        "BW3": {"color": "#44cc44", "ls": "--", "lw": 1.6, "label": "3rd Backward Whirl (BW3)"},
    }

    for mode_name, freqs in classified.items():
        sty = style_map.get(mode_name, {"color": "yellow", "ls": "-", "lw": 1.0,
                                         "label": mode_name})
        ax.plot(rpm_range, freqs, color=sty["color"], linestyle=sty["ls"],
                linewidth=sty["lw"], label=sty["label"], zorder=3)

    # ─── Critical speed markers ────────────────────────────────────────
    for i, crit in enumerate(criticals_1x):
        label = "1× Critical Speed" if i == 0 else None
        ax.plot(crit["rpm"], crit["freq_hz"], "D", color="#ff2222",
                markersize=10, markeredgecolor="white", markeredgewidth=1.2,
                zorder=5, label=label)
        ax.annotate(
            f'{crit["mode"]}\n{crit["rpm"]:.0f} RPM\n{crit["freq_hz"]:.0f} Hz',
            xy=(crit["rpm"], crit["freq_hz"]),
            xytext=(25, 20), textcoords="offset points",
            fontsize=8, color="#ff8888",
            arrowprops=dict(arrowstyle="->", color="#ff8888", lw=1.0),
            bbox=dict(boxstyle="round,pad=0.3", fc="#1a1a2e", ec="#ff4444",
                      alpha=0.85),
            zorder=6,
        )

    for i, crit in enumerate(criticals_2x):
        label = "2× Critical Speed" if i == 0 else None
        ax.plot(crit["rpm"], crit["freq_hz"], "s", color="#ffaa00",
                markersize=8, markeredgecolor="white", markeredgewidth=1.0,
                zorder=5, label=label)

    # ─── Formatting ────────────────────────────────────────────────────
    ax.set_xlabel("Rotor Speed [RPM]", fontsize=13, fontweight="bold")
    ax.set_ylabel("Natural Frequency [Hz]", fontsize=13, fontweight="bold")
    ax.set_title(
        "AEGIS-TJ1 Campbell Diagram — Rotor Critical Speed Analysis",
        fontsize=16, fontweight="bold", pad=15,
    )

    ax.set_xlim(0, rpm_range[-1])
    y_max = min(np.nanmax(f_2x) * 1.05, 2500)
    ax.set_ylim(0, y_max)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.7, ncol=2)

    # Design point annotation
    ax.axvline(35000, color="#00ff88", linewidth=0.8, alpha=0.5, linestyle=":")
    ax.text(35000, y_max * 0.97, "Design\n35,000 RPM", ha="center",
            fontsize=8, color="#00ff88", alpha=0.7)

    fig.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"\n  ✓ Campbell diagram saved → {output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS REPORTING
# ═══════════════════════════════════════════════════════════════════════════════

def print_results(
    criticals_1x: List[dict],
    criticals_2x: List[dict],
    rpm_idle: float,
    rpm_design: float,
    rpm_max: float,
):
    """Print formatted results table and safety assessment."""

    print("\n" + "═" * 80)
    print("  AEGIS-TJ1 ROTOR DYNAMICS — CRITICAL SPEED ANALYSIS RESULTS")
    print("═" * 80)

    print("\n  ┌─────────────────────────────────────────────────────────────┐")
    print("  │                  1× Critical Speeds                        │")
    print("  ├──────────┬──────────────┬───────────────┬──────────────────┤")
    print("  │  Mode    │   Speed      │  Frequency    │  Within Op Range │")
    print("  │          │   [RPM]      │  [Hz]         │                  │")
    print("  ├──────────┼──────────────┼───────────────┼──────────────────┤")

    for crit in criticals_1x:
        in_range = "⚠ YES" if rpm_idle <= crit["rpm"] <= rpm_max else "✓ NO"
        print(f"  │  {crit['mode']:<6s}  │  {crit['rpm']:>10.0f}  │  {crit['freq_hz']:>11.1f}  │"
              f"  {in_range:<16s}│")

    print("  └──────────┴──────────────┴───────────────┴──────────────────┘")

    if criticals_2x:
        print("\n  ┌─────────────────────────────────────────────────────────────┐")
        print("  │                  2× Critical Speeds                        │")
        print("  ├──────────┬──────────────┬───────────────┬──────────────────┤")
        print("  │  Mode    │   Speed      │  Frequency    │  Within Op Range │")
        print("  ├──────────┼──────────────┼───────────────┼──────────────────┤")
        for crit in criticals_2x:
            in_range = "⚠ YES" if rpm_idle <= crit["rpm"] <= rpm_max else "✓ NO"
            print(f"  │  {crit['mode']:<6s}  │  {crit['rpm']:>10.0f}  │  {crit['freq_hz']:>11.1f}  │"
                  f"  {in_range:<16s}│")
        print("  └──────────┴──────────────┴───────────────┴──────────────────┘")

    # ─── Safety margin analysis ────────────────────────────────────────
    print("\n  ┌─────────────────────────────────────────────────────────────┐")
    print("  │              SAFETY MARGIN ANALYSIS                        │")
    print("  ├────────────────────────────────────────────────────────────┤")

    crits_1x_rpm = [c["rpm"] for c in criticals_1x]
    below_idle = [r for r in crits_1x_rpm if r < rpm_idle]
    above_max = [r for r in crits_1x_rpm if r > rpm_max]
    in_range = [r for r in crits_1x_rpm if rpm_idle <= r <= rpm_max]

    if below_idle:
        nearest_below = max(below_idle)
        margin_below = (rpm_idle - nearest_below) / nearest_below * 100.0
        print(f"  │  Nearest 1× critical below idle:  {nearest_below:>8.0f} RPM       │")
        print(f"  │  Margin from idle (21,000 RPM):    {margin_below:>8.1f} %            │")
    else:
        margin_below = float("inf")
        print(f"  │  No 1× critical speed below idle RPM                     │")

    if above_max:
        nearest_above = min(above_max)
        margin_above = (nearest_above - rpm_max) / rpm_max * 100.0
        print(f"  │  Nearest 1× critical above max:   {nearest_above:>8.0f} RPM       │")
        print(f"  │  Margin from max (38,500 RPM):     {margin_above:>8.1f} %            │")
    else:
        margin_above = float("inf")
        print(f"  │  No 1× critical speed above max RPM                      │")

    print("  ├────────────────────────────────────────────────────────────┤")

    # Verdict
    # Real-world API/ISO aerospace limits: 10% below idle, 15% above max!
    safe = len(in_range) == 0 and margin_below > 10.0 and margin_above > 15.0
    if safe:
        verdict = "✅ SAFE — Operating range clear of all 1× critical speeds"
        detail = f"   Margins: {margin_below:.1f}% below (req >10%), {margin_above:.1f}% above (req >15%)"
    elif len(in_range) > 0:
        verdict = "❌ UNSAFE — Critical speed(s) within operating range!"
        detail = f"   {len(in_range)} critical speed(s) in [{rpm_idle:.0f}, {rpm_max:.0f}] RPM"
    else:
        verdict = "⚠️  MARGINAL — Separation margin insufficient"
        detail = f"   Margins: {margin_below:.1f}% below (req >10%), {margin_above:.1f}% above (req >15%)"

    print(f"  │  {verdict:<58s}│")
    print(f"  │  {detail:<58s}│")
    print("  └─────────────────────────────────────────────────────────────┘")

    return {
        "criticals_1x": criticals_1x,
        "criticals_2x": criticals_2x,
        "margin_below_pct": margin_below,
        "margin_above_pct": margin_above,
        "safe": safe,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """AEGIS-TJ1 Rotor Dynamics — Campbell Diagram Analysis."""

    print("=" * 80)
    print("  AEGIS-TJ1 ROTOR DYNAMICS — CAMPBELL DIAGRAM ANALYSIS")
    print("  Finite Element Timoshenko Beam Model (Dual-Spool Concentric Spools)")
    print("=" * 80)

    # ─── Material ──────────────────────────────────────────────────────
    inconel718 = Material(
        name="Inconel 718",
        E=205e9,       # Pa
        rho=8190.0,    # kg/m³
        nu=0.29,
    )
    print(f"\n  Material: {inconel718.name}")
    print(f"    E  = {inconel718.E/1e9:.0f} GPa")
    print(f"    G  = {inconel718.G/1e9:.1f} GPa")
    print(f"    ρ  = {inconel718.rho:.0f} kg/m³")
    print(f"    ν  = {inconel718.nu}")

    # ─── Shaft sections ─────────────────────────────────────────────────
    lp_shaft_sec = ShaftSection(D_outer=0.022, D_inner=0.012)
    hp_shaft_sec = ShaftSection(D_outer=0.036, D_inner=0.024)
    
    print(f"\n  LP Shaft (Inner): Hollow circular")
    print(f"    D_outer = {lp_shaft_sec.D_outer*1e3:.1f} mm")
    print(f"    D_inner = {lp_shaft_sec.D_inner*1e3:.1f} mm")
    print(f"  HP Shaft (Outer): Hollow circular")
    print(f"    D_outer = {hp_shaft_sec.D_outer*1e3:.1f} mm")
    print(f"    D_inner = {hp_shaft_sec.D_inner*1e3:.1f} mm")

    # ─── Disks ─────────────────────────────────────────────────────────
    lp_fan = Disk(
        name="LP Fan/LPC",
        x_pos=0.060,       # 60 mm
        mass=3.6,          # 4.5 * 0.8
        Ip=0.020,          # 0.025 * 0.8
        Id=0.0104,         # 0.013 * 0.8
        spool="LP"
    )
    lp_turbine = Disk(
        name="LP Turbine",
        x_pos=0.394,       # 394 mm
        mass=3.04,         # 3.8 * 0.8
        Ip=0.0144,         # 0.018 * 0.8
        Id=0.008,          # 0.010 * 0.8
        spool="LP"
    )
    hp_compressor = Disk(
        name="HP Compressor",
        x_pos=0.140,       # 140 mm
        mass=2.4,          # 3.0 * 0.8
        Ip=0.012,          # 0.015 * 0.8
        Id=0.0064,         # 0.008 * 0.8
        spool="HP"
    )
    hp_turbine = Disk(
        name="HP Turbine",
        x_pos=0.240,       # 240 mm
        mass=2.0,          # 2.5 * 0.8
        Ip=0.0096,         # 0.012 * 0.8
        Id=0.0048,         # 0.006 * 0.8
        spool="HP"
    )

    # ─── Bearings ──────────────────────────────────────────────────────
    front_lp_bearing = Bearing(
        name="Front LP Ball Brg",
        x_pos=-0.065,
        kxx=0.15e8, kyy=0.15e8,
        cxx=500.0, cyy=500.0,
        spool="LP"
    )
    rear_lp_bearing = Bearing(
        name="Rear LP Roller Brg",
        x_pos=0.385,
        kxx=0.15e8, kyy=0.15e8,
        cxx=800.0, cyy=800.0,
        spool="LP"
    )
    front_hp_bearing = Bearing(
        name="Front HP Casing Brg",
        x_pos=0.080,
        kxx=8.0e8, kyy=8.0e8,
        cxx=500.0, cyy=500.0,
        spool="HP"
    )
    inter_shaft_bearing = Bearing(
        name="HP/LP Inter-Shaft Brg",
        x_pos=0.280,
        kxx=3.0e8, kyy=3.0e8,
        cxx=500.0, cyy=500.0,
        spool="IS"
    )

    # ─── Shaft span ───────────────────────────────────────────────────
    x_start = -0.065   # m
    shaft_length = 0.540  # m (total shaft from -65 to 475 mm)

    print(f"\n  LP Shaft span: {x_start*1e3:.0f} mm to {(x_start + shaft_length)*1e3:.0f} mm (L = {shaft_length*1e3:.0f} mm)")
    print(f"  HP Shaft span: 80.0 mm to 280.0 mm (L = 200.0 mm)")

    # ─── Build FEM model ───────────────────────────────────────────────
    n_elements = 20
    print(f"\n  Building FE model ({n_elements} Timoshenko elements per shaft)...")

    rotor = RotorFEM(
        shaft_length=shaft_length,
        x_start=x_start,
        material=inconel718,
        section=lp_shaft_sec,
        n_elements=n_elements,
        disks=[lp_fan, lp_turbine, hp_compressor, hp_turbine],
        bearings=[front_lp_bearing, rear_lp_bearing, front_hp_bearing, inter_shaft_bearing],
        is_dual_spool=True,
        lp_section=lp_shaft_sec,
        hp_section=hp_shaft_sec,
        hp_shaft_length=0.200,
        hp_x_start=0.080,
        n_elements_hp=20
    )

    # ─── Operating points (Sweep N2 RPM, N1 = 0.65 * N2) ────────────────
    RPM_IDLE = 21_000.0
    RPM_DESIGN = 35_000.0
    RPM_MAX = 38_500.0

    # Analysis speed range
    rpm_range = np.arange(0, 45_500, 500)
    rpm_range[0] = 10  # avoid exactly zero for numerical stability

    # ─── Campbell sweep ────────────────────────────────────────────────
    n_modes = 6
    freq_map, damp_map = rotor.campbell_sweep(rpm_range, n_modes=n_modes)

    # ─── Classify modes ────────────────────────────────────────────────
    classified = classify_whirl(freq_map, rpm_range)

    print("\n  Mode classification at design speed (35,000 HP RPM):")
    i_design = np.argmin(np.abs(rpm_range - RPM_DESIGN))
    for mode_name in sorted(classified.keys()):
        freq_at_design = classified[mode_name][i_design]
        if not np.isnan(freq_at_design):
            print(f"    {mode_name}: {freq_at_design:.1f} Hz ({freq_at_design*60:.0f} CPM)")

    # ─── Find critical speeds ─────────────────────────────────────────
    criticals_1x = find_critical_speeds(rpm_range, classified, sync_order=1.0)
    criticals_2x = find_critical_speeds(rpm_range, classified, sync_order=2.0)

    # ─── Print results ─────────────────────────────────────────────────
    results = print_results(criticals_1x, criticals_2x,
                            RPM_IDLE, RPM_DESIGN, RPM_MAX)

    # ─── Plot ──────────────────────────────────────────────────────────
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "outputs", "campbell_diagram.png")

    plot_campbell_diagram(
        rpm_range, classified, criticals_1x, criticals_2x,
        RPM_IDLE, RPM_MAX, output_path,
    )

    print("\n" + "=" * 80)
    print("  Analysis complete.")
    print("=" * 80 + "\n")

    return results


if __name__ == "__main__":
    results = main()
