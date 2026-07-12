/**
 * @file fadec_hal.c
 * @brief FADEC Hardware Abstraction Layer Simulation Implementation
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#define _POSIX_C_SOURCE 199309L
#include "fadec_hal.h"
#include "rtos_tasks.h"
#include <time.h>
#include <math.h>
#include <stdlib.h>

SafetyVetoLatch_t hal_safety_veto = {
    .request_mask = VETO_REASON_NONE,
    .committed_latch = VETO_REASON_NONE
};

/* Simulated physical states of the engine core */
static double sim_n1_rpm = 15000.0;     /* Idle RPM */
static double sim_egt_k = 650.0;        /* Exhaust gas temp */
static double sim_p3_bar = 1.013;       /* Compressor discharge pressure */
static double sim_p2_bar = 1.013;       /* Ambient inlet pressure */
static double sim_t2_k = 288.15;       /* Ambient temperature */
static double sim_vibration_g = 0.8;    /* Engine vibration */
static double sim_fuel_flow = 0.05;     /* Fuel flow kg/s */
static double sim_ehd_voltage = 0.0;    /* EHD voltage */

/* Latest actuator commands */
static HAL_ActuatorCommands_t active_cmds = {
    .fuel_valve_pct = 5.0,
    .ehd_voltage_cmd_kv = 0.0,
    .stator_vanes_deg = 0.0
};

static uint64_t last_update_us = 0ULL;
static int32_t is_initialized = 0;

/* Simulated MMIO Register Bank */
static uint32_t mmio_registers[6] = {0U};

/* Nested ISR Timing & Configuration database */
static ISR_Config_t isr_table[ISR_COUNT] = {
    [ISR_TIMER_1MS] = { .priority = 0U, .timing_budget_us = 15ULL, .execution_count = 0ULL, .max_duration_us = 0ULL },
    [ISR_ADC_READY] = { .priority = 1U, .timing_budget_us = 25ULL, .execution_count = 0ULL, .max_duration_us = 0ULL },
    [ISR_CCDL_RX]   = { .priority = 2U, .timing_budget_us = 20ULL, .execution_count = 0ULL, .max_duration_us = 0ULL }
};

static int32_t isr_active_stack[ISR_COUNT];
static int32_t isr_stack_depth = 0;

static int32_t get_reg_offset(uint32_t reg_addr) {
    int32_t offset = -1;
    switch (reg_addr) {
        case REG_ADC_N1_CH1: offset = 0; break;
        case REG_ADC_N1_CH2: offset = 1; break;
        case REG_ADC_EGT:    offset = 2; break;
        case REG_ADC_P3:     offset = 3; break;
        case REG_DAC_FMV:    offset = 4; break;
        case REG_DAC_IGV:    offset = 5; break;
        default:             offset = -1; break;
    }
    return offset;
}

uint64_t hal_get_timestamp_us(void) {
    struct timespec ts;
    uint64_t us = 0ULL;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) == 0) {
        us = ((uint64_t)ts.tv_sec * 1000000ULL) + ((uint64_t)ts.tv_nsec / 1000ULL);
    }
    return us;
}

int32_t hal_init(void) {
    hal_safety_veto.request_mask = VETO_REASON_NONE;
    hal_safety_veto.committed_latch = VETO_REASON_NONE;
    sim_n1_rpm = 15000.0;
    sim_egt_k = 650.0;
    sim_p3_bar = 1.013;
    sim_p2_bar = 1.013;
    sim_t2_k = 288.15;
    sim_vibration_g = 0.8;
    sim_fuel_flow = 0.05;
    sim_ehd_voltage = 0.0;

    active_cmds.fuel_valve_pct = 5.0;
    active_cmds.ehd_voltage_cmd_kv = 0.0;
    active_cmds.stator_vanes_deg = 0.0;

    for (int32_t i = 0; i < 6; i++) {
        mmio_registers[i] = 0U;
    }

    isr_stack_depth = 0;
    for (int32_t i = 0; i < (int32_t)ISR_COUNT; i++) {
        isr_active_stack[i] = -1;
        isr_table[i].execution_count = 0ULL;
        isr_table[i].max_duration_us = 0ULL;
    }

    last_update_us = hal_get_timestamp_us();
    is_initialized = 1;
    return 0;
}

