/**
 * @file fadec_control.h
 * @brief FADEC Closed-Loop Control System Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 2.0.0
 */

#ifndef FADEC_CONTROL_H
#define FADEC_CONTROL_H

#ifdef __cplusplus
#define FADEC_EXPORT __attribute__((visibility("default")))
extern "C" {
#else
#define FADEC_EXPORT
#endif

#include <stdint.h>
#include <stdbool.h>
#include "fadec_hal.h"
#include "engine_start.h"
#include "thrust_modes.h"
#include "fuel_schedule.h"
#include "vane_schedule.h"
#include "dual_channel.h"
#include "safety_monitor.h"
#include "triple_buffer.h"
#include "arinc429.h"
#include "fdir_sensor.h"
#include "cognitive_engine.h"
#include "model_based_control.h"
#include "actuator_control.h"
#include "cyber_watermark.h"
#include "creep_governor.h"
#include "active_clearance.h"

typedef enum {
    MODE_STARTUP = 0,
    MODE_IDLE,
    MODE_ACCEL,
    MODE_CRUISE,
    MODE_DECEL,
    MODE_EMERGENCY_SHUTDOWN,
    MODE_AI_ADVISORY_ACTIVE,
    MODE_AI_LOCKOUT,
    MODE_LIMIT_ONLY
} FADEC_Mode_e;

typedef enum {
    CHANNEL_A = 0,
    CHANNEL_B
} FADEC_Channel_e;

typedef struct {
    double kp;
    double ki;
    double kd;
    double integral;
    double prev_error;
    double output;
    double min_limit;
    double max_limit;
    double dt;
} PID_State_t;

typedef struct {
    double max_n1_rpm;
    double max_egt_kelvin;
    double max_p3_bar;
    double accel_limit_rpm_per_sec;
    double decel_limit_rpm_per_sec;
} ControlLimits_t;

typedef struct {
    uint64_t timestamp_us;
    double wf_limit_pct;
    double surge_prob;
    uint32_t sequence_id;
} AI_Advisory_t;

typedef struct {
    double last_wf;
    double Ki;
} BumplessTransfer_t;

typedef struct {
    char sw_version[16];
    char cal_version[16];
    char engine_config[16];
    uint32_t sw_checksum;
} FADEC_ConfigID_t;

typedef struct {
    FADEC_Mode_e mode;
    FADEC_Channel_e active_channel;
    PID_State_t n1_speed_pid;
    ControlLimits_t limits;
    double throttle_demand_pct;
    double active_fuel_command;
    uint32_t surge_warning;
    uint32_t sensor_faults;
    double run_time_sec;
    
    /* Integrated Subsystems */
    StartSequence_t start_seq;
    ThrustRatingConfig_t thrust_config;
    VaneState_t vane_state;
    ChannelConfig_t channel_config;
    SafetyMonitorState_t safety_monitor;
    BumplessTransfer_t bumpless;
    FDIR_SensorState_t fdir_state;
    
    /* AI Advisory / Lockout States */
    uint32_t ai_lockout_timer_ms;
    AI_Advisory_t last_ai_advisory;
    uint32_t scheduler_ticks;
    double shaped_accel_limit;
    double prev_speed_rpm;
    float p3_history[5];
    AI_Advisory_Telemetry_t advisory_telemetry;
    
    /* FADEC v9.0 Advanced Subsystems */
    MBC_State_t mbc_state;
    ActuatorLoop_State_t actuator_state;
    Watermark_State_t watermark_state;
    CreepState_t creep_state;
    ACC_State_t acc_state;
    
    CognitiveState_t cognitive_state;
    FADEC_ConfigID_t config_id;
} FADEC_State_t;

/**
 * @brief Initialize FADEC control state and PID controllers
 */
FADEC_EXPORT int32_t fadec_init(FADEC_State_t *state);

/**
 * @brief Execute a single control step (called at 1 kHz / 1 ms rate)
 */
FADEC_EXPORT int32_t fadec_control_step(FADEC_State_t *state, 
                                        const HAL_SensorReadings_t *sensors, 
                                        HAL_ActuatorCommands_t *actuators);

/**
 * @brief Compute PID controller step output
 */
FADEC_EXPORT double pid_compute(PID_State_t *pid, double setpoint, double process_value);

/**
 * @brief Reset PID controller state variables
 */
FADEC_EXPORT void pid_reset(PID_State_t *pid);

/**
 * @brief Enforce acceleration limits on speed command rate of change
 */
FADEC_EXPORT double accel_limiter(const ControlLimits_t *limit, double current_rpm, double target_rpm, double dt);

/**
 * @brief Check engine parameters for surge threshold breaches
 */
FADEC_EXPORT uint32_t surge_protection_check(double flow_op, double pr_op, double speed_pct);

FADEC_EXPORT int32_t fadec_write_memory(uint32_t src_partition, uint32_t dest_addr, uint32_t value);

#ifdef __cplusplus
}
#endif

#endif /* FADEC_CONTROL_H */
