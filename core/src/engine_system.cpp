/**
 * @file engine_system.cpp
 * @brief Engine composition system and step implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C++:2008
 */

#include "engine_system.hpp"

extern "C" {
#include "fdir_sensor.h"
}

namespace FADEC {

    void Engine::init() {
        state.mode = static_cast<FADEC_Mode_e>(MODE_STARTUP);
        state.active_channel = static_cast<FADEC_Channel_e>(CHANNEL_A);
        state.throttle_demand_pct = 0.0;
        state.active_fuel_command = 0.0;
        state.surge_warning = 0;
        state.sensor_faults = 0;
        state.run_time_sec = 0.0;
        state.ai_lockout_timer_ms = 0;
        state.scheduler_ticks = 0;
        state.shaped_accel_limit = 0.0;
        state.prev_speed_rpm = 0.0;
        
        for (int i = 0; i < 5; ++i) {
            state.p3_history[i] = 1.013f;
        }

        StateEstimator estimator;
        FadecController controller;
        WatermarkMonitor watermark;
        SafetyKernel safety;

        estimator.init(&state.mbc_state);
        controller.init(&state);
        watermark.init(&state.watermark_state);
        safety.init(&state.safety_monitor);
    }

    void Engine::step(const SensorState* sensors, ActuatorState* actuators, uint32_t cbit_flags, double dt) {
        state.run_time_sec += dt;
        state.scheduler_ticks++;

        StateEstimator estimator;
        FadecController controller;
        WatermarkMonitor watermark;
        SafetyKernel safety;

        // 1. FDIR voter logic (preserving symbol bindings)
        FDIR_SensorState_t* fdir = &state.fdir_state;
        double validated_speed_rpm = 0.0;
        bool closed_loop_allowed = fdir_sensor_vote_speed(fdir, 
                                                          sensors->n1_rpm_sensor_1, 
                                                          sensors->n1_rpm_sensor_2, 
                                                          sensors->t2_kelvin,
                                                          sensors->p3_bar,
                                                          dt,
                                                          &validated_speed_rpm);
        
        if (!fdir->s1_valid) {
            state.sensor_faults |= 0x02U;
        }
        if (!fdir->s2_valid) {
            state.sensor_faults |= 0x04U;
        }
        if (fdir->dual_sensor_failure || !closed_loop_allowed) {
            state.sensor_faults |= 0x08U;
        }

        // 2. Run State Estimator (EKF & LUT)
        bool n1_valid = ((state.sensor_faults & 0x08U) == 0);
        bool p3_valid = ((state.sensor_faults & 0x10U) == 0);

        estimator.update(&state.mbc_state,
                          state.active_fuel_command,
                          actuators->stator_vanes_deg,
                          validated_speed_rpm,
                          n1_valid,
                          sensors->p3_bar,
                          p3_valid,
                          dt);

        if (state.mbc_state.fallback_active) {
            cbit_flags |= 0x20U;
        }

        // 3. Run FADEC Control Laws
        controller.update(&state, sensors, actuators, dt);

        // 4. Run Cyber watermark verification
        watermark.update(&state.watermark_state, actuators->fuel_valve_pct, sensors->fuel_flow_kgs);
        if (state.watermark_state.alarm_triggered) {
            cbit_flags |= 0x40U;
        }

        // 5. Run Safety Kernel
        double raw_wf_cmd = actuators->fuel_valve_pct;
        double safe_wf_cmd = raw_wf_cmd;
        
        int32_t sm_verdict = safety.process_stt(&state.safety_monitor,
                                                sensors,
                                                cbit_flags,
                                                raw_wf_cmd,
                                                &safe_wf_cmd,
                                                dt);

        actuators->fuel_valve_pct = safe_wf_cmd;
        state.active_fuel_command = safe_wf_cmd;

        if (sm_verdict == 2) {
            state.mode = static_cast<FADEC_Mode_e>(2); // MODE_EMERGENCY_SHUTDOWN (maps to 5 in FADEC_Mode_e, wait, in FADEC_Mode_e, MODE_EMERGENCY_SHUTDOWN is 5! Wait! In engine_system.cpp we wrote state.mode = MODE_EMERGENCY_SHUTDOWN which handles enums correctly!)
            state.mode = MODE_EMERGENCY_SHUTDOWN;
        } else if (sm_verdict == 1) {
            state.mode = MODE_LIMIT_ONLY;
        }
    }

} // namespace FADEC
