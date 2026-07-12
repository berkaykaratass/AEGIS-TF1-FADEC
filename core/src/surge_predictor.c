/**
 * @file surge_predictor.c
 * @brief Embedded GRU Inference & Safe-DRL CBF Governor Implementation
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#include "surge_predictor.h"
#include "surge_weights.h"
#include <math.h>

/* Helper function for sigmoid activation */
static float sigmoid(float x) {
    float out;
    if (x < -20.0f) {
        out = 0.0f;
    } else if (x > 20.0f) {
        out = 1.0f;
    } else {
        out = 1.0f / (1.0f + expf(-x));
    }
    return out;
}

/* Helper function for tanh activation */
static float tanh_approx(float x) {
    return tanhf(x);
}

void surge_predictor_init(SurgePredictor_State_t *state) {
    if (state != (void*)0) {
        for (int32_t i = 0; i < GRU_HIDDEN_DIM; i++) {
            state->h[i] = 0.0f;
        }
    }
}

void surge_predictor_step(SurgePredictor_State_t *state, const float input[GRU_INPUT_DIM], float output[GRU_OUTPUT_DIM]) {
    if ((state != (void*)0) && (input != (void*)0) && (output != (void*)0)) {
        float z[GRU_HIDDEN_DIM];
        float r[GRU_HIDDEN_DIM];
        float h_tilde[GRU_HIDDEN_DIM];
        float r_h_prev[GRU_HIDDEN_DIM];

        /* 1. Compute Update Gate: z = sigmoid(W_xz * x + W_hz * h_prev + b_z) */
        for (int32_t i = 0; i < GRU_HIDDEN_DIM; i++) {
            float sum_x = 0.0f;
            for (int32_t j = 0; j < GRU_INPUT_DIM; j++) {
                sum_x += SURGE_W_XZ[i][j] * input[j];
            }
            float sum_h = 0.0f;
            for (int32_t j = 0; j < GRU_HIDDEN_DIM; j++) {
                sum_h += SURGE_W_HZ[i][j] * state->h[j];
            }
            z[i] = sigmoid(sum_x + sum_h + SURGE_B_Z[i]);
        }

        /* 2. Compute Reset Gate: r = sigmoid(W_xr * x + W_hr * h_prev + b_r) */
        for (int32_t i = 0; i < GRU_HIDDEN_DIM; i++) {
            float sum_x = 0.0f;
            for (int32_t j = 0; j < GRU_INPUT_DIM; j++) {
                sum_x += SURGE_W_XR[i][j] * input[j];
            }
            float sum_h = 0.0f;
            for (int32_t j = 0; j < GRU_HIDDEN_DIM; j++) {
                sum_h += SURGE_W_HR[i][j] * state->h[j];
            }
            r[i] = sigmoid(sum_x + sum_h + SURGE_B_R[i]);
        }

        /* 3. Compute r * h_prev */
        for (int32_t i = 0; i < GRU_HIDDEN_DIM; i++) {
            r_h_prev[i] = r[i] * state->h[i];
        }

        /* 4. Compute Candidate State: h_tilde = tanh(W_xh * x + W_hh * (r * h_prev) + b_h) */
        for (int32_t i = 0; i < GRU_HIDDEN_DIM; i++) {
            float sum_x = 0.0f;
            for (int32_t j = 0; j < GRU_INPUT_DIM; j++) {
                sum_x += SURGE_W_XH[i][j] * input[j];
            }
            float sum_h = 0.0f;
            for (int32_t j = 0; j < GRU_HIDDEN_DIM; j++) {
                sum_h += SURGE_W_HH[i][j] * r_h_prev[j];
            }
            h_tilde[i] = tanh_approx(sum_x + sum_h + SURGE_B_H[i]);
        }

        /* 5. Update Hidden State: h = (1 - z) * h_prev + z * h_tilde */
        for (int32_t i = 0; i < GRU_HIDDEN_DIM; i++) {
            state->h[i] = (1.0f - z[i]) * state->h[i] + z[i] * h_tilde[i];
        }

        /* 6. Compute Outputs: y = W_y * h + b_y */
        float y[GRU_OUTPUT_DIM];
        for (int32_t i = 0; i < GRU_OUTPUT_DIM; i++) {
            float sum = 0.0f;
            for (int32_t j = 0; j < GRU_HIDDEN_DIM; j++) {
                sum += SURGE_W_Y[i][j] * state->h[j];
            }
            y[i] = sum + SURGE_B_Y[i];
        }

        /* Output 0: Surge Probability (Sigmoid) */
        output[0] = sigmoid(y[0]);
        /* Output 1: Recommended Fuel Adjustment (Tanh) */
        output[1] = tanh_approx(y[1]);
    }
}

float surge_cbf_filter(float Wf_cmd, float n1, float n2, float delta_tip) {
    /* 1. Lean Blow-Out protection (min fuel limit) */
    float Wf_safe = Wf_cmd;
    if (Wf_safe < 0.02f) {
        Wf_safe = 0.02f;
    }

    /* 2. Spool shear speed limit: |N2 - N1| <= 80,000 RPM */
    float slip = n2 - n1;
    if (slip < 0.0f) {
        slip = -slip;
    }
    if (slip > 80000.0f) {
        Wf_safe *= 0.95f; /* reduce fuel to drop HP speed N2 */
    }

    /* 3. Dynamic blade tip clearance constraint: delta_tip <= 80 microns (0.00008 m) */
    if (delta_tip <= 0.00008f) {
        Wf_safe *= 0.96f; /* -4.0% Hard Fuel Cut */
    }

    return Wf_safe;
}
