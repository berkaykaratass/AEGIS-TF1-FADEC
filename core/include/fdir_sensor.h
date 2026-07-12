/**
 * @file fdir_sensor.h
 * @brief Fault Detection, Isolation, and Recovery (FDIR) for sensors
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef FDIR_SENSOR_H
#define FDIR_SENSOR_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    double speed_sensor_1_rpm;
    double speed_sensor_2_rpm;
    bool s1_valid;
    bool s2_valid;
    double disagreement_duration_sec;
    bool dual_sensor_failure;
    double synthetic_n1_rpm;
    double s1_fault_timer_sec;
    double s2_fault_timer_sec;
    double s1_recover_timer_sec;
    double s2_recover_timer_sec;
    bool s1_confirmed_failed;
    bool s2_confirmed_failed;
} FDIR_SensorState_t;

/**
 * @brief Initialize FDIR sensor monitoring state
 */
void fdir_sensor_init(FDIR_SensorState_t *fdir);

/**
 * @brief Run voting logic on speed sensors and transition to degraded state if necessary
 * @param[in,out] fdir FDIR state
 * @param[in] raw_s1 Speed reading from sensor 1 (RPM)
 * @param[in] raw_s2 Speed reading from sensor 2 (RPM)
 * @param[in] t2_k Compressor inlet temperature (Kelvin)
 * @param[in] p3_bar Burner pressure (bar)
 * @param[in] dt Step time period (seconds)
 * @param[out] validated_speed_rpm Output validated speed for control loop use
 * @return True if speed is valid and closed-loop control is allowed, false if dual-failure (degraded mode)
 */
bool fdir_sensor_vote_speed(FDIR_SensorState_t *fdir,
                            double raw_s1,
                            double raw_s2,
                            double t2_k,
                            double p3_bar,
                            double dt,
                            double *validated_speed_rpm);

#endif /* FDIR_SENSOR_H */
