/**
 * @file databus_encryption.c
 * @brief ARINC 825 / CAN Bus Encrypted Message Frame Processing
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 * @version 1.0.0
 * @date 2026-06-19
 * 
 * Copyright (c) 2026 FADEC Systems. All rights reserved.
 * EXPORT CONTROLLED - Distribution limited to authorized personnel.
 */

#include <stdint.h>
#include "../../core/include/cyber_defense.h"

typedef struct {
    uint32_t message_id;      /* CAN/ARINC identifier */
    uint8_t payload[8];       /* 8-byte payload */
    uint8_t length;           /* 0 to 8 bytes */
    uint32_t message_crc;     /* Message integrity code (CRC32) */
} SecureFrame_t;

/**
 * @brief Simple CRC-32 calculator for frame integrity check
 */
static uint32_t calculate_crc32(const uint8_t *data, uint32_t len) {
    uint32_t crc = 0xFFFFFFFFU;
    for (uint32_t i = 0U; i < len; i++) {
        crc ^= (uint32_t)data[i];
        for (uint32_t j = 0U; j < 8U; j++) {
            if ((crc & 1U) != 0U) {
                crc = (crc >> 1U) ^ 0xEDB88320U;
            } else {
                crc >>= 1U;
            }
        }
    }
    return ~crc;
}

/**
 * @brief Encrypt and package a raw frame
 * @param[in] id Message ID
 * @param[in] raw_data Raw input bytes
 * @param[in] length Data length (max 8)
 * @param[out] secure_frame Destination SecureFrame
 * @return 0 on success, negative value on error
 */
int32_t package_secure_frame(uint32_t id, const uint8_t *raw_data, uint8_t length, SecureFrame_t *secure_frame) {
    int32_t status = 0;

    if ((raw_data == (void*)0) || (secure_frame == (void*)0) || (length > 8U)) {
        status = -1;
    }
    else {
        secure_frame->message_id = id;
        secure_frame->length = length;

        /* Encrypt payload using the FADEC cyber module */
        status = cyber_encrypt_msg(raw_data, (uint32_t)length, secure_frame->payload);

        if (status == 0) {
            /* Compute CRC over encrypted payload and ID for transmission integrity */
            uint8_t crc_buffer[12];
            crc_buffer[0] = (uint8_t)((id >> 24U) & 0xFFU);
            crc_buffer[1] = (uint8_t)((id >> 16U) & 0xFFU);
            crc_buffer[2] = (uint8_t)((id >> 8U) & 0xFFU);
            crc_buffer[3] = (uint8_t)(id & 0xFFU);
            
            for (uint32_t i = 0U; i < (uint32_t)length; i++) {
                crc_buffer[4U + i] = secure_frame->payload[i];
            }

            secure_frame->message_crc = calculate_crc32(crc_buffer, 4U + (uint32_t)length);
        }
    }

    return status;
}

/**
 * @brief Unpack and decrypt a secure frame, validating integrity
 * @param[in] secure_frame Incoming SecureFrame
 * @param[out] decrypted_data Destination buffer for decrypted payload
 * @return 0 on success, negative value on integrity validation or decryption failure
 */
int32_t unpack_secure_frame(const SecureFrame_t *secure_frame, uint8_t *decrypted_data) {
    int32_t status = 0;

    if ((secure_frame == (void*)0) || (decrypted_data == (void*)0) || (secure_frame->length > 8U)) {
        status = -1;
    }
    else {
        /* Recompute and check CRC */
        uint8_t crc_buffer[12];
        uint32_t id = secure_frame->message_id;
        uint32_t len = (uint32_t)secure_frame->length;

        crc_buffer[0] = (uint8_t)((id >> 24U) & 0xFFU);
        crc_buffer[1] = (uint8_t)((id >> 16U) & 0xFFU);
        crc_buffer[2] = (uint8_t)((id >> 8U) & 0xFFU);
        crc_buffer[3] = (uint8_t)(id & 0xFFU);

        for (uint32_t i = 0U; i < len; i++) {
            crc_buffer[4U + i] = secure_frame->payload[i];
        }

        uint32_t computed_crc = calculate_crc32(crc_buffer, 4U + len);

        if (computed_crc != secure_frame->message_crc) {
            status = -2; /* CRC validation error (possible tampering/spoofing) */
        }
        else {
            /* Decrypt payload */
            status = cyber_decrypt_msg(secure_frame->payload, len, decrypted_data);
        }
    }

    return status;
}
