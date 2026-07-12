/**
 * @file sensor_interface.c
 * @brief Safety-Critical Sensor Processing Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#include "sensor_interface.h"
#include <math.h>

#define STUCK_THRESHOLD_STEPS  100U

static SensorConfig_t configs[SENSOR_TYPE_COUNT];
static uint32_t stuck_counters[SENSOR_TYPE_COUNT];
static double last_calibrated_values[SENSOR_TYPE_COUNT];

int32_t sensor_init(void) {
    /* Speed Probe (Rotor RPM) config */
    configs[SENSOR_SPEED_PROBE].min_range = 0.0;
    configs[SENSOR_SPEED_PROBE].max_range = 115000.0;
    configs[SENSOR_SPEED_PROBE].calibration_gain = 1.0;
    configs[SENSOR_SPEED_PROBE].calibration_offset = 0.0;
    configs[SENSOR_SPEED_PROBE].filter_alpha = 0.2;

    /* Thermocouple (EGT Kelvin) config */
    configs[SENSOR_THERMOCOUPLE].min_range = 150.0;
    configs[SENSOR_THERMOCOUPLE].max_range = 1400.0;
    configs[SENSOR_THERMOCOUPLE].calibration_gain = 1.0;
    configs[SENSOR_THERMOCOUPLE].calibration_offset = 0.0;
    configs[SENSOR_THERMOCOUPLE].filter_alpha = 0.15;

    /* Pressure Sensor (Combustor P3 Bar) config */
    configs[SENSOR_PRESSURE].min_range = 0.1;
    configs[SENSOR_PRESSURE].max_range = 25.0;
    configs[SENSOR_PRESSURE].calibration_gain = 1.0;
    configs[SENSOR_PRESSURE].calibration_offset = 0.0;
    configs[SENSOR_PRESSURE].filter_alpha = 0.1;

    /* Vibration Accelerometer (Core Vibration G's) config */
    configs[SENSOR_VIBRATION].min_range = 0.0;
    configs[SENSOR_VIBRATION].max_range = 15.0;
    configs[SENSOR_VIBRATION].calibration_gain = 1.0;
    configs[SENSOR_VIBRATION].calibration_offset = 0.0;
    configs[SENSOR_VIBRATION].filter_alpha = 0.25;

    /* Fuel Flow Meter (kg/s) config */
    configs[SENSOR_FUEL_FLOW].min_range = 0.0;
    configs[SENSOR_FUEL_FLOW].max_range = 2.0;
    configs[SENSOR_FUEL_FLOW].calibration_gain = 1.0;
    configs[SENSOR_FUEL_FLOW].calibration_offset = 0.0;
    configs[SENSOR_FUEL_FLOW].filter_alpha = 0.3;

    for (int32_t i = 0; i < (int32_t)SENSOR_TYPE_COUNT; i++) {
        stuck_counters[i] = 0U;
        last_calibrated_values[i] = -9999.0;
    }

    return 0;
}

double sensor_calibrate(const SensorConfig_t *config, double raw) {
    double val = raw;
    if (config != (void*)0) {
        val = (raw * config->calibration_gain) + config->calibration_offset;
    }
    return val;
}

uint32_t sensor_validate(const SensorConfig_t *config, double value, SensorData_t *processed) {
    uint32_t is_valid = 1U;

    if ((config == (void*)0) || (processed == (void*)0)) {
        is_valid = 0U;
    }
    else {
        /* Range Check */
        if ((value < config->min_range) || (value > config->max_range)) {
            processed->fault = FAULT_OUT_OF_BOUNDS;
            is_valid = 0U;
        }
        else {
            /* Stuck Value Check */
            int32_t type_idx = -1;
            /* Find matching config index */
            for (int32_t i = 0; i < (int32_t)SENSOR_TYPE_COUNT; i++) {
                if (&configs[i] == config) {
                    type_idx = i;
                    break;
                }
            }

            if (type_idx != -1) {
                double diff = fabs(value - last_calibrated_values[type_idx]);
                /* If change is microscopically small, increment counter */
                if (diff < 1.0e-7) {
                    stuck_counters[type_idx]++;
                    if (stuck_counters[type_idx] >= STUCK_THRESHOLD_STEPS) {
                        processed->fault = FAULT_STUCK_VALUE;
                        is_valid = 0U;
                    }
                }
                else {
                    stuck_counters[type_idx] = 0U;
                    last_calibrated_values[type_idx] = value;
                }
            }
        }
    }

    if (is_valid == 1U) {
        processed->fault = FAULT_NONE;
    }

    return is_valid;
}

double sensor_filter_ema(double alpha, double current, double previous) {
    double filtered = current;
    if ((alpha > 0.0) && (alpha <= 1.0)) {
        filtered = (alpha * current) + ((1.0 - alpha) * previous);
    }
    return filtered;
}

int32_t sensor_process_point(SensorType_e type, double raw_input, SensorData_t *processed) {
    int32_t status = 0;

    if ((type >= SENSOR_TYPE_COUNT) || (processed == (void*)0)) {
        status = -1;
    }
    else {
        const SensorConfig_t *config = &configs[type];
        
        processed->raw_value = raw_input;
        
        /* 1. Calibrate */
        double calibrated = sensor_calibrate(config, raw_input);
        processed->calibrated_value = calibrated;

        /* 2. Validate */
        uint32_t valid = sensor_validate(config, calibrated, processed);
        processed->is_valid = valid;

        if (valid == 1U) {
            /* 3. Filter */
            double filtered = sensor_filter_ema(config->filter_alpha, calibrated, processed->filtered_value);
            processed->filtered_value = filtered;
        }
        else {
            status = -2; /* Validation fault */
        }
    }

    return status;
}
