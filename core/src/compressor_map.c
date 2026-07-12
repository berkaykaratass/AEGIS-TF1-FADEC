/**
 * @file compressor_map.c
 * @brief Compressor Map Interpolation and Moore-Greitzer Surge Model Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#include "compressor_map.h"
#include <math.h>

/* Reference atmospheric conditions */
#define T_REF_KELVIN    288.15
#define P_REF_PASCAL    101325.0
#define RPM_REF         20000.0

/* Moore-Greitzer Cubic Characteristic Constants */
#define PSI_CO          0.18
#define PHI_CO          0.25
#define S_CHAR          0.12

static double psi_c_eval(double phi);
static double phi_t_eval(double psi, double throttle);

static double psi_c_eval(double phi) {
    /* Cubic approximation of compressor characteristic */
    double ratio = phi / PHI_CO;
    double val = 1.0 + (1.5 * (ratio - 1.0)) - (0.5 * pow(ratio - 1.0, 3.0));
    return PSI_CO + (S_CHAR * val);
}

static double phi_t_eval(double psi, double throttle) {
    /* Throttle valve flow characteristic */
    double val = 0.0;
    if (psi > 0.0) {
        val = throttle * sqrt(psi);
    }
    return val;
}

int32_t compressor_map_init(CompressorMap_t *map) {
    int32_t status = 0;
    if (map == (void*)0) {
        status = -1;
    }
    else {
        map->num_speed_lines = 7;
        map->num_surge_points = 7;

        double speeds[7] = {50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0};
        /* Surge line points: corrected flow (kg/s) and pressure ratio */
        double surge_flows[7] = {4.5, 6.0, 8.2, 11.0, 14.5, 18.2, 21.0};
        double surge_prs[7] = {2.2, 3.1, 4.5, 6.8, 10.5, 15.2, 19.5};

        for (int32_t i = 0; i < 7; i++) {
            map->speed_lines[i].corrected_speed_pct = speeds[i];
            map->speed_lines[i].num_points = 5;

            /* Surge point for this speed line */
            map->surge_line[i].corrected_flow = surge_flows[i];
            map->surge_line[i].pressure_ratio = surge_prs[i];
            map->surge_line[i].efficiency = 0.72;

            /* Generate points on the speed line from surge to choke */
            double flow_surge = surge_flows[i];
            double pr_surge = surge_prs[i];

            for (int32_t j = 0; j < 5; j++) {
                double frac = (double)j / 4.0;
                /* Flow increases from surge line towards choke */
                double flow = flow_surge + (frac * (flow_surge * 0.4));
                /* Pressure ratio decreases towards choke */
                double pr = pr_surge - (frac * (pr_surge * 0.3));
                /* Efficiency is parabolic, peaking in the middle */
                double eff = 0.85 - (0.15 * pow(frac - 0.5, 2.0));

                map->speed_lines[i].points[j].corrected_flow = flow;
                map->speed_lines[i].points[j].pressure_ratio = pr;
                map->speed_lines[i].points[j].efficiency = eff;
            }
        }
    }
    return status;
}

