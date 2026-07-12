/**
 * @file safety_monitor.h
 * @brief Safety Monitor (Formal STT Safety Kernel) Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef SAFETY_MONITOR_H
#define SAFETY_MONITOR_H

#include <stdint.h>
#include <stdbool.h>
#include "fadec_hal.h"

#define ABSOLUTE_MAX_N1_RPM    105000.0
#define ABSOLUTE_MAX_EGT_K     1050.0
#define ABSOLUTE_MAX_P3_BAR    15.0
#define ABSOLUTE_MAX_VIB_G     5.0

#ifdef __cplusplus
#define FADEC_EXPORT __attribute__((visibility("default")))
extern "C" {
#else
#define FADEC_EXPORT
#endif

typedef enum {
    SAFETY_STATE_NORMAL = 0,
    SAFETY_STATE_DEGRADED,       /* Single sensor fault / EKF fallback active */
    SAFETY_STATE_LIMIT_ONLY,      /* Dual sensor fault / assertion CBIT flag */
    SAFETY_STATE_EMERGENCY_SHUTDOWN, /* Physical breaches (overspeed/overtemp) */
    SAFETY_STATE_MAX
} SafetyState_e;

typedef enum {
    CBIT_EVENT_NONE = 0,
    CBIT_EVENT_SINGLE_SENSOR_FAIL,
    CBIT_EVENT_EKF_DIVERGE,
    CBIT_EVENT_DUAL_SENSOR_FAIL,
    CBIT_EVENT_ASSERTION_FAIL,
    CBIT_EVENT_PHYSICAL_BREACH,  /* Overspeed, overtemp, vibration */
    CBIT_EVENT_MAX
} CBITEvent_e;

typedef enum {
    VERDICT_PASS = 0,
    VERDICT_INHIBIT_WF,      /* Clamping fuel flow due to degraded mode */
    VERDICT_EMERGENCY_SHUTDOWN /* Shutting down due to physical breach or crash */
} SafetyVerdict_e;

typedef struct {
    double egt_overshoot_timer;
    double vibration_overshoot_timer;
    bool trip_active;
    SafetyState_e current_state;
} SafetyMonitorState_t;

/**
 * @brief Initialize safety monitor and execute compile-time/init-time STT validation
 */
FADEC_EXPORT void safety_monitor_init(SafetyMonitorState_t *smon);

/**
 * @brief Evaluates CBIT event flags and executes a single transition step in exactly 1 ms.
 */
FADEC_EXPORT SafetyVerdict_e safety_monitor_process_stt(SafetyMonitorState_t *smon,
                                                       const HAL_SensorReadings_t *raw_sensors,
                                                       uint32_t cbit_flags,
                                                       double requested_wf_pct,
                                                       double *safe_wf_pct,
                                                       double dt);

#ifdef __cplusplus
}
#endif

#endif /* SAFETY_MONITOR_H */
