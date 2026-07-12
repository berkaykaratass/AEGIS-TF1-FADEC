"""
Digital Twin EKF Integration Tests
"""

import numpy as np
from simulation.digital_twin.twin_engine import DigitalTwinEngine

def test_twin_ekf_corrections():
    twin = DigitalTwinEngine(dt=0.02)
    initial_state = twin.get_state()
    
    # 1. Run predict step
    twin.predict(inputs=[1.0, 0.0, 15.0])
    predicted_state = twin.get_state()
    
    # 2. Case 1: Elevate only N1 and N2 spool speeds
    deviated_measurement_speed = np.array([
        predicted_state["n1_rpm"] + 5000.0,
        predicted_state["n2_rpm"] + 5000.0,
        predicted_state["egt"],
        predicted_state["p3_bar"]
    ])
    
    twin_speed = DigitalTwinEngine(dt=0.02)
    twin_speed.x = twin.x.copy()
    twin_speed.P = twin.P.copy()
    twin_speed.update(deviated_measurement_speed)
    corrected_speed = twin_speed.get_state()
    
    assert corrected_speed["n1_rpm"] > predicted_state["n1_rpm"]
    assert corrected_speed["n2_rpm"] > predicted_state["n2_rpm"]
    
    # Case 2: Elevate only p3_bar
    deviated_measurement_press = np.array([
        predicted_state["n1_rpm"],
        predicted_state["n2_rpm"],
        predicted_state["egt"],
        predicted_state["p3_bar"] + 0.5
    ])
    
    twin_press = DigitalTwinEngine(dt=0.02)
    twin_press.x = twin.x.copy()
    twin_press.P = twin.P.copy()
    twin_press.update(deviated_measurement_press)
    corrected_press = twin_press.get_state()
    
    assert corrected_press["p3_bar"] > predicted_state["p3_bar"]
