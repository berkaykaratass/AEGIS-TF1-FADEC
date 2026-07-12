/**
 * @file fuel_schedule.h
 * @brief Fuel Flow Scheduling and Acceleration Limits Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef FUEL_SCHEDULE_H
#define FUEL_SCHEDULE_H

#include <stdint.h>

typedef struct {
    double min_wf_pct;   /* absolute minimum fuel command (flameout limit) */
    double max_wf_pct;   /* absolute maximum fuel command (structural limit) */
} FuelLimits_t;

/**
 * @brief Initialize the fuel scheduling schedules
 */
void fuel_schedule_init(void);

/**
 * @brief Get fuel flow limits based on current speed and P3 pressure to prevent surge and flameout
 * @param[in] n2_rpm Engine spool speed
 * @param[in] p3_bar Burner discharge pressure (bar)
 * @param[in] t2_kelvin Inlet temperature (K)
 * @param[out] limits Calculated min and max fuel command limits (percent)
 */
void fuel_schedule_get_limits(double n2_rpm, double p3_bar, double t2_kelvin, FuelLimits_t *limits);

/**
 * @brief Interpolate a 2D look-up table (LUT)
 * @param[in] x Query input
 * @param[in] x_table Pointer to sorted input coordinate array
 * @param[in] y_table Pointer to corresponding output coordinate array
 * @param[in] table_size Size of the lookup table
 * @return Interpolated value
 */
double interpolate_1d_lut(double x, const double *x_table, const double *y_table, uint32_t table_size);

#endif /* FUEL_SCHEDULE_H */