int32_t compressor_map_lookup(const CompressorMap_t *map, 
                              double flow_corr, 
                              double speed_corr_pct, 
                              double *pr_out, 
                              double *eff_out) {
    int32_t status = 0;

    if ((map == (void*)0) || (pr_out == (void*)0) || (eff_out == (void*)0)) {
        status = -1;
    }
    else {
        /* Find speed line index */
        int32_t idx_speed = -1;
        for (int32_t i = 0; i < map->num_speed_lines - 1; i++) {
            if ((speed_corr_pct >= map->speed_lines[i].corrected_speed_pct) &&
                (speed_corr_pct <= map->speed_lines[i + 1].corrected_speed_pct)) {
                idx_speed = i;
                break;
            }
        }

        if (idx_speed == -1) {
            /* Clamp speed to boundaries */
            if (speed_corr_pct < map->speed_lines[0].corrected_speed_pct) {
                idx_speed = 0;
            }
            else {
                idx_speed = map->num_speed_lines - 2;
            }
        }

        /* Interpolate on lower speed line */
        const SpeedLine_t *line1 = &map->speed_lines[idx_speed];
        double pr1 = 1.0;
        double eff1 = 0.7;
        
        if (flow_corr <= line1->points[0].corrected_flow) {
            pr1 = line1->points[0].pressure_ratio;
            eff1 = line1->points[0].efficiency;
        }
        else if (flow_corr >= line1->points[line1->num_points - 1].corrected_flow) {
            pr1 = line1->points[line1->num_points - 1].pressure_ratio;
            eff1 = line1->points[line1->num_points - 1].efficiency;
        }
        else {
            for (int32_t j = 0; j < line1->num_points - 1; j++) {
                if ((flow_corr >= line1->points[j].corrected_flow) &&
                    (flow_corr <= line1->points[j + 1].corrected_flow)) {
                    double t = (flow_corr - line1->points[j].corrected_flow) /
                               (line1->points[j + 1].corrected_flow - line1->points[j].corrected_flow);
                    pr1 = line1->points[j].pressure_ratio + (t * (line1->points[j + 1].pressure_ratio - line1->points[j].pressure_ratio));
                    eff1 = line1->points[j].efficiency + (t * (line1->points[j + 1].efficiency - line1->points[j].efficiency));
                    break;
                }
            }
        }

        /* Interpolate on upper speed line */
        const SpeedLine_t *line2 = &map->speed_lines[idx_speed + 1];
        double pr2 = 1.0;
        double eff2 = 0.7;

        if (flow_corr <= line2->points[0].corrected_flow) {
            pr2 = line2->points[0].pressure_ratio;
            eff2 = line2->points[0].efficiency;
        }
        else if (flow_corr >= line2->points[line2->num_points - 1].corrected_flow) {
            pr2 = line2->points[line2->num_points - 1].pressure_ratio;
            eff2 = line2->points[line2->num_points - 1].efficiency;
        }
        else {
            for (int32_t j = 0; j < line2->num_points - 1; j++) {
                if ((flow_corr >= line2->points[j].corrected_flow) &&
                    (flow_corr <= line2->points[j + 1].corrected_flow)) {
                    double t = (flow_corr - line2->points[j].corrected_flow) /
                               (line2->points[j + 1].corrected_flow - line2->points[j].corrected_flow);
                    pr2 = line2->points[j].pressure_ratio + (t * (line2->points[j + 1].pressure_ratio - line2->points[j].pressure_ratio));
                    eff2 = line2->points[j].efficiency + (t * (line2->points[j + 1].efficiency - line2->points[j].efficiency));
                    break;
                }
            }
        }

        /* Interpolate between speed lines */
        double speed_t = (speed_corr_pct - line1->corrected_speed_pct) /
                         (line2->corrected_speed_pct - line1->corrected_speed_pct);
        if (speed_t < 0.0) { speed_t = 0.0; }
        if (speed_t > 1.0) { speed_t = 1.0; }

        *pr_out = pr1 + (speed_t * (pr2 - pr1));
        *eff_out = eff1 + (speed_t * (eff2 - eff1));
    }

    return status;
}

double compressor_surge_margin(double flow_op, double pr_op, double flow_surge, double pr_surge) {
    double sm = 0.0;
    if ((flow_op > 0.0) && (pr_op > 0.0) && (flow_surge > 0.0) && (pr_surge > 0.0)) {
        sm = ((flow_op * pr_surge) / (flow_surge * pr_op)) - 1.0;
    }
    return sm;
}

double compressor_corrected_flow(double flow, double P_t2, double T_t2) {
    double flow_corr = 0.0;
    if ((P_t2 > 0.0) && (T_t2 > 0.0)) {
        double theta = T_t2 / T_REF_KELVIN;
        double delta = P_t2 / P_REF_PASCAL;
        flow_corr = (flow * sqrt(theta)) / delta;
    }
    return flow_corr;
}

