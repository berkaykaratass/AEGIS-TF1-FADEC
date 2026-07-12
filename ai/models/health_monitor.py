"""
Engine Health Monitoring and RUL Prediction System

Maps physical sensor streams to brainwave frequency bands:
- Delta (0.5-4 Hz)   -> Rotor speed deviations / structural vibration
- Theta (4-8 Hz)     -> EGT variance / combustion instabilities
- Alpha (8-13 Hz)    -> Compressor discharge pressure ripples
- Beta (13-30 Hz)    -> Bearing high-frequency vibrations
- Gamma (30+ Hz)     -> Acoustic micro-cracks signals

Features a custom Recurrent Neural Network (RNN) built from scratch using NumPy
for estimating Remaining Useful Life (RUL) based on degradation paths.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np
from scipy.signal import welch

class MotorHealthMonitor:
    def __init__(self, sample_rate_hz=100.0):
        self.fs = sample_rate_hz
        
        # Band definition ranges (Hz)
        self.bands = {
            "delta": (0.5, 4.0),
            "theta": (4.0, 8.0),
            "alpha": (8.0, 13.0),
            "beta": (13.0, 30.0),
            "gamma": (30.0, 45.0)
        }

        # Weighting factors for Health Index calculation
        self.weights = {
            "delta": 0.15,
            "theta": 0.25,
            "alpha": 0.15,
            "beta": 0.25,
            "gamma": 0.20
        }

        # Baseline profiles (normal operating values)
        self.baselines = {
            "delta": 1.0,
            "theta": 1.2,
            "alpha": 0.8,
            "beta": 0.5,
            "gamma": 0.3
        }

        # Initialize Custom RNN Weights
        # Input shape: (5 bands + 1 current HI = 6 features)
        # Hidden shape: (10 hidden states)
        # Output shape: (1 output value: RUL)
        input_dim = 6
        hidden_dim = 10
        output_dim = 1

        self.W_xh = np.random.randn(hidden_dim, input_dim) * np.sqrt(2.0 / input_dim)
        self.W_hh = np.random.randn(hidden_dim, hidden_dim) * np.sqrt(2.0 / hidden_dim)
        self.b_h = np.zeros((hidden_dim, 1))

        self.W_hy = np.random.randn(output_dim, hidden_dim) * np.sqrt(2.0 / hidden_dim)
        self.b_y = np.zeros((output_dim, 1))

    def compute_band_powers(self, signal):
        """
        Computes power spectral density (PSD) using Welch's method
        and aggregates power into frequency bands.
        """
        # Calculate PSD
        nperseg = min(len(signal), 256)
        freqs, psd = welch(signal, self.fs, nperseg=nperseg)

        band_powers = {}
        for band_name, (f_min, f_max) in self.bands.items():
            # Find frequencies in band range
            indices = np.where((freqs >= f_min) & (freqs <= f_max))[0]
            if len(indices) > 0:
                # Integrate PSD using trapezoidal rule
                power = np.trapz(psd[indices], freqs[indices])
            else:
                power = 0.0
            band_powers[band_name] = power

        return band_powers

    def update_baseline(self, calibration_signal):
        """Calibrates healthy baseline profiles"""
        self.baselines = self.compute_band_powers(calibration_signal)
        # Ensure no baseline power is zero to prevent division errors
        for key in self.baselines:
            if self.baselines[key] <= 0:
                self.baselines[key] = 1e-5

    def compute_health_index(self, current_powers):
        """
        Computes overall Health Index (HI) ranging from 1.0 (perfect) to 0.0 (failure).
        HI = 1 - sum(wi * |xi - baseline_i| / baseline_i)
        """
        deviation_sum = 0.0
        for band, weight in self.weights.items():
            power = current_powers.get(band, 0.0)
            baseline = self.baselines.get(band, 1.0)
            
            # Absolute relative deviation
            dev = abs(power - baseline) / baseline
            deviation_sum += weight * dev

        health_index = 1.0 - deviation_sum
        return max(0.0, min(1.0, health_index))


    def rnn_forward(self, X_sequence):
        """
        Executes forward pass of the custom Recurrent Neural Network (RNN).
        X_sequence: NumPy array of shape (seq_len, 6) where each row is [delta, theta, alpha, beta, gamma, HI]
        Returns list of predictions (seq_len, 1) and list of hidden states.
        """
        seq_len = X_sequence.shape[0]
        hidden_dim = self.W_hh.shape[0]
        
        # Initialize hidden state h_t as zero
        h = np.zeros((hidden_dim, 1))
        
        h_states = []
        outputs = []

        for t in range(seq_len):
            x_t = X_sequence[t].reshape(-1, 1)  # shape (6, 1)
            
            # Recurrent relation: h_t = tanh(W_xh * x_t + W_hh * h_prev + b_h)
            h = np.tanh(np.dot(self.W_xh, x_t) + np.dot(self.W_hh, h) + self.b_h)
            h_states.append(h)

            # Output relation: y_t = W_hy * h_t + b_y
            y = np.dot(self.W_hy, h) + self.b_y
            outputs.append(y)

        return np.array(outputs).squeeze(), h_states

    def train_rnn(self, X_seq_list, y_seq_list, epochs=100, lr=0.01):
        """
        Trains the RNN using Backpropagation Through Time (BPTT).
        """
        hidden_dim = self.W_hh.shape[0]
        
        for epoch in range(epochs):
            loss = 0.0
            
            # Gradients accumulator
            dW_xh_total = np.zeros_like(self.W_xh)
            dW_hh_total = np.zeros_like(self.W_hh)
            db_h_total = np.zeros_like(self.b_h)
            dW_hy_total = np.zeros_like(self.W_hy)
            db_y_total = np.zeros_like(self.b_y)

            for X_seq, y_seq in zip(X_seq_list, y_seq_list):
                predictions, h_states = self.rnn_forward(X_seq)
                
                seq_len = X_seq.shape[0]
                h_prev_states = [np.zeros((hidden_dim, 1))] + h_states[:-1]
                
                # Forward errors
                dy = predictions - y_seq  # shape (seq_len,)
                loss += 0.5 * np.sum(dy**2)

                # Backprop variables
                dh_next = np.zeros((hidden_dim, 1))

                for t in reversed(range(seq_len)):
                    x_t = X_seq[t].reshape(-1, 1)
                    h_t = h_states[t]
                    h_prev = h_prev_states[t]
                    
                    dy_t = dy[t] if seq_len > 1 else dy

                    # Gradient output layer
                    dW_hy_total += dy_t * h_t.T
                    db_y_total += dy_t

                    # Gradient hidden state
                    dh = np.dot(self.W_hy.T, dy_t) + dh_next
                    
                    # Backprop through tanh: dtanh = (1 - h^2)
                    dtanh = (1.0 - h_t**2) * dh
                    
                    dW_xh_total += np.dot(dtanh, x_t.T)
                    dW_hh_total += np.dot(dtanh, h_prev.T)
                    db_h_total += dtanh
                    
                    # Pass back error to next step
                    dh_next = np.dot(self.W_hh.T, dtanh)

            # Update weights
            self.W_xh -= lr * dW_xh_total
            self.W_hh -= lr * dW_hh_total
            self.b_h -= lr * db_h_total
            self.W_hy -= lr * dW_hy_total
            self.b_y -= lr * db_y_total

    def estimate_rul(self, sensor_history):
        """
        Estimates Remaining Useful Life (RUL) in hours based on historical trends.
        sensor_history: list of signals, each of size sample_rate_hz * 5s
        """
        features_list = []
        for signal in sensor_history:
            powers = self.compute_band_powers(signal)
            hi = self.compute_health_index(powers)
            features = list(powers.values()) + [hi]
            features_list.append(features)

        X_seq = np.array(features_list)
        rul_predictions, _ = self.rnn_forward(X_seq)
        
        # Latest prediction is current RUL
        if X_seq.shape[0] == 1:
            current_rul = rul_predictions
        else:
            current_rul = rul_predictions[-1]
            
        return max(0.0, float(current_rul))

    def save_weights(self, filepath):
        np.savez(filepath,
                 W_xh=self.W_xh, W_hh=self.W_hh, b_h=self.b_h,
                 W_hy=self.W_hy, b_y=self.b_y)

    def load_weights(self, filepath):
        data = np.load(filepath)
        self.W_xh = data["W_xh"]
        self.W_hh = data["W_hh"]
        self.b_h = data["b_h"]
        self.W_hy = data["W_hy"]
        self.b_y = data["b_y"]
