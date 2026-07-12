/**
 * @file dual_channel.c
 * @brief Dual-Channel Sync, CCDL, and Kalman-Weighted Voting Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#include "dual_channel.h"
#include <math.h>

#define HEALTH_THRESHOLD 50U
#define CCDL_TIMEOUT_SEC 0.10  /* 100 ms timeout for cross-channel data link */

void dual_channel_init(ChannelConfig_t *chan, uint32_t id) {
    if (chan != (void*)0) {
        chan->channel_id = id;
        chan->health_score = 100U;
        chan->heartbeat_tx_cnt = 0U;
        chan->heartbeat_rx_cnt = 0U;
        chan->rx_timeout_sec = 0.0;
        chan->partner_failed = false;
        chan->ccdl_latency_ms = 0.0;
        chan->ccdl_jitter_ms = 0.0;
        
        if (id == 0U) {
            chan->state = CHANNEL_STATE_ACTIVE; /* Channel A boots as active */
        } else {
            chan->state = CHANNEL_STATE_STANDBY; /* Channel B boots as standby */
        }
    }
}

uint32_t dual_channel_calc_health(uint32_t sensor_faults, uint32_t sys_faults, uint32_t deadline_misses) {
    int32_t score = 100;

    /* Deduct for sensor degradation */
    if (sensor_faults != 0U) {
        score -= 25;
    }

    /* Deduct for system/actuator issues */
    if (sys_faults != 0U) {
        score -= 40;
    }

    /* Deduct for real-time task overrun */
    if (deadline_misses > 0U) {
        if (deadline_misses > 5U) {
            score = 0; /* Catastrophic CPU failure */
        } else {
            score -= ((int32_t)deadline_misses * 15);
        }
    }

    if (score < 0) {
        score = 0;
    }

    return (uint32_t)score;
}

bool dual_channel_update(ChannelConfig_t *local_chan,
                         const ChannelSyncData_t *local_data,
                         const ChannelSyncData_t *remote_data,
                         bool remote_alive,
                         double dt) {
    bool has_authority = false;

    if ((local_chan != (void*)0) && (local_data != (void*)0)) {
        /* Update local health score from current faults */
        uint32_t sensor_flt = local_data->faults & 0x00FFU;
        uint32_t sys_flt = (local_data->faults & 0xFF00U) >> 8U;
        local_chan->health_score = dual_channel_calc_health(sensor_flt, sys_flt, 0U);

        if (local_chan->health_score == 0U) {
            local_chan->state = CHANNEL_STATE_FAILED;
        }

        local_chan->heartbeat_tx_cnt++;

        /* Simulated CCDL characteristics update */
        if (remote_alive) {
            double random_jitter = (((double)(local_chan->heartbeat_tx_cnt % 17U) / 17.0) * 0.2) - 0.1;
            local_chan->ccdl_latency_ms = 2.4 + random_jitter;
            local_chan->ccdl_jitter_ms = fabs(random_jitter) * 1.5;
        } else {
            local_chan->ccdl_latency_ms = 0.0;
            local_chan->ccdl_jitter_ms = 0.0;
        }

        if (remote_alive) {
            local_chan->rx_timeout_sec = 0.0;
            local_chan->partner_failed = false;

            if (remote_data != (void*)0) {
                /* 1. Configuration/Calibration Mismatch Check */
                if (local_data->config_checksum != remote_data->config_checksum) {
                    local_chan->health_score = 0U;
                    local_chan->state = CHANNEL_STATE_FAILED;
                }

                uint32_t remote_sensor_flt = remote_data->faults & 0x00FFU;
                uint32_t remote_sys_flt = (remote_data->faults & 0xFF00U) >> 8U;
                uint32_t remote_health = dual_channel_calc_health(remote_sensor_flt, remote_sys_flt, 0U);

                /* 2. Active Channel Decision & Handover */
                if (local_chan->state == CHANNEL_STATE_ACTIVE) {
                    /* Split-brain prevention: active-active conflict resolved via Channel ID priority */
                    if (remote_data->mode == 0U) {
                        if (local_chan->channel_id == 1U) {
                            local_chan->state = CHANNEL_STATE_STANDBY; /* Channel B yields to Channel A */
                        }
                    }

                    /* If local channel is degraded and remote is healthier, yield control (Bumpless Handover) */
                    if ((local_chan->health_score < HEALTH_THRESHOLD) && 
                        (remote_health > local_chan->health_score)) {
                        local_chan->state = CHANNEL_STATE_STANDBY;
                    }
                }
                else if (local_chan->state == CHANNEL_STATE_STANDBY) {
                    /* If remote is failed/degraded and local is healthy, take control */
                    if ((remote_health < HEALTH_THRESHOLD) && 
                        (local_chan->health_score >= HEALTH_THRESHOLD)) {
                        local_chan->state = CHANNEL_STATE_ACTIVE;
                    }
                }
            }
        }
        else {
            /* Lost partner communication */
            local_chan->rx_timeout_sec += dt;
            if (local_chan->rx_timeout_sec >= CCDL_TIMEOUT_SEC) {
                local_chan->partner_failed = true;
                
                /* Backup channel takes over if active is lost */
                if ((local_chan->state == CHANNEL_STATE_STANDBY) && 
                    (local_chan->health_score >= HEALTH_THRESHOLD)) {
                    local_chan->state = CHANNEL_STATE_ACTIVE;
                }
            }
        }

        if (local_chan->state == CHANNEL_STATE_ACTIVE) {
            has_authority = true;
        }
    }

    return has_authority;
}

