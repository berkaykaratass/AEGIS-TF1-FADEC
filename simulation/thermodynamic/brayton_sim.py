"""
Brayton Cycle Thermodynamic Simulator

Models a station-by-station gas turbine cycle:
0: Ambient air
2: Compressor inlet / diffuser exit
3: Compressor exit
4: Combustion chamber exit / turbine inlet
5: Turbine exit / nozzle inlet
9: Nozzle exit / exhaust plume

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np

class BraytonCycleSimulator:
    def __init__(self, 
                 gamma_a=1.4, 
                 gamma_g=1.33, 
                 cp_a=1005.0, 
                 cp_g=1148.0, 
                 Q_R=4.3e7, 
                 eta_b=0.98, 
                 eta_c=0.85, 
                 eta_t=0.90, 
                 eta_n=0.95):
        self.gamma_a = gamma_a
        self.gamma_g = gamma_g
        self.cp_a = cp_a
        self.cp_g = cp_g
        self.Q_R = Q_R
        self.eta_b = eta_b
        self.eta_c = eta_c
        self.eta_t = eta_t
        self.eta_n = eta_n
        self.R_air = 287.05

    def compute_cycle(self, T_amb, P_amb, M_flight, r_p, T4_max, bleed_ratio=0.05):
        """
        Computes the complete cycle with secondary cooling flow bleed.
        All inputs are SI units: T in K, P in Pa, velocities in m/s.
        """
        # Speed of sound
        a_0 = np.sqrt(self.gamma_a * self.R_air * T_amb)
        V_0 = M_flight * a_0

        # Totals at station 2 (Compressor Inlet)
        T_t2 = T_amb * (1.0 + 0.5 * (self.gamma_a - 1.0) * M_flight**2)
        P_t2 = P_amb * (T_t2 / T_amb)**(self.gamma_a / (self.gamma_a - 1.0))
        V_2 = V_0

        # Station 2.5 & 3 (Dual-Spool Compressor Exit)
        # LP compressor pressure ratio (PR_LPC) and HP compressor pressure ratio (PR_HPC)
        # OPR = PR_LPC * PR_HPC
        r_p_lpc = r_p**0.45
        r_p_hpc = r_p**0.55
        
        # LPC (LP Compressor)
        P_t25 = P_t2 * r_p_lpc
        gamma_a_exp = (self.gamma_a - 1.0) / self.gamma_a
        T_t25_ideal = T_t2 * (r_p_lpc**gamma_a_exp)
        T_t25 = T_t2 + (T_t25_ideal - T_t2) / self.eta_c
        W_comp_lpc = self.cp_a * (T_t25 - T_t2)
        
        # HPC (HP Compressor)
        P_t3 = P_t25 * r_p_hpc
        T_t3_ideal = T_t25 * (r_p_hpc**gamma_a_exp)
        T_t3 = T_t25 + (T_t3_ideal - T_t25) / self.eta_c
        W_comp_hpc = self.cp_a * (T_t3 - T_t25)

        # Station 4 (Combustor Exit)
        T_t4 = T4_max
        P_t4 = P_t3 * 0.97  # 3% combustor pressure loss

        # Fuel-air ratio (with secondary cooling flow bleed)
        b = bleed_ratio
        f_local = (self.cp_g * (T_t4 - T_t3)) / (self.Q_R * self.eta_b - self.cp_g * T_t4)
        if f_local <= 0:
            raise ValueError("Flameout condition or unphysical temperature inputs.")
        f_overall = f_local * (1.0 - b)

        # Station 4.5 & 5 (Dual-Spool Turbine Expansion)
        gamma_g_exp = (self.gamma_g - 1.0) / self.gamma_g
        # HPT (High-Pressure Turbine) drives HPC
        W_turb_hpt = W_comp_hpc / (1.0 - b + f_overall)
        T_t45 = T_t4 - W_turb_hpt / self.cp_g
        pr_turb_hpt = (1.0 - (1.0 - T_t45 / T_t4) / self.eta_t)**(self.gamma_g / (self.gamma_g - 1.0))
        P_t45 = P_t4 * pr_turb_hpt
        
        # LPT (Low-Pressure Turbine) drives LPC
        W_turb_lpt = W_comp_lpc / (1.0 - b + f_overall)
        T_t5_unmixed = T_t45 - W_turb_lpt / self.cp_g
        pr_turb_lpt = (1.0 - (1.0 - T_t5_unmixed / T_t45) / self.eta_t)**(self.gamma_g / (self.gamma_g - 1.0))
        P_t5 = P_t45 * pr_turb_lpt
        
        # Mix the cooling air (at T_t3) with the turbine exit gas
        T_t5 = ((1.0 - b + f_overall) * self.cp_g * T_t5_unmixed + b * self.cp_a * T_t3) / ((1.0 + f_overall) * self.cp_g)

        # Station 9 (Nozzle Exit)
        P_t9 = P_amb
        V_e_sq = 2.0 * self.cp_g * self.eta_n * T_t5 * (1.0 - (P_amb / P_t5)**gamma_g_exp)
        V_e = np.sqrt(max(0.0, V_e_sq))
        T_t9 = T_t5 - (V_e**2) / (2.0 * self.cp_g)

        # Performance metrics
        F_specific = (1.0 + f_overall) * V_e - V_0
        TSFC = f_overall / F_specific if F_specific > 0 else float('inf')

        kinetic_out = (1.0 + f_overall) * V_e**2
        kinetic_in = V_0**2
        heat_in = 2.0 * f_overall * self.Q_R
        
        eta_thermal = (kinetic_out - kinetic_in) / heat_in if heat_in > 0 else 0.0
        eta_prop = (2.0 * V_0) / ((1.0 + f_overall) * V_e + V_0) if ((1.0 + f_overall) * V_e + V_0) > 0 else 0.0
        eta_overall = eta_thermal * eta_prop

        return {
            "T_t": [T_amb, T_t2, T_t3, T_t4, T_t5, T_t9],
            "P_t": [P_amb, P_t2, P_t3, P_t4, P_t5, P_t9],
            "V": [V_0, V_2, 0.0, 0.0, 0.0, V_e],
            "F_specific": F_specific,
            "TSFC": TSFC,
            "eta_thermal": eta_thermal,
            "eta_propulsive": eta_prop,
            "eta_overall": eta_overall,
            "f": f_overall
        }

    def generate_ts_diagram(self, results):
        """Generates T-s coordinates for diagram plotting"""
        T = results["T_t"]
        P = results["P_t"]
        
        # Entropy change relative to state 0: s - s0 = cp*ln(T/T0) - R*ln(P/P0)
        s = [0.0]
        # Diffuser (0 -> 2)
        s.append(self.cp_a * np.log(T[1] / T[0]) - self.R_air * np.log(P[1] / P[0]))
        # Compressor (2 -> 3)
        s.append(s[-1] + self.cp_a * np.log(T[2] / T[1]) - self.R_air * np.log(P[2] / P[1]))
        # Combustor (3 -> 4)
        s.append(s[-1] + self.cp_g * np.log(T[3] / T[2]) - 287.05 * np.log(P[3] / P[2]))
        # Turbine (4 -> 5)
        s.append(s[-1] + self.cp_g * np.log(T[4] / T[3]) - 287.05 * np.log(P[4] / P[3]))
        # Nozzle (5 -> 9)
        s.append(s[-1] + self.cp_g * np.log(T[5] / T[4]) - 287.05 * np.log(P[5] / P[4]))
        
        return s, T

    def generate_pv_diagram(self, results):
        """Generates P-v coordinates (v = R*T/P)"""
        P = results["P_t"]
        T = results["T_t"]
        
        # Specific volumes
        v = []
        for i in range(len(P)):
            v.append(self.R_air * T[i] / P[i])
            
        return v, P
