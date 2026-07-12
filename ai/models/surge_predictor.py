"""
Surge Predictor Gated Recurrent Unit (GRU) & CBF Safety Module

Implements a 7D GRU policy network in pure NumPy to resolve transient flow inertia.
Features a Control Barrier Function (CBF) gating fuel flow commands based on
inter-spool shear stress (|N2 - N1| <= 80k RPM) and dynamic blade tip clearance (<= 80 microns).

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np

class CompressorEnvironment:
    """
    Simulates a Two-Spool coaxial turbofan compressor/fan environment.
    State vector: [flow, pr, n1, n2, slip_rate, surge_margin, d_sm_dt]
    """
    def __init__(self, dt=0.01):
        self.dt = dt
        self.reset()
        
        # Reference limits
        self.flow_stall_ref = 11.0
        self.pr_stall_ref = 6.8

    def reset(self):
        self.n1 = 15000.0        # LP Spool speed [RPM]
        self.n2 = 15000.0        # HP Spool speed [RPM]
        self.flow = 14.0         # kg/s core flow
        self.pr = 5.0            # pressure ratio
        self.surge_margin = 0.25
        self.prev_surge_margin = 0.25
        self.gamma_sep = 0.0     # flow separation index
        self.delta_tip = 0.00045 # 0.45 mm tip clearance
        self.time_step = 0
        self.is_surged = False
        return self.get_state()

    def get_state(self):
        slip_rate = (self.n2 - self.n1) / (self.n2 + 1e-5)
        d_sm_dt = (self.surge_margin - self.prev_surge_margin) / self.dt
        return np.array([
            self.flow,
            self.pr,
            self.n1,
            self.n2,
            slip_rate,
            self.surge_margin,
            d_sm_dt
        ], dtype=np.float32)

    def step(self, action_fuel_adj):
        """
        Steps environment.
        action_fuel_adj: Fuel metering adjustment (-1.0 to 1.0)
        """
        self.time_step += 1
        self.prev_surge_margin = self.surge_margin

        # Physics simulation: fuel adjustment affects pressure ratio
        self.pr += action_fuel_adj * 0.2 + (np.random.randn() * 0.02)
        self.flow -= (action_fuel_adj * 0.15 + (self.pr - 5.0) * 0.1)
        self.flow += (np.random.randn() * 0.05)

        # Enforce physical constraints
        self.flow = max(0.5, self.flow)
        self.pr = max(1.0, self.pr)

        # Spool speed acceleration dynamics
        self.n2 += action_fuel_adj * 500.0 - (self.pr - 5.0) * 100.0
        self.n1 += action_fuel_adj * 300.0 - self.gamma_sep * 150.0
        
        # Enforce speed limits
        self.n1 = np.clip(self.n1, 1000.0, 110000.0)
        self.n2 = np.clip(self.n2, 1000.0, 110000.0)

        # 2nd-order flow separation simulation
        dmbypass_dt = (self.flow * 1.15) / self.dt
        if dmbypass_dt > 2.0:
            self.gamma_sep += 0.05
        else:
            self.gamma_sep -= 0.02
        self.gamma_sep = np.clip(self.gamma_sep, 0.0, 1.0)

        # Centrifugal tip clearance stretch at N2 speed (omega)
        omega_N2 = self.n2 * np.pi / 30.0
        delta_L_cf = (8190.0 * (omega_N2**2) * (0.094**3)) / (3.0 * 205e9)
        self.delta_tip = max(0.0, 0.00045 - delta_L_cf - 1.2e-4)

        # Surge margin calculation
        flow_stall = self.flow_stall_ref * (self.n2 / 15000.0)
        pr_stall = self.pr_stall_ref * (self.n2 / 15000.0)
        self.surge_margin = (self.flow * pr_stall) / (flow_stall * self.pr) - 1.0 - 0.12 * self.gamma_sep

        reward = 1.0  # survival reward
        
        # Check surge or other failure limits
        if self.surge_margin < 0.0:
            self.is_surged = True
            reward = -100.0
            done = True
        elif self.delta_tip <= 0.00008:
            # Rubbing casing penalty
            reward = -50.0
            done = True
        elif self.time_step >= 100:
            done = True
        else:
            done = False
            # Penalize low surge margin
            if self.surge_margin < 0.1:
                reward -= (0.1 - self.surge_margin) * 10.0

        return self.get_state(), reward, done, {}


class SurgePredictor:
    """
    7D-Input, 16-Hidden GRU Policy Network with CBF safety filter built in pure NumPy.
    Input size: 7 [flow_core, pr, n1, n2, slip_rate, surge_margin, d_sm_dt]
    Output size: 2 [surge_probability, fuel_adjustment]
    """
    def __init__(self, input_dim=7, hidden_dim=16, output_dim=2, lr=0.002):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.lr = lr

        # Weight initialization for gates
        # Update gate weights
        self.W_xz = np.random.randn(hidden_dim, input_dim) * np.sqrt(2.0 / input_dim)
        self.W_hz = np.random.randn(hidden_dim, hidden_dim) * np.sqrt(2.0 / hidden_dim)
        self.b_z = np.zeros((hidden_dim, 1))

        # Reset gate weights
        self.W_xr = np.random.randn(hidden_dim, input_dim) * np.sqrt(2.0 / input_dim)
        self.W_hr = np.random.randn(hidden_dim, hidden_dim) * np.sqrt(2.0 / hidden_dim)
        self.b_r = np.zeros((hidden_dim, 1))

        # Candidate state weights
        self.W_xh = np.random.randn(hidden_dim, input_dim) * np.sqrt(2.0 / input_dim)
        self.W_hh = np.random.randn(hidden_dim, hidden_dim) * np.sqrt(2.0 / hidden_dim)
        self.b_h = np.zeros((hidden_dim, 1))

        # Output linear layer weights
        self.W_y = np.random.randn(output_dim, hidden_dim) * np.sqrt(2.0 / hidden_dim)
        self.b_y = np.zeros((output_dim, 1))

        # Hidden state initialization
        self.h = np.zeros((hidden_dim, 1))

        # Value network (Critic) for PPO Baseline
        self.W_v = np.random.randn(1, hidden_dim) * np.sqrt(2.0 / hidden_dim)
        self.b_v = np.zeros((1, 1))

    def reset_hidden(self):
        self.h = np.zeros((self.hidden_dim, 1))

    def sigmoid(self, x):
        x = np.clip(x, -50.0, 50.0)
        return 1.0 / (1.0 + np.exp(-x))

    def tanh(self, x):
        return np.tanh(x)

    def tanh_derivative(self, x):
        return 1.0 - np.tanh(x)**2

    def forward_step(self, x, h_prev):
        """Executes a single recurrent GRU step forward"""
        if len(x.shape) == 1:
            x = x.reshape(-1, 1)
        if len(h_prev.shape) == 1:
            h_prev = h_prev.reshape(-1, 1)

        # Update Gate
        z = self.sigmoid(np.dot(self.W_xz, x) + np.dot(self.W_hz, h_prev) + self.b_z)
        
        # Reset Gate
        r = self.sigmoid(np.dot(self.W_xr, x) + np.dot(self.W_hr, h_prev) + self.b_r)
        
        # Candidate Hidden State
        h_tilde = self.tanh(np.dot(self.W_xh, x) + np.dot(self.W_hh, r * h_prev) + self.b_h)
        
        # Hidden State update
        h = (1.0 - z) * h_prev + z * h_tilde
        
        # Output layers
        y = np.dot(self.W_y, h) + self.b_y
        out_prob = self.sigmoid(y[0:1, :])
        out_adj = self.tanh(y[1:2, :])
        out = np.vstack([out_prob, out_adj])

        return out, h, z, r, h_tilde

    def forward(self, x):
        """Inference wrapper that tracks internal hidden state"""
        out, self.h, _, _, _ = self.forward_step(x, self.h)
        return out

    def predict(self, x):
        """Inference wrapper returning flat array"""
        out = self.forward(x)
        return out.flatten()

    def get_value(self, h):
        """Returns value state prediction for Critic"""
        val = np.dot(self.W_v, h) + self.b_v
        return float(val.item() if hasattr(val, "item") else val)

    def apply_cbf_filter(self, Wf_cmd, n1, n2, delta_tip):
        """
        Gating function implementing Two-Spool Safe-DRL Control Barrier Function:
        1. Lean Blow-Out protection (min fuel).
        2. HP/LP spool shear speed limits (|N2 - N1| <= 80,000 RPM).
        3. Blade-to-casing clearance limits (hard -4% cut at <= 80 microns).
        """
        # 1. Lean Blow-Out limit
        Wf_safe = max(0.02, Wf_cmd)
        
        # 2. HP/LP Spool shear limits
        if abs(n2 - n1) > 80000.0:
            Wf_safe *= 0.95  # curtail fuel to drop speed difference
            
        # 3. Dynamic blade tip clearance constraint (0.08 mm is 0.00008 m)
        if delta_tip <= 0.00008:
            Wf_safe *= 0.96  # -4% Hard Fuel Cut
            
        return Wf_safe

    def train_ppo_step(self, states, actions, old_log_probs, advantages, returns, hs):
        """
        Proximal Policy Optimization (PPO) step for NumPy GRU Cell.
        """
        eps_clip = 0.2
        c1 = 0.5 # Critic coefficient
        sigma_action = 0.5

        # Accumulated gradients
        dW_xz, dW_hz, db_z = np.zeros_like(self.W_xz), np.zeros_like(self.W_hz), np.zeros_like(self.b_z)
        dW_xr, dW_hr, db_r = np.zeros_like(self.W_xr), np.zeros_like(self.W_hr), np.zeros_like(self.b_r)
        dW_xh, dW_hh, db_h = np.zeros_like(self.W_xh), np.zeros_like(self.W_hh), np.zeros_like(self.b_h)
        dW_y, db_y = np.zeros_like(self.W_y), np.zeros_like(self.b_y)
        dW_v, db_v = np.zeros_like(self.W_v), np.zeros_like(self.b_v)

        T = len(states)
        dh_next = np.zeros((self.hidden_dim, 1))

        # We execute BPTT back through time
        for t in reversed(range(T)):
            x = states[t].reshape(-1, 1)
            a = actions[t]
            adv = advantages[t]
            ret = returns[t]
            h_prev = hs[t].reshape(-1, 1)
            old_log_prob = old_log_probs[t]

            # Forward pass to reconstruct intermediate activations
            out, h_curr, z, r, h_tilde = self.forward_step(x, h_prev)

            # 1. Critic Update (MSE Loss)
            v_est = np.dot(self.W_v, h_curr) + self.b_v
            dv = v_est - ret
            dW_v += np.dot(dv, h_curr.T)
            db_v += dv

            # 2. Actor Update (Clipped PPO Loss)
            mu = out[1, 0]
            new_log_prob = -0.5 * np.log(2 * np.pi * sigma_action**2) - ((a - mu)**2) / (2 * sigma_action**2)
            ratio = np.exp(new_log_prob - old_log_prob)

            # Clipped objective gradient factor
            surr1 = ratio * adv
            surr2 = np.clip(ratio, 1.0 - eps_clip, 1.0 + eps_clip) * adv
            
            # Policy gradient if ratio doesn't push beyond clipping boundaries
            if surr1 <= surr2 or (ratio > 1.0 - eps_clip and ratio < 1.0 + eps_clip):
                d_mu = ratio * (a - mu) / (sigma_action**2) * adv
            else:
                d_mu = 0.0

            # Derivatives at output node
            d_out = np.zeros((2, 1))
            # Node 0: Surge prediction auxiliary loss (Cross-Entropy to target)
            surge_target = 1.0 if adv < -10.0 else 0.0
            d_out[0, 0] = out[0, 0] - surge_target
            d_out[1, 0] = -d_mu

            # Output layer gradients
            d_z3 = np.zeros((2, 1))
            d_z3[0, 0] = d_out[0, 0]
            d_z3[1, 0] = d_out[1, 0] * self.tanh_derivative(np.dot(self.W_y, h_curr) + self.b_y)[1, 0]

            dW_y += np.dot(d_z3, h_curr.T)
            db_y += d_z3

            # 3. Backprop through GRU cell
            dh = np.dot(self.W_y.T, d_z3) + np.dot(self.W_v.T, dv) * c1 + dh_next

            # GRU gates gradients
            dh_tilde = dh * z
            dz = dh * (h_tilde - h_prev)

            # z gate activation derivatives
            ds_z = dz * z * (1.0 - z)
            dW_xz += np.dot(ds_z, x.T)
            dW_hz += np.dot(ds_z, h_prev.T)
            db_z += ds_z

            # h_tilde activation derivatives
            ds_h = dh_tilde * (1.0 - h_tilde**2)
            dW_xh += np.dot(ds_h, x.T)
            dW_hh += np.dot(ds_h, (r * h_prev).T)
            db_h += ds_h

            # r gate activation derivatives
            dr = np.dot(self.W_hh.T, ds_h) * h_prev
            ds_r = dr * r * (1.0 - r)
            dW_xr += np.dot(ds_r, x.T)
            dW_hr += np.dot(ds_r, h_prev.T)
            db_r += ds_r

            # dh_next for BPTT step
            dh_next = dh * (1.0 - z) + np.dot(self.W_hz.T, ds_z) + np.dot(self.W_hr.T, ds_r) + np.dot(self.W_hh.T, ds_h) * r

        # Apply parameters gradients step
        self.W_xz -= self.lr * dW_xz
        self.W_hz -= self.lr * dW_hz
        self.b_z -= self.lr * db_z
        self.W_xr -= self.lr * dW_xr
        self.W_hr -= self.lr * dW_hr
        self.b_r -= self.lr * db_r
        self.W_xh -= self.lr * dW_xh
        self.W_hh -= self.lr * dW_hh
        self.b_h -= self.lr * db_h
        self.W_y -= self.lr * dW_y
        self.b_y -= self.lr * db_y
        self.W_v -= self.lr * dW_v
        self.b_v -= self.lr * db_v

    def save_weights(self, filepath):
        np.savez(filepath, 
                 W_xz=self.W_xz, W_hz=self.W_hz, b_z=self.b_z,
                 W_xr=self.W_xr, W_hr=self.W_hr, b_r=self.b_r,
                 W_xh=self.W_xh, W_hh=self.W_hh, b_h=self.b_h,
                 W_y=self.W_y, b_y=self.b_y,
                 W_v=self.W_v, b_v=self.b_v)

    def load_weights(self, filepath):
        data = np.load(filepath)
        self.W_xz = data["W_xz"]
        self.W_hz = data["W_hz"]
        self.b_z = data["b_z"]
        self.W_xr = data["W_xr"]
        self.W_hr = data["W_hr"]
        self.b_r = data["b_r"]
        self.W_xh = data["W_xh"]
        self.W_hh = data["W_hh"]
        self.b_h = data["b_h"]
        self.W_y = data["W_y"]
        self.b_y = data["b_y"]
        if "W_v" in data:
            self.W_v = data["W_v"]
            self.b_v = data["b_v"]
