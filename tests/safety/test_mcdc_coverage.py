#!/usr/bin/env python3
"""
FADEC Modified Condition/Decision Coverage (MC/DC) Verification
==================================================================

Provides safety-critical software logic verification under DO-178C Level A.
Tests safety guard decisions by executing independent condition/decision pairs
to achieve 100% MC/DC path coverage.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import pytest

# ═══════════════════════════════════════════════════════════════════════════════
# FADEC Safety Guard Decision Functions
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_surge_bleed_valve(surge_prob_high, rate_of_decel_high, inlet_temp_low):
    """
    Decision D1: Trigger Surge Bleed Valve (SBV) Open
    Formula: D1 = A or (B and C)
      A: Surge Probability > 0.85
      B: Rotor Deceleration Rate > 500 RPM/s
      C: Compressor Inlet Temperature < 250 K
    """
    return surge_prob_high or (rate_of_decel_high and inlet_temp_low)


def evaluate_overtemp_shutdown(temp_t4_high, speed_n2_high, fuel_flow_high):
    """
    Decision D2: Trigger Turbine Overtemperature Emergency Shutdown
    Formula: D2 = X and (Y or Z)
      X: Turbine Inlet Temperature T4 > 1650 K
      Y: HP Spool Speed N2 > 36000 RPM
      Z: Fuel Flow Rate > 1.2 kg/s
    """
    return temp_t4_high and (speed_n2_high or fuel_flow_high)


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests and MC/DC Independence Pair Verification
# ═══════════════════════════════════════════════════════════════════════════════

def test_mcdc_surge_bleed_valve():
    """
    Verifies 100% MC/DC coverage for the Surge Bleed Valve decision.
    Decision: D1 = A or (B and C)
    Required test cases:
      T1: (True, False, True)  -> True
      T2: (False, False, True) -> False
      T3: (False, True, True)  -> True
      T4: (False, True, False) -> False
    """
    # Define test suite inputs and expected outputs
    test_cases = {
        'T1': (True, False, True),
        'T2': (False, False, True),
        'T3': (False, True, True),
        'T4': (False, True, False)
    }
    
    # Evaluate outcomes
    results = {name: evaluate_surge_bleed_valve(*vals) for name, vals in test_cases.items()}
    
    # Assert correctness of outcomes
    assert results['T1'] is True
    assert results['T2'] is False
    assert results['T3'] is True
    assert results['T4'] is False

    # Verify Independence Pairs:
    # 1. Condition A (Surge Probability):
    #    Comparing T1 and T2: B and C are held constant (False, True).
    #    A changes True -> False. Outcome changes True -> False.
    assert test_cases['T1'][1] == test_cases['T2'][1] # B constant
    assert test_cases['T1'][2] == test_cases['T2'][2] # C constant
    assert test_cases['T1'][0] != test_cases['T2'][0] # A changes
    assert results['T1'] != results['T2']             # Outcome changes
    
    # 2. Condition B (Rotor Deceleration):
    #    Comparing T3 and T2: A and C are held constant (False, True).
    #    B changes True -> False. Outcome changes True -> False.
    assert test_cases['T3'][0] == test_cases['T2'][0] # A constant
    assert test_cases['T3'][2] == test_cases['T2'][2] # C constant
    assert test_cases['T3'][1] != test_cases['T2'][1] # B changes
    assert results['T3'] != results['T2']             # Outcome changes
    
    # 3. Condition C (Inlet Temperature):
    #    Comparing T3 and T4: A and B are held constant (False, True).
    #    C changes True -> False. Outcome changes True -> False.
    assert test_cases['T3'][0] == test_cases['T4'][0] # A constant
    assert test_cases['T3'][1] == test_cases['T4'][1] # B constant
    assert test_cases['T3'][2] != test_cases['T4'][2] # C changes
    assert results['T3'] != results['T4']             # Outcome changes

    print("\n[MC/DC] Surge Bleed Valve (D1 = A or (B and C)) achieves 100% coverage!")


def test_mcdc_overtemp_shutdown():
    """
    Verifies 100% MC/DC coverage for the Overtemperature Shutdown decision.
    Decision: D2 = X and (Y or Z)
    Required test cases:
      U1: (True, True, False)  -> True
      U2: (False, True, False) -> False
      U3: (True, False, False) -> False
      U4: (True, False, True)  -> True
    """
    # Define test suite inputs and expected outputs
    test_cases = {
        'U1': (True, True, False),
        'U2': (False, True, False),
        'U3': (True, False, False),
        'U4': (True, False, True)
    }
    
    # Evaluate outcomes
    results = {name: evaluate_overtemp_shutdown(*vals) for name, vals in test_cases.items()}
    
    # Assert correctness of outcomes
    assert results['U1'] is True
    assert results['U2'] is False
    assert results['U3'] is False
    assert results['U4'] is True

    # Verify Independence Pairs:
    # 1. Condition X (T4 Temperature):
    #    Comparing U1 and U2: Y and Z are held constant (True, False).
    #    X changes True -> False. Outcome changes True -> False.
    assert test_cases['U1'][1] == test_cases['U2'][1] # Y constant
    assert test_cases['U1'][2] == test_cases['U2'][2] # Z constant
    assert test_cases['U1'][0] != test_cases['U2'][0] # X changes
    assert results['U1'] != results['U2']             # Outcome changes
    
    # 2. Condition Y (N2 Speed):
    #    Comparing U1 and U3: X and Z are held constant (True, False).
    #    Y changes True -> False. Outcome changes True -> False.
    assert test_cases['U1'][0] == test_cases['U3'][0] # X constant
    assert test_cases['U1'][2] == test_cases['U3'][2] # Z constant
    assert test_cases['U1'][1] != test_cases['U3'][1] # Y changes
    assert results['U1'] != results['U3']             # Outcome changes
    
    # 3. Condition Z (Fuel Flow):
    #    Comparing U4 and U3: X and Y are held constant (True, False).
    #    Z changes True -> False. Outcome changes True -> False.
    assert test_cases['U4'][0] == test_cases['U3'][0] # X constant
    assert test_cases['U4'][1] == test_cases['U3'][1] # Y constant
    assert test_cases['U4'][2] != test_cases['U3'][2] # Z changes
    assert results['U4'] != results['U3']             # Outcome changes

    print("\n[MC/DC] Overtemp Shutdown (D2 = X and (Y or Z)) achieves 100% coverage!")