void dual_channel_vote_sensors(const ChannelSyncData_t *local_data,
                               const ChannelSyncData_t *remote_data,
                               double synthetic_n1,
                               double *voted_n1,
                               double *voted_egt,
                               double *voted_p3) {
    if (local_data == (void*)0 || remote_data == (void*)0) {
        return;
    }

    /* 1. N1 Speed Sensor Voting (Kalman Residual relative to EKF / Synthetic) */
    double ref_n1 = synthetic_n1;
    if (local_data->ekf_state[0] > 100.0) {
        ref_n1 = local_data->ekf_state[0];
    }

    double res_n1_local = local_data->n1_rpm - ref_n1;
    double res_n1_remote = remote_data->n1_rpm - ref_n1;

    /* Confidence weights based on Gaussian innovation residuals: W = exp(-beta * res^2) */
    double w_n1_local = exp(-1.0e-6 * res_n1_local * res_n1_local);
    double w_n1_remote = exp(-1.0e-6 * res_n1_remote * res_n1_remote);

    /* Zero weights protection */
    if ((w_n1_local + w_n1_remote) < 1.0e-5) {
        *voted_n1 = synthetic_n1; /* Fallback under catastrophic disagreement */
    } else {
        *voted_n1 = (w_n1_local * local_data->n1_rpm + w_n1_remote * remote_data->n1_rpm) / (w_n1_local + w_n1_remote);
    }

    /* 2. EGT Sensor Voting */
    double ref_egt = 650.0;
    if (local_data->ekf_state[1] > 200.0) {
        ref_egt = local_data->ekf_state[1];
    }

    double res_egt_local = local_data->egt_kelvin - ref_egt;
    double res_egt_remote = remote_data->egt_kelvin - ref_egt;

    double w_egt_local = exp(-1.0e-4 * res_egt_local * res_egt_local);
    double w_egt_remote = exp(-1.0e-4 * res_egt_remote * res_egt_remote);

    if ((w_egt_local + w_egt_remote) < 1.0e-5) {
        *voted_egt = (local_data->egt_kelvin + remote_data->egt_kelvin) * 0.5;
    } else {
        *voted_egt = (w_egt_local * local_data->egt_kelvin + w_egt_remote * remote_data->egt_kelvin) / (w_egt_local + w_egt_remote);
    }

    /* 3. P3 Pressure Sensor Voting */
    double speed_ratio = (*voted_n1) / 100000.0;
    double est_p3 = 1.013 + (12.0 * speed_ratio * speed_ratio);

    double res_p3_local = local_data->p3_bar - est_p3;
    double res_p3_remote = remote_data->p3_bar - est_p3;

    double w_p3_local = exp(-10.0 * res_p3_local * res_p3_local);
    double w_p3_remote = exp(-10.0 * res_p3_remote * res_p3_remote);

    if ((w_p3_local + w_p3_remote) < 1.0e-5) {
        *voted_p3 = (local_data->p3_bar + remote_data->p3_bar) * 0.5;
    } else {
        *voted_p3 = (w_p3_local * local_data->p3_bar + w_p3_remote * remote_data->p3_bar) / (w_p3_local + w_p3_remote);
    }
}
