/**
 * @file ehd_thrust.c
 * @brief Electrohydrodynamic (EHD) Thrust Augmentation Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#include "ehd_thrust.h"
#include <math.h>

#define E0_BREAKDOWN    3.0e6  /* Dielectric breakdown strength of air (V/m) */
#define MIN_GAP_METERS  0.001
#define MAX_GAP_METERS  1.0
#define MIN_RADIUS      1e-6
#define MAX_RADIUS      0.01

double ehd_corona_onset_voltage(const EHD_Config_t *config, double air_density_ratio) {
    double v_onset_kv = -1.0;

    if ((config != (void*)0) && (air_density_ratio > 0.0)) {
        double r = config->emitter_radius_m;
        double d = config->gap_m;

        if ((r >= MIN_RADIUS) && (r <= MAX_RADIUS) && 
            (d >= MIN_GAP_METERS) && (d <= MAX_GAP_METERS) && (d > r)) {
            
            /* Peek's formula for coaxial/wire-to-plane geometry */
            double term1 = 1.0 + (0.308 / sqrt(r * air_density_ratio));
            double E_onset = E0_BREAKDOWN * air_density_ratio * term1;
            
            /* V = E * r * ln(d/r) */
            double v_onset_v = E_onset * r * log(d / r);
            v_onset_kv = v_onset_v / 1000.0;
        }
    }

    return v_onset_kv;
}

int32_t ehd_compute_thrust(const EHD_Config_t *config, 
                           double voltage_kv, 
                           double air_density_ratio, 
                           EHD_State_t *state) {
    int32_t status = 0;

    if ((config == (void*)0) || (state == (void*)0)) {
        status = -1;
    }
    else if ((voltage_kv < 0.0) || (air_density_ratio <= 0.0)) {
        status = -2;
    }
    else {
        double v_onset_kv = ehd_corona_onset_voltage(config, air_density_ratio);

        state->voltage_kv = voltage_kv;

        if ((v_onset_kv < 0.0) || (voltage_kv <= v_onset_kv)) {
            /* Under threshold, no corona discharge */
            state->current_uA = 0.0;
            state->force_mN = 0.0;
            state->power_W = 0.0;
        }
        else {
            double v_volt = voltage_kv * 1000.0;
            double v_onset_volt = v_onset_kv * 1000.0;
            double d = config->gap_m;

            /* Townsend's Corona Current Approximation: I = K * V * (V - V_onset) */
            /* K coefficient derivation from space charge limits */
            double K = (2.0 * config->ion_mobility * config->epsilon_0) / (d * d * log(d / config->emitter_radius_m));
            double i_amp = K * v_volt * (v_volt - v_onset_volt);

            state->current_uA = i_amp * 1.0e6;
            
            /* Biefeld-Brown/Ion Drag Force: F = I * d / mu_ion (in Newtons) */
            double force_n = (i_amp * d) / config->ion_mobility;
            state->force_mN = force_n * 1000.0;

            state->power_W = i_amp * v_volt;
        }
    }

    return status;
}

double ehd_thrust_to_weight(double force_mN, double engine_weight_N) {
    double tw = 0.0;
    if ((force_mN > 0.0) && (engine_weight_N > 0.0)) {
        double force_n = force_mN / 1000.0;
        tw = force_n / engine_weight_N;
    }
    return tw;
}
