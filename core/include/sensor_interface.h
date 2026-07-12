/**
 * @file sensor_interface.h
 * @brief Safety-Critical Sensor Processing Interface
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#ifndef SENSOR_INTERFACE_H
#define SENSOR_INTERFACE_H

#include <stdint.h>

typedef enum {
    SENSOR_SPEED_PROBE = 0,
    SENSOR_THERMOCOUPLE,
    SENSOR_PRESSURE,
    SENSOR_VIBRATION,
    SENSOR_FUEL_FLOW,
    SENSOR_TYPE_COUNT
} SensorType_e;

typedef enum {
    FAULT_NONE = 0,
    FAULT_OUT_OF_BOUNDS,
    FAULT_STUCK_VALUE,
    FAULT_NO_SIGNAL
} SensorFault_e;

typedef struct {
    double min_range;
    double max_range;
    double calibration_gain;
    double calibration_offset;
    double filter_alpha;       /* Exponential moving average alpha (0.0 to 1.0) */
} SensorConfig_t;

typedef struct {
    double raw_value;
    double calibrated_value;
    double filtered_value;
    uint32_t is_valid;
    SensorFault_e fault;
} SensorData_t;

/**
 * @brief Initialize sensor configs and data structures
 * @return 0 on success, negative value on error
 */
int32_t sensor_init(void);

/**
 * @brief Process single sensor reading point
 * @param[in] type Sensor channel to process
 * @param[in] raw_input Raw analog/digital value read from hardware
 * @param[out] processed Output processed data structure
 * @return 0 on success, negative value on validation or bounds error
 */
int32_t sensor_process_point(SensorType_e type, double raw_input, SensorData_t *processed);

/**
 * @brief Perform signal calibration correction
 * @param[in] config Calibration config
 * @param[in] raw Raw input value
 * @return Calibrated value
 */
double sensor_calibrate(const SensorConfig_t *config, double raw);

/**
 * @brief Perform Range and Fault Validation checks
 * @param[in] config Validation config
 * @param[in] value Calibrated value
 * @param[in,out] processed Sensor state tracker
 * @return 1 if valid, 0 if fault detected
 */
uint32_t sensor_validate(const SensorConfig_t *config, double value, SensorData_t *processed);

/**
 * @brief Compute Exponential Moving Average (EMA) filter step
 * @param[in] alpha Smoothing factor (0.0 < alpha <= 1.0)
 * @param[in] current Current value
 * @param[in] previous Previous filtered value
 * @return Filtered output
 */
double sensor_filter_ema(double alpha, double current, double previous);

#endif /* SENSOR_INTERFACE_H */
