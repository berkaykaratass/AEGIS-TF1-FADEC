import numpy as np
from scipy import linalg
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class Material:
    name: str
    E: float
    rho: float
    nu: float

    @property
    def G(self) -> float:
        return self.E / (2.0 * (1.0 + self.nu))

@dataclass
class ShaftSection:
    D_outer: float
    D_inner: float

    @property
    def A(self) -> float:
        return np.pi / 4.0 * (self.D_outer**2 - self.D_inner**2)

    @property
    def I(self) -> float:
        return np.pi / 64.0 * (self.D_outer**4 - self.D_inner**4)

    @property
    def Ip(self) -> float:
        return 2.0 * self.I

    @property
    def kappa(self) -> float:
        r = self.D_inner / self.D_outer if self.D_outer > 0 else 0
        nu = 0.29
        return (6.0 * (1.0 + nu) * (1.0 + r**2)**2) / (
            (7.0 + 6.0 * nu) * (1.0 + r**2)**2 + (20.0 + 12.0 * nu) * r**2
        )

@dataclass
class Disk:
    name: str
    x_pos: float
    mass: float
    Ip: float
    Id: float
    node: int = -1
    spool: str = "LP"

@dataclass
class Bearing:
    name: str
    x_pos: float
    kxx: float
    kyy: float
    cxx: float
    cyy: float
    node: int = -1
    spool: str = "LP"
    lp_node: int = -1
    hp_node: int = -1

def timoshenko_element_matrices(L, E, G_mod, rho, A, I_sec, Ip, kappa):
    phi = 12.0 * E * I_sec / (kappa * G_mod * A * L**2) if A > 0 else 0
    denom = (1.0 + phi)**2
    coeff_k = E * I_sec / ((1.0 + phi) * L**3)
    K_plane = coeff_k * np.array([
        [ 12.0,       6.0*L,      -12.0,       6.0*L     ],
        [  6.0*L,    (4.0+phi)*L**2, -6.0*L, (2.0-phi)*L**2],
        [-12.0,      -6.0*L,       12.0,      -6.0*L     ],
        [  6.0*L,   (2.0-phi)*L**2, -6.0*L, (4.0+phi)*L**2],
    ])
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
    G_e = np.zeros((8, 8))
    coeff_gyro = 2.0 * rho * Ip / (30.0 * L * denom)
    G_sub = coeff_gyro * np.array([
        [ 0.0,           -36.0,           0.0,        -(3.0 - 15.0*phi)*L],
        [ 36.0,            0.0,          (3.0 - 15.0*phi)*L, 0.0],
        [ 0.0,           (3.0 - 15.0*phi)*L, 0.0,          -36.0],
        [-(3.0 - 15.0*phi)*L, 0.0,           36.0,           0.0],
    ])
    idx_y = [0, 1, 4, 5]
    idx_z = [2, 3, 6, 7]
    K_e = np.zeros((8, 8))
    M_e = np.zeros((8, 8))
    for i_loc, i_glob in enumerate(idx_y):
        for j_loc, j_glob in enumerate(idx_y):
            K_e[i_glob, j_glob] += K_plane[i_loc, j_loc]
            M_e[i_glob, j_glob] += M_plane[i_loc, j_loc]
    for i_loc, i_glob in enumerate(idx_z):
        for j_loc, j_glob in enumerate(idx_z):
            K_e[i_glob, j_glob] += K_plane[i_loc, j_loc]
            M_e[i_glob, j_glob] += M_plane[i_loc, j_loc]
    for i_loc, i_glob in enumerate(idx_y):
        for j_loc, j_glob in enumerate(idx_z):
            G_e[i_glob, j_glob] += G_sub[i_loc, j_loc]
            G_e[j_glob, i_glob] -= G_sub[i_loc, j_loc]
    return M_e, K_e, G_e