double compressor_corrected_speed(double speed_rpm, double T_t2) {
    double speed_corr = 0.0;
    if (T_t2 > 0.0) {
        double theta = T_t2 / T_REF_KELVIN;
        speed_corr = (speed_rpm / sqrt(theta)) * (100.0 / RPM_REF);
    }
    return speed_corr;
}

int32_t moore_greitzer_step(MooreGreitzerState_t *state, double throttle_opening, double dt) {
    int32_t status = 0;

    if ((state == (void*)0) || (dt <= 0.0)) {
        status = -1;
    }
    else {
        /* Runge-Kutta 4th order integration */
        double phi = state->phi;
        double psi = state->psi;
        double J = state->J_amp;
        double B = state->B_param;
        double l_c = state->l_c;
        double sigma = state->sigma;

        /* k1 derivatives */
        double dphi1 = (1.0 / l_c) * (psi_c_eval(phi) - psi);
        double dpsi1 = (1.0 / (4.0 * B * B * l_c)) * (phi - phi_t_eval(psi, throttle_opening));
        double dJ1 = 2.0 * sigma * J * (1.0 - phi - J); /* Simplified stall term */

        /* Intermediate step 1 */
        double phi_i1 = phi + (0.5 * dt * dphi1);
        double psi_i1 = psi + (0.5 * dt * dpsi1);
        double J_i1 = J + (0.5 * dt * dJ1);

        /* k2 derivatives */
        double dphi2 = (1.0 / l_c) * (psi_c_eval(phi_i1) - psi_i1);
        double dpsi2 = (1.0 / (4.0 * B * B * l_c)) * (phi_i1 - phi_t_eval(psi_i1, throttle_opening));
        double dJ2 = 2.0 * sigma * J_i1 * (1.0 - phi_i1 - J_i1);

        /* Intermediate step 2 */
        double phi_i2 = phi + (0.5 * dt * dphi2);
        double psi_i2 = psi + (0.5 * dt * dpsi2);
        double J_i2 = J + (0.5 * dt * dJ2);

        /* k3 derivatives */
        double dphi3 = (1.0 / l_c) * (psi_c_eval(phi_i2) - psi_i2);
        double dpsi3 = (1.0 / (4.0 * B * B * l_c)) * (phi_i2 - phi_t_eval(psi_i2, throttle_opening));
        double dJ3 = 2.0 * sigma * J_i2 * (1.0 - phi_i2 - J_i2);

        /* Intermediate step 3 */
        double phi_i3 = phi + (dt * dphi3);
        double psi_i3 = psi + (dt * dpsi3);
        double J_i3 = J + (dt * dJ3);

        /* k4 derivatives */
        double dphi4 = (1.0 / l_c) * (psi_c_eval(phi_i3) - psi_i3);
        double dpsi4 = (1.0 / (4.0 * B * B * l_c)) * (phi_i3 - phi_t_eval(psi_i3, throttle_opening));
        double dJ4 = 2.0 * sigma * J_i3 * (1.0 - phi_i3 - J_i3);

        /* Update state */
        state->phi += (dt / 6.0) * (dphi1 + (2.0 * dphi2) + (2.0 * dphi3) + dphi4);
        state->psi += (dt / 6.0) * (dpsi1 + (2.0 * dpsi2) + (2.0 * dpsi3) + dpsi4);
        state->J_amp += (dt / 6.0) * (dJ1 + (2.0 * dJ2) + (2.0 * dJ3) + dJ4);

        /* Keep values bounded physically */
        if (state->phi < 0.001) { state->phi = 0.001; }
        if (state->psi < 0.001) { state->psi = 0.001; }
        if (state->J_amp < 0.0) { state->J_amp = 0.0; }
    }

    return status;
}
