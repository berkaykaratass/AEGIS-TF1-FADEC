"""
Wavelet Anomaly Detector Autoencoder Unit Tests
"""

import numpy as np
from ai.models.anomaly_detector import WaveletAnomalyDetector

def test_morlet_wavelet():
    detector = WaveletAnomalyDetector(sample_rate_hz=100.0)
    t = np.linspace(-1, 1, 100)
    
    wavelet = detector.morlet_wavelet(t, scale=2.0)
    assert len(wavelet) == 100
    assert np.iscomplexobj(wavelet)

def test_fft_cwt_convolution():
    detector = WaveletAnomalyDetector(sample_rate_hz=100.0)
    # Sine wave signal
    t = np.linspace(0, 10, 1000)
    signal = np.sin(2.0 * np.pi * 5.0 * t)  # 5 Hz
    
    scales = np.arange(1, 33) # 32 scales
    cwt = detector.compute_cwt(signal, scales)
    
    assert cwt.shape == (32, 1000)

def test_anomaly_detection_autoencoder():
    detector = WaveletAnomalyDetector(sample_rate_hz=100.0)
    t = np.linspace(0, 10, 1000)
    # normal operation: smooth sine waves
    healthy_signal = np.sin(2.0 * np.pi * 5.0 * t) + np.random.randn(1000) * 0.1
    
    scales = np.arange(1, 33) # 32 scales
    
    # Train NumPy Autoencoder on healthy signal
    detector.train_autoencoder(healthy_signal, scales, epochs=3)
    
    # Generate signal with large anomalous shock waves
    faulty_signal = healthy_signal.copy()
    faulty_signal[500:540] += 8.0  # inject high-energy vibration shock wave
    
    anomaly_indices, mses = detector.detect_anomalies(faulty_signal, scales)
    
    assert len(anomaly_indices) > 0
    # The anomaly should be detected near the injected interval
    assert any(450 < idx < 600 for idx in anomaly_indices)
