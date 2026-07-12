/**
 * @file arinc429.c
 * @brief ARINC 429 Transceiver protocol serialization and verification
 * 
 * @compliance DO-178C DAL A: REQ-FADEC-011, REQ-FADEC-012
 * @standard MISRA C:2012
 */

#include "arinc429.h"

static uint32_t count_bits_set(uint32_t val);

static uint32_t count_bits_set(uint32_t val) {
    uint32_t count = 0U;
    uint32_t temp = val;
    while (temp > 0U) {
        if ((temp & 1U) != 0U) {
            count++;
        }
        temp >>= 1U;
    }
    return count;
}

bool arinc429_verify_parity(uint32_t packed_word) {
    uint32_t ones = count_bits_set(packed_word);
    /* Odd parity: total number of 1 bits must be odd */
    return (ones % 2U) != 0U;
}

uint32_t arinc429_pack(const ARINC429_Word_t *raw_word) {
    uint32_t packed = 0U;

    if (raw_word != (void*)0) {
        packed = ((uint32_t)raw_word->label & 0xFFU) |
                 (((uint32_t)raw_word->sdi & 0x03U) << 8U) |
                 (((uint32_t)raw_word->data & 0x7FFFFU) << 10U) |
                 (((uint32_t)raw_word->ssm & 0x03U) << 29U);

        /* Calculate odd parity on first 31 bits */
        uint32_t ones = count_bits_set(packed);
        if ((ones % 2U) == 0U) {
            packed |= (1U << 31U); /* Set parity bit to make total count odd */
        }
    }

    return packed;
}

void arinc429_unpack(uint32_t packed_word, ARINC429_Word_t *decoded_word) {
    if (decoded_word != (void*)0) {
        decoded_word->label = (uint8_t)(packed_word & 0xFFU);
        decoded_word->sdi   = (uint8_t)((packed_word >> 8U) & 0x03U);
        decoded_word->data  = (packed_word >> 10U) & 0x7FFFFU;
        decoded_word->ssm   = (uint8_t)((packed_word >> 29U) & 0x03U);
        decoded_word->parity = (uint8_t)((packed_word >> 31U) & 0x01U);
    }
}

uint32_t arinc429_encode_bnr(double value, double max_range) {
    uint32_t data = 0U;

    if (max_range > 0.0) {
        double ratio = value / max_range;
        if (ratio > 1.0) {
            ratio = 1.0;
        }
        else if (ratio < -1.0) {
            ratio = -1.0;
        }
        else {
            /* Ratio in bounds */
        }

        /* 19-bit signed BNR (1 sign bit + 18 magnitude bits) */
        if (value >= 0.0) {
            data = (uint32_t)(ratio * 262143.0);
        }
        else {
            /* Convert negative number to 19-bit two's complement */
            int32_t val = (int32_t)(ratio * 262144.0);
            data = (uint32_t)val & 0x7FFFFU;
        }
    }

    return data;
}

double arinc429_decode_bnr(uint32_t raw_data, double max_range, bool is_signed) {
    double value = 0.0;

    if (max_range > 0.0) {
        uint32_t data_field = raw_data & 0x7FFFFU;

        if (is_signed) {
            /* Check if sign bit (bit 18, index 18) is set */
            if ((data_field & (1U << 18U)) != 0U) {
                /* Sign extend 19-bit to 32-bit signed int */
                int32_t val = (int32_t)(data_field | 0xFFF80000U);
                value = ((double)val / 262144.0) * max_range;
            }
            else {
                value = ((double)data_field / 262143.0) * max_range;
            }
        }
        else {
            value = ((double)data_field / 524287.0) * max_range;
        }
    }

    return value;
}
