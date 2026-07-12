/**
 * @file surge_predictor.h
 * @brief Embedded GRU Inference & Safe-DRL CBF Governor Header
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#ifndef SURGE_PREDICTOR_H
#define SURGE_PREDICTOR_H

#include <stdint.h>

#define GRU_INPUT_DIM   7
#define GRU_HIDDEN_DIM  16
#define GRU_OUTPUT_DIM  2

typedef struct {
    float h[GRU_HIDDEN_DIM]; /* Hidden state vector */
} SurgePredictor_State_t;

/**
 * @brief Initialize the GRU hidden state variables to zero
 * @param[out] state GRU state struct to reset
 */
void surge_predictor_init(SurgePredictor_State_t *state);

/**
 * @brief Execute a single recurrent step of the 7D GRU network
 * @param[in,out] state GRU state containing hidden state history
 * @param[in] input 7D input vector [flow, pr, n1, n2, slip, sm, dsm]
 * @param[out] output 2D output vector [surge_prob, fuel_adj]
 */
void surge_predictor_step(SurgePredictor_State_t *state, const float input[GRU_INPUT_DIM], float output[GRU_OUTPUT_DIM]);

/**
 * @brief Control Barrier Function (CBF) safety envelope gating
 * @param[in] Wf_cmd Un-gated fuel flow command setpoint
 * @param[in] n1 LP spool speed [RPM]
 * @param[in] n2 HP spool speed [RPM]
 * @param[in] delta_tip Dynamic blade tip clearance [meters]
 * @return Safe gated fuel flow command
 */
float surge_cbf_filter(float Wf_cmd, float n1, float n2, float delta_tip);

#endif /* SURGE_PREDICTOR_H */
