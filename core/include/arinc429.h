/**
 * @file arinc429.h
 * @brief ARINC 429 Transceiver protocol serialization and verification
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef ARINC429_H
#define ARINC429_H

#include <stdint.h>
#include <stdbool.h>

/* Standard ARINC 429 SSM codes */
#define ARINC_SSM_NO     0U  /* Normal Operation */
#define ARINC_SSM_FT     1U  /* Functional Test */
#define ARINC_SSM_NCD    2U  /* No Computed Data */
#define ARINC_SSM_FW     3U  /* Failure Warning */

typedef struct {
    uint8_t label;    /* Octal label (represented as 0-255 decimal) */
    uint8_t sdi;      /* 2-bit SDI (0-3) */
    uint32_t data;    /* 19-bit data field */
    uint8_t ssm;      /* 2-bit SSM (0-3) */
    uint8_t parity;   /* 1-bit odd parity */
} ARINC429_Word_t;

/**
 * @brief Pack an ARINC 429 structure into a single 32-bit word
 */
uint32_t arinc429_pack(const ARINC429_Word_t *raw_word);

/**
 * @brief Unpack a 32-bit word into an ARINC 429 structure
 */
void arinc429_unpack(uint32_t packed_word, ARINC429_Word_t *decoded_word);

/**
 * @brief Calculate and verify odd parity for a packed word
 * @return True if parity is correct (odd number of set bits), false otherwise
 */
bool arinc429_verify_parity(uint32_t packed_word);

/**
 * @brief Assemble a BNR (binary) value into data bits based on resolution and scale
 * @param[in] value Real engineering value
 * @param[in] max_range Max physical value of parameter
 * @return 19-bit packed integer value
 */
uint32_t arinc429_encode_bnr(double value, double max_range);

/**
 * @brief Extract a BNR (binary) value from data bits
 * @param[in] raw_data 19-bit packed integer
 * @param[in] max_range Max physical value of parameter
 * @param[in] is_signed True if parameter is signed (MSB is sign)
 * @return Decoded engineering value
 */
double arinc429_decode_bnr(uint32_t raw_data, double max_range, bool is_signed);

#endif /* ARINC429_H */
