"""
Flight Envelope Protection Module

Implements ISA standard atmosphere models, flight envelope boundary checks
(altitude-Mach limits), and safety schedules for maximum engine thrust,
EGT, and rotor speeds.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np

class FlightEnvelope:
    def __init__(self):
        # Sea level ISA values
        self.T_sl = 288.15     # Kelvin
        self.P_sl = 101325.0   # Pascal
        self.rho_sl = 1.225    # kg/m^3
        self.R = 287.05
        self.g = 9.80665

        # Flight envelope boundaries
        self.max_mach = 2.0
        self.max_altitude_ft = 50000.0

    def get_ambient_conditions(self, altitude_ft):
        """
        Computes ambient temperature, pressure, and density using the
        International Standard Atmosphere (ISA) model.
        altitude_ft: altitude in feet
        """
        # Convert feet to meters
        h = altitude_ft * 0.3048

        if h < 11000.0:
            # Troposphere: constant temperature lapse rate (-6.5 K/km)
            T_amb = self.T_sl - 0.0065 * h
            P_amb = self.P_sl * (1.0 - 0.0065 * h / self.T_sl)**5.2561
        else:
            # Lower Stratosphere: isothermal (constant temperature)
            T_amb = 216.65
            P_11 = self.P_sl * (1.0 - 0.0065 * 11000.0 / self.T_sl)**5.2561
            h_diff = h - 11000.0
            P_amb = P_11 * np.exp(-self.g * h_diff / (self.R * T_amb))

        rho_amb = P_amb / (self.R * T_amb)
        
        return T_amb, P_amb, rho_amb

    def check_envelope(self, altitude_ft, mach):
        """
        Verifies if flight condition is within structural and aerodynamic limits.
        """
        if altitude_ft < 0.0 or altitude_ft > self.max_altitude_ft:
            return False, "Altitude outside envelope limits."
        
        if mach < 0.0 or mach > self.max_mach:
            return False, "Mach number exceeds aerodynamic limit."

        # Dynamic pressure limit (q = 0.5 * rho * V^2)
        T_amb, P_amb, rho_amb = self.get_ambient_conditions(altitude_ft)
        a = np.sqrt(1.4 * self.R * T_amb)  # speed of sound
        V = mach * a
        dynamic_pressure = 0.5 * rho_amb * V**2

        max_q = 60000.0  # Pascal limit
        if dynamic_pressure > max_q:
            return False, f"Dynamic pressure ({dynamic_pressure:.1f} Pa) exceeds structural limit."

        return True, "Flight state secure."

    def get_limits(self, altitude_ft, mach):
        """
        Computes maximum allowable engine speed, EGT, and thrust command
        based on current altitude and speed (ram air heating).
        """
        T_amb, P_amb, _ = self.get_ambient_conditions(altitude_ft)
        
        # Ram temperature factor: T_total = T_amb * (1 + 0.2 * M^2)
        T_t2 = T_amb * (1.0 + 0.2 * mach**2)

        # High inlet temp requires speed reduction to protect compressor blades
        if T_t2 > 330.0:
            # Derate max rotor speed
            max_speed_pct = 100.0 - (T_t2 - 330.0) * 0.4
        else:
            max_speed_pct = 100.0

        max_speed_pct = max(90.0, min(100.0, max_speed_pct))

        # EGT limits (more restrictive at high Mach due to combustion thermal loading)
        max_egt = 980.0 - (mach * 40.0)
        max_egt = max(880.0, max_egt)

        # Max thrust limit scales with ambient density
        density_ratio = P_amb / self.P_sl
        max_thrust_n = 45000.0 * density_ratio * (1.0 + 0.3 * mach)

        return {
            "max_n1_speed_pct": max_speed_pct,
            "max_egt_kelvin": max_egt,
            "max_thrust_n": max_thrust_n
        }
