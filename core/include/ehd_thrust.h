/**
 * @file ehd_thrust.h
 * @brief Electrohydrodynamic (EHD) Thrust Augmentation Header
 * 
 * @details Models the Biefeld-Brown effect and ion-drag force for boundary
 *          layer flow control and auxiliary thrust generation.
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#ifndef EHD_THRUST_H
#define EHD_THRUST_H

#include <stdint.h>

typedef struct {
    double gap_m;             /* Distance between electrodes (meters) */
    double emitter_radius_m;  /* Wire emitter radius (meters) */
    double ion_mobility;      /* Ion mobility constant (m^2/(V*s), typically 2.0e-4) */
    double epsilon_0;         /* Permittivity of free space (F/m, typically 8.854e-12) */
} EHD_Config_t;

typedef struct {
    double voltage_kv;        /* Operating voltage (kilovolts) */
    double current_uA;        /* Corona current (microamperes) */
    double force_mN;         /* Generated ion-drag force (millinewtons) */
    double power_W;           /* Power consumption (Watts) */
} EHD_State_t;

/**
 * @brief Calculate the corona discharge onset voltage (Peek's Law)
 * @param[in] config EHD geometry configuration
 * @param[in] air_density_ratio Ratio of ambient density to sea-level density
 * @return Corona onset voltage in kV, or negative on configuration error
 */
double ehd_corona_onset_voltage(const EHD_Config_t *config, double air_density_ratio);

/**
 * @brief Compute active EHD thrust force and electrical parameters
 * @param[in] config EHD geometry configuration
 * @param[in] voltage_kv Applied voltage in kV
 * @param[in] air_density_ratio Air density ratio delta
 * @param[out] state Computed voltage, current, force, and power
 * @return 0 on success, negative on range or calculation error
 */
int32_t ehd_compute_thrust(const EHD_Config_t *config, 
                           double voltage_kv, 
                           double air_density_ratio, 
                           EHD_State_t *state);

/**
 * @brief Compute the thrust-to-weight ratio contribution of EHD
 * @param[in] force_mN EHD force in mN
 * @param[in] engine_weight_N Total physical engine weight in Newtons
 * @return T/W contribution (dimensionless)
 */
double ehd_thrust_to_weight(double force_mN, double engine_weight_N);

#endif /* EHD_THRUST_H */
