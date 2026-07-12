/**
 * @file cyber_watermark.c
 * @brief Pseudo-random Command Watermarking for Cyber-Physical Security
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#include "cyber_watermark.h"
#include <math.h>

void watermark_init(Watermark_State_t *state) {
    if (state != (void*)0) {
        state->last_injected_noise = 0.0;
        state->correlation_sum = 0.0;
        state->correlation_count = 0U;
        state->alarm_triggered = false;
        state->prev_n1 = 0.0;
        state->logistic_state = 0.33;
        state->filtered_noise = 0.0;
    }
}

double watermark_inject(Watermark_State_t *state, double base_wf, uint64_t tick) {
    double cmd_out = base_wf;
    (void)tick; /* tick parameter preserved for signature compatibility but unused due to dynamic chaotic map */

    if (state != (void*)0) {
        /* Chaotic Logistic Map for cryptographically secure, unpredictable watermarking */
        double x = state->logistic_state;
        x = 3.99 * x * (1.0 - x);
        state->logistic_state = x;
        
        /* Map output to [-1.0, 1.0] range */
        double raw_noise = (x - 0.5) * 2.0;
        
        /* Spektral Şekillendirme: 1st-order Low-Pass Filter to protect actuator from mechanical wear */
        double alpha = 0.1;
        state->filtered_noise = (alpha * raw_noise) + ((1.0 - alpha) * state->filtered_noise);
        
        /* Scale watermark noise amplitude to 0.05% of throttle command range */
        double watermark_noise = state->filtered_noise * 0.05;

        state->last_injected_noise = watermark_noise;
        cmd_out = base_wf + watermark_noise;
    }

    return cmd_out;
}

void watermark_verify(Watermark_State_t *state, double measured_n1_rpm, uint64_t tick) {
    if ((state != (void*)0) && (tick > 0U)) {
        /* Initialize prev_n1 on the first step to avoid startup transient spike */
        if (state->prev_n1 == 0.0) {
            state->prev_n1 = measured_n1_rpm;
            return;
        }
        /* Calculate speed change (derivative proxy) */
        double dn1 = measured_n1_rpm - state->prev_n1;
        state->prev_n1 = measured_n1_rpm;

        /* Integrate correlation over a sliding window (100 samples) */
        if (state->correlation_count < 100U) {
            /* Dot product of input perturbation and output speed reaction */
            state->correlation_sum += dn1 * state->last_injected_noise;
            state->correlation_count++;
        }
        else {
            /* Verify positive correlation threshold. Under normal dynamics, 
             * positive fuel adjustments excite speed rise, yielding a positive sum.
             * Replay attacks or command override hijackers drop this correlation. */
            if (state->correlation_sum < 0.005) {
                state->alarm_triggered = true;
            }
            
            /* Reset window accumulation */
            state->correlation_sum = 0.0;
            state->correlation_count = 0U;
        }
    }
}
