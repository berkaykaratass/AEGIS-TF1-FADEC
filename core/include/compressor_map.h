/**
 * @file compressor_map.h
 * @brief Compressor Map and Moore-Greitzer Surge Model Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#ifndef COMPRESSOR_MAP_H
#define COMPRESSOR_MAP_H

#include <stdint.h>

#define MAX_SPEED_LINES       12
#define MAX_POINTS_PER_LINE   20

typedef struct {
    double corrected_flow;  /* kg/s */
    double pressure_ratio;  /* PR */
    double efficiency;      /* 0.0 - 1.0 */
} CompressorMapPoint_t;

typedef struct {
    double corrected_speed_pct;  /* Corrected speed percent (50% to 110%) */
    int32_t num_points;
    CompressorMapPoint_t points[MAX_POINTS_PER_LINE];
} SpeedLine_t;

typedef struct {
    int32_t num_speed_lines;
    SpeedLine_t speed_lines[MAX_SPEED_LINES];
    int32_t num_surge_points;
    CompressorMapPoint_t surge_line[MAX_SPEED_LINES];
} CompressorMap_t;

typedef struct {
    double phi;       /* Flow coefficient (annulus averaged axial velocity / blade tip speed) */
    double psi;       /* Pressure rise coefficient */
    double J_amp;     /* Squared amplitude of first rotating stall harmonic */
    double B_param;   /* Greitzer stability parameter */
    double sigma;     /* Reciprocal of time constant for stall development */
    double l_c;       /* Effective length of compressor and duct */
} MooreGreitzerState_t;

/**
 * @brief Initialize the compressor map with synthetic calibrated data
 * @param[out] map Compressor map structure to populate
 * @return 0 on success, negative value on failure
 */
int32_t compressor_map_init(CompressorMap_t *map);

/**
 * @brief Lookup operating pressure ratio and efficiency from corrected flow and speed
 * @param[in] map Compressor map structure
 * @param[in] flow_corr Corrected mass flow rate (kg/s)
 * @param[in] speed_corr_pct Corrected rotor speed percent
 * @param[out] pr_out Interpolated pressure ratio
 * @param[out] eff_out Interpolated efficiency
 * @return 0 on success, negative on interpolation or range error
 */
int32_t compressor_map_lookup(const CompressorMap_t *map, 
                              double flow_corr, 
                              double speed_corr_pct, 
                              double *pr_out, 
                              double *eff_out);

/**
 * @brief Calculate the dynamic surge margin
 * @param[in] flow_op Operating corrected flow (kg/s)
 * @param[in] pr_op Operating pressure ratio
 * @param[in] flow_surge Surge line corrected flow at the same speed (kg/s)
 * @param[in] pr_surge Surge line pressure ratio at the same speed
 * @return Surge margin (SM = (m_stall*PR_op)/(m_op*PR_stall) - 1). Negative values indicate active stall/surge.
 */
double compressor_surge_margin(double flow_op, double pr_op, double flow_surge, double pr_surge);

/**
 * @brief Calculate corrected mass flow rate
 * @param[in] flow Physical mass flow rate (kg/s)
 * @param[in] P_t2 Compressor inlet total pressure (Pascal)
 * @param[in] T_t2 Compressor inlet total temperature (Kelvin)
 * @return Corrected mass flow rate (kg/s)
 */
double compressor_corrected_flow(double flow, double P_t2, double T_t2);

/**
 * @brief Calculate corrected speed percentage
 * @param[in] speed_rpm Physical speed in RPM
 * @param[in] T_t2 Compressor inlet total temperature (Kelvin)
 * @return Corrected speed percentage
 */
double compressor_corrected_speed(double speed_rpm, double T_t2);

/**
 * @brief Execute a single integration step of the Moore-Greitzer model (Runge-Kutta 4th order)
 * @param[in,out] state State of the Moore-Greitzer model
 * @param[in] throttle_opening Throttle command/opening area (0.0 to 1.0)
 * @param[in] dt Time step (seconds)
 * @return 0 on success, negative value on numerical failure
 */
int32_t moore_greitzer_step(MooreGreitzerState_t *state, double throttle_opening, double dt);

#endif /* COMPRESSOR_MAP_H */
