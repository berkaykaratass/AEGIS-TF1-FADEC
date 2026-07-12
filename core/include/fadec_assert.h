/**
 * @file fadec_assert.h
 * @brief Flight-Safe Continuous Built-In Test (CBIT) Assertion & Contract Framework
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#ifndef FADEC_ASSERT_H
#define FADEC_ASSERT_H

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief Log assertion failure to the CBIT diagnostic logging buffer
 * @param[in] file Source file name where failure occurred
 * @param[in] line Line number where failure occurred
 * @param[in] cond String expression of the failed condition
 */
void FADEC_AssertionFailed(const char *file, int32_t line, const char *cond);

#define CBIT_ASSERTION_FAULT_BIT 0x80U

/* Global CBIT assertion failure flag (extern) */
extern volatile uint32_t g_cbit_assertion_failed;

/**
 * @brief Precondition contract check (CBIT monitoring)
 */
#define FADEC_PRE(cond, dummy) \
    do { \
        if (!(cond)) { \
            FADEC_AssertionFailed(__FILE__, (int32_t)__LINE__, #cond); \
            g_cbit_assertion_failed = 1U; \
        } \
    } while (0)

/**
 * @brief Postcondition contract check (CBIT monitoring)
 */
#define FADEC_POST(cond, dummy) \
    do { \
        if (!(cond)) { \
            FADEC_AssertionFailed(__FILE__, (int32_t)__LINE__, #cond); \
            g_cbit_assertion_failed = 1U; \
        } \
    } while (0)

/**
 * @brief Invariant contract check (CBIT monitoring)
 */
#define FADEC_INV(cond, dummy) \
    do { \
        if (!(cond)) { \
            FADEC_AssertionFailed(__FILE__, (int32_t)__LINE__, #cond); \
            g_cbit_assertion_failed = 1U; \
        } \
    } while (0)

#endif /* FADEC_ASSERT_H */
