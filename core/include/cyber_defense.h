/**
 * @file cyber_defense.h
 * @brief Safety-Critical Cyber Security and Defense Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLled - Distribution limited to authorized personnel.
 */

#ifndef CYBER_DEFENSE_H
#define CYBER_DEFENSE_H

#include <stdint.h>

#define KEY_SIZE_BYTES       32
#define MAX_KEYS             4
#define MIRAGE_NODES_COUNT   3

typedef struct {
    uint32_t rotation_counter;
    uint32_t active_key_index;
    uint8_t keys[MAX_KEYS][KEY_SIZE_BYTES];
} CryptoContext_t;

typedef struct {
    double sensor_mismatch_z; /* Z-score of sensor values vs physical twin predictions */
    double timing_jitter_us;  /* Measured execution jitter (microseconds) */
    double protocol_violations;/* Frequency of malformed CAN/ARINC messages */
    double total_threat_level;/* Combined computed threat score */
    double threat_threshold;   /* Threshold above which safety mitigation triggers */
} AnomalyScore_t;

typedef struct {
    uint32_t node_id;
    uint32_t is_active;
    uint32_t requests_trapped;
} MirageNode_t;

/**
 * @brief Initialize cryptographic context and cyber defense parameters
 * @return 0 on success, negative value on failure
 */
int32_t cyber_init(void);

/**
 * @brief Encrypt a message payload using current active AES key (simulated XOR for embedded efficiency)
 * @param[in] plaintext Input byte buffer
 * @param[in] length Buffer length in bytes
 * @param[out] ciphertext Output encrypted buffer
 * @return 0 on success, negative value on failure
 */
int32_t cyber_encrypt_msg(const uint8_t *plaintext, uint32_t length, uint8_t *ciphertext);

/**
 * @brief Decrypt a message payload using current active key
 * @param[in] ciphertext Input encrypted buffer
 * @param[in] length Buffer length in bytes
 * @param[out] plaintext Output decrypted buffer
 * @return 0 on success, negative value on decryption or integrity fail
 */
int32_t cyber_decrypt_msg(const uint8_t *ciphertext, uint32_t length, uint8_t *plaintext);

/**
 * @brief Force rotation of the active encryption keys
 * @return 0 on success, negative value on error
 */
int32_t cyber_rotate_keys(void);

/**
 * @brief Perform real-time threat/anomaly assessment
 * @param[in] score Input raw metrics from network/sensors
 * @return 1 if threat detected (mitigation needed), 0 if secure
 */
uint32_t cyber_check_anomaly(const AnomalyScore_t *score);

/**
 * @brief Activate cyber mirage deception nodes to entrap intruders
 * @return 0 on success, negative value on error
 */
int32_t cyber_activate_mirage(void);

#endif /* CYBER_DEFENSE_H */
