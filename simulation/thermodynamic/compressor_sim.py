"""
Compressor Simulator

Simulates axial compressor performance based on speed lines and mass flow ratios.
Tracks operating lines, surge margins, and handles Moore-Greitzer transient simulation.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np

class CompressorSimulator:
    def __init__(self):
        # Build synthetic compressor map parameters
        self.speeds = np.array([50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0])
        self.surge_flows = np.array([4.5, 6.0, 8.2, 11.0, 14.5, 18.2, 21.0])
        self.surge_prs = np.array([2.2, 3.1, 4.5, 6.8, 10.5, 15.2, 19.5])

    def get_surge_line(self):
        """Returns the mass flow and pressure ratios defining the surge line"""
        return self.surge_flows, self.surge_prs

    def lookup_performance(self, speed_pct, flow):
        """
        Looks up pressure ratio and efficiency for a given speed line and flow rate
        """
        # Clamp speed percentage
        speed_pct = np.clip(speed_pct, 50.0, 110.0)
        
        # Linear interpolation to find the surge flow and PR at target speed
        flow_stall = np.interp(speed_pct, self.speeds, self.surge_flows)
        pr_stall = np.interp(speed_pct, self.speeds, self.surge_prs)
        
        # If mass flow is below stall line, we are in surge
        if flow <= flow_stall:
            pr = pr_stall * (flow / flow_stall)**2  # Cubic/parabolic drop in pressure rise
            eff = 0.5 * (flow / flow_stall)
            return pr, eff, True  # Active surge

        # Operating line lookup: Pressure ratio drops as flow increases towards choke
        flow_max = flow_stall * 1.5
        if flow >= flow_max:
            pr = 1.0
            eff = 0.1
            return pr, eff, False

        # Remap flow relative to operating width
        t = (flow - flow_stall) / (flow_max - flow_stall)
        
        # Pressure ratio drops from surge value
        pr = pr_stall - t * (pr_stall * 0.35)
        # Efficiency is parabolic, peaking around 40% of the way to choke
        eff = 0.86 - 0.2 * (t - 0.4)**2
        
        return pr, eff, False

    def compute_surge_margin(self, speed_pct, flow_op, pr_op):
        """
        Computes the surge margin.
        SM = (flow_op / flow_stall) * (pr_stall / pr_op) - 1
        """
        flow_stall = np.interp(speed_pct, self.speeds, self.surge_flows)
        pr_stall = np.interp(speed_pct, self.speeds, self.surge_prs)
        
        if flow_stall > 0 and pr_op > 0:
            sm = (flow_op * pr_stall) / (flow_stall * pr_op) - 1.0
        else:
            sm = -1.0
        return sm
