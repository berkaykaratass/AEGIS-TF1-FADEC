"""
AI Models Package

Imports core neural and wave analysis models for the FADEC system.
"""

from .surge_predictor import SurgePredictor, CompressorEnvironment
from .anomaly_detector import WaveletAnomalyDetector
from .health_monitor import MotorHealthMonitor
from .adaptive_mpc import AdaptiveMPC, NonlinearStateSpace
from .flight_envelope import FlightEnvelope

__all__ = [
    "SurgePredictor",
    "CompressorEnvironment",
    "WaveletAnomalyDetector",
    "MotorHealthMonitor",
    "AdaptiveMPC",
    "NonlinearStateSpace",
    "FlightEnvelope"
]
