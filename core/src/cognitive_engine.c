/**
 * @file cognitive_engine.c
 * @brief Next-Generation Bounded Advisory AI Engine & Digital Twin Implementations
 * 
 * @compliance DO-178C DAL C / MISRA C:2012
 */

#include "cognitive_engine.h"
#include <math.h>

void cognitive_engine_init(CognitiveState_t *state) {
    if (state != (void*)0) {
        /* Initialize output telemetry to nominal bounds */
        state->telemetry.compressor_degradation = 0.0f;
        state->telemetry.turbine_wear = 0.0f;
        state->telemetry.bayesian_surge_risk = 0.01f;
        state->telemetry.anomaly_score = 0.0f;
        state->telemetry.confidence_interval = 1.0f;

        /* Initialize Bayesian surge estimator parameters */
        state->surge_estimator.prior_surge_prob = 0.01f;
        state->surge_estimator.system_noise_var = 0.02f;
        state->surge_estimator.observation_noise_var = 0.05f;

        /* Initialize Engine Health Digital Twin states */
        state->digital_twin.est_compressor_eff = 1.0f;
        state->digital_twin.est_turbine_eff = 1.0f;
        state->digital_twin.learning_rate = 0.002f;
        state->digital_twin.residual_index = 0U;
        for (int32_t i = 0; i < 5; i++) {
            state->digital_twin.residual_history[i] = 0.0f;
        }
    }
}

void cognitive_digital_twin_step(CognitiveState_t *state, 
                                 float p3_bar, 
                                 float t3_kelvin, 
                                 float egt_kelvin, 
                                 float fuel_flow_pct, 
                                 float dt) {
    if ((state != (void*)0) && (dt > 0.0f) && (p3_bar > 0.0f) && (t3_kelvin > 0.0f)) {
        DigitalTwin_State_t *twin = &state->digital_twin;

        /* Physics-informed expected thermodynamic calculations */
        float expected_temp_rise = fuel_flow_pct * 12.5f;
        float predicted_t4 = t3_kelvin + (expected_temp_rise * twin->est_compressor_eff);
        float predicted_egt = predicted_t4 * 0.72f * twin->est_turbine_eff;

        float residual = egt_kelvin - predicted_egt;

        /* Update digital twin parameter estimates via bounded gradient adjustments */
        twin->est_compressor_eff -= twin->learning_rate * residual * (fuel_flow_pct / 100.0f) * dt;
        twin->est_turbine_eff += twin->learning_rate * residual * 0.10f * dt;

        /* Enforce strict parameter bounds to guarantee model stability [0.70, 1.30] */
        if (twin->est_compressor_eff < 0.70f) {
            twin->est_compressor_eff = 0.70f;
        }
        if (twin->est_compressor_eff > 1.30f) {
            twin->est_compressor_eff = 1.30f;
        }
        if (twin->est_turbine_eff < 0.70f) {
            twin->est_turbine_eff = 0.70f;
        }
        if (twin->est_turbine_eff > 1.30f) {
            twin->est_turbine_eff = 1.30f;
        }

        /* Update degradation and wear telemetry indicators (strictly mapped to [0.0, 1.0]) */
        float comp_deg = 1.0f - twin->est_compressor_eff;
        if (comp_deg < 0.0f) {
            comp_deg = 0.0f;
        }
        if (comp_deg > 1.0f) {
            comp_deg = 1.0f;
        }
        state->telemetry.compressor_degradation = comp_deg;

        float turb_wear = 1.0f - twin->est_turbine_eff;
        if (turb_wear < 0.0f) {
            turb_wear = 0.0f;
        }
        if (turb_wear > 1.0f) {
            turb_wear = 1.0f;
        }
        state->telemetry.turbine_wear = turb_wear;

        /* Track rolling residuals for anomaly diagnostics */
        twin->residual_history[twin->residual_index] = fabsf(residual);
        twin->residual_index = (twin->residual_index + 1U) % 5U;

        float avg_residual = 0.0f;
        for (uint32_t i = 0U; i < 5U; i++) {
            avg_residual += twin->residual_history[i];
        }
        avg_residual /= 5.0f;

        /* Bounded Anomaly Score [0.0, 1.0]: 1.0 indicates a massive EGT drift of >= 150K */
        float anomaly = avg_residual / 150.0f;
        if (anomaly < 0.0f) {
            anomaly = 0.0f;
        }
        if (anomaly > 1.0f) {
            anomaly = 1.0f;
        }
        state->telemetry.anomaly_score = anomaly;

        /* Confidence interval drops as anomaly deviations increase */
        float confidence = 1.0f - (anomaly * 0.5f);
        if (confidence < 0.5f) {
            confidence = 0.5f;
        }
        if (confidence > 1.0f) {
            confidence = 1.0f;
        }
        state->telemetry.confidence_interval = confidence;
    }
}

void cognitive_bayesian_surge_estimate(CognitiveState_t *state, 
                                       float p3_variance, 
                                       float dn1_dt, 
                                       float dt) {
    if ((state != (void*)0) && (dt > 0.0f)) {
        BayesianSurge_State_t *estimator = &state->surge_estimator;

        /* Compute Likelihood of surge occurrence based on sensor observations */
        float likelihood_surge = 0.05f;

        /* Pressure variance sensitivity */
        if (p3_variance > 0.02f) {
            likelihood_surge += 0.45f * (p3_variance / 0.10f);
        }

        /* Rapid shaft deceleration sensitivity */
        if (dn1_dt < -3000.0f) {
            likelihood_surge += 0.35f * (fabsf(dn1_dt) / 10000.0f);
        }

        /* Bounded likelihood mapping range [0.01, 0.99] */
        if (likelihood_surge < 0.01f) {
            likelihood_surge = 0.01f;
        }
        if (likelihood_surge > 0.99f) {
            likelihood_surge = 0.99f;
        }

        /* Recursive Bayesian Update: Posterior P(Surge | Data) = (L * Prior) / (L * Prior + (1-L) * (1-Prior)) */
        float prior = estimator->prior_surge_prob;
        float numerator = likelihood_surge * prior;
        float denominator = (likelihood_surge * prior) + ((1.0f - likelihood_surge) * (1.0f - prior));

        float posterior = 0.01f;
        if (denominator > 1e-6f) {
            posterior = numerator / denominator;
        }

        /* Bound and update state */
        if (posterior < 0.01f) {
            posterior = 0.01f;
        }
        if (posterior > 0.99f) {
            posterior = 0.99f;
        }

        estimator->prior_surge_prob = posterior;
        state->telemetry.bayesian_surge_risk = posterior;
    }
}
