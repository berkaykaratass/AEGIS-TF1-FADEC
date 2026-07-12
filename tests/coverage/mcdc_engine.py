#!/usr/bin/env python3
"""
@file mcdc_engine.py
@brief DO-178C DAL A MC/DC Coverage Analysis Engine
"""

import sys

def analyze_mcdc_decision(decision_name, formula, conditions, test_cases):
    """
    Analyzes whether the given test cases achieve 100% MC/DC coverage for the decision.
    """
    print(f"\nAnalyzing Decision: {decision_name} ({formula})")
    print("-" * 50)
    
    # 1. Evaluate decisions for each case
    results = {}
    for case_id, vals in test_cases.items():
        # Evaluate formula dynamically
        env = {cond: val for cond, val in zip(conditions, vals)}
        results[case_id] = eval(formula, {}, env)
        print(f"  Case {case_id}: {env} -> Outcome: {results[case_id]}")
        
    # 2. Check independence pair for each condition
    covered_conditions = []
    for cond_idx, cond in enumerate(conditions):
        found_pair = False
        for c1_id, c1_vals in test_cases.items():
            for c2_id, c2_vals in test_cases.items():
                if c1_id >= c2_id:
                    continue
                
                # Check if all other conditions are constant
                other_constant = True
                for idx in range(len(conditions)):
                    if idx != cond_idx:
                        if c1_vals[idx] != c2_vals[idx]:
                            other_constant = False
                            
                # Check if this condition toggles
                cond_toggles = c1_vals[cond_idx] != c2_vals[cond_idx]
                
                # Check if outcome toggles
                outcome_toggles = results[c1_id] != results[c2_id]
                
                if other_constant and cond_toggles and outcome_toggles:
                    print(f"  > Condition '{cond}' covered by independence pair ({c1_id}, {c2_id})")
                    found_pair = True
                    break
            if found_pair:
                covered_conditions.append(cond)
                break
                
    coverage_pct = (len(covered_conditions) / len(conditions)) * 100.0
    print(f"MC/DC Coverage for {decision_name}: {len(covered_conditions)}/{len(conditions)} conditions covered ({coverage_pct:.1f}%)")
    return coverage_pct == 100.0

def main():
    print("=" * 60)
    print("      DO-178C MC/DC STRUCTURAL COVERAGE VERIFICATION")
    print("=" * 60)
    
    # Decision 1: Surge Bleed Valve (A or (B and C))
    d1_ok = analyze_mcdc_decision(
        decision_name="Surge Bleed Valve Trigger",
        formula="A or (B and C)",
        conditions=["A", "B", "C"],
        test_cases={
            'T1': (True, False, True),
            'T2': (False, False, True),
            'T3': (False, True, True),
            'T4': (False, True, False)
        }
    )
    
    # Decision 2: Overtemp Shutdown (X and (Y or Z))
    d2_ok = analyze_mcdc_decision(
        decision_name="Overtemp Emergency Shutdown",
        formula="X and (Y or Z)",
        conditions=["X", "Y", "Z"],
        test_cases={
            'U1': (True, True, False),
            'U2': (False, True, False),
            'U3': (True, False, False),
            'U4': (True, False, True)
        }
    )
    
    success = d1_ok and d2_ok
    if success:
        print("\nSUCCESS: All critical decisions achieve 100% MC/DC Coverage!")
        sys.exit(0)
    else:
        print("\nFAILURE: MC/DC coverage gaps detected!")
        sys.exit(1)

if __name__ == "__main__":
    main()