int32_t hal_read_sensors(HAL_SensorReadings_t *readings) {
    int32_t status = 0;

    if (readings == (void*)0) {
        status = -1;
    }
    else if (is_initialized == 0) {
        status = -2;
    }
    else {
        uint64_t current_time = hal_get_timestamp_us();
        double dt = (double)(current_time - last_update_us) / 1000000.0;
        
        if (dt > 0.1) {
            dt = 0.1;
        }

        last_update_us = current_time;

        /* Simplified engine dynamics simulation */
        double target_rpm = 15000.0 + (active_cmds.fuel_valve_pct * 850.0);
        if (target_rpm > 110000.0) {
            target_rpm = 110000.0;
        }

        sim_n1_rpm += (target_rpm - sim_n1_rpm) * 0.8 * dt;

        double target_egt = 500.0 + (active_cmds.fuel_valve_pct * 12.0) - ((sim_n1_rpm - 15000.0) * 0.002);
        sim_egt_k += (target_egt - sim_egt_k) * 1.5 * dt;

        double speed_ratio = sim_n1_rpm / 100000.0;
        sim_p3_bar = 1.013 + (12.0 * speed_ratio * speed_ratio);

        double target_ff = active_cmds.fuel_valve_pct * 0.02;
        sim_fuel_flow += (target_ff - sim_fuel_flow) * 5.0 * dt;

        sim_ehd_voltage += (active_cmds.ehd_voltage_cmd_kv - sim_ehd_voltage) * 10.0 * dt;

        sim_vibration_g = 0.2 + (2.5 * speed_ratio * speed_ratio);

        double noise = 0.001 * ((double)(current_time % 100ULL) - 50.0);
        
        readings->n1_rpm = sim_n1_rpm + (noise * 50.0);
        readings->egt_kelvin = sim_egt_k + noise;
        readings->p3_bar = sim_p3_bar + (noise * 0.05);
        readings->p2_bar = sim_p2_bar;
        readings->t2_kelvin = sim_t2_k;
        readings->vibration_g = sim_vibration_g + (noise * 0.02);
        readings->fuel_flow_kgs = sim_fuel_flow;
        readings->ehd_voltage_kv = sim_ehd_voltage;
    }

    return status;
}

int32_t hal_write_actuators(const HAL_ActuatorCommands_t *commands) {
    int32_t status = 0;

    if (commands == (void*)0) {
        status = -1;
    }
    else if (is_initialized == 0) {
        status = -2;
    }
    else {
        uint32_t sticky_requests = hal_safety_veto.request_mask & ~VETO_REASON_OVERTEMP;
        if (hal_safety_veto.committed_latch != VETO_REASON_NONE) {
            active_cmds.fuel_valve_pct = 0.0;
            active_cmds.fuel_valve_coil_ma = 0.0;
        } else if (sticky_requests != VETO_REASON_NONE) {
            hal_safety_veto.committed_latch = sticky_requests;
            active_cmds.fuel_valve_pct = 0.0;
            active_cmds.fuel_valve_coil_ma = 0.0;
        } else {
            active_cmds.fuel_valve_pct = commands->fuel_valve_pct;
            active_cmds.fuel_valve_coil_ma = commands->fuel_valve_pct * 2.0;
            active_cmds.stator_vanes_deg = commands->stator_vanes_deg;
        }
    }

    return status;
}

int32_t hal_self_test(void) {
    return 0;
}

/* MMIO register access simulating bus latency and DMA jitter */
int32_t hal_read_register(uint32_t reg_addr, uint32_t *val) {
    int32_t offset = get_reg_offset(reg_addr);
    if (offset < 0 || val == (void*)0) {
        return -1;
    }

    /* Calculate dynamic latency overhead = standard latency + DMA jitter */
    uint64_t jitter = hal_get_timestamp_us() % DMA_JITTER_MAX_US;
    uint64_t transaction_latency_us = ARINC_BUS_LATENCY_US + jitter;

    *val = mmio_registers[offset];

    /* Return latency as positive microsecond value for timing validation */
    return (int32_t)transaction_latency_us;
}

int32_t hal_write_register(uint32_t reg_addr, uint32_t val) {
    int32_t offset = get_reg_offset(reg_addr);
    if (offset < 0) {
        return -1;
    }

    uint64_t jitter = hal_get_timestamp_us() % DMA_JITTER_MAX_US;
    uint64_t transaction_latency_us = ARINC_BUS_LATENCY_US + jitter;

    mmio_registers[offset] = val;

    return (int32_t)transaction_latency_us;
}

/* Simulates nested ISR execution and timing budget enforcement */
int32_t hal_simulate_isr(ISR_ID_e isr_id, uint64_t actual_duration_us) {
    if (isr_id >= ISR_COUNT) {
        return -1;
    }

    /* Nested preemption check: assert priority ordering (lower numeric priority = higher importance) */
    if (isr_stack_depth > 0) {
        ISR_ID_e active_isr = (ISR_ID_e)isr_active_stack[isr_stack_depth - 1];
        if (isr_table[isr_id].priority >= isr_table[active_isr].priority) {
            /* Priority Inversion / nesting order violation! */
            rtos_arinc_report_error(HM_ERROR_ASSERTION_FAIL, PARTITION_FADEC_CORE);
            return -2;
        }
    }

    /* Push current ISR onto execution stack */
    isr_active_stack[isr_stack_depth] = (int32_t)isr_id;
    isr_stack_depth++;

    /* Record performance statistics */
    isr_table[isr_id].execution_count++;
    if (actual_duration_us > isr_table[isr_id].max_duration_us) {
        isr_table[isr_id].max_duration_us = actual_duration_us;
    }

    /* Verify execution duration against timing budget */
    if (actual_duration_us > isr_table[isr_id].timing_budget_us) {
        rtos_arinc_report_error(HM_ERROR_BUDGET_EXCEEDED, PARTITION_FADEC_CORE);
    }

    /* Pop from active stack */
    isr_stack_depth--;
    isr_active_stack[isr_stack_depth] = -1;

    return 0;
}

void hal_get_isr_stats(ISR_ID_e isr_id, uint64_t *executions, uint64_t *max_duration_us) {
    if (isr_id < ISR_COUNT) {
        if (executions != (void*)0) {
            *executions = isr_table[isr_id].execution_count;
        }
        if (max_duration_us != (void*)0) {
            *max_duration_us = isr_table[isr_id].max_duration_us;
        }
    }
}
