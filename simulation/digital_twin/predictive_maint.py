"""
Predictive Maintenance Engine

Models components reliability using Weibull distribution failure modeling.
Optimizes maintenance schedules minimizing cost matrices:
- Unplanned shutdown cost (severe penalty)
- Scheduled replacement/inspection cost (moderate)

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import numpy as np

class PredictiveMaintenance:
    def __init__(self, cost_scheduled=5000.0, cost_unplanned=75000.0):
        # Cost parameters
        self.C_scheduled = cost_scheduled
        self.C_unplanned = cost_unplanned
        
        # Weibull parameters for key structural components
        # eta (characteristic life in hours), beta (shape parameter: >1 implies wear-out phase)
        self.components = {
            "compressor_blades": {"eta": 3500.0, "beta": 2.2},
            "turbine_rotors": {"eta": 2800.0, "beta": 2.8},
            "combustor_liner": {"eta": 4000.0, "beta": 1.8},
            "bearings": {"eta": 1500.0, "beta": 3.1}
        }

    def compute_failure_probability(self, component_name, operating_hours):
        """
        Calculates cumulative failure probability using Weibull distribution:
        F(t) = 1 - exp( - (t / eta)^beta )
        """
        if component_name not in self.components:
            raise KeyError(f"Component '{component_name}' not registered in Weibull model.")

        params = self.components[component_name]
        eta = params["eta"]
        beta = params["beta"]

        F_t = 1.0 - np.exp(- (operating_hours / eta)**beta)
        return float(F_t)

    def optimize_maintenance_schedule(self, component_name, current_hours):
        """
        Calculates the optimal interval (in hours) to perform maintenance
        to minimize the expected total cost:
        E(C) = (C_scheduled * (1 - F(t))) + (C_unplanned * F(t))
        """
        params = self.components[component_name]
        eta = params["eta"]
        beta = params["beta"]

        # Search for optimal time t ahead of current_hours to perform maintenance
        t_search = np.linspace(1.0, eta * 1.5, 1000)
        
        costs = []
        for t in t_search:
            # Probability of failure occurring before interval t
            F_t = 1.0 - np.exp(- (t / eta)**beta)
            
            # Expected cost per unit of time
            # E(C) = [ C_scheduled * (1-F) + C_unplanned * F ] / t
            expected_cost = (self.C_scheduled * (1.0 - F_t) + self.C_unplanned * F_t) / t
            costs.append(expected_cost)

        opt_idx = np.argmin(costs)
        optimal_interval = t_search[opt_idx]
        optimal_cost_per_hour = costs[opt_idx]

        remaining_hours_to_maint = optimal_interval - current_hours

        return {
            "optimal_inspection_interval_hours": float(optimal_interval),
            "expected_min_cost_per_hour": float(optimal_cost_per_hour),
            "remaining_hours": float(remaining_hours_to_maint),
            "action_required": remaining_hours_to_maint < 100.0
        }
