/**
 * @file safety_monitor.cpp
 * @brief Safety Monitor (Formal STT Safety Kernel) Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C++:2008
 */

#include "engine_system.hpp"
#include "safety_monitor.h"
extern "C" {
#include "fadec_assert.h"
}
#include <cstdio>

/* State Transition Table (STT) Matrix */
static constexpr SafetyState_e STT[SAFETY_STATE_MAX][CBIT_EVENT_MAX] = {
    /* Current State: SAFETY_STATE_NORMAL */
    {
        /* CBIT_EVENT_NONE */ SAFETY_STATE_NORMAL,
        /* CBIT_EVENT_SINGLE_SENSOR_FAIL */ SAFETY_STATE_DEGRADED,
        /* CBIT_EVENT_EKF_DIVERGE */ SAFETY_STATE_DEGRADED,
        /* CBIT_EVENT_DUAL_SENSOR_FAIL */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_ASSERTION_FAIL */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_PHYSICAL_BREACH */ SAFETY_STATE_EMERGENCY_SHUTDOWN
    },
    /* Current State: SAFETY_STATE_DEGRADED */
    {
        /* CBIT_EVENT_NONE */ SAFETY_STATE_DEGRADED,
        /* CBIT_EVENT_SINGLE_SENSOR_FAIL */ SAFETY_STATE_DEGRADED,
        /* CBIT_EVENT_EKF_DIVERGE */ SAFETY_STATE_DEGRADED,
        /* CBIT_EVENT_DUAL_SENSOR_FAIL */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_ASSERTION_FAIL */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_PHYSICAL_BREACH */ SAFETY_STATE_EMERGENCY_SHUTDOWN
    },
    /* Current State: SAFETY_STATE_LIMIT_ONLY */
    {
        /* CBIT_EVENT_NONE */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_SINGLE_SENSOR_FAIL */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_EKF_DIVERGE */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_DUAL_SENSOR_FAIL */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_ASSERTION_FAIL */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_PHYSICAL_BREACH */ SAFETY_STATE_EMERGENCY_SHUTDOWN
    },
    /* Current State: SAFETY_STATE_EMERGENCY_SHUTDOWN */
    {
        /* CBIT_EVENT_NONE */ SAFETY_STATE_NORMAL,
        /* CBIT_EVENT_SINGLE_SENSOR_FAIL */ SAFETY_STATE_DEGRADED,
        /* CBIT_EVENT_EKF_DIVERGE */ SAFETY_STATE_DEGRADED,
        /* CBIT_EVENT_DUAL_SENSOR_FAIL */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_ASSERTION_FAIL */ SAFETY_STATE_LIMIT_ONLY,
        /* CBIT_EVENT_PHYSICAL_BREACH */ SAFETY_STATE_EMERGENCY_SHUTDOWN
    }
};

namespace FADEC {

    void SafetyKernel::init(SafetyState* smon) {
        if (smon != nullptr) {
            smon->egt_overshoot_timer = 0.0;
            smon->vibration_overshoot_timer = 0.0;
            smon->trip_active = false;
            smon->current_state = SAFETY_STATE_NORMAL;
            
            hal_safety_veto.request_mask = VETO_REASON_NONE;
            hal_safety_veto.committed_latch = VETO_REASON_NONE;

            /* Completeness check at initialization */
            for (int32_t state = 0; state < static_cast<int32_t>(SAFETY_STATE_MAX); state++) {
                for (int32_t event = 0; event < static_cast<int32_t>(CBIT_EVENT_MAX); event++) {
                    SafetyState_e next = STT[state][event];
                    if ((next < SAFETY_STATE_NORMAL) || (next >= SAFETY_STATE_MAX)) {
                        smon->current_state = SAFETY_STATE_EMERGENCY_SHUTDOWN;
                    }
                }
            }
        }
    }

    static CBITEvent_e priority_encode_cbit(uint32_t cbit_flags, bool physical_breach) {
        CBITEvent_e event = CBIT_EVENT_NONE;

        if (physical_breach) {
            event = CBIT_EVENT_PHYSICAL_BREACH;
        }
        else if ((cbit_flags & 0x80U) != 0U) { /* CBIT_ASSERTION_FAULT_BIT */
            event = CBIT_EVENT_ASSERTION_FAIL;
        }
        else if ((cbit_flags & 0x08U) != 0U) { /* Dual sensor failure flag */
            event = CBIT_EVENT_DUAL_SENSOR_FAIL;
        }
        else if ((cbit_flags & 0x20U) != 0U) { /* EKF diverge flag */
            event = CBIT_EVENT_EKF_DIVERGE;
        }
        else if ((cbit_flags & 0x06U) != 0U) { /* Single sensor failure flags */
            event = CBIT_EVENT_SINGLE_SENSOR_FAIL;
        }
        else {
            event = CBIT_EVENT_NONE;
        }

        return event;
    }

