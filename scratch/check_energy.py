import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rotor_dynamics.campbell_diagram import RotorFEM, Material, ShaftSection, Disk, Bearing

inconel718 = Material(name="Inconel 718", E=2.05e11, rho=8190.0, nu=0.29)
lp_shaft_sec = ShaftSection(D_outer=0.022, D_inner=0.012)
hp_shaft_sec = ShaftSection(D_outer=0.036, D_inner=0.024)

lp_fan = Disk("LP Fan/LPC", x_pos=0.060, mass=3.6, Ip=0.020, Id=0.0104, spool="LP")
lp_turbine = Disk("LP Turbine", x_pos=0.394, mass=3.04, Ip=0.0144, Id=0.008, spool="LP")
hp_compressor = Disk("HP Compressor", x_pos=0.140, mass=2.4, Ip=0.012, Id=0.0064, spool="HP")
hp_turbine = Disk("HP Turbine", x_pos=0.240, mass=2.0, Ip=0.0096, Id=0.0048, spool="HP")

front_lp = Bearing("Front LP Ball Brg", x_pos=-0.065, kxx=0.15e8, kyy=0.15e8, cxx=500.0, cyy=500.0, spool="LP")
rear_lp = Bearing("Rear LP Roller Brg", x_pos=0.385, kxx=0.15e8, kyy=0.15e8, cxx=800.0, cyy=800.0, spool="LP")
front_hp = Bearing("Front HP Casing Brg", x_pos=0.080, kxx=8.0e8, kyy=8.0e8, cxx=500.0, cyy=500.0, spool="HP")
inter_shaft = Bearing("HP/LP Inter-Shaft Brg", x_pos=0.280, kxx=3.0e8, kyy=3.0e8, cxx=500.0, cyy=500.0, spool="IS")

rotor = RotorFEM(
    shaft_length=0.540, x_start=-0.065, material=inconel718, section=lp_shaft_sec,
    n_elements=20, disks=[lp_fan, lp_turbine, hp_compressor, hp_turbine],
    bearings=[front_lp, rear_lp, front_hp, inter_shaft],
    is_dual_spool=True, lp_section=lp_shaft_sec, hp_section=hp_shaft_sec,
    hp_shaft_length=0.200, hp_x_start=0.080
)

omega_design = 35000.0 * np.pi / 30.0
eigvals, eigvecs = rotor.solve_eigenvalues(omega_design)

n = rotor.n_dof
K_global = rotor.K_global

# Filter positive imaginary eigenvalues
forward_modes = []
for i in range(2 * n):
    val = eigvals[i]
    if val.imag > 1.0:
        forward_modes.append((val.imag / (2 * np.pi), eigvecs[:n, i]))

forward_modes = sorted(forward_modes, key=lambda x: x[0])

for k in range(3):
    freq, phi = forward_modes[k]
    # Total potential energy
    E_total = 0.5 * np.real(np.dot(np.dot(phi.T, K_global), np.conj(phi)))
    
    # Bearing energy
    E_bearings = 0.0
    for brg in rotor.bearings:
        if brg.spool == "LP":
            idx_y = brg.node * 4
            idx_z = brg.node * 4 + 2
            E_bearings += 0.5 * brg.kxx * (abs(phi[idx_y])**2 + abs(phi[idx_z])**2)
        elif brg.spool == "HP":
            idx_y = (rotor.n_nodes_lp + brg.node) * 4
            idx_z = (rotor.n_nodes_lp + brg.node) * 4 + 2
            E_bearings += 0.5 * brg.kxx * (abs(phi[idx_y])**2 + abs(phi[idx_z])**2)
        elif brg.spool == "IS":
            idx_y_lp = brg.lp_node * 4
            idx_z_lp = brg.lp_node * 4 + 2
            idx_y_hp = (rotor.n_nodes_lp + brg.hp_node) * 4
            idx_z_hp = (rotor.n_nodes_lp + brg.hp_node) * 4 + 2
            dy = phi[idx_y_hp] - phi[idx_y_lp]
            dz = phi[idx_z_hp] - phi[idx_z_lp]
            E_bearings += 0.5 * brg.kxx * (abs(dy)**2 + abs(dz)**2)
            
    E_shaft = E_total - E_bearings
    pct_shaft = E_shaft / E_total * 100
    pct_bearings = E_bearings / E_total * 100
    print(f"Mode {k+1} ({freq:.1f} Hz): E_total = {E_total:.6e}, E_bearings = {E_bearings:.6e}, Shaft = {pct_shaft:.1f}%, Bearings = {pct_bearings:.1f}%")
