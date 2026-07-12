/**
 * @file cognitive_engine.h
 * @brief Next-Generation Bounded Advisory AI Engine & Digital Twin Interfaces
 * 
 * @compliance DO-178C DAL C / MISRA C:2012
 * @note Strictly observer-only; produces bounded risk and health telemetry.
 */

#ifndef COGNITIVE_ENGINE_H
#define COGNITIVE_ENGINE_H

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief Bounded Advisory AI Telemetry Output structure
 */
typedef struct {
    float compressor_degradation;   /* [0.0, 1.0] scale where 0.0 is nominal, 1.0 is retired */
    float turbine_wear;             /* [0.0, 1.0] wear coefficient */
    float bayesian_surge_risk;      /* [0.0, 1.0] probability of surge */
    float anomaly_score;            /* [0.0, 1.0] deviation indicator */
    float confidence_interval;      /* [0.0, 1.0] measurement certainty range */
} AI_Advisory_Telemetry_t;

/**
 * @brief State structure for the Bayesian Surge Risk Estimator
 */
typedef struct {
    float prior_surge_prob;
    float system_noise_var;
    float observation_noise_var;
} BayesianSurge_State_t;

/**
 * @brief State structure for the Engine Health Digital Twin
 */
typedef struct {
    float est_compressor_eff;       /* Estimated compressor efficiency scale */
    float est_turbine_eff;          /* Estimated turbine efficiency scale */
    float learning_rate;
    float residual_history[5];      /* Rolling residual history for anomaly tracking */
    uint32_t residual_index;
} DigitalTwin_State_t;

/**
 * @brief Combined state structure for the Bounded Advisory AI Subsystem
 */
typedef struct {
    BayesianSurge_State_t surge_estimator;
    DigitalTwin_State_t digital_twin;
    AI_Advisory_Telemetry_t telemetry;
} CognitiveState_t;

/**
 * @brief Initializes the Bounded Advisory AI Engine states.
 */
void cognitive_engine_init(CognitiveState_t *state);

/**
 * @brief Computes online Engine Health Digital Twin diagnostics.
 * @details Evaluates compressor and turbine degradation trends, calculating residuals and anomaly scores.
 */
void cognitive_digital_twin_step(CognitiveState_t *state, 
                                 float p3_bar, 
                                 float t3_kelvin, 
                                 float egt_kelvin, 
                                 float fuel_flow_pct, 
                                 float dt);

/**
 * @brief Computes Bayesian Surge Risk probability.
 * @details Updates prior probabilities using recursive Bayesian estimation based on pressure noise and speed rate.
 */
void cognitive_bayesian_surge_estimate(CognitiveState_t *state, 
                                       float p3_variance, 
                                       float dn1_dt, 
                                       float dt);

#endif /* COGNITIVE_ENGINE_H */
