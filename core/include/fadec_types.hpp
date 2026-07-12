/**
 * @file fadec_types.hpp
 * @brief Standard-Layout Sub-States for DAL-A Compliant FADEC
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C++:2008
 */

#ifndef FADEC_TYPES_HPP
#define FADEC_TYPES_HPP

#include <stdint.h>

extern "C" {
#include "fadec_hal.h"
#include "engine_start.h"
#include "thrust_modes.h"
#include "vane_schedule.h"
#include "dual_channel.h"
#include "safety_monitor.h"
#include "fdir_sensor.h"
#include "model_based_control.h"
#include "actuator_control.h"
#include "cyber_watermark.h"
#include "creep_governor.h"
#include "active_clearance.h"
#include "cognitive_engine.h"
#include "fadec_control.h"
}

namespace FADEC {

    using Mode = FADEC_Mode_e;
    using Channel = FADEC_Channel_e;
    using PIDState = PID_State_t;
    using ControlLimits = ControlLimits_t;
    using AI_Advisory = AI_Advisory_t;
    using BumplessTransfer = BumplessTransfer_t;
    using FADEC_ConfigID = FADEC_ConfigID_t;
    using EstimatorState = MBC_State_t;
    using SafetyState = SafetyMonitorState_t;
    using CyberState = Watermark_State_t;

    struct SensorState {
        double n1_rpm;
        double n1_rpm_sensor_1;
        double n1_rpm_sensor_2;
        double egt_kelvin;
        double p3_bar;
        double p2_bar;
        double t2_kelvin;
        double vibration_g;
        double fuel_flow_kgs;
        double ehd_voltage_kv;
    };

    struct ActuatorState {
        double fuel_valve_pct;
        double fuel_valve_coil_ma;
        double stator_vanes_deg;
        double acc_valve_cmd_pct;
        double ehd_voltage_cmd_kv;
    };

    struct EngineState {
        FADEC_Mode_e mode;
        FADEC_Channel_e active_channel;
        PID_State_t n1_speed_pid;
        ControlLimits_t limits;
        double throttle_demand_pct;
        double active_fuel_command;
        uint32_t surge_warning;
        uint32_t sensor_faults;
        double run_time_sec;
        
        StartSequence_t start_seq;
        ThrustRatingConfig_t thrust_config;
        VaneState_t vane_state;
        ChannelConfig_t channel_config;
        SafetyMonitorState_t safety_monitor;
        BumplessTransfer_t bumpless;
        FDIR_SensorState_t fdir_state;
        
        uint32_t ai_lockout_timer_ms;
        AI_Advisory_t last_ai_advisory;
        uint32_t scheduler_ticks;
        double shaped_accel_limit;
        double prev_speed_rpm;
        float p3_history[5];
        AI_Advisory_Telemetry_t advisory_telemetry;
        
        MBC_State_t mbc_state;
        ActuatorLoop_State_t actuator_state;
        Watermark_State_t watermark_state;
        CreepState_t creep_state;
        ACC_State_t acc_state;
        
        CognitiveState_t cognitive_state;
        FADEC_ConfigID_t config_id;
    };

} // namespace FADEC

#endif // FADEC_TYPES_HPP
