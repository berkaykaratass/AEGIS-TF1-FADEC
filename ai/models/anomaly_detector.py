"""
Continuous Wavelet Transform (CWT) & Deep Autoencoder Anomaly Detector

Implements FFT-based Continuous Wavelet Transform using Morlet wavelets,
and a NumPy-based Deep Autoencoder for reconstructing 32x32 scalogram patches
to detect transient structural anomalies.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np
from scipy import fft

class ScalogramAutoencoder:
    """
    4-Layer Dense Deep Autoencoder built from scratch in NumPy:
    Input: 1024 (32 scales x 32 time steps)
    Encoder: 1024 -> 128 (ReLU) -> 16 (Latent space)
    Decoder: 16 -> 128 (ReLU) -> 1024 (Linear reconstruction)
    """
    def __init__(self, input_dim=1024, hidden_dim=128, latent_dim=16, lr=0.0002):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.lr = lr

        # Weights initialization
        self.W_enc1 = np.random.randn(hidden_dim, input_dim) * 0.01
        self.b_enc1 = np.zeros((hidden_dim, 1))

        self.W_enc2 = np.random.randn(latent_dim, hidden_dim) * 0.01
        self.b_enc2 = np.zeros((latent_dim, 1))

        self.W_dec1 = np.random.randn(hidden_dim, latent_dim) * 0.01
        self.b_dec1 = np.zeros((hidden_dim, 1))

        self.W_dec2 = np.random.randn(input_dim, hidden_dim) * 0.01
        self.b_dec2 = np.zeros((input_dim, 1))

    def relu(self, x):
        return np.maximum(0.0, x)

    def relu_derivative(self, x):
        return (x > 0.0).astype(float)

    def forward(self, x):
        """Forward pass reconstruction"""
        if len(x.shape) == 1:
            x = x.reshape(-1, 1)

        z1 = np.dot(self.W_enc1, x) + self.b_enc1
        a1 = self.relu(z1)

        z2 = np.dot(self.W_enc2, a1) + self.b_enc2
        a2 = z2 # Latent bottleneck linear activation

        z3 = np.dot(self.W_dec1, a2) + self.b_dec1
        a3 = self.relu(z3)

        z4 = np.dot(self.W_dec2, a3) + self.b_dec2
        out = z4 # Reconstruction

        return out, a1, a2, a3, z1, z3

    def train_step(self, x):
        """Supervised MSE loss reconstruction gradient update"""
        if len(x.shape) == 1:
            x = x.reshape(-1, 1)

        # Forward pass
        out, a1, a2, a3, z1, z3 = self.forward(x)

        # Compute MSE loss gradient
        d_out = out - x # shape (1024, 1)

        # Decoder Layer 2 gradients
        dW_dec2 = np.dot(d_out, a3.T)
        db_dec2 = d_out

        # Decoder Layer 1 gradients
        d_a3 = np.dot(self.W_dec2.T, d_out)
        d_z3 = d_a3 * self.relu_derivative(z3)
        dW_dec1 = np.dot(d_z3, a2.T)
        db_dec1 = d_z3

        # Encoder Layer 2 gradients
        d_a2 = np.dot(self.W_dec1.T, d_z3)
        d_z2 = d_a2
        dW_enc2 = np.dot(d_z2, a1.T)
        db_enc2 = d_z2

        # Encoder Layer 1 gradients
        d_a1 = np.dot(self.W_enc2.T, d_z2)
        d_z1 = d_a1 * self.relu_derivative(z1)
        dW_enc1 = np.dot(d_z1, x.T)
        db_enc1 = d_z1

        # Apply updates with gradient clipping to prevent NaN overflow
        grad_clip = 1.0
        for grad in [dW_dec2, db_dec2, dW_dec1, db_dec1, dW_enc2, db_enc2, dW_enc1, db_enc1]:
            np.clip(grad, -grad_clip, grad_clip, out=grad)

        self.W_dec2 -= self.lr * dW_dec2
        self.b_dec2 -= self.lr * db_dec2
        self.W_dec1 -= self.lr * dW_dec1
        self.b_dec1 -= self.lr * db_dec1
        self.W_enc2 -= self.lr * dW_enc2
        self.b_enc2 -= self.lr * db_enc2
        self.W_enc1 -= self.lr * dW_enc1
        self.b_enc1 -= self.lr * db_enc1

        mse = 0.5 * np.mean((out - x)**2)
        return mse

    def save_weights(self, filepath):
        np.savez(filepath,
                 W_enc1=self.W_enc1, b_enc1=self.b_enc1,
                 W_enc2=self.W_enc2, b_enc2=self.b_enc2,
                 W_dec1=self.W_dec1, b_dec1=self.b_dec1,
                 W_dec2=self.W_dec2, b_dec2=self.b_dec2)

    def load_weights(self, filepath):
        data = np.load(filepath)
        self.W_enc1 = data["W_enc1"]
        self.b_enc1 = data["b_enc1"]
        self.W_enc2 = data["W_enc2"]
        self.b_enc2 = data["b_enc2"]
        self.W_dec1 = data["W_dec1"]
        self.b_dec1 = data["b_dec1"]
        self.W_dec2 = data["W_dec2"]
        self.b_dec2 = data["b_dec2"]


class WaveletAnomalyDetector:
    def __init__(self, sample_rate_hz=1000.0, omega0=6.0):
        self.fs = sample_rate_hz
        self.omega0 = omega0
        self.autoencoder = ScalogramAutoencoder()
        self.anomaly_threshold_mse = 0.05  # default baseline threshold

    def morlet_wavelet(self, t, scale):
        t_scaled = t / scale
        normalization = (np.pi ** -0.25) * (1.0 / np.sqrt(scale))
        envelope = np.exp(-0.5 * t_scaled**2)
        oscillator = np.exp(1j * self.omega0 * t_scaled)
        return normalization * envelope * oscillator

    def compute_cwt(self, signal, scales):
        n_signal = len(signal)
        n_fft = int(2 ** np.ceil(np.log2(n_signal + 1000)))
        
        signal_fft = fft.fft(signal, n=n_fft)
        cwt_matrix = np.zeros((len(scales), n_signal), dtype=np.complex128)

        for i, scale in enumerate(scales):
            t_max = 5.0 * scale
            t = np.arange(-t_max, t_max, 1.0 / self.fs)
            wavelet = np.conj(self.morlet_wavelet(t, scale))
            wavelet_fft = fft.fft(wavelet, n=n_fft)
            
            conv_fft = signal_fft * wavelet_fft
            conv_result = fft.ifft(conv_fft)[:n_signal]
            cwt_matrix[i, :] = conv_result

        return cwt_matrix

    def compute_scalogram(self, signal, scales):
        cwt_matrix = self.compute_cwt(signal, scales)
        return np.abs(cwt_matrix) ** 2

    def train_autoencoder(self, healthy_signal, scales, epochs=10):
        scalogram = self.compute_scalogram(healthy_signal, scales)
        
        # Save the calibration max for normalizing test signals
        self.calibration_max = np.max(scalogram)
        
        # Normalize the entire scalogram to prevent activation overflow
        if self.calibration_max > 1e-8:
            scalogram = scalogram / self.calibration_max
            
        # Extract overlapping 32x32 patches
        patches = []
        n_scales, n_time = scalogram.shape
        step = 4
        
        for t in range(0, n_time - 32, step):
            patch = scalogram[:, t:t+32]
            if patch.shape == (32, 32):
                patches.append(patch.flatten())
        
        patches = np.array(patches)
        print(f"Extracted {len(patches)} healthy training scalogram patches.")
        
        # Train loop
        for epoch in range(epochs):
            losses = []
            for p in patches:
                loss = self.autoencoder.train_step(p)
                losses.append(loss)
            print(f"  Autoencoder Epoch {epoch+1}/{epochs} | Average MSE: {np.mean(losses):.6f}")

        # Set threshold based on maximum reconstruction error on healthy set + safety margin
        recon_errors = []
        for p in patches:
            out, _, _, _, _, _ = self.autoencoder.forward(p)
            recon_errors.append(0.5 * np.mean((out.flatten() - p) ** 2))
        
        self.anomaly_threshold_mse = np.mean(recon_errors) + 3.0 * np.std(recon_errors)
        print(f"Dynamic Anomaly Threshold set to MSE: {self.anomaly_threshold_mse:.6f}")

    def detect_anomalies(self, signal, scales):
        """
        Detects bearing and structural anomalies by measuring patch reconstruction MSE.
        Returns indices where anomalies are detected, and reconstruction MSEs.
        """
        scalogram = self.compute_scalogram(signal, scales)
        
        # Normalize test scalogram using the baseline calibration_max to preserve relative energy spikes
        scale_factor = getattr(self, "calibration_max", np.max(scalogram))
        if scale_factor > 1e-8:
            scalogram = scalogram / scale_factor
            
        n_scales, n_time = scalogram.shape
        
        anomaly_indices = []
        mses = np.zeros(n_time)

        # Slide window of 32 time steps
        for t in range(n_time - 32):
            patch = scalogram[:, t:t+32]
            if patch.shape == (32, 32):
                flat = patch.flatten()
                out, _, _, _, _, _ = self.autoencoder.forward(flat)
                mse = 0.5 * np.mean((out.flatten() - flat) ** 2)
                mses[t] = mse
                
                # Check reconstruction breach
                if mse > self.anomaly_threshold_mse:
                    anomaly_indices.append(t + 16) # middle of the window

        return anomaly_indices, mses

    def detect_blade_pass_anomaly(self, signal, num_blades, rpm, tolerance_pct=5.0):
        bpf = (rpm / 60.0) * num_blades
        n = len(signal)
        freqs = fft.fftfreq(n, 1.0 / self.fs)
        fft_vals = np.abs(fft.fft(signal))
        
        pos_indices = freqs > 0
        freqs = freqs[pos_indices]
        fft_vals = fft_vals[pos_indices]

        peak_idx = np.argmax(fft_vals)
        peak_freq = freqs[peak_idx]

        lower_bound = bpf * (1.0 - tolerance_pct / 100.0)
        upper_bound = bpf * (1.0 + tolerance_pct / 100.0)

        is_defective = False
        details = ""

        if lower_bound <= peak_freq <= upper_bound:
            if fft_vals[peak_idx] > 500.0:
                is_defective = True
                details = f"Excessive energy amplitude at BPF ({peak_freq:.2f} Hz): {fft_vals[peak_idx]:.1f}"
        else:
            is_defective = True
            details = f"Asymmetric frequency shift: dominant peak at {peak_freq:.2f} Hz instead of BPF ({bpf:.2f} Hz)"

        return is_defective, peak_freq, details
