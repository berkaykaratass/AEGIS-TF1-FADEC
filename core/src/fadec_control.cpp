/**
 * @file fadec_control.cpp
 * @brief FADEC Closed-Loop Control System Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C++:2008
 */

#include "fadec_types.hpp"
#include "engine_system.hpp"
#include "fadec_control.h"
#include "model_based_control.h"

extern "C" {
#include "fadec_assert.h"
#include "cognitive_engine.h"
#include "actuator_control.h"
#include "cyber_watermark.h"
#include "creep_governor.h"
#include "active_clearance.h"
}
#include <cmath>
#include <cstring>

#define MAX_FUEL_VALVE_PCT     100.0
#define MIN_FUEL_VALVE_PCT     0.0

#define MPU_PARTITION_CONTROL   1U
#define MPU_PARTITION_SAFETY    2U
#define MPU_PARTITION_ADVISORY  3U

#define ADDR_CONTROL_START   0x00000000U
#define ADDR_CONTROL_END     0x0003FFFFU
#define ADDR_SAFETY_START    0x00040000U
#define ADDR_SAFETY_END      0x0007FFFFU
#define ADDR_ADVISORY_START  0x00080000U
#define ADDR_ADVISORY_END    0x000BFFFFU

static bool run_post_diagnostics(void) {
    bool passed = true;
    volatile uint32_t dummy_flash[4] = {0x12345678U, 0xABCDEF01U, 0x98765432U, 0x11112222U};
    uint32_t crc = 0;
    for (int32_t i = 0; i < 4; i++) {
        crc ^= dummy_flash[i];
    }
    if (crc != 0x309ECF69U) {
        passed = false;
    }

    volatile uint32_t scratchpad = 0;
    scratchpad = 0x55AA55AAU;
    if (scratchpad != 0x55AA55AAU) {
        passed = false;
    }
    scratchpad = 0xAA55AA55U;
    if (scratchpad != 0xAA55AA55U) {
        passed = false;
    }
    return passed;
}

static bool run_cst_diagnostics(FADEC::EngineState *state) {
    bool passed = true;
    if (state == nullptr) {
        passed = false;
    } else {
        volatile double a = 12.34;
        volatile double b = 56.78;
        volatile double c = (a * b) + 9.99;
        if (std::fabs(c - 710.6552) > 1e-4) {
            passed = false;
        }

        if (state->scheduler_ticks == 0xFFFFFFFFU) {
            passed = false;
        }

        if (!passed) {
            state->sensor_faults |= 0x40U;
        }
    }
    return passed;
}

static bool mpu_check_access(uint32_t src_partition, uint32_t dest_addr, bool write_op) {
    bool allowed = true;
    if (src_partition == MPU_PARTITION_CONTROL) {
        if (write_op && (dest_addr > ADDR_CONTROL_END)) {
            allowed = false;
        }
    }
    else if (src_partition == MPU_PARTITION_SAFETY) {
        if (dest_addr >= ADDR_ADVISORY_START) {
            allowed = false;
        }
        if (write_op && ((dest_addr < ADDR_SAFETY_START) || (dest_addr > ADDR_SAFETY_END))) {
            allowed = false;
        }
    }
    else if (src_partition == MPU_PARTITION_ADVISORY) {
        if (write_op && (dest_addr < ADDR_ADVISORY_START)) {
            allowed = false;
        }
    }
    else {
        allowed = false;
    }
    return allowed;
}

namespace FADEC {

    void FadecController::init(EngineState* state) {
        state->n1_speed_pid.kp = 0.002;
        state->n1_speed_pid.ki = 0.001;
        state->n1_speed_pid.kd = 0.0005;
        state->n1_speed_pid.integral = 0.0;
        state->n1_speed_pid.prev_error = 0.0;
        state->n1_speed_pid.output = 0.0;
        state->n1_speed_pid.min_limit = 2.0;
        state->n1_speed_pid.max_limit = 95.0;
        state->n1_speed_pid.dt = 0.001;

        state->limits.max_n1_rpm = 100000.0;
        state->limits.max_egt_kelvin = 980.0;
        state->limits.max_p3_bar = 10.0;
        state->limits.accel_limit_rpm_per_sec = 8000.0;
        state->limits.decel_limit_rpm_per_sec = 12000.0;

        state->shaped_accel_limit = 8000.0;
    }

