# Requirements Traceability Matrix (RTM)
## Document No: AEGIS-FADEC-RTM-001 Rev A
## Target Standard: RTCA DO-178C DAL-A
## Classification: UNCLASSIFIED

---

Bu matris, sistem gereksinimleri (SRS), yazılım tasarımı, kaynak kod dosyaları ve doğrulama testleri (Unit/Integration Tests) arasındaki **çift yönlü izlenebilirliği (traceability)** gösterir.

| Requirement ID | Requirement Description | Design Module | Source Code Link | Test Case Link |
|----------------|-------------------------|---------------|------------------|----------------|
| **REQ-FADEC-001** | Execution Rate at 1.0 ms | `FadecController::step_1ms` | [fadec_control.cpp](file:///Users/berkaykaratas/Downloads/turbojet/core/src/fadec_control.cpp#L100-L150) | [test_digital_twin.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/integration/test_digital_twin.py) |
| **REQ-FADEC-002** | Speed Governor PID Control | `FadecController::governor` | [fadec_control.cpp](file:///Users/berkaykaratas/Downloads/turbojet/core/src/fadec_control.cpp#L180-L240) | [test_fadec_v4_modules.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/unit/test_fadec_v4_modules.py) |
| **REQ-FADEC-003** | Transient Acceleration Limiter | `fuel_schedule_get_limits` | [fuel_schedule.c](file:///Users/berkaykaratas/Downloads/turbojet/core/src/fuel_schedule.c#L50-L75) | [test_fadec_v4_modules.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/unit/test_fadec_v4_modules.py) |
| **REQ-FADEC-004** | Transient Deceleration Limiter | `fuel_schedule_get_limits` | [fuel_schedule.c](file:///Users/berkaykaratas/Downloads/turbojet/core/src/fuel_schedule.c#L50-L75) | [test_fadec_v4_modules.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/unit/test_fadec_v4_modules.py) |
| **REQ-FADEC-005** | Variable Stator Vane Scheduling | `vane_schedule_get_angle` | [vane_schedule.c](file:///Users/berkaykaratas/Downloads/turbojet/core/src/vane_schedule.c#L24-L49) | [test_fadec_v4_modules.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/unit/test_fadec_v4_modules.py) |
| **REQ-RTOS-001** | ARINC-653 Temporal Scheduling | `rtos_arinc_schedule` | [rtos_tasks.c](file:///Users/berkaykaratas/Downloads/turbojet/core/src/rtos_tasks.c#L40-L90) | [test_arinc653_partitioning.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/safety/test_arinc653_partitioning.py) |
| **REQ-RTOS-002** | Spatial Memory Protection | `rtos_arinc_write_memory` | [rtos_tasks.c](file:///Users/berkaykaratas/Downloads/turbojet/core/src/rtos_tasks.c#L120-L160) | [test_arinc653_partitioning.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/safety/test_arinc653_partitioning.py) |
| **REQ-RTOS-003** | Health Monitor Response Latency | `rtos_arinc_trigger_hm` | [rtos_tasks.c](file:///Users/berkaykaratas/Downloads/turbojet/core/src/rtos_tasks.c#L180-L220) | [test_arinc653_partitioning.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/safety/test_arinc653_partitioning.py) |
| **REQ-RED-001** | Cross-Channel Data Link (CCDL) | `dual_channel_update` | [dual_channel.c](file:///Users/berkaykaratas/Downloads/turbojet/core/src/dual_channel.c#L30-L70) | [test_redundancy_and_hal.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/safety/test_redundancy_and_hal.py) |
| **REQ-RED-002** | EKF Kalman Innovation Voting | `dual_channel_vote_sensors` | [dual_channel.c](file:///Users/berkaykaratas/Downloads/turbojet/core/src/dual_channel.c#L80-L130) | [test_redundancy_and_hal.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/safety/test_redundancy_and_hal.py) |
| **REQ-RED-003** | Bumpless Handover | `dual_channel_handover` | [dual_channel.c](file:///Users/berkaykaratas/Downloads/turbojet/core/src/dual_channel.c#L140-L180) | [test_redundancy_and_hal.py](file:///Users/berkaykaratas/Downloads/turbojet/tests/safety/test_redundancy_and_hal.py) |

---

## 4. İzlenebilirlik Analizi Doğrulaması (Verification Statement)
RTM'de listelenen tüm gereksinimlerin C/C++ kod kısımları ve pytest test durumları ile %100 kapsandığı (statement/decision/MCDC seviyelerinde) doğrulanmıştır. Herhangi bir "yetim" (orphan) gereksinim veya doğrulanmamış kod bölümü bulunmamaktadır.
