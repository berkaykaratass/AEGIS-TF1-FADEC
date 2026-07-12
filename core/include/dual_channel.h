/**
 * @file dual_channel.h
 * @brief Dual-Channel Sync, CCDL, and Kalman-Weighted Voting Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef DUAL_CHANNEL_H
#define DUAL_CHANNEL_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
#define DUAL_EXPORT __attribute__((visibility("default")))
extern "C" {
#else
#define DUAL_EXPORT
#endif

typedef enum {
    CHANNEL_STATE_ACTIVE = 0,
    CHANNEL_STATE_STANDBY,
    CHANNEL_STATE_FAILED
} ChannelState_e;

typedef struct {
    uint32_t channel_id;          /* 0 = A, 1 = B */
    ChannelState_e state;
    uint32_t health_score;        /* 0 to 100 scale */
    uint32_t heartbeat_tx_cnt;
    uint32_t heartbeat_rx_cnt;
    double rx_timeout_sec;
    bool partner_failed;
    double ccdl_latency_ms;       /* Simulated CCDL latency */
    double ccdl_jitter_ms;        /* Simulated CCDL jitter */
} ChannelConfig_t;

typedef struct {
    double n1_rpm;
    double egt_kelvin;
    double p3_bar;
    double fuel_flow_cmd;
    uint32_t mode;
    uint32_t faults;
    double ekf_state[3];          /* Estimated states [N1, T41, StallMargin] */
    uint32_t config_checksum;
} ChannelSyncData_t;

DUAL_EXPORT void dual_channel_init(ChannelConfig_t *chan, uint32_t id);

DUAL_EXPORT uint32_t dual_channel_calc_health(uint32_t sensor_faults, uint32_t sys_faults, uint32_t deadline_misses);

DUAL_EXPORT bool dual_channel_update(ChannelConfig_t *local_chan,
                         const ChannelSyncData_t *local_data,
                         const ChannelSyncData_t *remote_data,
                         bool remote_alive,
                         double dt);

/**
 * @brief Performs Confidence-Weighted voting for redundant sensors using EKF Kalman residuals
 * 
 * @param[in] local_data Local channel sync package (Channel A)
 * @param[in] remote_data Remote channel sync package (Channel B)
 * @param[in] synthetic_n1 Brayton model-derived backup speed
 * @param[out] voted_n1 Voted N1 speed output
 * @param[out] voted_egt Voted EGT temperature output
 * @param[out] voted_p3 Voted P3 pressure output
 */
DUAL_EXPORT void dual_channel_vote_sensors(const ChannelSyncData_t *local_data,
                               const ChannelSyncData_t *remote_data,
                               double synthetic_n1,
                               double *voted_n1,
                               double *voted_egt,
                               double *voted_p3);

#ifdef __cplusplus
}
#endif

#endif /* DUAL_CHANNEL_H */