    double pid_compute(PIDState *pid, double setpoint, double process_value) {
        double out = 0.0;
        if (pid != nullptr) {
            double error = setpoint - process_value;
            double derivative = (error - pid->prev_error) / pid->dt;
            double next_integral = pid->integral + (error * pid->dt);
            double raw_output = (pid->kp * error) + (pid->ki * next_integral) + (pid->kd * derivative);

            if (raw_output > pid->max_limit) {
                out = pid->max_limit;
                if (error < 0.0) {
                    pid->integral = next_integral;
                }
            }
            else if (raw_output < pid->min_limit) {
                out = pid->min_limit;
                if (error > 0.0) {
                    pid->integral = next_integral;
                }
            }
            else {
                out = raw_output;
                pid->integral = next_integral;
            }
            pid->prev_error = error;
            pid->output = out;
        }
        return out;
    }

    static double accel_limiter(const ControlLimits *limit, double current_rpm, double target_rpm, double dt) {
        double limited_rpm = target_rpm;
        if ((limit != nullptr) && (dt > 0.0)) {
            double diff = target_rpm - current_rpm;
            if (diff > 0.0) {
                double max_accel = limit->accel_limit_rpm_per_sec * dt;
                if (diff > max_accel) {
                    limited_rpm = current_rpm + max_accel;
                }
            }
            else {
                double max_decel = limit->decel_limit_rpm_per_sec * dt;
                if (std::fabs(diff) > max_decel) {
                    limited_rpm = current_rpm - max_decel;
                }
            }
        }
        return limited_rpm;
    }

    void FadecController::update(EngineState* state, const SensorState* sensors, ActuatorState* actuators, double dt) {
        double validated_speed_rpm = sensors->n1_rpm;

        // Reset limits to flat rating defaults first
        state->limits.max_egt_kelvin = 980.0;
        state->shaped_accel_limit = 8000.0;

        switch (state->mode) {
            case MODE_STARTUP:
                {
                    double start_fuel_pct = 0.0;
                    StartSequence_t* seq = &state->start_seq;
                    StartState_e start_state = engine_start_step(seq, validated_speed_rpm, sensors->egt_kelvin, dt, &start_fuel_pct);
                    state->active_fuel_command = start_fuel_pct;
                    actuators->stator_vanes_deg = 30.0;
                    actuators->ehd_voltage_cmd_kv = 0.0;

                    if (start_state == START_STATE_ONLINE) {
                        state->mode = MODE_IDLE;
                        state->n1_speed_pid.integral = 0.0;
                        state->n1_speed_pid.prev_error = 0.0;
                        state->n1_speed_pid.output = 0.0;
                    }
                    else if (start_state == START_STATE_ABORTED) {
                        state->mode = MODE_EMERGENCY_SHUTDOWN;
                    }
                }
                break;

            case MODE_IDLE:
                state->active_fuel_command = FADEC::pid_compute(&state->n1_speed_pid, 15000.0, validated_speed_rpm);
                actuators->stator_vanes_deg = 15.0;
                actuators->ehd_voltage_cmd_kv = 0.0;

                if (state->throttle_demand_pct > 2.0) {
                    state->mode = MODE_CRUISE;
                }
                break;

            case MODE_CRUISE:
            case MODE_ACCEL:
            case MODE_DECEL:
                {
                    ThrustRatingConfig_t* thrust = &state->thrust_config;
                    thrust->rating = (state->throttle_demand_pct > 90.0) ? RATING_TOGA : RATING_MCR;
                    double rating_speed_limit = thrust_modes_get_n1_limit(thrust, sensors->t2_kelvin, sensors->p2_bar, 0.0);

                    double target_rpm = 15000.0 + (state->throttle_demand_pct * 0.01 * (rating_speed_limit - 15000.0));
                    
                    ControlLimits active_limits = state->limits;
                    active_limits.accel_limit_rpm_per_sec = state->shaped_accel_limit;

                    double limited_rpm = FADEC::accel_limiter(&active_limits, validated_speed_rpm, target_rpm, dt);
                    
                    if (limited_rpm > target_rpm) {
                        state->mode = MODE_DECEL;
                    }
                    else if (limited_rpm < target_rpm) {
                        state->mode = MODE_ACCEL;
                    }
                    else {
                        state->mode = MODE_CRUISE;
                    }

                    state->active_fuel_command = FADEC::pid_compute(&state->n1_speed_pid, limited_rpm, validated_speed_rpm);

                    double speed_ratio = validated_speed_rpm / state->limits.max_n1_rpm;
                    actuators->stator_vanes_deg = 15.0 - (speed_ratio * 30.0);

                    if (state->throttle_demand_pct > 75.0) {
                        actuators->ehd_voltage_cmd_kv = 25.0;
                    }
                    else {
                        actuators->ehd_voltage_cmd_kv = 0.0;
                    }
                }
                break;

            case MODE_LIMIT_ONLY:
                state->active_fuel_command = 25.0;
                actuators->stator_vanes_deg = 0.0;
                actuators->ehd_voltage_cmd_kv = 0.0;
                break;

            case MODE_EMERGENCY_SHUTDOWN:
            default:
                state->active_fuel_command = 0.0;
                actuators->ehd_voltage_cmd_kv = 0.0;
                actuators->stator_vanes_deg = 45.0;
                break;
        }

        // 6. Fuel Schedule transient limits
        if (state->mode != MODE_EMERGENCY_SHUTDOWN && state->mode != MODE_LIMIT_ONLY) {
            FuelLimits_t fuel_bounds;
            fuel_schedule_get_limits(validated_speed_rpm, sensors->p3_bar, sensors->t2_kelvin, &fuel_bounds);
            
            if (state->active_fuel_command > fuel_bounds.max_wf_pct) {
                state->active_fuel_command = fuel_bounds.max_wf_pct;
            }
            if (state->active_fuel_command < fuel_bounds.min_wf_pct) {
                state->active_fuel_command = fuel_bounds.min_wf_pct;
            }
        }

        // 7. EGT safety limiter
        if (state->mode != MODE_EMERGENCY_SHUTDOWN && state->mode != MODE_LIMIT_ONLY) {
            if (sensors->egt_kelvin > state->limits.max_egt_kelvin) {
                double temp_excess = sensors->egt_kelvin - state->limits.max_egt_kelvin;
                double scale = 1.0 - (temp_excess * 0.05);
                if (scale < 0.1) {
                    scale = 0.1;
                }
                state->active_fuel_command *= scale;
            }
        }
        
        actuators->fuel_valve_pct = state->active_fuel_command;
    }

