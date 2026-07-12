/**
 * @file fadec_assert.c
 * @brief Continuous Built-In Test (CBIT) Assertion & Contract Framework Implementation
 * 
 * @compliance DO-178C DAL A / MISRA C:2012
 */

#include "fadec_assert.h"
#include <stdio.h>
#include <string.h>

#define MAX_ASSERT_LOGS 16

typedef struct {
    char file[64];
    int32_t line;
    char cond[64];
} FADEC_AssertLog_t;

/* Global CBIT assertion failure flag */
volatile uint32_t g_cbit_assertion_failed = 0U;

/* Circular logging buffer for diagnostic telemetry */
static FADEC_AssertLog_t g_assert_logs[MAX_ASSERT_LOGS];
static int32_t g_assert_log_count = 0;

void FADEC_AssertionFailed(const char *file, int32_t line, const char *cond) {
    /* Write to stderr / flight data recorder log partition */
    (void)fprintf(stderr, "[CBIT CONTRACT FAILURE] Assert failed in file %s at line %d: %s\n", file, line, cond);
    
    /* Safely save to circular diagnostic RAM partition */
    int32_t idx = g_assert_log_count % MAX_ASSERT_LOGS;
    
    /* Bound check and copy file name */
    if (file != (void*)0) {
        (void)strncpy(g_assert_logs[idx].file, file, sizeof(g_assert_logs[idx].file) - 1U);
        g_assert_logs[idx].file[sizeof(g_assert_logs[idx].file) - 1U] = '\0';
    } else {
        (void)strcpy(g_assert_logs[idx].file, "UNKNOWN");
    }
    
    g_assert_logs[idx].line = line;
    
    /* Bound check and copy condition expression */
    if (cond != (void*)0) {
        (void)strncpy(g_assert_logs[idx].cond, cond, sizeof(g_assert_logs[idx].cond) - 1U);
        g_assert_logs[idx].cond[sizeof(g_assert_logs[idx].cond) - 1U] = '\0';
    } else {
        (void)strcpy(g_assert_logs[idx].cond, "UNKNOWN");
    }
    
    g_assert_log_count++;
}
