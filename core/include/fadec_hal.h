/**
 * @file fadec_hal.h
 * @brief FADEC Hardware Abstraction Layer Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef FADEC_HAL_H
#define FADEC_HAL_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
#define HAL_EXPORT __attribute__((visibility("default")))
extern "C" {
#else
#define HAL_EXPORT
#endif

/* Memory-Mapped I/O (MMIO) Registers */
#define REG_ADC_N1_CH1     0x40001000U  /* Speed Sensor 1 ADC Register */
#define REG_ADC_N1_CH2     0x40001004U  /* Speed Sensor 2 ADC Register */
#define REG_ADC_EGT        0x40001008U  /* Exhaust Gas Temperature ADC Register */
#define REG_ADC_P3         0x4000100CU  /* Burner Pressure P3 ADC Register */
#define REG_DAC_FMV        0x40002000U  /* Fuel Metering Valve DAC Command Register */
#define REG_DAC_IGV        0x40002004U  /* Inlet Guide Vanes DAC Command Register */

/* ARINC Bus Physical Characteristics */
#define ARINC_BUS_LATENCY_US  80ULL    /* ARINC-429 standard transmission delay */
#define DMA_JITTER_MAX_US     5ULL     /* Random DMA latency variation bounds */

/* Interrupt Service Routine (ISR) IDs */
typedef enum {
    ISR_TIMER_1MS = 0,                 /* Priority 0 (Highest) */
    ISR_ADC_READY,                     /* Priority 1 */
    ISR_CCDL_RX,                       /* Priority 2 */
    ISR_COUNT
} ISR_ID_e;

typedef struct {
    uint32_t priority;                 /* ISR Priority (0 = highest) */
    uint64_t timing_budget_us;         /* WCET timing budget threshold */
    uint64_t execution_count;          /* Performance monitor counters */
    uint64_t max_duration_us;          /* Measured maximum duration */
} ISR_Config_t;

typedef uint32_t SafetyVetoReason_t;
#define VETO_REASON_NONE         0x00000000U
#define VETO_REASON_OVERSPEED    0x00000001U
#define VETO_REASON_OVERTEMP     0x00000002U
#define VETO_REASON_PRESSURE     0x00000004U
#define VETO_REASON_VIBRATION    0x00000008U
#define VETO_REASON_COMM_FAULT   0x00000010U

typedef struct {
    volatile uint32_t request_mask;
    volatile uint32_t committed_latch;
} SafetyVetoLatch_t;

extern SafetyVetoLatch_t hal_safety_veto;

typedef struct {
    double n1_rpm;           /* Physical speed N1 (RPM) */
    double n1_rpm_sensor_1;  /* Redundant Speed Sensor Channel 1 (RPM) */
    double n1_rpm_sensor_2;  /* Redundant Speed Sensor Channel 2 (RPM) */
    double egt_kelvin;       /* Exhaust Gas Temperature (K) */
    double p3_bar;           /* Combustor pressure (bar) */
    double p2_bar;           /* Compressor inlet pressure (bar) */
    double t2_kelvin;       /* Compressor inlet temperature (K) */
    double vibration_g;      /* Core vibration amplitude (g) */
    double fuel_flow_kgs;    /* Actual measured fuel flow (kg/s) */
    double ehd_voltage_kv;   /* Actual measured EHD grid voltage (kV) */
} HAL_SensorReadings_t;

typedef struct {
    double fuel_valve_pct;      /* Fuel metering valve position command (0.0 to 100.0%) */
    double ehd_voltage_cmd_kv;  /* EHD grid voltage command (kV) */
    double stator_vanes_deg;    /* Variable stator vane angle command (degrees) */
    double fuel_valve_coil_ma;  /* Torque motor coil drive current (mA) */
    double acc_valve_cmd_pct;   /* Active Clearance Control cooling valve command (0-100%) */
} HAL_ActuatorCommands_t;

/* Standard HAL interfaces */
HAL_EXPORT int32_t hal_init(void);
HAL_EXPORT int32_t hal_read_sensors(HAL_SensorReadings_t *readings);
HAL_EXPORT int32_t hal_write_actuators(const HAL_ActuatorCommands_t *commands);
HAL_EXPORT int32_t hal_self_test(void);
HAL_EXPORT uint64_t hal_get_timestamp_us(void);

/* MMIO, Bus Latency, and ISR Timing interfaces */
HAL_EXPORT int32_t hal_read_register(uint32_t reg_addr, uint32_t *val);
HAL_EXPORT int32_t hal_write_register(uint32_t reg_addr, uint32_t val);
HAL_EXPORT int32_t hal_simulate_isr(ISR_ID_e isr_id, uint64_t actual_duration_us);
HAL_EXPORT void hal_get_isr_stats(ISR_ID_e isr_id, uint64_t *executions, uint64_t *max_duration_us);

#ifdef __cplusplus
}
#endif

#endif /* FADEC_HAL_H */
