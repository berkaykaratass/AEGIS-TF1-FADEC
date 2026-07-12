"""
Adaptive Model Predictive Control (AMPC) Module for AEGIS-TF1

Implements a non-linear 4D state-space model of the coaxial turbofan engine:
- States: [omega_N1 (LP spool rad/s), omega_N2 (HP spool rad/s), T_t4 (turbine inlet temp K), P3 (combustor pressure Pa)]
- Inputs: [Wf (fuel flow kg/s), V_ehd (EHD grid voltage kV), theta_vane (stator angle deg)]

Features:
- Dual-Spool Coaxial turbofan physics (LP/HP spool power matching, bypass ratio = 1.15)
- Tanrı Parametresi 1: Dynamic tip-clearance centrifugal and thermal expansion
- Tanrı Parametresi 2: Bypass 2nd-order transient flow separation bubble simulation
- Lyapunov stability checking

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np
from scipy.optimize import minimize

class NonlinearStateSpace:
    def __init__(self):
        # Engine physical properties
        self.J_N1 = 0.40       # LP spool moment of inertia (kg*m^2) (Fan + LPC + LPT)
        self.J_N2 = 0.20       # HP spool moment of inertia (kg*m^2) (HPC + HPT)
        self.tau_c = 0.15      # Combustor thermal delay time constant (seconds)
        self.V_comb = 0.008    # Combustor volume (m^3)
        self.gamma = 1.4       # Ratio of specific heats
        self.R = 287.05        # Gas constant (J/kg*K)
        self.cp = 1005.0       # Specific heat constant (J/kg*K)
        
        # Reference ambient conditions
        self.T_amb = 288.15
        self.P_amb = 101325.0
        
        # Bypass ratio
        self.BPR = 1.15

        # Dynamic Tip Clearance Parameters
        self.delta_cold = 0.00045   # 0.45 mm cold clearance
        self.L_blade = 0.094        # 94 mm blade height
        self.R_case = 0.094         # casing radius
        self.rho = 8190.0           # density (Inconel 718)
        self.E = 205e9              # Elastic Modulus (Inconel 718)
        self.alpha_blade = 13e-6    # thermal expansion coeff
        self.alpha_casing = 13e-6
        self.T_case = 288.15        # casing temperature state

        # Flow Separation Parameters
        self.tau_sep = 0.1          # time constant
        self.zeta = 0.7             # damping ratio
        self.kappa = 0.5            # sensitivity
        self.Phi_crit = 2.0         # threshold acceleration
        self.gamma_sep = 0.0        # separation index state
        self.dgamma_sep_dt = 0.0
        self.prev_m_bypass = 0.0

        # Environmental parameter & degradation deformation
        self.delta_T_day = 0.0                  # ISA temperature deviation (K)
        self.compressor_fouling_factor = 0.0    # 0.0 (clean) to 1.0 (degraded)
        self.turbine_erosion_factor = 0.0       # 0.0 (clean) to 1.0 (degraded)

        # Station Graph node properties: P (Pa), T (K), W (kg/s), h (J/kg), Mach
        self.stations = {
            2:  {"P": 101325.0, "T": 288.15, "W": 12.0, "h": 289000.0, "Mach": 0.45},
            3:  {"P": 101325.0 * 12.0, "T": 600.0, "W": 12.0, "h": 603000.0, "Mach": 0.30},
            4:  {"P": 101325.0 * 11.5, "T": 1600.0, "W": 12.3, "h": 1.7e6, "Mach": 0.15},
            45: {"P": 101325.0 * 4.0, "T": 1100.0, "W": 12.3, "h": 1.1e6, "Mach": 0.25},
            5:  {"P": 101325.0 * 1.5, "T": 850.0, "W": 12.3, "h": 8.5e5, "Mach": 0.35},
            9:  {"P": 101325.0, "T": 650.0, "W": 12.3, "h": 6.5e5, "Mach": 0.85}
        }

    def derivatives(self, state, inputs):
        """
        Calculates state derivatives using Station-Based Quasi-1D flow network matching.
        state: [omega_N1, omega_N2, T_t4, P3]
        inputs: [Wf, V_ehd, theta_vane]
        """
        omega_N1, omega_N2, T_t4, P3 = state
        Wf, V_ehd, theta_vane = inputs

        Wf = np.clip(Wf, 0.0, 3.0)
        omega_N1 = max(100.0, omega_N1)
        omega_N2 = max(100.0, omega_N2)
        T_t4 = np.clip(T_t4, 200.0, 2500.0)
        P3 = np.clip(P3, 1e4, 2e6)

        # 1. Environment definition (ISA + delta_T_day)
        T2 = self.T_amb + self.delta_T_day
        P2 = self.P_amb

        # 2. Corrected speed Nc and Compressor Map lookup
        Nc = (omega_N2 * 30.0 / np.pi) / np.sqrt(T2 / 288.15)
        clearance_mm = self.get_tip_clearance(state) * 1000.0
        clearance_penalty = max(0.0, (clearance_mm - 0.45) * 0.15)

        # Apply fouling efficiency penalty
        eta_hpc = 0.85 - clearance_penalty - 0.01 * max(0.0, self.delta_T_day / 15.0) - 0.05 * self.compressor_fouling_factor
        eta_hpc = np.clip(eta_hpc, 0.6, 0.95)

        # 3. Iterative solver: Match compressor flow to turbine nozzle guide throat area
        C_throat = 0.00035
        
        # Apply numerical fixed-point solver to converge on flow continuity
        for _ in range(5):
            speed_pct = (omega_N1 * 30.0 / np.pi) / 35000.0 * 100.0
            # Fouling degrades compressor surge pressure limit
            surge_pr = (1.0 + 13.0 * (Nc / 35000.0)**2) * (1.0 - 0.12 * self.compressor_fouling_factor)
            pr_current = P3 / P2
            stall_margin = (surge_pr - pr_current) / surge_pr
            
            is_stalled = (stall_margin <= 0.08)
            
            if is_stalled:
                Wc = 0.15 * 1.2 * (omega_N2 / 8000.0) * (P3 / 1e5)
            else:
                Wc = 1.2 * (omega_N2 / 8000.0) * (P3 / 1e5)
                
            # Apply inlet temperature density correction to get physical mass flow
            W_comp = Wc * (P2 / 101325.0) / np.sqrt(T2 / 288.15)
            
            P4_target = (W_comp + Wf) * np.sqrt(T_t4) / (C_throat * 1e5)
            P3 += 0.3 * (P4_target / 0.96 - P3)
            P3 = np.clip(P3, 1e4, 2e6)

        P4 = P3 * 0.96
        W3 = W_comp
        W4 = W3 + Wf

        # 4. Spool matching and power terms
        pr = P3 / P2
        pr_lpc = pr**0.35
        pr_hpc = pr**0.65

        # Work of LPC and Fan
        eta_lpc = 0.85
        W_lpc_spec = self.cp * T2 * (pr_lpc**((self.gamma - 1.0) / self.gamma) - 1.0) / eta_lpc
        power_lpc = W_lpc_spec * W3

        eta_fan = 0.88
        mass_flow_bypass = self.BPR * W3
        W_fan_spec = self.cp * T2 * (pr_lpc**((self.gamma - 1.0) / self.gamma) - 1.0) / eta_fan
        power_fan = W_fan_spec * mass_flow_bypass * (1.0 + 0.15 * self.gamma_sep)

        # HPC Work
        T_t25 = T2 * pr_lpc**((self.gamma - 1.0) / self.gamma)
        W_hpc_spec = self.cp * T_t25 * (pr_hpc**((self.gamma - 1.0) / self.gamma) - 1.0) / eta_hpc
        power_hpc = W_hpc_spec * W3

        # HP Turbine (Erosion reduces turbine efficiency)
        eta_hpt = 0.90 - 0.001 * (theta_vane - 15.0)**2 - 0.04 * self.turbine_erosion_factor
        eta_hpt = np.clip(eta_hpt, 0.6, 0.95)
        W_hpt_spec = self.cp * T_t4 * (1.0 - (1.0 / pr_hpc)**((self.gamma - 1.0) / self.gamma)) * eta_hpt
        power_hpt = W_hpt_spec * W4

        # LP Turbine
        T_t45 = T_t4 - W_hpt_spec / self.cp
        T_t45 = max(288.15, T_t45)

        eta_lpt = 0.90 - 0.03 * self.turbine_erosion_factor
        W_lpt_spec = self.cp * T_t45 * (1.0 - (1.0 / pr_lpc)**((self.gamma - 1.0) / self.gamma)) * eta_lpt
        power_lpt = W_lpt_spec * W4

        # EHD voltage assists spools
        ehd_lp_assist = V_ehd * 50.0
        ehd_hp_assist = V_ehd * 100.0

        # Spool speed derivatives
        d_omega_N1 = (power_lpt - power_fan - power_lpc + ehd_lp_assist) / (self.J_N1 * omega_N1)
        d_omega_N2 = (power_hpt - power_hpc + ehd_hp_assist) / (self.J_N2 * omega_N2)

        # Thermal dynamics (combustor delay)
        T_t4_ss = T2 + (Wf * 4.3e7 * 0.98) / (self.cp * (W3 + 1e-5))
        T_t4_ss = np.clip(T_t4_ss, 288.15, 2500.0)
        d_T_t4 = (T_t4_ss - T_t4) / self.tau_c

        # Quasi-1D Pressure dynamics
        m_in = W3 + Wf
        m_out = W3 * np.sqrt(T2 / T_t4)
        d_P3 = (self.gamma * self.R * T_t4 / self.V_comb) * (m_in - m_out)

        if is_stalled:
            d_P3 -= 5.0e5
            d_T_t4 += 150.0 / self.tau_c

        d_omega_N1 = np.clip(d_omega_N1, -50000.0, 50000.0)
        d_omega_N2 = np.clip(d_omega_N2, -50000.0, 50000.0)
        d_T_t4 = np.clip(d_T_t4, -20000.0, 20000.0)
        d_P3 = np.clip(d_P3, -1e7, 1e7)

        # 5. Populate Station Graph Node Properties for feedback
        self.stations[2] = {"P": P2, "T": T2, "W": W3, "h": self.cp*T2, "Mach": 0.45}
        self.stations[3] = {"P": P3, "T": T_t25, "W": W3, "h": self.cp*T_t25, "Mach": 0.30}
        self.stations[4] = {"P": P4, "T": T_t4, "W": W4, "h": self.cp*T_t4, "Mach": 0.15}
        self.stations[45] = {"P": P4 * 0.4, "T": T_t45, "W": W4, "h": self.cp*T_t45, "Mach": 0.25}
        
        T5 = T_t45 - W_lpt_spec / self.cp
        P5 = P4 * 0.15
        self.stations[5] = {"P": P5, "T": T5, "W": W4, "h": self.cp*T5, "Mach": 0.35}

        pr_nozzle = P5 / self.P_amb
        pr_nozzle = max(1.0, pr_nozzle)
        T9 = T5 * (1.0 / pr_nozzle)**0.286
        Mach_9 = np.sqrt(max(0.0, 2.0 * ((pr_nozzle)**0.286 - 1.0) / (self.gamma - 1.0)))
        self.stations[9] = {"P": self.P_amb, "T": T9, "W": W4, "h": self.cp*T9, "Mach": min(1.0, Mach_9)}

        return np.array([d_omega_N1, d_omega_N2, d_T_t4, d_P3], dtype=np.float32)

    def propagate(self, state, inputs, dt):
        """Propagates state forward using RK4 while stepping physical parameters"""
        # Calculate bypass mass flow derivative before step
        omega_N2, P3 = state[1], state[3]
        mass_flow_core = 1.2 * (omega_N2 / 8000.0) * (P3 / 1e5)
        m_bypass = self.BPR * mass_flow_core
        dmbypass_dt = (m_bypass - self.prev_m_bypass) / dt
        self.prev_m_bypass = m_bypass

        # Solve 2nd-order flow separation ODE using Euler-Maruyama/Euler step
        d2_gamma_sep = (self.kappa * max(0.0, dmbypass_dt - self.Phi_crit) - 
                        2.0 * self.zeta * self.dgamma_sep_dt - self.gamma_sep) / (self.tau_sep)
        self.gamma_sep += self.dgamma_sep_dt * dt
        self.dgamma_sep_dt += d2_gamma_sep * dt
        self.gamma_sep = max(0.0, min(2.0, self.gamma_sep))

        # Solve Casing thermal lag
        T_t4 = state[2]
        self.T_case += dt * (T_t4 - self.T_case) / 2.0

        # Run RK4 state propagation
        k1 = self.derivatives(state, inputs)
        k2 = self.derivatives(state + 0.5 * dt * k1, inputs)
        k3 = self.derivatives(state + 0.5 * dt * k2, inputs)
        k4 = self.derivatives(state + dt * k3, inputs)
        next_state = state + (dt / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)
        
        # Clamp state values
        next_state[0] = max(100.0, next_state[0])
        next_state[1] = max(100.0, next_state[1])
        next_state[2] = np.clip(next_state[2], 200.0, 2500.0)
        next_state[3] = np.clip(next_state[3], 1.5e4, 2e6)
        
        return next_state

    def get_tip_clearance(self, state):
        """Calculates dynamic blade tip clearance delta_tip in meters"""
        _, omega_N2, T_t4, _ = state
        
        # Centrifugal stretch
        delta_L_cf = (self.rho * (omega_N2**2) * (self.L_blade**3)) / (3.0 * self.E)
        
        # Thermal expansion of blade (scaled gradient)
        delta_L_thermal_blade = self.alpha_blade * self.L_blade * (T_t4 - 288.15) * 0.15
        
        # Thermal expansion of casing (scaled gradient)
        delta_L_thermal_casing = self.alpha_casing * self.R_case * (self.T_case - 288.15) * 0.15
        
        delta_tip = self.delta_cold - delta_L_cf - delta_L_thermal_blade + delta_L_thermal_casing
        return max(0.0, delta_tip)


class AdaptiveMPC:
    def __init__(self, sys_model, N_p=5, N_c=2, dt=0.02):
        self.model = sys_model
        self.Np = N_p
        self.Nc = N_c
        self.dt = dt

        # State weights [omega_N1, omega_N2, T_t4, P3]
        self.Q = np.diag([0.5, 1.0, 0.01, 0.1])
        self.R = np.diag([10.0, 0.1, 0.05])

        # Input constraints
        self.u_min = np.array([0.01, 0.0, -15.0])
        self.u_max = np.array([2.5, 45.0, 30.0])

        # State constraints
        self.x_min = np.array([1000.0, 1000.0, 300.0, 5e4])
        self.x_max = np.array([115000.0, 115000.0, 2500.0, 2e6])

    def surge_loss(self, sm, pr):
        """Surge penalty coupled with Brayton thermal efficiency."""
        alpha = 10.0
        gamma_exp = (1.4 - 1.0) / 1.4
        if pr > 1.0:
            eta_th = 1.0 - (1.0 / (pr**gamma_exp))
        else:
            eta_th = 0.0
        return np.exp(-alpha * sm) * (1.0 - eta_th)

    def compute_cost(self, u_sequence, current_state, target_state, prev_u):
        cost = 0.0
        state = current_state.copy()
        u_seq = u_sequence.reshape(self.Nc, 3)
        last_u = prev_u.copy()

        for k in range(self.Np):
            u = u_seq[k] if k < self.Nc else u_seq[-1]
            state = self.model.propagate(state, u, self.dt)

            state_error = state - target_state
            cost += np.dot(np.dot(state_error.T, self.Q), state_error)

            u_error = u - last_u
            cost += np.dot(np.dot(u_error.T, self.R), u_error)

            # Surge Margin calculation (influenced by flow separation)
            speed_pct = (state[1] / (100000.0 * np.pi / 30.0)) * 100.0
            speed_pct = np.clip(speed_pct, 50.0, 110.0)
            flow = 14.0 * (speed_pct / 80.0)
            pr = state[3] / 101325.0
            pr = max(1.0, pr)
            
            flow_stall = 11.0 * (speed_pct / 80.0)
            pr_stall = 6.8 * (speed_pct / 80.0)
            
            # Flow separation directly degrades the surge margin
            sm = (flow * pr_stall) / (flow_stall * pr) - 1.0 - 0.12 * self.model.gamma_sep
            cost += 500.0 * self.surge_loss(sm, pr)
            
            # Constraint violation soft penalties
            cost += np.sum(np.maximum(0.0, state - self.x_max) ** 2) * 1e4
            cost += np.sum(np.maximum(0.0, self.x_min - state) ** 2) * 1e4

            last_u = u

        return cost

    def optimize_control(self, current_state, target_state, prev_u):
        initial_u = np.tile(prev_u, self.Nc)
        bounds = [(self.u_min[i], self.u_max[i]) for _ in range(self.Nc) for i in range(3)]

        res = minimize(
            fun=self.compute_cost,
            x0=initial_u,
            args=(current_state, target_state, prev_u),
            method='SLSQP',
            bounds=bounds,
            options={'maxiter': 10, 'ftol': 1e-3}
        )

        return res.x[:3]

    def check_lyapunov_stability(self, current_state, target_state, next_state):
        P = self.Q
        err_curr = current_state - target_state
        err_next = next_state - target_state

        V_curr = np.dot(np.dot(err_curr.T, P), err_curr)
        V_next = np.dot(np.dot(err_next.T, P), err_next)
        V_dot = (V_next - V_curr) / self.dt

        return (V_curr > 0) and (V_dot < 0.0), V_curr, V_dot
