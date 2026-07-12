/**
 * @file actuator_control.c
 * @brief High-Rate Actuator Closed-Loop Demodulator & Coil Driver
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#include "actuator_control.h"
#include <math.h>
#include <stdbool.h>

void actuator_loop_init(ActuatorLoop_State_t *state) {
    if (state != (void*)0) {
        state->prev_error = 0.0;
        state->integral = 0.0;
        state->coil_a_current_ma = 0.0;
        state->coil_b_current_ma = 0.0;
        state->measured_position_pct = 0.0;
        state->fault_bits = 0U;
    }
}

void actuator_loop_close(ActuatorLoop_State_t *state, 
                         double cmd_pct, 
                         double feedback_lvdt, 
                         double dt, 
                         double *coil_ma) {
    if ((state != (void*)0) && (dt > 0.0) && (coil_ma != (void*)0)) {
        /* --- 1. LVDT Demodulation & Scaling --- */
        double measured_pos = 0.0;
        
        /* Check for out-of-bounds voltage representing open/short circuit */
        if ((feedback_lvdt < -0.5) || (feedback_lvdt > 7.5)) {
            state->fault_bits |= 0x04U; /* Flag LVDT feedback failure */
            /* Revert to last safe position measurement estimate */
            measured_pos = state->measured_position_pct;
        } else {
            /* Map 0.0 - 7.0 V LVDT feedback linearly to 0.0 - 100.0% position */
            measured_pos = (feedback_lvdt / 7.0) * 100.0;
            if (measured_pos < 0.0) {
                measured_pos = 0.0;
            }
            if (measured_pos > 100.0) {
                measured_pos = 100.0;
            }
            state->measured_position_pct = measured_pos;
        }

        /* --- 2. Closed-Loop PI Control --- */
        double error = cmd_pct - measured_pos;
        
        /* High gain accumulation for rapid coil excitation */
        state->integral += error * dt;

        /* Anti-windup clamping on integrator */
        if (state->integral > 10.0) {
            state->integral = 10.0;
        }
        if (state->integral < -10.0) {
            state->integral = -10.0;
        }

        double kp = 0.8;
        double ki = 50.0;
        double drive_current_ma = (kp * error) + (ki * state->integral);

        /* Saturation limit for typical Moog torque motor coils (+/- 40 mA) */
        if (drive_current_ma > 40.0) {
            drive_current_ma = 40.0;
        }
        if (drive_current_ma < -40.0) {
            drive_current_ma = -40.0;
        }

        /* --- 3. Redundant Dual-Coil Current Driver Allocation --- */
        /* Check if Coil A failed */
        bool coil_a_fail = ((state->fault_bits & 0x01U) != 0U);
        /* Check if Coil B failed */
        bool coil_b_fail = ((state->fault_bits & 0x02U) != 0U);

        if (coil_a_fail && coil_b_fail) {
            /* Dual coil failure - absolute loss of control */
            state->coil_a_current_ma = 0.0;
            state->coil_b_current_ma = 0.0;
            *coil_ma = 0.0;
        }
        else if (coil_a_fail) {
            /* Shift full drive authority to healthy Coil B */
            state->coil_a_current_ma = 0.0;
            state->coil_b_current_ma = drive_current_ma;
            *coil_ma = drive_current_ma;
        }
        else if (coil_b_fail) {
            /* Shift full drive authority to healthy Coil A */
            state->coil_a_current_ma = drive_current_ma;
            state->coil_b_current_ma = 0.0;
            *coil_ma = drive_current_ma;
        }
        else {
            /* Share current equally (reduces thermal wear on individual coils) */
            state->coil_a_current_ma = drive_current_ma * 0.5;
            state->coil_b_current_ma = drive_current_ma * 0.5;
            *coil_ma = drive_current_ma;
        }

        state->prev_error = error;
    }
}