class RotorFEM:
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
        
        self.dof_per_node = 4
        
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

        self._assign_nodes()
        self._assemble()

    def _assign_nodes(self):
        if not self.is_dual_spool:
            for disk in self.disks:
                idx = np.argmin(np.abs(self.node_x_lp - disk.x_pos))
                disk.node = idx
            for brg in self.bearings:
                idx = np.argmin(np.abs(self.node_x_lp - brg.x_pos))
                brg.node = idx
        else:
            for disk in self.disks:
                if disk.spool == "LP":
                    idx = np.argmin(np.abs(self.node_x_lp - disk.x_pos))
                    disk.node = idx
                else:
                    idx = np.argmin(np.abs(self.node_x_hp - disk.x_pos))
                    disk.node = idx

            for brg in self.bearings:
                if brg.spool == "LP":
                    idx = np.argmin(np.abs(self.node_x_lp - brg.x_pos))
                    brg.node = idx
                elif brg.spool == "HP":
                    idx = np.argmin(np.abs(self.node_x_hp - brg.x_pos))
                    brg.node = idx
                elif brg.spool == "IS":
                    lp_idx = np.argmin(np.abs(self.node_x_lp - brg.x_pos))
                    hp_idx = np.argmin(np.abs(self.node_x_hp - brg.x_pos))
                    brg.lp_node = lp_idx
                    brg.hp_node = hp_idx

    def _assemble(self):
        n = self.n_dof
        M = np.zeros((n, n))
        K = np.zeros((n, n))
        C = np.zeros((n, n))
        
        G_lp = np.zeros((n, n))
        G_hp = np.zeros((n, n))

        mat = self.material
        sec_lp = self.section if not self.is_dual_spool else self.lp_section

        for e in range(self.n_elem_lp):
            Me, Ke, Ge = timoshenko_element_matrices(
                L=self.elem_L_lp, E=mat.E, G_mod=mat.G, rho=mat.rho,
                A=sec_lp.A, I_sec=sec_lp.I, Ip=sec_lp.Ip, kappa=sec_lp.kappa
            )
            dof_start = e * self.dof_per_node
            idx = list(range(dof_start, dof_start + 8))
            for i_loc in range(8):
                for j_loc in range(8):
                    M[idx[i_loc], idx[j_loc]] += Me[i_loc, j_loc]
                    K[idx[i_loc], idx[j_loc]] += Ke[i_loc, j_loc]
                    G_lp[idx[i_loc], idx[j_loc]] += Ge[i_loc, j_loc]

        if self.is_dual_spool:
            sec_hp = self.hp_section
            for e in range(self.n_elem_hp):
                Me, Ke, Ge = timoshenko_element_matrices(
                    L=self.elem_L_hp, E=mat.E, G_mod=mat.G, rho=mat.rho,
                    A=sec_hp.A, I_sec=sec_hp.I, Ip=sec_hp.Ip, kappa=sec_hp.kappa
                )
                dof_start = (self.n_nodes_lp + e) * self.dof_per_node
                idx = list(range(dof_start, dof_start + 8))
                for i_loc in range(8):
                    for j_loc in range(8):
                        M[idx[i_loc], idx[j_loc]] += Me[i_loc, j_loc]
                        K[idx[i_loc], idx[j_loc]] += Ke[i_loc, j_loc]
                        G_hp[idx[i_loc], idx[j_loc]] += Ge[i_loc, j_loc]

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

    def solve_eigenvalues(self, omega_spin: float) -> Tuple[np.ndarray, np.ndarray]:
        n = self.n_dof
        M = self.M_global
        K = self.K_global
        
        if self.is_dual_spool:
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

    def extract_natural_frequencies(self, eigvals: np.ndarray, n_modes: int = 6):
        mask = np.imag(eigvals) > 1.0
        pos_eigvals = eigvals[mask]
        sort_idx = np.argsort(np.imag(pos_eigvals))
        sorted_eig = pos_eigvals[sort_idx]
        n_take = min(n_modes, len(sorted_eig))
        selected = sorted_eig[:n_take]
        omega_d = np.abs(np.imag(selected))
        sigma = np.real(selected)
        omega_n = np.sqrt(sigma**2 + omega_d**2)
        zeta = -sigma / omega_n
        freqs_hz = omega_d / (2.0 * np.pi)
        return freqs_hz, zeta

def classify_whirl(freq_map: np.ndarray, rpm_range: np.ndarray) -> dict:
    n_speeds, n_modes = freq_map.shape
    classified = {}
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
        slope_a = np.nanmean(np.diff(freq_a[i_low:i_high]))
        slope_b = np.nanmean(np.diff(freq_b[i_low:i_high]))
        if slope_a >= slope_b:
            classified[f"FW{p+1}"] = freq_a
            classified[f"BW{p+1}"] = freq_b
        else:
            classified[f"FW{p+1}"] = freq_b
            classified[f"BW{p+1}"] = freq_a
    return classified

def find_critical_speeds(rpm_range: np.ndarray, classified: dict, sync_order: float = 1.0) -> List[dict]:
    f_sync = sync_order * rpm_range / 60.0
    criticals = []
    for mode_name, freqs in classified.items():
        diff = freqs - f_sync
        valid = ~np.isnan(diff)
        for i in range(len(rpm_range) - 1):
            if valid[i] and valid[i + 1]:
                if diff[i] * diff[i + 1] < 0:
                    frac = abs(diff[i]) / (abs(diff[i]) + abs(diff[i + 1]))
                    rpm_crit = rpm_range[i] + frac * (rpm_range[i + 1] - rpm_range[i])
                    freq_crit = sync_order * rpm_crit / 60.0
                    criticals.append({
                        "mode": mode_name,
                        "rpm": rpm_crit,
                        "freq_hz": freq_crit,
                        "order": sync_order,
                    })
    criticals.sort(key=lambda c: c["rpm"])
    return criticals

