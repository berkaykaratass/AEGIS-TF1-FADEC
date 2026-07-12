# Software Requirements Specification (SRS)
## Document No: AEGIS-FADEC-SRS-001 Rev A
## Target Standard: RTCA DO-178C DAL-A
## Classification: UNCLASSIFIED

---

## 1. Core Flight Control Loop Requirements

#### REQ-FADEC-001: Execution Rate
The FADEC Controller core loop shall execute at a deterministic period of $1.0\text{ ms} \pm 5.0\ \mu\text{s}$ (1 MIF).

#### REQ-FADEC-002: Speed Governor Control
The system shall calculate the active fuel valve command ($Wf_{\text{cmd}}$) using a Closed-loop PID Governor based on the error between target N1 RPM (demanded via PLA) and validated N1 sensor RPM.

#### REQ-FADEC-003: Transient Acceleration Fuel Limiter (Wf/P3 Max Limit)
The system shall limit the maximum fuel flow command ($Wf_{\text{max}}$) dynamically based on the current compressor discharge pressure ($P_3$) to prevent engine surge, satisfying:
$$Wf_{\text{max}} = (Wf/P3)_{\text{max\_limit}} \cdot P_3$$
where $(Wf/P3)_{\text{max\_limit}}$ is interpolated from the corrected spool speed $N_{2c} = N_2 / \sqrt{T_2 / 288.15}$.

#### REQ-FADEC-004: Transient Deceleration Fuel Limiter (Wf/P3 Min Limit)
The system shall enforce a minimum fuel flow command ($Wf_{\text{min}}$) dynamically based on $P_3$ to prevent combustor lean blowout (flameout), satisfying:
$$Wf_{\text{min}} = (Wf/P3)_{\text{min\_limit}} \cdot P_3$$
where $(Wf/P3)_{\text{min\_limit}}$ is interpolated from the corrected spool speed $N_{2c} = N_2 / \sqrt{T_2 / 288.15}$.

#### REQ-FADEC-005: Variable Stator Vane (VSV) Scheduling
The system shall command the stator vane angle dynamically as a function of the corrected spool speed $N_{2c}$ to maintain optimum compressor flow angles and maximize surge margins.

---

## 2. Real-Time OS & Partitioning Requirements

#### REQ-RTOS-001: ARINC-653 Temporal Scheduling
The RTOS shall enforce static time-triggered scheduling allocating dedicated slots inside a 10 ms Major Frame (MAF) for control, safety, and advisory partitions.

#### REQ-RTOS-002: Spatial Memory Protection (MPU)
The RTOS virtual memory page protection (Virtual MPU) shall restrict write access to the safety-critical control memory zones (`MEM_ZONE_CONTROL`) exclusively to the FADEC Core partition (`PARTITION_FADEC_CORE`).

#### REQ-RTOS-003: Health Monitor Response Latency
The Health Monitor (HM) response latency from error detection (e.g. MPU violation, timing overrun) to the execution of the containment response (warm restart, lockout) shall not exceed $1\text{ MIF}$ ($1000\ \mu\text{s}$).

---

## 3. Redundancy & Voting Requirements

#### REQ-RED-001: Cross-Channel Data Link (CCDL)
The FADEC Lane A and Lane B controllers shall synchronize internal states (sensor data, computed speed estimations, safety modes) via a dual-redundant CCDL connection every 1 ms.

#### REQ-RED-002: Kalman Innovation Voting
The oylama (voting) logic shall evaluate the health of redundant sensor readings (N1, EGT, P3) by calculating a confidence weight ($W_i$) based on the Extended Kalman Filter (EKF) innovation residuals, filtering out soft-drifting sensors.

#### REQ-RED-003: Bumpless Handover
In the event that the active lane health score drops below the failure threshold, the control authority shall transition to the standby lane within $1\text{ MIF}$ ($1.0\text{ ms}$) without causing discontinuities (bumps) in the active fuel valve actuator command.
