"""
Turbine Simulator

Simulates turbine stage power balance, temperature drops, expansions,
and provides turbine efficiency maps based on pressure ratios and rotor speeds.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np

class TurbineSimulator:
    def __init__(self, cp_g=1148.0, gamma_g=1.33):
        self.cp_g = cp_g
        self.gamma_g = gamma_g

    def compute_performance(self, T_t4, P_t4, W_comp_required, flow_rate, speed_rpm):
        """
        Computes turbine exit parameters matching compressor load requirements.
        W_comp_required: specific work required by compressor (J/kg)
        flow_rate: mass flow rate through turbine (kg/s)
        """
        # Specific work produced by turbine (J/kg)
        # Power balance: W_turb = W_comp / (1.0 + f), but here we take specific work directly
        # Turbine temperature drop: T_t4 - T_t5 = W_turb / cp_g
        W_turb_required = W_comp_required
        
        # Temperature drop
        delta_T = W_turb_required / self.cp_g
        T_t5 = T_t4 - delta_T

        # Efficiency map based on speed and pressure ratio
        # Peak efficiency at optimal design speed
        opt_speed = 80000.0
        speed_ratio = speed_rpm / opt_speed
        
        # Parabolic speed dependency
        eta_t = 0.92 - 0.1 * (speed_ratio - 1.0)**2
        eta_t = np.clip(eta_t, 0.5, 0.96)

        # Solve for pressure ratio to extract this amount of work
        # T_t5 = T_t4 * (1 - eta_t * (1 - (P_t5 / P_t4)^((gamma-1)/gamma)))
        # So: (T_t4 - T_t5) / (T_t4 * eta_t) = 1 - (P_t5 / P_t4)^((gamma-1)/gamma)
        # (P_t5 / P_t4)^((gamma-1)/gamma) = 1 - delta_T / (T_t4 * eta_t)
        # P_t5 / P_t4 = (1 - delta_T / (T_t4 * eta_t))^(gamma / (gamma - 1))
        
        gamma_g_exp = (self.gamma_g - 1.0) / self.gamma_g
        temp_ratio = 1.0 - (delta_T / (T_t4 * eta_t))
        
        if temp_ratio <= 0.1:
            # Turbine choke/unphysical state
            P_t5 = P_t4 * 0.1
        else:
            P_t5 = P_t4 * (temp_ratio**(1.0 / gamma_g_exp))

        return {
            "T_t5": T_t5,
            "P_t5": P_t5,
            "eta_t": eta_t,
            "work_produced": W_turb_required,
            "power_produced_W": W_turb_required * flow_rate
        }
