/**
 * @file actuator_control.h
 * @brief High-Rate Actuator Closed-Loop Demodulator & Coil Driver
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#ifndef ACTUATOR_CONTROL_H
#define ACTUATOR_CONTROL_H

#include <stdint.h>

typedef struct {
    double prev_error;
    double integral;
    double coil_a_current_ma;
    double coil_b_current_ma;
    double measured_position_pct;
    uint32_t fault_bits;            /* Bit 0: Coil A Fail, Bit 1: Coil B Fail, Bit 2: LVDT Degraded */
} ActuatorLoop_State_t;

/**
 * @brief Initialize actuator feedback and current drive states.
 */
void actuator_loop_init(ActuatorLoop_State_t *state);

/**
 * @brief Closes the loop at 2 kHz using demodulated LVDT and drives differential currents.
 * @param[in,out] state Actuator control state structure
 * @param[in] cmd_pct Target position percentage (0.0 to 100.0)
 * @param[in] feedback_lvdt Raw LVDT voltage feedback (e.g. 0.0 to 7.0 V)
 * @param[in] dt Time step duration (seconds, e.g. 0.0005 for 2 kHz)
 * @param[out] coil_ma Destination for driven differential coil currents
 */
void actuator_loop_close(ActuatorLoop_State_t *state, 
                         double cmd_pct, 
                         double feedback_lvdt, 
                         double dt, 
                         double *coil_ma);

#endif /* ACTUATOR_CONTROL_H */
