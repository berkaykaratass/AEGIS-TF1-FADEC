/**
 * @file fuel_schedule.c
 * @brief Fuel Flow Scheduling and Acceleration Limits Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#include "fuel_schedule.h"
#include <math.h>

#define MAX_LIMIT_TABLE_SIZE 4U
#define MIN_LIMIT_TABLE_SIZE 4U

static const double max_limit_rpm_pts[MAX_LIMIT_TABLE_SIZE]   = {15000.0, 50000.0, 80000.0, 100000.0};
static const double max_limit_wf_p3_pts[MAX_LIMIT_TABLE_SIZE] = {0.012, 0.015, 0.022, 0.026};

static const double min_limit_rpm_pts[MIN_LIMIT_TABLE_SIZE]   = {15000.0, 50000.0, 80000.0, 100000.0};
static const double min_limit_wf_p3_pts[MIN_LIMIT_TABLE_SIZE] = {0.003, 0.003, 0.005, 0.006};

void fuel_schedule_init(void) {
    /* No dynamically allocated states to initialize */
}

double interpolate_1d_lut(double x, const double *x_table, const double *y_table, uint32_t table_size) {
    double y = 0.0;

    if ((x_table != (void*)0) && (y_table != (void*)0) && (table_size > 0U)) {
        if (x <= x_table[0]) {
            y = y_table[0];
        }
        else if (x >= x_table[table_size - 1U]) {
            y = y_table[table_size - 1U];
        }
        else {
            /* Linear search for interval */
            uint32_t i = 0U;
            while (i < (table_size - 1U)) {
                if ((x >= x_table[i]) && (x < x_table[i + 1U])) {
                    double fraction = (x - x_table[i]) / (x_table[i + 1U] - x_table[i]);
                    y = y_table[i] + (fraction * (y_table[i + 1U] - y_table[i]));
                    break;
                }
                i++;
            }
        }
    }

    return y;
}

void fuel_schedule_get_limits(double n2_rpm, double p3_bar, double t2_kelvin, FuelLimits_t *limits) {
    if (limits != (void*)0) {
        double theta = t2_kelvin / 288.15;
        if (theta < 0.1) {
            theta = 0.1;
        }
        
        /* Correct N2 speed based on inlet temperature T2 */
        double n2_corr = n2_rpm / sqrt(theta);
        
        /* Interpolate Wf/P3 ratio limits */
        double max_wf_p3 = interpolate_1d_lut(n2_corr, max_limit_rpm_pts, max_limit_wf_p3_pts, MAX_LIMIT_TABLE_SIZE);
        double min_wf_p3 = interpolate_1d_lut(n2_corr, min_limit_rpm_pts, min_limit_wf_p3_pts, MIN_LIMIT_TABLE_SIZE);
        
        /* Calculate actual physical fuel flow limits (kg/s) */
        double max_wf = max_wf_p3 * p3_bar;
        double min_wf = min_wf_p3 * p3_bar;
        
        /* Convert physical Wf limit back to valve position percent (0-100%) */
        /* Wf = 0.01 + (pct/100)*0.29 -> pct = (Wf - 0.01) / 0.29 * 100 */
        double max_pct = ((max_wf - 0.01) / 0.29) * 100.0;
        double min_pct = ((min_wf - 0.01) / 0.29) * 100.0;
        
        if (max_pct < 0.0) max_pct = 0.0;
        if (max_pct > 100.0) max_pct = 100.0;
        if (min_pct < 0.0) min_pct = 0.0;
        if (min_pct > 100.0) min_pct = 100.0;
        
        limits->max_wf_pct = max_pct;
        limits->min_wf_pct = min_pct;
    }
}
