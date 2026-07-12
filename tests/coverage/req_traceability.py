#!/usr/bin/env python3
"""
FADEC Bi-Directional Requirements Traceability Tool
===================================================
DO-178C Compliance Artifact. Checks that:
1. Every system requirement is implemented in code.
2. Every system requirement is verified in a unit/integration test.
"""

import sys
import os
import re

# Central requirements registry
REQUIREMENTS = {
    "REQ-FADEC-001": "Engine startup sequence logic, lightoff, and Crank/Crank cutoff.",
    "REQ-FADEC-002": "Hot-start abort during startup if EGT exceeds limit.",
    "REQ-FADEC-003": "Hung-start abort if engine fails to light off or reach idle in time.",
    "REQ-FADEC-004": "Thrust rating limits and flat rating schedule based on T2 inlet temp.",
    "REQ-FADEC-005": "Flex temperature takeoff thrust derating configuration.",
    "REQ-FADEC-006": "Fuel transient schedule bounds (max/min fuel command vs RPM).",
    "REQ-FADEC-007": "Variable stator guide vanes scheduling based on corrected speed.",
    "REQ-FADEC-008": "VSV actuator jam detection and warning fault flagging.",
    "REQ-FADEC-009": "Dual-channel health score calculations and voting.",
    "REQ-FADEC-010": "Active/standby redundancy sync, heartbeat, and automatic handover.",
    "REQ-FADEC-011": "ARINC 429 serialization, SSM encoding, and odd parity calculation.",
    "REQ-FADEC-012": "ARINC 429 deserialization and BNR decoding checks.",
    "REQ-FADEC-013": "Triple-buffered lock-free atomic IPC buffer exchange.",
    "REQ-FADEC-014": "Safety monitor low-pass filtering, linear projection, and EGT rate check."
}

def analyze_traceability():
    print("=" * 60)
    print("      DO-178C BI-DIRECTIONAL REQUIREMENTS TRACEABILITY")
    print("=" * 60)

    # Search paths
    code_dir = "core/src"
    test_dirs = ["tests/unit", "tests/integration", "tests/safety"]

    implementation_map = {req: [] for req in REQUIREMENTS}
    verification_map = {req: [] for req in REQUIREMENTS}

    # Scan C implementation files
    req_pattern = re.compile(r"REQ-FADEC-\d{3}")
    
    for root, _, files in os.walk(code_dir):
        for file in files:
            if file.endswith(('.c', '.h')):
                path = os.path.join(root, file)
                with open(path, 'r', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        matches = req_pattern.findall(line)
                        for match in matches:
                            if match in REQUIREMENTS:
                                implementation_map[match].append(f"{file}:{line_num}")

    # Scan test files
    for test_dir in test_dirs:
        for root, _, files in os.walk(test_dir):
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    with open(path, 'r', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            matches = req_pattern.findall(line)
                            for match in matches:
                                if match in REQUIREMENTS:
                                    verification_map[match].append(f"{file}:{line_num}")

    # Report results
    unimplemented = []
    unverified = []

    print(f"{'Requirement ID':<16} | {'Status':<10} | {'Implementation (C)':<22} | {'Verification (Test)':<22}")
    print("-" * 80)
    
    for req, desc in REQUIREMENTS.items():
        impls = len(implementation_map[req])
        verifs = len(verification_map[req])
        
        status = "PASSED"
        if impls == 0:
            status = "NO_IMPL"
            unimplemented.append(req)
        elif verifs == 0:
            status = "NO_TEST"
            unverified.append(req)
            
        impl_str = f"{impls} refs" if impls > 0 else "MISSING"
        verif_str = f"{verifs} refs" if verifs > 0 else "MISSING"
        
        print(f"{req:<16} | {status:<10} | {impl_str:<22} | {verif_str:<22}")

    print("\nTraceability Analysis Summary:")
    print(f"  Total Requirements: {len(REQUIREMENTS)}")
    print(f"  Fully Implemented:  {len(REQUIREMENTS) - len(unimplemented)}/{len(REQUIREMENTS)}")
    print(f"  Fully Verified:     {len(REQUIREMENTS) - len(unverified)}/{len(REQUIREMENTS)}")

    if len(unimplemented) > 0 or len(unverified) > 0:
        print("\nTraceability gaps found!")
        return False
    
    print("\nSUCCESS: 100% Requirements Traceability Matrix Completed.")
    return True

if __name__ == "__main__":
    success = analyze_traceability()
    sys.exit(0 if success else 1)
