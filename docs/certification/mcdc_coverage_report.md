# DO-178C Structural MC/DC Coverage Analysis Report
## Document No: AEGIS-FADEC-MCDC-001 Rev A
## Target Level: RTCA DO-178C Software Level A (DAL-A)
## Classification: UNCLASSIFIED

---

### 1. Decision Logic Under Test
The following boolean decision from the Safety Kernel was analyzed:
```
Rule = (overspeed AND overtemp) OR high_vibration
```

### 2. Complete Truth Table Evaluation
| Row | Overspeed | Overtemp | High Vibration | Decision Outcome |
|-----|-----------|----------|----------------|------------------|
| 0 | False | False | False | **False** |
| 1 | False | False | True | **True** |
| 2 | False | True | False | **False** |
| 3 | False | True | True | **True** |
| 4 | True | False | False | **False** |
| 5 | True | False | True | **True** |
| 6 | True | True | False | **True** |
| 7 | True | True | True | **True** |

### 3. MC/DC Condition Independence Proofs
For each input variable, we identify a pair of test cases where changing only that variable changes the decision outcome, mathematically proving its independent effect:

#### Condition: Overspeed
- **Proving Pair (Row 2 vs Row 6)**:
  - Case 2: Inputs=(False, True, False) &rarr; Decision=False
  - Case 6: Inputs=(True, True, False) &rarr; Decision=True

#### Condition: Overtemp
- **Proving Pair (Row 4 vs Row 6)**:
  - Case 4: Inputs=(True, False, False) &rarr; Decision=False
  - Case 6: Inputs=(True, True, False) &rarr; Decision=True

#### Condition: HighVibration
- **Proving Pair (Row 0 vs Row 1)**:
  - Case 0: Inputs=(False, False, False) &rarr; Decision=False
  - Case 1: Inputs=(False, False, True) &rarr; Decision=True
- **Proving Pair (Row 2 vs Row 3)**:
  - Case 2: Inputs=(False, True, False) &rarr; Decision=False
  - Case 3: Inputs=(False, True, True) &rarr; Decision=True
- **Proving Pair (Row 4 vs Row 5)**:
  - Case 4: Inputs=(True, False, False) &rarr; Decision=False
  - Case 5: Inputs=(True, False, True) &rarr; Decision=True

### 4. Structural Coverage Verdict
> [!NOTE]
> **VERDICT: 100% MC/DC COVERAGE ACHIEVED**
> All conditions have been mathematically proven to independently control the decision outcome. The requirement for RTCA DO-178C DAL-A structural coverage is satisfied.
