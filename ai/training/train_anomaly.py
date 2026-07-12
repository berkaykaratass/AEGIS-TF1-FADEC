"""
Deep Autoencoder Anomaly Detector Training Script

Loads healthy vibration data, computes CWT scalograms using 32 scales,
trains the ScalogramAutoencoder on healthy 32x32 patches,
and saves the trained weights and threshold to anomaly_baseline.npz.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import os
import numpy as np
import pandas as pd
from ai.models.anomaly_detector import WaveletAnomalyDetector

def train():
    dataset_path = "/Users/berkaykaratas/Downloads/turbojet/ai/training/datasets/egt_vibration_data.csv"
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Missing training dataset: {dataset_path}")

    print("Loading sensor vibration dataset...")
    df = pd.read_csv(dataset_path)

    # Filter out anomalous segments to learn normal healthy profile
    healthy_data = df[df["is_anomaly"] == 0]
    vibration_signal = healthy_data["vibration_g"].values
    
    print(f"Loaded {len(vibration_signal)} healthy samples. Extracting wavelet scalogram and training Autoencoder...")

    # Define exactly 32 scales (corresponds to 32 BPF frequencies)
    fs = 1000.0  # Simulated sampling rate in dataset (1000 Hz)
    scales = np.arange(1, 33)

    detector = WaveletAnomalyDetector(sample_rate_hz=fs)
    
    # Train the NumPy Deep Autoencoder on 32x32 scalogram patches
    detector.train_autoencoder(vibration_signal, scales, epochs=10)

    # Save Autoencoder weights and threshold
    save_path = "/Users/berkaykaratas/Downloads/turbojet/ai/models/anomaly_baseline.npz"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Save weights from inner autoencoder along with scales and threshold
    np.savez(save_path,
             W_enc1=detector.autoencoder.W_enc1, b_enc1=detector.autoencoder.b_enc1,
             W_enc2=detector.autoencoder.W_enc2, b_enc2=detector.autoencoder.b_enc2,
             W_dec1=detector.autoencoder.W_dec1, b_dec1=detector.autoencoder.b_dec1,
             W_dec2=detector.autoencoder.W_dec2, b_dec2=detector.autoencoder.b_dec2,
             threshold=detector.anomaly_threshold_mse,
             scales=scales)
             
    print(f"Deep Autoencoder weights successfully saved to {save_path}")

if __name__ == "__main__":
    train()
