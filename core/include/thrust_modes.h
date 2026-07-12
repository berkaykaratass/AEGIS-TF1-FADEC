/**
 * @file thrust_modes.h
 * @brief FADEC Thrust Rating and Flat-Rating Configuration Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef THRUST_MODES_H
#define THRUST_MODES_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    RATING_IDLE = 0,
    RATING_MCR,  /* Max Cruise */
    RATING_MCL,  /* Max Climb */
    RATING_TOGA  /* Takeoff / Go-Around */
} ThrustRating_e;

typedef struct {
    ThrustRating_e rating;
    double flex_temp_k;       /* User-input assumed hot day temperature for derated takeoff */
    bool flex_enabled;
    double max_n1_ref;        /* Target design speed limit reference */
} ThrustRatingConfig_t;

/**
 * @brief Initialize thrust rating config
 */
void thrust_modes_init(ThrustRatingConfig_t *config);

/**
 * @brief Calculate the maximum allowable N1 speed limit based on flight conditions and rating
 * @param[in] config Thrust rating configuration
 * @param[in] t2_k Compressor inlet temperature (K)
 * @param[in] p2_bar Inlet pressure (bar)
 * @param[in] mach Flight Mach number
 * @return Calculated target maximum speed (RPM)
 */
double thrust_modes_get_n1_limit(const ThrustRatingConfig_t *config,
                                 double t2_k,
                                 double p2_bar,
                                 double mach);

#endif /* THRUST_MODES_H */
