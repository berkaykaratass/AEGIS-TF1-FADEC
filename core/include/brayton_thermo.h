/**
 * @file brayton_thermo.h
 * @brief Brayton Cycle Thermodynamic Calculations Header
 * 
 * @details Models the thermodynamic cycle of a single-spool turbojet engine
 *          under varying flight conditions (altitude, Mach, throttle).
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#ifndef BRAYTON_THERMO_H
#define BRAYTON_THERMO_H

#include <stdint.h>

/**
 * @brief Thermodynamic parameters for the engine cycle
 */
typedef struct {
    double gamma_a;  /* Specific heat ratio for air (typically 1.4) */
    double gamma_g;  /* Specific heat ratio for gas (typically 1.33) */
    double cp_a;     /* Specific heat at constant pressure for air (J/kg*K, e.g. 1005) */
    double cp_g;     /* Specific heat at constant pressure for gas (J/kg*K, e.g. 1148) */
    double Q_R;      /* Fuel lower heating value (J/kg, e.g. 4.3e7) */
    double eta_b;    /* Combustor efficiency (0.0 - 1.0) */
    double eta_c;    /* Compressor efficiency (0.0 - 1.0) */
    double eta_t;    /* Turbine efficiency (0.0 - 1.0) */
    double eta_n;    /* Nozzle efficiency (0.0 - 1.0) */
} BraytonParams_t;

/**
 * @brief Thermodynamic state at cycle stations (0 to 9)
 * 
 * Stations:
 * 0: Free-stream ambient
 * 2: Compressor inlet / Engine face
 * 3: Compressor exit / Combustor inlet
 * 4: Combustor exit / Turbine inlet
 * 5: Turbine exit / Nozzle inlet
 * 9: Nozzle exit
 */
typedef struct {
    double T_t[10];  /* Total temperature at stations (Kelvin) */
    double P_t[10];  /* Total pressure at stations (Pascal) */
    double V[10];    /* Gas velocity at stations (m/s) */
    double W_comp;   /* Specific work consumed by compressor (J/kg) */
    double W_turb;   /* Specific work produced by turbine (J/kg) */
} BraytonState_t;

/**
 * @brief Performance metrics of the Brayton cycle
 */
typedef struct {
    double F_specific;     /* Specific thrust (N/(kg/s)) */
    double TSFC;           /* Thrust Specific Fuel Consumption (kg/(N*s)) */
    double eta_thermal;    /* Thermal efficiency */
    double eta_propulsive; /* Propulsive efficiency */
    double eta_overall;    /* Overall efficiency */
    double f;              /* Fuel-to-air ratio */
} BraytonPerformance_t;

/**
 * @brief Compute the thermodynamic state and performance for a single cycle point
 * @param[in] params Thermodynamic configuration constants
 * @param[in] T_amb Ambient temperature (Kelvin)
 * @param[in] P_amb Ambient pressure (Pascal)
 * @param[in] M_flight Flight Mach number
 * @param[in] r_p Compressor pressure ratio
 * @param[in] T4_max Maximum turbine inlet temperature (Kelvin)
 * @param[out] state Computed state values at each station
 * @param[out] perf Computed performance parameters
 * @return 0 on success, negative value on validation failure or thermal calculation error
 */
int32_t brayton_compute_cycle(const BraytonParams_t *params, 
                             double T_amb, 
                             double P_amb, 
                             double M_flight, 
                             double r_p, 
                             double T4_max, 
                             BraytonState_t *state, 
                             BraytonPerformance_t *perf);

/**
 * @brief Calculate the ideal Brayton cycle thermal efficiency
 * @param[in] r_p Pressure ratio
 * @param[in] gamma Specific heat ratio
 * @return Ideal thermal efficiency
 */
double brayton_thermal_efficiency(double r_p, double gamma);

/**
 * @brief Calculate the specific thrust
 * @param[in] state Current cycle state
 * @param[in] f Fuel-to-air ratio
 * @return Specific thrust in N/(kg/s)
 */
double brayton_specific_thrust(const BraytonState_t *state, double f);

/**
 * @brief Calculate Thrust Specific Fuel Consumption
 * @param[in] f Fuel-to-air ratio
 * @param[in] F_specific Specific thrust
 * @return TSFC in kg/(N*s)
 */
double brayton_tsfc(double f, double F_specific);

#endif /* BRAYTON_THERMO_H */
