/**
 * @file model_based_control.h
 * @brief Extended Kalman Filter (EKF) State Estimator & Model-Based Control
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#ifndef MODEL_BASED_CONTROL_H
#define MODEL_BASED_CONTROL_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
#define FADEC_EXPORT __attribute__((visibility("default")))
extern "C" {
#else
#define FADEC_EXPORT
#endif

typedef struct {
    double x[3];            /* State vector: [N1_speed, T41_temp_k, stall_margin] */
    double P[3][3];         /* State covariance matrix */
    double Q[3][3];         /* Process noise covariance matrix */
    double R[2][2];         /* Measurement noise covariance matrix [N1, P3] */
    double estimated_t41_k;
    double estimated_stall_margin;
    bool fallback_active;   /* Latching fallback mode indicator */
    uint32_t consecutive_failures; /* Counter for EKF conditioning/gating failures */
} MBC_State_t;

/**
 * @brief Initialize the EKF estimator states and covariances.
 */
FADEC_EXPORT void mbc_init(MBC_State_t *state);

/**
 * @brief Performs EKF prediction and correction step based on inputs and measurements.
 */
FADEC_EXPORT void mbc_ekf_step(MBC_State_t *state, 
                               double fuel_flow_pct, 
                               double vane_angle_deg, 
                               double measured_n1_rpm, 
                               bool n1_valid,
                               double measured_p3_bar, 
                               bool p3_valid, 
                               double dt);

/**
 * @brief Mathematically verifies covariance matrix positive-definiteness via Sylvester's Criterion
 */
FADEC_EXPORT bool mbc_ekf_is_positive_definite(const double P[3][3]);

#ifdef __cplusplus
}
#endif

#endif /* MODEL_BASED_CONTROL_H */