    int32_t SafetyKernel::process_stt(SafetyState* smon,
                                      const SensorState* raw_sensors,
                                      uint32_t cbit_flags,
                                      double requested_wf_pct,
                                      double* safe_wf_pct,
                                      double dt) {
        int32_t verdict = 0; // PASS

        if ((smon != nullptr) && (raw_sensors != nullptr) && (safe_wf_pct != nullptr) && (dt > 0.0)) {
            *safe_wf_pct = requested_wf_pct;

            /* 1. Immediate physical overlimit checks */
            if (raw_sensors->n1_rpm > ABSOLUTE_MAX_N1_RPM) {
                hal_safety_veto.request_mask |= VETO_REASON_OVERSPEED;
            }
            if (raw_sensors->p3_bar > ABSOLUTE_MAX_P3_BAR) {
                hal_safety_veto.request_mask |= VETO_REASON_PRESSURE;
            }

            /* 2. Debounced physical overlimit checks */
            if (raw_sensors->egt_kelvin > ABSOLUTE_MAX_EGT_K) {
                smon->egt_overshoot_timer += dt;
                if (smon->egt_overshoot_timer >= 0.020) {
                    hal_safety_veto.request_mask |= VETO_REASON_OVERTEMP;
                }
            }
            else {
                smon->egt_overshoot_timer = 0.0;
                hal_safety_veto.request_mask &= ~VETO_REASON_OVERTEMP;
            }

            if (raw_sensors->vibration_g > ABSOLUTE_MAX_VIB_G) {
                smon->vibration_overshoot_timer += dt;
                if (smon->vibration_overshoot_timer >= 0.020) {
                    hal_safety_veto.request_mask |= VETO_REASON_VIBRATION;
                }
            }
            else {
                smon->vibration_overshoot_timer = 0.0;
            }

            /* 3. Veto Latching & Sticky Cooldown logic */
            uint32_t sticky_requests = hal_safety_veto.request_mask & ~VETO_REASON_OVERTEMP;
            hal_safety_veto.committed_latch |= sticky_requests;

            if ((hal_safety_veto.request_mask & VETO_REASON_OVERTEMP) != 0U) {
                hal_safety_veto.committed_latch |= VETO_REASON_OVERTEMP;
            }

            if (raw_sensors->egt_kelvin < 950.0) {
                hal_safety_veto.request_mask &= ~VETO_REASON_OVERTEMP;
                hal_safety_veto.committed_latch &= ~VETO_REASON_OVERTEMP;
            }

            bool physical_breach = (hal_safety_veto.committed_latch != VETO_REASON_NONE);

            /* 4. Priority Encoder CBIT resolution */
            CBITEvent_e active_event = priority_encode_cbit(cbit_flags, physical_breach);

            /* 5. Transition safety state */
            SafetyState_e current = static_cast<SafetyState_e>(smon->current_state);
            
            if ((current >= SAFETY_STATE_NORMAL) && (current < SAFETY_STATE_MAX) &&
                (active_event >= CBIT_EVENT_NONE) && (active_event < CBIT_EVENT_MAX)) {
                smon->current_state = STT[current][active_event];
            } else {
                smon->current_state = SAFETY_STATE_EMERGENCY_SHUTDOWN;
            }

            /* 6. Map resulting SafetyState */
            switch (smon->current_state) {
                case SAFETY_STATE_EMERGENCY_SHUTDOWN:
                    smon->trip_active = true;
                    verdict = 2; // VERDICT_EMERGENCY_SHUTDOWN
                    *safe_wf_pct = 0.0;
                    break;

                case SAFETY_STATE_LIMIT_ONLY:
                    smon->trip_active = false;
                    verdict = 1; // VERDICT_INHIBIT_WF
                    if (*safe_wf_pct > 25.0) {
                        *safe_wf_pct = 25.0;
                    }
                    if (*safe_wf_pct < 2.0) {
                        *safe_wf_pct = 2.0;
                    }
                    break;

                case SAFETY_STATE_DEGRADED:
                case SAFETY_STATE_NORMAL:
                default:
                    smon->trip_active = false;
                    verdict = 0; // VERDICT_PASS
                    break;
            }
        }

        return verdict;
    }

} // namespace FADEC

/* extern "C" Wrappers for absolute link-time compatibility */
extern "C" {

    void safety_monitor_init(SafetyMonitorState_t *smon) {
        FADEC::SafetyKernel kernel;
        kernel.init(reinterpret_cast<FADEC::SafetyState*>(smon));
    }

    SafetyVerdict_e safety_monitor_process_stt(SafetyMonitorState_t *smon,
                                               const HAL_SensorReadings_t *raw_sensors,
                                               uint32_t cbit_flags,
                                               double requested_wf_pct,
                                               double *safe_wf_pct,
                                               double dt) {
        FADEC::SafetyKernel kernel;
        int32_t res = kernel.process_stt(reinterpret_cast<FADEC::SafetyState*>(smon),
                                         reinterpret_cast<const FADEC::SensorState*>(raw_sensors),
                                         cbit_flags,
                                         requested_wf_pct,
                                         safe_wf_pct,
                                         dt);
        return static_cast<SafetyVerdict_e>(res);
    }

}