def run_simulation(
    lp_do, lp_di, hp_do, hp_di,
    k_lp_f, k_lp_r, k_hp_f, k_is,
    lp_fan_mass=3.6, lp_turb_mass=3.04, hp_comp_mass=2.4, hp_turb_mass=2.0
):
    inconel718 = Material(name="Inconel 718", E=205e9, rho=8190.0, nu=0.29)
    lp_shaft_sec = ShaftSection(D_outer=lp_do, D_inner=lp_di)
    hp_shaft_sec = ShaftSection(D_outer=hp_do, D_inner=hp_di)
    
    lp_fan = Disk(name="LP Fan/LPC", x_pos=0.060, mass=lp_fan_mass, Ip=0.020, Id=0.0104, spool="LP")
    lp_turbine = Disk(name="LP Turbine", x_pos=0.394, mass=lp_turb_mass, Ip=0.0144, Id=0.008, spool="LP")
    hp_compressor = Disk(name="HP Compressor", x_pos=0.140, mass=hp_comp_mass, Ip=0.012, Id=0.0064, spool="HP")
    hp_turbine = Disk(name="HP Turbine", x_pos=0.240, mass=hp_turb_mass, Ip=0.0096, Id=0.0048, spool="HP")

    front_lp_bearing = Bearing(name="Front LP Ball Brg", x_pos=-0.065, kxx=k_lp_f, kyy=k_lp_f, cxx=500.0, cyy=500.0, spool="LP")
    rear_lp_bearing = Bearing(name="Rear LP Roller Brg", x_pos=0.385, kxx=k_lp_r, kyy=k_lp_r, cxx=800.0, cyy=800.0, spool="LP")
    front_hp_bearing = Bearing(name="Front HP Casing Brg", x_pos=0.080, kxx=k_hp_f, kyy=k_hp_f, cxx=500.0, cyy=500.0, spool="HP")
    inter_shaft_bearing = Bearing(name="HP/LP Inter-Shaft Brg", x_pos=0.280, kxx=k_is, kyy=k_is, cxx=500.0, cyy=500.0, spool="IS")

    x_start = -0.065
    shaft_length = 0.540
    n_elements = 20

    rotor = RotorFEM(
        shaft_length=shaft_length, x_start=x_start, material=inconel718, section=lp_shaft_sec,
        n_elements=n_elements, disks=[lp_fan, lp_turbine, hp_compressor, hp_turbine],
        bearings=[front_lp_bearing, rear_lp_bearing, front_hp_bearing, inter_shaft_bearing],
        is_dual_spool=True, lp_section=lp_shaft_sec, hp_section=hp_shaft_sec,
        hp_shaft_length=0.200, hp_x_start=0.080, n_elements_hp=20
    )

    rpm_range = np.arange(0, 50500, 500)
    rpm_range[0] = 10

    n_speeds = len(rpm_range)
    freq_map = np.zeros((n_speeds, 6))
    for i, rpm in enumerate(rpm_range):
        omega = rpm * 2.0 * np.pi / 60.0
        eigvals, _ = rotor.solve_eigenvalues(omega)
        freqs, _ = rotor.extract_natural_frequencies(eigvals, n_modes=6)
        freq_map[i, :len(freqs)] = freqs

    classified = classify_whirl(freq_map, rpm_range)
    criticals_1x = find_critical_speeds(rpm_range, classified, sync_order=1.0)
    
    rpm_idle = 21000.0
    rpm_max = 38500.0
    
    crits_1x_rpm = [c["rpm"] for c in criticals_1x]
    in_range = [r for r in crits_1x_rpm if rpm_idle <= r <= rpm_max]
    below_idle = [r for r in crits_1x_rpm if r < rpm_idle]
    above_max = [r for r in crits_1x_rpm if r > rpm_max]

    margin_below = (rpm_idle - max(below_idle)) / max(below_idle) * 100.0 if below_idle else float("inf")
    margin_above = (min(above_max) - rpm_max) / rpm_max * 100.0 if above_max else float("inf")

    safe = len(in_range) == 0 and margin_below > 10.0 and margin_above > 15.0
    return safe, crits_1x_rpm, margin_below, margin_above

# Test config with real CAD sizes: LP = 22/14, HP = 36/24
# k_lp_f=0.35e8, k_lp_r=0.35e8, k_hp_f=12.0e8, k_is=4.0e8
res = run_simulation(0.022, 0.014, 0.036, 0.024, 0.35e8, 0.35e8, 12.0e8, 4.0e8)
print("REAL CAD SHAFTS:", res)
