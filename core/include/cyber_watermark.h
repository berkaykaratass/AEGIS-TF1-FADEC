/**
 * @file cyber_watermark.h
 * @brief Pseudo-random Command Watermarking for Cyber-Physical Security
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#ifndef CYBER_WATERMARK_H
#define CYBER_WATERMARK_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    double last_injected_noise;
    double correlation_sum;
    uint32_t correlation_count;
    bool alarm_triggered;
    double prev_n1;
    double logistic_state;
    double filtered_noise;
} Watermark_State_t;

/**
 * @brief Initialize the watermarking engine.
 */
void watermark_init(Watermark_State_t *state);

/**
 * @brief Injects a pseudo-random low-amplitude watermark noise signature into the fuel flow command.
 * @param[in,out] state Watermarking state structure
 * @param[in] base_wf Baseline fuel flow command (percent)
 * @param[in] tick Real-time scheduler tick counter
 * @return Fuel command containing the active watermark signature
 */
double watermark_inject(Watermark_State_t *state, double base_wf, uint64_t tick);

/**
 * @brief Verifies that the watermark signature is reflected on the rotor speed (N1) feedback.
 * @details Flags a cyber attack alarm if the signature correlation drops below acceptable thresholds.
 * @param[in,out] state Watermarking state structure
 * @param[in] measured_n1_rpm Measured N1 rotor speed (RPM)
 * @param[in] tick Real-time scheduler tick counter
 */
void watermark_verify(Watermark_State_t *state, double measured_n1_rpm, uint64_t tick);

#endif /* CYBER_WATERMARK_H */
