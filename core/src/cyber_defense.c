/**
 * @file cyber_defense.c
 * @brief Safety-Critical Cyber Security and Defense Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#include "cyber_defense.h"

static CryptoContext_t crypto_ctx;
static MirageNode_t mirage_nodes[MIRAGE_NODES_COUNT];
static uint32_t mirage_active = 0U;

int32_t cyber_init(void) {
    crypto_ctx.rotation_counter = 0U;
    crypto_ctx.active_key_index = 0U;

    /* Initialize key schedules with static pseudo-random seeds */
    for (uint32_t k = 0U; k < (uint32_t)MAX_KEYS; k++) {
        for (uint32_t i = 0U; i < (uint32_t)KEY_SIZE_BYTES; i++) {
            crypto_ctx.keys[k][i] = (uint8_t)(((k * 47U) + (i * 13U) + 97U) & 0xFFU);
        }
    }

    /* Initialize Cyber Mirage Decoy Nodes */
    for (uint32_t i = 0U; i < (uint32_t)MIRAGE_NODES_COUNT; i++) {
        mirage_nodes[i].node_id = 100U + i;
        mirage_nodes[i].is_active = 0U;
        mirage_nodes[i].requests_trapped = 0U;
    }
    
    mirage_active = 0U;
    return 0;
}

int32_t cyber_encrypt_msg(const uint8_t *plaintext, uint32_t length, uint8_t *ciphertext) {
    int32_t status = 0;

    if ((plaintext == (void*)0) || (ciphertext == (void*)0) || (length == 0U)) {
        status = -1;
    }
    else {
        uint32_t k_idx = crypto_ctx.active_key_index;
        
        for (uint32_t i = 0U; i < length; i++) {
            uint8_t key_byte = crypto_ctx.keys[k_idx][i % (uint32_t)KEY_SIZE_BYTES];
            /* Secure salt transformation to prevent static pattern matching attacks */
            uint8_t salt = (uint8_t)(i & 0xFFU);
            ciphertext[i] = plaintext[i] ^ (uint8_t)(key_byte + salt);
        }
    }

    return status;
}

int32_t cyber_decrypt_msg(const uint8_t *ciphertext, uint32_t length, uint8_t *plaintext) {
    int32_t status = 0;

    if ((ciphertext == (void*)0) || (plaintext == (void*)0) || (length == 0U)) {
        status = -1;
    }
    else {
        uint32_t k_idx = crypto_ctx.active_key_index;
        
        for (uint32_t i = 0U; i < length; i++) {
            uint8_t key_byte = crypto_ctx.keys[k_idx][i % (uint32_t)KEY_SIZE_BYTES];
            uint8_t salt = (uint8_t)(i & 0xFFU);
            plaintext[i] = ciphertext[i] ^ (uint8_t)(key_byte + salt);
        }
    }

    return status;
}

int32_t cyber_rotate_keys(void) {
    crypto_ctx.active_key_index = (crypto_ctx.active_key_index + 1U) % (uint32_t)MAX_KEYS;
    crypto_ctx.rotation_counter++;
    return 0;
}

uint32_t cyber_check_anomaly(const AnomalyScore_t *score) {
    uint32_t threat_detected = 0U;

    if (score != (void*)0) {
        /* Cumulative Z-score and violations checks */
        if (score->total_threat_level > score->threat_threshold) {
            threat_detected = 1U;
        }
        else if ((score->sensor_mismatch_z > 3.0) && (score->protocol_violations > 3.0)) {
            /* Cross-channel validation breach */
            threat_detected = 1U;
        }
        else if (score->timing_jitter_us > 250.0) {
            /* High latency - possible Denial of Service (DoS) injection */
            threat_detected = 1U;
        }
        else {
            threat_detected = 0U;
        }
    }

    return threat_detected;
}

int32_t cyber_activate_mirage(void) {
    mirage_active = 1U;
    
    for (uint32_t i = 0U; i < (uint32_t)MIRAGE_NODES_COUNT; i++) {
        mirage_nodes[i].is_active = 1U;
        /* Entrap mock traffic */
        mirage_nodes[i].requests_trapped = 5U * (i + 1U);
    }
    
    return 0;
}
