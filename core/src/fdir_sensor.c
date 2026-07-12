/**
 * @file fdir_sensor.c
 * @brief Fault Detection, Isolation, and Recovery (FDIR) for sensors (v2.0)
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#include "fdir_sensor.h"
#include <math.h>

#define MAX_DISAGREEMENT_RPM  1500.0
#define DISAGREEMENT_TIME_SEC 0.10
#define MAX_VALID_SPEED_RPM   115000.0

void fdir_sensor_init(FDIR_SensorState_t *fdir) {
    if (fdir != (void*)0) {
        fdir->speed_sensor_1_rpm = 0.0;
        fdir->speed_sensor_2_rpm = 0.0;
        fdir->s1_valid = true;
        fdir->s2_valid = true;
        fdir->disagreement_duration_sec = 0.0;
        fdir->dual_sensor_failure = false;
        fdir->synthetic_n1_rpm = 0.0;
        fdir->s1_fault_timer_sec = 0.0;
        fdir->s2_fault_timer_sec = 0.0;
        fdir->s1_recover_timer_sec = 0.0;
        fdir->s2_recover_timer_sec = 0.0;
        fdir->s1_confirmed_failed = false;
        fdir->s2_confirmed_failed = false;
    }
}

bool fdir_sensor_vote_speed(FDIR_SensorState_t *fdir,
                            double raw_s1,
                            double raw_s2,
                            double t2_k,
                            double p3_bar,
                            double dt,
                            double *validated_speed_rpm) {
    bool closed_loop_allowed = true;

    if ((fdir != (void*)0) && (validated_speed_rpm != (void*)0) && (dt > 0.0)) {
        /* 1. Calculate synthetic N1 for telemetry/advisory strictly based on Brayton equations */
        double p3_ratio = p3_bar / 1.013;
        double t2_ratio = 288.15 / (t2_k > 50.0 ? t2_k : 288.15);
        
        if (p3_ratio < 0.0) {
            p3_ratio = 0.0;
        }
        
        fdir->synthetic_n1_rpm = 35000.0 * sqrt(p3_ratio) * sqrt(t2_ratio);

        /* 2. Validate individual sensors boundaries */
        bool s1_bounds_valid = (raw_s1 >= 0.0) && (raw_s1 <= MAX_VALID_SPEED_RPM);
        bool s2_bounds_valid = (raw_s2 >= 0.0) && (raw_s2 <= MAX_VALID_SPEED_RPM);

        /* Plausibility check against synthetic N1 speed model (for slow sensor drift detection) */
        if (s1_bounds_valid && (raw_s1 > 20000.0) && (p3_bar > 0.5) && (fabs(raw_s1 - fdir->synthetic_n1_rpm) > 5000.0)) {
            s1_bounds_valid = false; /* Flags implausible drift */
        }
        if (s2_bounds_valid && (raw_s2 > 20000.0) && (p3_bar > 0.5) && (fabs(raw_s2 - fdir->synthetic_n1_rpm) > 5000.0)) {
            s2_bounds_valid = false; /* Flags implausible drift */
        }

        /* 3. Debounce & Fault confirmation (Sticky after 100 ms) */
        if (fdir->s1_confirmed_failed) {
            /* Sticky fault */
            fdir->s1_valid = false;
        }
        else if (!s1_bounds_valid) {
            fdir->s1_fault_timer_sec += dt;
            fdir->s1_recover_timer_sec = 0.0;
            if (fdir->s1_fault_timer_sec >= DISAGREEMENT_TIME_SEC) {
                fdir->s1_confirmed_failed = true;
                fdir->s1_valid = false;
            }
        }
        else {
            fdir->s1_recover_timer_sec += dt;
            fdir->s1_fault_timer_sec = 0.0;
            fdir->s1_valid = true;
        }

        if (fdir->s2_confirmed_failed) {
            fdir->s2_valid = false;
        }
        else if (!s2_bounds_valid) {
            fdir->s2_fault_timer_sec += dt;
            fdir->s2_recover_timer_sec = 0.0;
            if (fdir->s2_fault_timer_sec >= DISAGREEMENT_TIME_SEC) {
                fdir->s2_confirmed_failed = true;
                fdir->s2_valid = false;
            }
        }
        else {
            fdir->s2_recover_timer_sec += dt;
            fdir->s2_fault_timer_sec = 0.0;
            fdir->s2_valid = true;
        }

        /* 4. Voting and Disagreement Logic */
        if (fdir->s1_valid && fdir->s2_valid) {
            double diff = fabs(raw_s1 - raw_s2);
            if (diff > MAX_DISAGREEMENT_RPM) {
                fdir->disagreement_duration_sec += dt;
                if (fdir->disagreement_duration_sec >= DISAGREEMENT_TIME_SEC) {
                    fdir->dual_sensor_failure = true;
                }
            } else {
                fdir->disagreement_duration_sec = 0.0;
            }
        }
        else if (!fdir->s1_valid && !fdir->s2_valid) {
            fdir->dual_sensor_failure = true;
        }
        else {
            fdir->disagreement_duration_sec = 0.0;
        }

        /* 5. Determine final output speed and control allowance */
        if (fdir->dual_sensor_failure) {
            *validated_speed_rpm = fdir->synthetic_n1_rpm;
            closed_loop_allowed = false;
        }
        else if (fdir->s1_valid && fdir->s2_valid) {
            *validated_speed_rpm = (raw_s1 + raw_s2) * 0.5;
            closed_loop_allowed = true;
        }
        else if (fdir->s1_valid) {
            *validated_speed_rpm = raw_s1;
            closed_loop_allowed = true;
        }
        else {
            *validated_speed_rpm = raw_s2;
            closed_loop_allowed = true;
        }
    }

    return closed_loop_allowed;
}
