/**
 * @file vane_schedule.h
 * @brief Variable Stator Vane (VSV) Schedule Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef VANE_SCHEDULE_H
#define VANE_SCHEDULE_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    double cmd_deg;            /* commanded angle (degrees) */
    double fdbk_deg;           /* feedback angle (degrees) */
    double error_duration_sec; /* duration of command-feedback disagreement */
    bool jam_fault;            /* jam warning flag */
} VaneState_t;

/**
 * @brief Initialize stator vane state variables
 */
void vane_schedule_init(VaneState_t *vstate);

/**
 * @brief Calculate commanded stator vane angle based on corrected rotor speed
 * @param[in] n2_rpm Engine physical speed
 * @param[in] t2_k Compressor inlet temperature (Kelvin)
 * @return Command stator vane angle (degrees)
 */
double vane_schedule_get_angle(double n2_rpm, double t2_k);

/**
 * @brief Run stator vane health monitor and jam detection loop
 * @param[in,out] vstate Stator vane state structure
 * @param[in] cmd_deg New commanded angle
 * @param[in] fdbk_deg Sensor feedback angle
 * @param[in] dt Task execution period (seconds)
 * @return true if vane is healthy, false if jam detected
 */
bool vane_schedule_monitor(VaneState_t *vstate, double cmd_deg, double fdbk_deg, double dt);

#endif /* VANE_SCHEDULE_H */