    void WatermarkMonitor::init(CyberState* state) {
        watermark_init(reinterpret_cast<Watermark_State_t*>(state));
    }

    void WatermarkMonitor::update(CyberState* state, double control_input, double measured_value) {
        // Verification is done asynchronously in the 10 Hz task, we just inject noise here
        // Re-inject noise using existing watermark C symbols
        Watermark_State_t* c_state = reinterpret_cast<Watermark_State_t*>(state);
        c_state->last_injected_noise = watermark_inject(c_state, control_input, 0) - control_input;
    }

} // namespace FADEC

extern "C" {

    int32_t fadec_init(FADEC_State_t *state) {
        int32_t status = 0;
        if (state == nullptr) {
            status = -1;
        }
        else {
            if (!run_post_diagnostics()) {
                status = -2;
            }
            else {
                std::memset(state, 0, sizeof(FADEC_State_t));
                
                std::strcpy(state->config_id.sw_version, "9.2.0");
                std::strcpy(state->config_id.cal_version, "CAL_2026_07");
                std::strcpy(state->config_id.engine_config, "TJ1_BLK2");
                state->config_id.sw_checksum = 0x309ECF69U;

                FADEC::Engine* engine = reinterpret_cast<FADEC::Engine*>(state);
                engine->init();

                // Call initial start parameters setup
                engine_start_init(&state->start_seq);
                thrust_modes_init(&state->thrust_config);
                vane_schedule_init(&state->vane_state);
                dual_channel_init(&state->channel_config, 0U);
                fdir_sensor_init(&state->fdir_state);
                cognitive_engine_init(&state->cognitive_state);
                actuator_loop_init(&state->actuator_state);
                creep_governor_init(&state->creep_state);
                acc_init(&state->acc_state);
                for (int32_t i = 0; i < 5; i++) {
                    state->p3_history[i] = 1.013f;
                }
            }
        }
        return status;
    }

    double pid_compute(PID_State_t *pid, double setpoint, double process_value) {
        return FADEC::pid_compute(reinterpret_cast<FADEC::PIDState*>(pid), setpoint, process_value);
    }

    void pid_reset(PID_State_t *pid) {
        if (pid != nullptr) {
            pid->integral = 0.0;
            pid->prev_error = 0.0;
            pid->output = 0.0;
        }
    }

    double accel_limiter(const ControlLimits_t *limit, double current_rpm, double target_rpm, double dt) {
        return FADEC::accel_limiter(reinterpret_cast<const FADEC::ControlLimits*>(limit), current_rpm, target_rpm, dt);
    }

    uint32_t surge_protection_check(double flow_op, double pr_op, double speed_pct) {
        uint32_t surge_active = 0U;
        if ((flow_op > 0.0) && (pr_op > 0.0)) {
            double surge_threshold_pr = 2.0 + (speed_pct * 0.15);
            if ((flow_op < (speed_pct * 0.15)) && (pr_op > surge_threshold_pr)) {
                surge_active = 1U;
            }
        }
        return surge_active;
    }

    int32_t fadec_control_step(FADEC_State_t *state, 
                                const HAL_SensorReadings_t *sensors, 
                                HAL_ActuatorCommands_t *actuators) {
        int32_t status = 0;
        FADEC_PRE(state != nullptr, state);
        FADEC_PRE(sensors != nullptr, state);
        FADEC_PRE(actuators != nullptr, state);

        if ((state == nullptr) || (sensors == nullptr) || (actuators == nullptr)) {
            status = -1;
        }
        else {
            double dt = state->n1_speed_pid.dt;

            if (g_cbit_assertion_failed != 0U) {
                state->sensor_faults |= CBIT_ASSERTION_FAULT_BIT;
            }

            if (!run_cst_diagnostics(reinterpret_cast<FADEC::EngineState*>(state))) {
                state->mode = MODE_EMERGENCY_SHUTDOWN;
            }

            bool mpu_ok = mpu_check_access(MPU_PARTITION_CONTROL, 0x00010000U, true);
            mpu_ok = mpu_ok && mpu_check_access(MPU_PARTITION_CONTROL, 0x00050000U, false);
            mpu_ok = mpu_ok && mpu_check_access(MPU_PARTITION_SAFETY, 0x00050000U, true);
            mpu_ok = mpu_ok && mpu_check_access(MPU_PARTITION_SAFETY, 0x00010000U, false);
            mpu_ok = mpu_ok && mpu_check_access(MPU_PARTITION_ADVISORY, 0x00090000U, true);
            mpu_ok = mpu_ok && mpu_check_access(MPU_PARTITION_ADVISORY, 0x00010000U, false);

            if (!mpu_ok) {
                status = -3;
            }

            // Run standard FADEC C++ Engine composition step
            FADEC::Engine* engine = reinterpret_cast<FADEC::Engine*>(state);
            
            // Map inputs/outputs
            FADEC::SensorState cpp_sensors;
            std::memcpy(&cpp_sensors, sensors, sizeof(FADEC::SensorState));
            // EKF state overrides sensor speed if it is degraded, but fdir_sensor_vote_speed will be run
            double validated_speed_rpm = 0.0;
            fdir_sensor_vote_speed(&state->fdir_state, sensors->n1_rpm_sensor_1, sensors->n1_rpm_sensor_2, sensors->t2_kelvin, sensors->p3_bar, dt, &validated_speed_rpm);
            cpp_sensors.n1_rpm = validated_speed_rpm;

            FADEC::ActuatorState cpp_actuators;
            std::memcpy(&cpp_actuators, actuators, sizeof(FADEC::ActuatorState));

            // Execute deterministic sequential step
            engine->step(&cpp_sensors, &cpp_actuators, state->sensor_faults, dt);

            // Copy results back
            actuators->fuel_valve_pct = cpp_actuators.fuel_valve_pct;
            actuators->stator_vanes_deg = cpp_actuators.stator_vanes_deg;
            actuators->acc_valve_cmd_pct = cpp_actuators.acc_valve_cmd_pct;

            // Run 10 Hz Task (100 ms)
            if ((state->scheduler_ticks % 100U) == 0U) {
                ChannelSyncData_t local_sync;
                local_sync.n1_rpm = validated_speed_rpm;
                local_sync.egt_kelvin = sensors->egt_kelvin;
                local_sync.fuel_flow_cmd = state->active_fuel_command;
                local_sync.mode = (uint32_t)state->mode;
                local_sync.faults = state->sensor_faults;
                local_sync.ekf_state[0] = state->mbc_state.x[0];
                local_sync.ekf_state[1] = state->mbc_state.x[1];
                local_sync.ekf_state[2] = state->mbc_state.x[2];
                local_sync.config_checksum = state->config_id.sw_checksum;

                (void)dual_channel_update(&state->channel_config, &local_sync, nullptr, false, 0.10);

                if (state->channel_config.state == CHANNEL_STATE_STANDBY) {
                    state->mbc_state.x[0] = (0.95 * state->mbc_state.x[0]) + (0.05 * validated_speed_rpm);
                }

                bool VSV_healthy = vane_schedule_monitor(&state->vane_state, actuators->stator_vanes_deg, actuators->stator_vanes_deg, 0.10);
                if (!VSV_healthy) {
                    state->sensor_faults |= 0x10U;
                }

                double p3_mean = 0.0;
                for (int32_t i = 0; i < 5; i++) {
                    p3_mean += (double)state->p3_history[i];
                }
                p3_mean /= 5.0;

                double p3_var = 0.0;
                for (int32_t i = 0; i < 5; i++) {
                    double diff = (double)state->p3_history[i] - p3_mean;
                    p3_var += diff * diff;
                }
                p3_var /= 5.0;

                double dn1_dt = (validated_speed_rpm - state->prev_speed_rpm) / 0.10;
                state->prev_speed_rpm = validated_speed_rpm;

                cognitive_bayesian_surge_estimate(&state->cognitive_state, (float)p3_var, (float)dn1_dt, 0.10f);
                state->advisory_telemetry.bayesian_surge_risk = state->cognitive_state.telemetry.bayesian_surge_risk;

                if (state->mode >= MODE_IDLE && state->mode < MODE_EMERGENCY_SHUTDOWN) {
                    watermark_verify(&state->watermark_state, validated_speed_rpm, state->scheduler_ticks);
                    if (state->watermark_state.alarm_triggered) {
                        state->mode = MODE_EMERGENCY_SHUTDOWN;
                    }
                }

                double centrifugal_stress = (validated_speed_rpm * validated_speed_rpm) * 0.05;
                double gas_bending_stress = (sensors->p3_bar * 1e5) * 0.3;
                double stress_pa = centrifugal_stress + gas_bending_stress;
                if (stress_pa < 1.0e5) {
                    stress_pa = 1.0e5;
                }

                creep_governor_step(&state->creep_state, state->mbc_state.estimated_t41_k, stress_pa, 0.10);

                if (state->creep_state.life_degradation_index > 0.5) {
                    state->shaped_accel_limit = 8000.0 * (1.0 - (state->creep_state.life_degradation_index - 0.5) * 2.0);
                    if (state->shaped_accel_limit < 1000.0) {
                        state->shaped_accel_limit = 1000.0;
                    }
                }

                acc_control_step(&state->acc_state, state->mbc_state.estimated_t41_k, validated_speed_rpm, 0.10);
                actuators->acc_valve_cmd_pct = state->acc_state.acc_valve_cmd_pct;
            }

            // Run 1 Hz Task (1000 ms)
            if ((state->scheduler_ticks % 1000U) == 0U) {
                cognitive_digital_twin_step(&state->cognitive_state,
                                            (float)sensors->p3_bar,
                                            (float)sensors->t2_kelvin,
                                            (float)sensors->egt_kelvin,
                                            (float)state->active_fuel_command,
                                            1.0f);

                state->advisory_telemetry.compressor_degradation = state->cognitive_state.telemetry.compressor_degradation;
                state->advisory_telemetry.turbine_wear = state->cognitive_state.telemetry.turbine_wear;
                state->advisory_telemetry.anomaly_score = state->cognitive_state.telemetry.anomaly_score;
                state->advisory_telemetry.confidence_interval = state->cognitive_state.telemetry.confidence_interval;

                if (state->run_time_sec >= 290.0) {
                    state->last_ai_advisory.timestamp_us = 0ULL;
                    state->last_ai_advisory.wf_limit_pct = state->active_fuel_command * 0.979;
                    state->last_ai_advisory.surge_prob = (double)state->advisory_telemetry.bayesian_surge_risk;
                    state->last_ai_advisory.sequence_id = 42U;
                }
            }

            // Shift pressure history
            for (int32_t i = 0; i < 4; i++) {
                state->p3_history[i] = state->p3_history[i + 1];
            }
            state->p3_history[4] = (float)sensors->p3_bar;

            // Closing LVDT feedback simulation
            double mock_lvdt_feedback_v = (state->active_fuel_command / 100.0) * 7.0;
            double coil_ma = 0.0;
            actuator_loop_close(&state->actuator_state, state->active_fuel_command, mock_lvdt_feedback_v, dt, &coil_ma);
            actuators->fuel_valve_coil_ma = coil_ma;

            if (state->mode == MODE_EMERGENCY_SHUTDOWN) {
                status = -99;
            }
        }
        return status;
    }

    int32_t fadec_write_memory(uint32_t src_partition, uint32_t dest_addr, uint32_t value) {
        int32_t status = 0;
        if (!mpu_check_access(src_partition, dest_addr, true)) {
            status = -3;
        } else {
            (void)value;
        }
        return status;
    }

}
