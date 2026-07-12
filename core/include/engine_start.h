/**
 * @file engine_start.h
 * @brief Engine Startup Sequencing and Abort Logic Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef ENGINE_START_H
#define ENGINE_START_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    START_STATE_OFF = 0,
    START_STATE_CRANKING,
    START_STATE_IGNITION,
    START_STATE_LIGHTOFF,
    START_STATE_ACCELERATING,
    START_STATE_ONLINE,
    START_STATE_ABORTED
} StartState_e;

typedef enum {
    START_ABORT_NONE = 0,
    START_ABORT_HOT_START,   /* EGT exceeds thermal limits during start */
    START_ABORT_HUNG_START,  /* Speed fails to accelerate within time limits */
    START_ABORT_NO_LIGHTOFF  /* EGT fails to rise after fuel/igniters on */
} StartAbortReason_e;

typedef struct {
    StartState_e state;
    StartAbortReason_e abort_reason;
    double time_in_state_sec;
    double total_start_time_sec;
    bool igniter_on;
    bool starter_on;
    double peak_egt_k;
    double egt_history[5]; /* for lightoff trend analysis */
} StartSequence_t;

/**
 * @brief Initialize engine startup sequence parameters
 */
void engine_start_init(StartSequence_t *seq);

/**
 * @brief Process engine startup step (called at 1 kHz)
 * @param[in,out] seq Startup sequence state
 * @param[in] n2_rpm Engine speed
 * @param[in] egt_k Exhaust Gas Temperature
 * @param[in] dt Task delta-time (seconds)
 * @param[out] fuel_cmd_pct Output startup fuel flow command (0.0 to 100.0)
 * @return Current startup state
 */
StartState_e engine_start_step(StartSequence_t *seq,
                               double n2_rpm,
                               double egt_k,
                               double dt,
                               double *fuel_cmd_pct);

#endif /* ENGINE_START_H */
