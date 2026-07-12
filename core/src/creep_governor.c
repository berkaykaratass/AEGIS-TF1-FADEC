/**
 * @file creep_governor.c
 * @brief Turbine Blade Creep Damage Accumulator (Larson-Miller Parameter)
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#include "creep_governor.h"
#include <math.h>

void creep_governor_init(CreepState_t *state) {
    if (state != (void*)0) {
        state->accumulated_damage = 0.0;
        state->creep_rate = 0.0;
        state->life_degradation_index = 0.0;
    }
}

void creep_governor_step(CreepState_t *state, 
                         double t41_temp_k, 
                         double stress_pa, 
                         double dt) {
    if ((state != (void*)0) && (dt > 0.0) && (t41_temp_k > 0.0) && (stress_pa > 0.0)) {
        /* Convert stress from Pascals to ksi (kilopounds per square inch) */
        double stress_ksi = (stress_pa / 1.0e6) * 0.1450377;
        if (stress_ksi < 1.0) {
            stress_ksi = 1.0;
        }

        /* Larson-Miller Parameter curve fit for typical Rene turbine blade superalloy:
         * LMP = T * (20.0 + log10(t_rupture_hours)) */
        double LMP = 42000.0 - (8000.0 * log10(stress_ksi));

        /* Compute log10 of rupture time in hours */
        double log_tr = (LMP / t41_temp_k) - 20.0;
        
        /* Bound exponent to prevent numerical overflow in pow() */
        if (log_tr > 10.0) {
            log_tr = 10.0;
        }
        if (log_tr < -2.0) {
            log_tr = -2.0;
        }

        double t_rupture_hours = pow(10.0, log_tr);
        if (t_rupture_hours < 0.01) {
            t_rupture_hours = 0.01; /* Minimum rupture lifetime clamp */
        }

        /* Convert rupture time to seconds and compute creep damage rate (1/s) */
        double t_rupture_sec = t_rupture_hours * 3600.0;
        state->creep_rate = 1.0 / t_rupture_sec;

        /* Accumulate fatigue damage */
        state->accumulated_damage += state->creep_rate * dt;
        if (state->accumulated_damage > 1.0) {
            state->accumulated_damage = 1.0;
        }

        state->life_degradation_index = state->accumulated_damage;
    }
}
