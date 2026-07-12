/**
 * @file creep_governor.h
 * @brief Turbine Blade Creep Damage Accumulator (Larson-Miller Parameter)
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#ifndef CREEP_GOVERNOR_H
#define CREEP_GOVERNOR_H

#include <stdint.h>

typedef struct {
    double accumulated_damage;      /* Life consumed: 0.0 (nominal) to 1.0 (retired) */
    double creep_rate;              /* Instantaneous damage rate per second */
    double life_degradation_index;  /* Normalised index used for transient clamping */
} CreepState_t;

/**
 * @brief Initialize creep governor parameters.
 */
void creep_governor_init(CreepState_t *state);

/**
 * @brief Calculates online turbine blade creep life consumption.
 * @param[in,out] state Creep monitoring state structure
 * @param[in] t41_temp_k Turbine inlet temperature T4.1 (K)
 * @param[in] stress_pa Core shaft mechanical stress (Pa)
 * @param[in] dt Time step duration (seconds)
 */
void creep_governor_step(CreepState_t *state, 
                         double t41_temp_k, 
                         double stress_pa, 
                         double dt);

#endif /* CREEP_GOVERNOR_H */
