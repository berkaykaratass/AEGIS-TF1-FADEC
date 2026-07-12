"""
Telemetry Ingester

Manages incoming high-frequency telemetry streams.
Features thread-safe ring buffer storage, raw statistical metrics calculation,
outlier validation, and data parsing interfaces.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

from collections import deque
import threading
import numpy as np

class TelemetryIngester:
    def __init__(self, buffer_size=1000):
        self.buffer_size = buffer_size
        self.buffer = deque(maxlen=buffer_size)
        self.lock = threading.Lock()
        
        # Ranges for simple outlier detection
        self.limits = {
            "n1_rpm": (0.0, 115000.0),
            "egt_kelvin": (200.0, 1300.0),
            "p3_bar": (0.1, 20.0),
            "vibration_g": (0.0, 15.0),
            "fuel_flow_kgs": (0.0, 3.0),
            "ehd_voltage_kv": (0.0, 50.0)
        }

    def ingest_frame(self, frame):
        """
        Validates and appends a single telemetry frame.
        frame: dict of sensor readings
        """
        validated_frame = {}
        is_valid = True
        faults = []

        for key, limits in self.limits.items():
            val = frame.get(key, 0.0)
            # Outlier / range validation
            if val < limits[0] or val > limits[1]:
                is_valid = False
                faults.append(f"{key}_out_of_bounds")
                validated_frame[key] = np.clip(val, limits[0], limits[1])
            else:
                validated_frame[key] = val

        validated_frame["is_valid"] = is_valid
        validated_frame["faults"] = faults
        validated_frame["timestamp"] = frame.get("timestamp", 0.0)

        with self.lock:
            self.buffer.append(validated_frame)

        return is_valid, faults

    def get_recent_window(self, window_size=100):
        """Returns the last N elements from the ring buffer"""
        with self.lock:
            buffer_list = list(self.buffer)
        return buffer_list[-window_size:]

    def calculate_rolling_statistics(self, window_size=100):
        """Computes statistical metrics (mean, std) for active channels"""
        window = self.get_recent_window(window_size)
        if len(window) == 0:
            return {}

        stats = {}
        for key in self.limits.keys():
            vals = [frame[key] for frame in window]
            stats[key] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "min": float(np.min(vals)),
                "max": float(np.max(vals))
            }
        return stats
