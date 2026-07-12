/**
 * @file vane_schedule.c
 * @brief Variable Stator Vane (VSV) Schedule Implementation
 * 
 * @compliance DO-178C DAL A: REQ-FADEC-007, REQ-FADEC-008
 * @standard MISRA C:2012
 */

#include "vane_schedule.h"
#include <math.h>

#define JAM_DEVIATION_LIMIT_DEG 5.0
#define JAM_TIME_LIMIT_SEC      0.50

void vane_schedule_init(VaneState_t *vstate) {
    if (vstate != (void*)0) {
        vstate->cmd_deg = 15.0;
        vstate->fdbk_deg = 15.0;
        vstate->error_duration_sec = 0.0;
        vstate->jam_fault = false;
    }
}

double vane_schedule_get_angle(double n2_rpm, double t2_k) {
    double cmd_deg = 15.0;
    double t2_ref = 288.15;
    double theta = t2_k / t2_ref;

    if (theta < 0.1) {
        theta = 0.1;
    }

    double n2_corr = n2_rpm / sqrt(theta);

    /* 2D Vane Schedule Map (N2_corr vs theta_vane) */
    if (n2_corr <= 15000.0) {
        cmd_deg = 30.0; /* Vanes fully closed at start/crank to avoid surge */
    }
    else if (n2_corr >= 90000.0) {
        cmd_deg = -15.0; /* Vanes fully open for maximum flow capacity */
    }
    else {
        /* Linear interpolation between 15000 RPM (30 deg) and 90000 RPM (-15 deg) */
        double ratio = (n2_corr - 15000.0) / (90000.0 - 15000.0);
        cmd_deg = 30.0 - (ratio * (30.0 - (-15.0)));
    }

    return cmd_deg;
}

bool vane_schedule_monitor(VaneState_t *vstate, double cmd_deg, double fdbk_deg, double dt) {
    bool is_healthy = true;

    if (vstate != (void*)0) {
        vstate->cmd_deg = cmd_deg;
        vstate->fdbk_deg = fdbk_deg;

        double deviation = fabs(cmd_deg - fdbk_deg);
        if (deviation > JAM_DEVIATION_LIMIT_DEG) {
            vstate->error_duration_sec += dt;
            if (vstate->error_duration_sec >= JAM_TIME_LIMIT_SEC) {
                vstate->jam_fault = true;
            }
        }
        else {
            if (vstate->error_duration_sec > 0.0) {
                vstate->error_duration_sec -= dt;
                if (vstate->error_duration_sec < 0.0) {
                    vstate->error_duration_sec = 0.0;
                }
            }
            vstate->jam_fault = false;
        }

        if (vstate->jam_fault) {
            is_healthy = false;
        }
    }

    return is_healthy;
}
