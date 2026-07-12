/**
 * @file thrust_modes.c
 * @brief FADEC Thrust Rating and Flat-Rating Configuration Implementation
 * 
 * @compliance DO-178C DAL A: REQ-FADEC-004, REQ-FADEC-005
 * @standard MISRA C:2012
 */

#include "thrust_modes.h"

#define FLAT_RATE_BREAKPOINT_K 303.15  /* ISA + 15C */
#define DERATING_SLOPE         0.012   /* 1.2% N1 reduction per Kelvin */

void thrust_modes_init(ThrustRatingConfig_t *config) {
    if (config != (void*)0) {
        config->rating = RATING_IDLE;
        config->flex_temp_k = 320.0; /* Default flex temperature assumed day */
        config->flex_enabled = false;
        config->max_n1_ref = 100000.0; /* 100% speed reference is 100k RPM */
    }
}

double thrust_modes_get_n1_limit(const ThrustRatingConfig_t *config,
                                 double t2_k,
                                 double p2_bar,
                                 double mach) {
    double base_limit = 100000.0;
    (void)p2_bar; /* Omit for simple altitude scale */
    (void)mach;   /* Omit for basic aerolimit */

    if (config == (void*)0) {
        return base_limit;
    }

    /* 1. Set base N1 limit according to thrust rating */
    switch (config->rating) {
        case RATING_TOGA:
            base_limit = config->max_n1_ref;
            break;
        case RATING_MCL:
            base_limit = config->max_n1_ref * 0.95;
            break;
        case RATING_MCR:
            base_limit = config->max_n1_ref * 0.90;
            break;
        case RATING_IDLE:
        default:
            base_limit = config->max_n1_ref * 0.15; /* 15% speed idle limit */
            break;
    }

    /* 2. Determine temperature parameter to use for flat rating */
    double effective_temp_k = t2_k;
    if (config->rating == RATING_TOGA && config->flex_enabled && config->flex_temp_k > t2_k) {
        effective_temp_k = config->flex_temp_k;
    }

    /* 3. Apply flat rating derating schedule */
    if (effective_temp_k > FLAT_RATE_BREAKPOINT_K) {
        double temp_excess = effective_temp_k - FLAT_RATE_BREAKPOINT_K;
        double derating_factor = 1.0 - (temp_excess * DERATING_SLOPE);
        
        /* Clamp derating factor to prevent excessive thrust reduction */
        if (derating_factor < 0.70) {
            derating_factor = 0.70;
        }
        base_limit *= derating_factor;
    }

    return base_limit;
}
