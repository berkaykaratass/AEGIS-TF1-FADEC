/**
 * @file rtos_tasks.h
 * @brief ARINC-653 Partitioned Real-Time Scheduler Header
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef RTOS_TASKS_H
#define RTOS_TASKS_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
#define FADEC_EXPORT __attribute__((visibility("default")))
extern "C" {
#else
#define FADEC_EXPORT
#endif

#define MINOR_FRAME_US   1000ULL  /* 1 ms MIF */
#define MAJOR_FRAME_US  10000ULL  /* 10 ms MAF (10 MIFs) */

typedef enum {
    PARTITION_FADEC_CORE = 0,    /* DAL-A Control Laws */
    PARTITION_SAFETY_KERNEL,     /* DAL-A Safety Envelope STT */
    PARTITION_AI_ADVISORY,       /* DAL-C Cognitive Engine */
    PARTITION_TEST_GROUND,       /* DAL-D Simulation, Injection, Telemetry */
    PARTITION_COUNT
} PartitionID_e;

typedef enum {
    PARTITION_STATE_NORMAL = 0,
    PARTITION_STATE_RESTARTING,
    PARTITION_STATE_LOCKED_OUT
} PartitionState_e;

typedef enum {
    MEM_ZONE_CONTROL = 0,
    MEM_ZONE_SAFETY,
    MEM_ZONE_ADVISORY,
    MEM_ZONE_TEST_GROUND,
    MEM_ZONE_COUNT
} MemZone_e;

typedef enum {
    HM_ERROR_BUDGET_EXCEEDED = 0,
    HM_ERROR_MPU_VIOLATION,
    HM_ERROR_ASSERTION_FAIL,
    HM_ERROR_COUNT
} HM_Error_e;

typedef enum {
    HM_RECOVERY_IGNORE = 0,
    HM_RECOVERY_PARTITION_RESTART,
    HM_RECOVERY_PARTITION_LOCKOUT,
    HM_RECOVERY_SYSTEM_SHUTDOWN
} HM_RecoveryPolicy_e;

typedef enum {
    TASK_SENSOR_ACQUISITION = 0,
    TASK_FLIGHT_CONTROL,
    TASK_TELEMETRY,
    TASK_HEALTH_CHECK,
    TASK_COUNT
} TaskID_e;

typedef void (*TaskFunc_t)(void);

typedef struct {
    uint64_t offset_us;
    uint64_t duration_us;
} PartitionWindow_t;

typedef struct {
    PartitionID_e id;
    PartitionState_e state;
    PartitionWindow_t window;
    uint64_t accumulated_time_us;
    uint32_t restart_count;
} PartitionConfig_t;

typedef struct {
    TaskID_e task_id;
    PartitionID_e partition_id;
    uint64_t period_us;
    uint64_t next_run_us;
    uint64_t wcet_us;
    TaskFunc_t func;
} TaskConfig_t;

typedef struct {
    uint64_t execution_count;
    uint64_t max_execution_time_us;
    uint64_t deadline_misses;
} TaskStats_t;

typedef struct {
    HM_Error_e last_error;
    uint32_t last_faulty_partition;
    uint32_t alarm_triggered;
    uint64_t recovery_duration_us;
} HM_Status_t;

/* Scheduler & HM API functions */
FADEC_EXPORT int32_t rtos_arinc_init(void);
FADEC_EXPORT int32_t rtos_arinc_configure_partition(PartitionID_e id, uint64_t offset_us, uint64_t duration_us);
FADEC_EXPORT int32_t rtos_arinc_create_task(TaskID_e task_id, PartitionID_e partition_id, uint64_t period_us, uint64_t wcet_us, TaskFunc_t func);
FADEC_EXPORT bool rtos_arinc_verify_feasibility(void);
FADEC_EXPORT int32_t rtos_arinc_run_tick(uint64_t simulated_elapsed_us);
FADEC_EXPORT bool rtos_arinc_mpu_check_access(PartitionID_e src_partition, uint32_t dest_addr, bool write_op);
FADEC_EXPORT int32_t rtos_arinc_write_memory(PartitionID_e src_partition, uint32_t dest_addr, uint32_t value);
FADEC_EXPORT void rtos_arinc_report_error(HM_Error_e error, PartitionID_e partition_id);
FADEC_EXPORT int32_t rtos_arinc_get_partition_state(PartitionID_e id);
FADEC_EXPORT void rtos_arinc_get_hm_status(HM_Status_t* status);
FADEC_EXPORT void rtos_arinc_get_task_stats(TaskID_e task_id, TaskStats_t* stats);

#ifdef __cplusplus
}
#endif

#endif /* RTOS_TASKS_H */
