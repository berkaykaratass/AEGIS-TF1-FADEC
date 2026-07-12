/**
 * @file engine_start.c
 * @brief Engine Startup Sequencing and Abort Logic Implementation
 * 
 * @compliance DO-178C DAL A: REQ-FADEC-001, REQ-FADEC-002, REQ-FADEC-003
 * @standard MISRA C:2012
 */

#include "engine_start.h"
#include <string.h>

#define N2_CRANK_THRESHOLD_RPM 2500.0
#define N2_STARTER_CUTOFF_RPM  12000.0
#define N2_IDLE_RPM            15000.0

#define IGNITION_TIMELIMIT_SEC 15.0
#define TOTAL_START_TIMELIMIT_SEC 45.0
#define STARTUP_HOT_START_TEMP_K 980.0

void engine_start_init(StartSequence_t *seq) {
    if (seq != (void*)0) {
        seq->state = START_STATE_OFF;
        seq->abort_reason = START_ABORT_NONE;
        seq->time_in_state_sec = 0.0;
        seq->total_start_time_sec = 0.0;
        seq->igniter_on = false;
        seq->starter_on = false;
        seq->peak_egt_k = 0.0;
        (void)memset(seq->egt_history, 0, sizeof(seq->egt_history));
    }
}

StartState_e engine_start_step(StartSequence_t *seq,
                               double n2_rpm,
                               double egt_k,
                               double dt,
                               double *fuel_cmd_pct) {
    if ((seq == (void*)0) || (fuel_cmd_pct == (void*)0)) {
        return START_STATE_ABORTED;
    }

    /* Accumulate timers */
    seq->time_in_state_sec += dt;
    if (seq->state != START_STATE_OFF && seq->state != START_STATE_ABORTED) {
        seq->total_start_time_sec += dt;
    }

    /* Track peak EGT for reporting/aborts */
    if (egt_k > seq->peak_egt_k) {
        seq->peak_egt_k = egt_k;
    }

    /* Update history buffer (shifting) */
    static uint32_t history_ticks = 0U;
    history_ticks++;
    if (history_ticks % 100U == 0U) { /* Update history every 100ms */
        seq->egt_history[4] = seq->egt_history[3];
        seq->egt_history[3] = seq->egt_history[2];
        seq->egt_history[2] = seq->egt_history[1];
        seq->egt_history[1] = seq->egt_history[0];
        seq->egt_history[0] = egt_k;
    }

    /* Global Safety Aborts */
    if (seq->state != START_STATE_ABORTED && seq->state != START_STATE_OFF && seq->state != START_STATE_ONLINE) {
        /* 1. Hot Start Abort */
        if (egt_k > STARTUP_HOT_START_TEMP_K) {
            seq->state = START_STATE_ABORTED;
            seq->abort_reason = START_ABORT_HOT_START;
        }
        /* 2. Hung Start Abort */
        else if (seq->total_start_time_sec > TOTAL_START_TIMELIMIT_SEC) {
            seq->state = START_STATE_ABORTED;
            seq->abort_reason = START_ABORT_HUNG_START;
        }
        else {
            /* Keep going */
        }
    }

    /* State Machine Execution */
    switch (seq->state) {
        case START_STATE_OFF:
            seq->starter_on = false;
            seq->igniter_on = false;
            *fuel_cmd_pct = 0.0;
            
            /* Transition to Cranking */
            seq->state = START_STATE_CRANKING;
            seq->time_in_state_sec = 0.0;
            seq->total_start_time_sec = 0.0;
            seq->peak_egt_k = egt_k;
            break;

        case START_STATE_CRANKING:
            seq->starter_on = true;
            seq->igniter_on = false;
            *fuel_cmd_pct = 0.0;

            /* Check crank threshold speed to turn on igniter */
            if (n2_rpm >= N2_CRANK_THRESHOLD_RPM) {
                seq->state = START_STATE_IGNITION;
                seq->time_in_state_sec = 0.0;
            }
            break;

        case START_STATE_IGNITION:
            seq->starter_on = true;
            seq->igniter_on = true;
            
            /* Introduce ignition fuel flow (constant fuel floor) */
            *fuel_cmd_pct = 8.5;

            /* Check for lightoff: EGT rise rate or threshold */
            bool lightoff_detected = false;
            if (egt_k > 480.0) {
                lightoff_detected = true;
            }
            /* Trend analysis: EGT rising by > 40K compared to history of 500ms ago */
            if ((seq->egt_history[4] > 100.0) && ((egt_k - seq->egt_history[4]) > 40.0)) {
                lightoff_detected = true;
            }

            if (lightoff_detected) {
                seq->state = START_STATE_LIGHTOFF;
                seq->time_in_state_sec = 0.0;
            }
            /* Abort if no lightoff detected in time */
            else if (seq->time_in_state_sec > IGNITION_TIMELIMIT_SEC) {
                seq->state = START_STATE_ABORTED;
                seq->abort_reason = START_ABORT_NO_LIGHTOFF;
            }
            else {
                /* Waiting for lightoff */
            }
            break;

        case START_STATE_LIGHTOFF:
            seq->starter_on = true;
            seq->igniter_on = true; /* Keep igniters on to stabilize combustion */
            
            /* Start ramping fuel flow slowly to build pressure */
            *fuel_cmd_pct = 8.5 + (seq->time_in_state_sec * 0.5);
            if (*fuel_cmd_pct > 12.0) {
                *fuel_cmd_pct = 12.0;
            }

            if (seq->time_in_state_sec > 2.0) { /* Hold 2 seconds to establish flame */
                seq->state = START_STATE_ACCELERATING;
                seq->time_in_state_sec = 0.0;
            }
            break;

        case START_STATE_ACCELERATING:
            seq->igniter_on = false; /* Turn off igniters */

            /* Fuel acceleration ramp */
            *fuel_cmd_pct = 12.0 + (seq->time_in_state_sec * 1.5);
            if (*fuel_cmd_pct > 20.0) {
                *fuel_cmd_pct = 20.0;
            }

            /* Starter Cutoff Check */
            if (n2_rpm >= N2_STARTER_CUTOFF_RPM) {
                seq->starter_on = false;
            } else {
                seq->starter_on = true;
            }

            /* Reached Idle Speed */
            if (n2_rpm >= N2_IDLE_RPM) {
                seq->state = START_STATE_ONLINE;
                seq->starter_on = false;
                seq->time_in_state_sec = 0.0;
            }
            break;

        case START_STATE_ONLINE:
            seq->starter_on = false;
            seq->igniter_on = false;
            /* Handover fuel control to PID governor */
            break;

        case START_STATE_ABORTED:
        default:
            /* Immediately cut fuel, ignition, and starter */
            seq->starter_on = false;
            seq->igniter_on = false;
            *fuel_cmd_pct = 0.0;
            break;
    }

    return seq->state;
}
