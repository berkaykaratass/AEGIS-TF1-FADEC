/**
 * @file brayton_thermo.c
 * @brief Brayton Cycle Thermodynamic Calculations Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#include "brayton_thermo.h"
#include <math.h>

#define MIN_TEMPERATURE 100.0
#define MAX_TEMPERATURE 3000.0
#define MIN_PRESSURE    1000.0
#define MIN_EFFICIENCY  0.1
#define MAX_EFFICIENCY  1.0

double brayton_thermal_efficiency(double r_p, double gamma) {
    double eff = 0.0;
    if ((r_p > 1.0) && (gamma > 1.0)) {
        double exponent = (gamma - 1.0) / gamma;
        eff = 1.0 - (1.0 / pow(r_p, exponent));
    }
    return eff;
}

double brayton_specific_thrust(const BraytonState_t *state, double f) {
    double F_s = 0.0;
    if (state != (void*)0) {
        F_s = ((1.0 + f) * state->V[9]) - state->V[0];
    }
    return F_s;
}

double brayton_tsfc(double f, double F_specific) {
    double tsfc = 0.0;
    if ((F_specific > 0.0) && (f > 0.0)) {
        tsfc = f / F_specific;
    }
    return tsfc;
}

int32_t brayton_compute_cycle(const BraytonParams_t *params, 
                             double T_amb, 
                             double P_amb, 
                             double M_flight, 
                             double r_p, 
                             double T4_max, 
                             BraytonState_t *state, 
                             BraytonPerformance_t *perf) {
    int32_t status = 0;

    /* Parameter validation for safety critical compliance */
    if ((params == (void*)0) || (state == (void*)0) || (perf == (void*)0)) {
        status = -1;
    }
    else if ((T_amb < MIN_TEMPERATURE) || (T_amb > MAX_TEMPERATURE) ||
             (P_amb < MIN_PRESSURE) || (M_flight < 0.0) || (r_p < 1.0) ||
             (T4_max < MIN_TEMPERATURE) || (T4_max > MAX_TEMPERATURE)) {
        status = -2;
    }
    else if ((params->eta_c < MIN_EFFICIENCY) || (params->eta_c > MAX_EFFICIENCY) ||
             (params->eta_b < MIN_EFFICIENCY) || (params->eta_b > MAX_EFFICIENCY) ||
             (params->eta_t < MIN_EFFICIENCY) || (params->eta_t > MAX_EFFICIENCY) ||
             (params->eta_n < MIN_EFFICIENCY) || (params->eta_n > MAX_EFFICIENCY)) {
        status = -3;
    }
    else {
        double gamma_a_exp = (params->gamma_a - 1.0) / params->gamma_a;
        double gamma_g_exp = (params->gamma_g - 1.0) / params->gamma_g;

        /* Station 0 & 2: Ram Compression */
        state->T_t[0] = T_amb;
        state->P_t[0] = P_amb;
        
        /* Speed of sound in ambient air: a_0 = sqrt(gamma * R * T) */
        double R_air = 287.05;
        double a_0 = sqrt(params->gamma_a * R_air * T_amb);
        state->V[0] = M_flight * a_0;

        /* Total temperature and pressure at compressor face (station 2) */
        state->T_t[2] = T_amb * (1.0 + (((params->gamma_a - 1.0) / 2.0) * (M_flight * M_flight)));
        state->P_t[2] = P_amb * pow(state->T_t[2] / T_amb, params->gamma_a / (params->gamma_a - 1.0));
        state->V[2] = state->V[0]; /* Assume simple inlet flow */

        /* Station 3: Compressor exit */
        state->P_t[3] = state->P_t[2] * r_p;
        double T_t3_ideal = state->T_t[2] * pow(r_p, gamma_a_exp);
        state->T_t[3] = state->T_t[2] + ((T_t3_ideal - state->T_t[2]) / params->eta_c);
        state->W_comp = params->cp_a * (state->T_t[3] - state->T_t[2]);

        /* Station 4: Combustor exit / Turbine inlet */
        state->T_t[4] = T4_max;
        /* 3% Pressure loss in combustion chamber */
        state->P_t[4] = state->P_t[3] * 0.97; 

        /* Fuel-to-air ratio calculation */
        double f_num = params->cp_g * (state->T_t[4] - state->T_t[3]);
        double f_den = (params->Q_R * params->eta_b) - (params->cp_g * state->T_t[4]);
        
        if (f_den <= 0.0) {
            status = -4;
        }
        else {
            perf->f = f_num / f_den;

            /* Station 5: Turbine exit (Power balance: W_t = W_c / (1+f)) */
            state->W_turb = state->W_comp / (1.0 + perf->f);
            state->T_t[5] = state->T_t[4] - (state->W_turb / params->cp_g);
            
            double P5_temp = 1.0 - ((1.0 - (state->T_t[5] / state->T_t[4])) / params->eta_t);
            if (P5_temp <= 0.0) {
                status = -5;
            }
            else {
                state->P_t[5] = state->P_t[4] * pow(P5_temp, params->gamma_g / (params->gamma_g - 1.0));

                /* Station 9: Nozzle exit */
                state->P_t[9] = P_amb; /* Fully expanded nozzle assumption */
                double V_e_sq = 2.0 * params->cp_g * params->eta_n * state->T_t[5] * 
                               (1.0 - pow(P_amb / state->P_t[5], gamma_g_exp));
                
                if (V_e_sq < 0.0) {
                    state->V[9] = 0.0;
                }
                else {
                    state->V[9] = sqrt(V_e_sq);
                }
                state->T_t[9] = state->T_t[5] - ((state->V[9] * state->V[9]) / (2.0 * params->cp_g));

                /* Performance metrics calculation */
                perf->F_specific = ((1.0 + perf->f) * state->V[9]) - state->V[0];
                perf->TSFC = brayton_tsfc(perf->f, perf->F_specific);

                /* Thermal and Propulsive Efficiencies */
                double kinetic_out = (1.0 + perf->f) * (state->V[9] * state->V[9]);
                double kinetic_in = state->V[0] * state->V[0];
                double heat_in = 2.0 * perf->f * params->Q_R;
                
                if (heat_in > 0.0) {
                    perf->eta_thermal = (kinetic_out - kinetic_in) / heat_in;
                }
                else {
                    perf->eta_thermal = 0.0;
                }

                double denom_prop = ((1.0 + perf->f) * state->V[9]) + state->V[0];
                if (denom_prop > 0.0) {
                    perf->eta_propulsive = (2.0 * state->V[0]) / denom_prop;
                }
                else {
                    perf->eta_propulsive = 0.0;
                }

                perf->eta_overall = perf->eta_thermal * perf->eta_propulsive;
            }
        }
    }

    return status;
}
