"""
Digital Twin Engine Model for AEGIS-TF1

Combines thermodynamic cycle physics with real-time sensor streams using
an Extended Kalman Filter (EKF) acting as a Non-Linear Thermodynamic State Observer.
Tracks LP and HP spool speeds, combustor pressure, and estimates the unobservable
Turbine Inlet Temperature (T_t4) using turbine expansion exhaust gas temperature (EGT) measurements.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np
from ai.models.adaptive_mpc import NonlinearStateSpace

class DigitalTwinEngine:
    def __init__(self, dt=0.05):
        self.dt = dt
        self.physics_model = NonlinearStateSpace()
        
        # Twin states: [omega_N1 (rad/s), omega_N2 (rad/s), T_t4 (K), P3 (Pa)]
        self.x = np.array([15000.0 * np.pi / 30.0, 15000.0 * np.pi / 30.0, 650.0, 101325.0])
        
        # Covariance matrices
        self.P = np.diag([10.0, 10.0, 5.0, 1000.0])  # State uncertainty covariance
        self.Q = np.diag([1.0, 1.0, 0.1, 100.0])     # Process noise covariance
        self.R = np.diag([25.0, 25.0, 4.0, 0.01])     # Measurement noise covariance [N1, N2, EGT, P3_bar]
        
        # Degradation factor: 1.0 (perfect) to 0.8 (failed compressor/turbine efficiency)
        self.compressor_health = 1.0
        self.turbine_health = 1.0

    def compute_jacobian(self, state, inputs):
        """Numerically computes the state transition Jacobian (F)"""
        n_states = len(state)
        F = np.zeros((n_states, n_states))
        eps = 1e-4

        for i in range(n_states):
            state_plus = state.copy()
            state_plus[i] += eps
            deriv_plus = self.physics_model.derivatives(state_plus, inputs)

            state_minus = state.copy()
            state_minus[i] -= eps
            deriv_minus = self.physics_model.derivatives(state_minus, inputs)

            F[:, i] = (deriv_plus - deriv_minus) / (2.0 * eps)

        # F_discrete = I + F_continuous * dt
        return np.eye(n_states) + F * self.dt

    def predict(self, inputs):
        """EKF State prediction step: x_k|k-1 = f(x_k-1, u_k-1)"""
        # Apply degradation to physical parameters in physics model
        # eta_c in physics model can be set dynamically
        # Propagate states using non-linear physics
        self.x = self.physics_model.propagate(self.x, inputs, self.dt)

        # Propagate covariance P = F * P * F^T + Q
        F = self.compute_jacobian(self.x, inputs)
        self.P = np.dot(np.dot(F, self.P), F.T) + self.Q

    def update(self, measurements):
        """
        EKF Measurement correction step.
        measurements: array of [n1_rpm, n2_rpm, egt_kelvin, p3_bar]
        """
        omega_N1, omega_N2, T_t4, P3 = self.x
        n1_rpm_est = omega_N1 * 30.0 / np.pi
        n2_rpm_est = omega_N2 * 30.0 / np.pi
        
        # Calculate EGT using polytropic turbine expansion formula:
        # T_t5 = T_t4 * (P_amb / P3)**( (gamma_t - 1)/gamma_t * eta_t )
        # Using gamma_t = 1.33 and eta_t = 0.90 => exponent = 0.223
        p_amb = self.physics_model.P_amb
        pr = P3 / p_amb
        pr = max(1.0, pr)
        egt_est = T_t4 * ((1.0 / pr) ** 0.223)
        p3_bar_est = P3 / 100000.0

        z_est = np.array([n1_rpm_est, n2_rpm_est, egt_est, p3_bar_est])

        # Measurement Jacobian H (4x4)
        H = np.zeros((4, 4))
        H[0, 0] = 30.0 / np.pi
        H[1, 1] = 30.0 / np.pi
        # dEGT/dT_t4
        H[2, 2] = (1.0 / pr) ** 0.223
        # dEGT/dP3
        H[2, 3] = -0.223 * egt_est / P3
        # dP3_bar/dP3
        H[3, 3] = 1.0 / 100000.0

        # Kalman gain K = P * H^T * (H * P * H^T + R)^-1
        denom = np.dot(np.dot(H, self.P), H.T) + self.R
        K = np.dot(self.P, H.T) @ np.linalg.inv(denom)

        # Correct state
        y = measurements - z_est
        self.x += K @ y

        # Correct covariance P = (I - K*H) * P
        self.P = (np.eye(4) - K @ H) @ self.P

        # Track health degradation
        if y[3] < -0.2:
            self.compressor_health -= 0.0001
            self.compressor_health = max(0.8, self.compressor_health)

        if y[2] > 20.0:  # Higher EGT suggests turbine degradation
            self.turbine_health -= 0.0001
            self.turbine_health = max(0.8, self.turbine_health)

    def get_state(self):
        """Returns standard dict of states"""
        omega_N1, omega_N2, T_t4, P3 = self.x
        p_amb = self.physics_model.P_amb
        pr = P3 / p_amb
        pr = max(1.0, pr)
        egt = T_t4 * ((1.0 / pr) ** 0.223)
        return {
            "n1_rpm": float(omega_N1 * 30.0 / np.pi),
            "n2_rpm": float(omega_N2 * 30.0 / np.pi),
            "egt": float(egt),
            "p3_bar": float(P3 / 100000.0),
            "compressor_health": float(self.compressor_health),
            "turbine_health": float(self.turbine_health),
            "t4": float(T_t4),
            "tip_clearance": float(self.physics_model.get_tip_clearance(self.x))
        }
