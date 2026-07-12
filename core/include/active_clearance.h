/**
 * @file active_clearance.h
 * @brief Turbine Blade Active Clearance Control (ACC) Model
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#ifndef ACTIVE_CLEARANCE_H
#define ACTIVE_CLEARANCE_H

#include <stdint.h>

typedef struct {
    double rotor_thermal_growth_mm;
    double casing_thermal_growth_mm;
    double tip_clearance_mm;
    double acc_valve_cmd_pct;       /* Cooling valve command (0.0 to 100.0%) */
    double rotor_temp_k;
    double casing_temp_k;
} ACC_State_t;

/**
 * @brief Initialize Active Clearance Control thermal state.
 */
void acc_init(ACC_State_t *state);

/**
 * @brief Computes casing cooling valve command to maintain target tip clearance.
 * @param[in,out] state ACC control state structure
 * @param[in] turbine_temp_k Turbine gas temperature T4.1 (K)
 * @param[in] n1_rpm Spool rotational speed (RPM)
 * @param[in] dt Time step duration (seconds)
 */
void acc_control_step(ACC_State_t *state, 
                      double turbine_temp_k, 
                      double n1_rpm, 
                      double dt);

#endif /* ACTIVE_CLEARANCE_H */
