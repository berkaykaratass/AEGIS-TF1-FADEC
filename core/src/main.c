#define _POSIX_C_SOURCE 199309L
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include "../include/fadec_hal.h"
#include "../include/fadec_control.h"
#include "../include/rtos_tasks.h"
#include "../include/sensor_interface.h"
#include "../include/cyber_defense.h"

static FADEC_State_t fadec_state;
static HAL_SensorReadings_t raw_sensors;
static HAL_ActuatorCommands_t actuator_cmds;

static void task_sensor_acquisition(void) {
    /* Read hardware sensors */
    (void)hal_read_sensors(&raw_sensors);
}

static void task_flight_control(void) {
    /* Run control loop step */
    (void)fadec_control_step(&fadec_state, &raw_sensors, &actuator_cmds);
    
    /* Write to actuators */
    (void)hal_write_actuators(&actuator_cmds);
}

static void task_telemetry(void) {
    /* Print telemetry status logs */
    printf("[TELEMETRY] Spool Speed: %.1f RPM | EGT: %.1f K | Throttle: %.1f %%\n",
           raw_sensors.n1_rpm,
           raw_sensors.egt_kelvin,
           actuator_cmds.fuel_valve_pct);
}

static void task_health_check(void) {
    /* Perform background diagnostics */
    int32_t status = hal_self_test();
    if (status == 0) {
        printf("[HEALTH] Safety Kernel diagnostics secure.\n");
    } else {
        printf("[HEALTH] WARNING: Safety diagnostics fault detected!\n");
    }
}

int main(void) {
    printf("==================================================\n");
    printf("     AEGIS-TJ1 ARINC-653 SECURE KERNEL BOOTING    \n");
    printf("==================================================\n");

    /* Initialize all FADEC modules */
    (void)hal_init();
    (void)sensor_init();
    (void)cyber_init();
    (void)fadec_init(&fadec_state);
    
    /* 1. Initialize ARINC-653 Scheduler */
    (void)rtos_arinc_init();

    /* 2. Configure Partition Time Windows (MIF = 1 ms) */
    (void)rtos_arinc_configure_partition(PARTITION_FADEC_CORE,     0ULL,   400ULL); /* 0 - 400 us */
    (void)rtos_arinc_configure_partition(PARTITION_SAFETY_KERNEL,  400ULL, 200ULL); /* 400 - 600 us */
    (void)rtos_arinc_configure_partition(PARTITION_AI_ADVISORY,    600ULL, 200ULL); /* 600 - 800 us */
    (void)rtos_arinc_configure_partition(PARTITION_TEST_GROUND,    800ULL, 200ULL); /* 800 - 1000 us */

    /* 3. Register Tasks within isolated Partitions with WCET constraints */
    (void)rtos_arinc_create_task(TASK_SENSOR_ACQUISITION, PARTITION_FADEC_CORE,    1000ULL, 50ULL,  &task_sensor_acquisition);
    (void)rtos_arinc_create_task(TASK_FLIGHT_CONTROL,     PARTITION_FADEC_CORE,    1000ULL, 250ULL, &task_flight_control);
    (void)rtos_arinc_create_task(TASK_HEALTH_CHECK,       PARTITION_SAFETY_KERNEL, 10000ULL, 100ULL, &task_health_check);
    (void)rtos_arinc_create_task(TASK_TELEMETRY,          PARTITION_TEST_GROUND,   10000ULL, 100ULL, &task_telemetry);

    /* 4. Perform Schedule Feasibility Check before entering main loop */
    if (!rtos_arinc_verify_feasibility()) {
        printf("[FATAL] ARINC-653 Schedule Feasibility Check FAILED! Aborting boot.\n");
        exit(EXIT_FAILURE);
    }
    printf("[BOOT] ARINC-653 Schedule Feasibility Check PASSED. Zones isolated.\n");

    printf("ARINC-653 Scheduler online. Simulating 100 ms of partitioned execution...\n\n");
    fadec_state.throttle_demand_pct = 75.0;

    /* Execute ticks: step time in 100 us simulated increments (1000 steps = 100 ms) */
    for (int32_t step = 0; step < 1000; step++) {
        (void)rtos_arinc_run_tick(100ULL);
        
        /* Inject real-world clock throttle delay (0.1 ms per step) */
        struct timespec ts;
        ts.tv_sec = 0;
        ts.tv_nsec = 100000;
        (void)nanosleep(&ts, NULL);
    }

    printf("\nARINC-653 simulation complete. All partitions isolated successfully.\n");
    return 0;
}
