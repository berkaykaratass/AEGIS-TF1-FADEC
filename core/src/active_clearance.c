/**
 * @file active_clearance.c
 * @brief Turbine Blade Active Clearance Control (ACC) Model
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#include "active_clearance.h"
#include <math.h>

void acc_init(ACC_State_t *state) {
    if (state != (void*)0) {
        state->rotor_thermal_growth_mm = 0.0;
        state->casing_thermal_growth_mm = 0.0;
        state->tip_clearance_mm = 1.5;     /* Cold clearance 1.5 mm */
        state->acc_valve_cmd_pct = 0.0;
        state->rotor_temp_k = 288.15;
        state->casing_temp_k = 288.15;
    }
}

void acc_control_step(ACC_State_t *state, 
                      double turbine_temp_k, 
                      double n1_rpm, 
                      double dt) {
    if ((state != (void*)0) && (dt > 0.0) && (turbine_temp_k > 0.0)) {
        /* 1. Rotor/Blade Radial Growth Modeling:
         * Centrifugal strain: delta_R_c = K * RPM^2 */
        double growth_centrifugal = (n1_rpm * n1_rpm) * 1.5e-10;

        /* Lumped-Parameter Rotor Thermal Node:
         * dT_r/dt = h_rotor * (T_gas - T_rotor) */
        double dTr = (turbine_temp_k - state->rotor_temp_k) * 0.05 * dt;
        state->rotor_temp_k += dTr;

        state->rotor_thermal_growth_mm = (state->rotor_temp_k - 288.15) * 1.2e-4;
        double total_rotor_growth = growth_centrifugal + state->rotor_thermal_growth_mm;

        /* 2. Lumped-Parameter Casing Thermal Node:
         * dT_c/dt = h_casing * (T_gas - T_casing) - h_cool * ACC_valve * (T_casing - T_cool) */
        double dTc_gas = (turbine_temp_k - state->casing_temp_k) * 0.02 * dt;
        double dTc_cool = (state->acc_valve_cmd_pct * 0.005) * (state->casing_temp_k - 288.15) * dt;
        state->casing_temp_k += (dTc_gas - dTc_cool);

        /* Prevent cooling past ambient temperature */
        if (state->casing_temp_k < 288.15) {
            state->casing_temp_k = 288.15;
        }

        state->casing_thermal_growth_mm = (state->casing_temp_k - 288.15) * 1.0e-4;

        /* 3. Compute Net Tip Clearance (mm) */
        state->tip_clearance_mm = 1.5 + state->casing_thermal_growth_mm - total_rotor_growth;
        if (state->tip_clearance_mm < 0.1) {
            state->tip_clearance_mm = 0.1; /* Mechanical rub boundary clamp */
        }

        /* 4. Closed-Loop Clearance Controller:
         * Target clearance is set to 0.4 mm for optimal aerodynamic efficiency.
         * If clearance exceeds 0.4 mm, open the cooling valve to contract the casing. */
        double target_clearance = 0.4;
        double error = state->tip_clearance_mm - target_clearance;

        if (error > 0.0) {
            state->acc_valve_cmd_pct = error * 200.0; /* Proportional cooling gain */
        } else {
            state->acc_valve_cmd_pct = 0.0; /* Keep valve closed if clearance is tight */
        }

        /* Clamp command to actuator physical range [0.0, 100.0%] */
        if (state->acc_valve_cmd_pct > 100.0) {
            state->acc_valve_cmd_pct = 100.0;
        }
        if (state->acc_valve_cmd_pct < 0.0) {
            state->acc_valve_cmd_pct = 0.0;
        }
    }
}
