#!/usr/bin/env python3
"""
Hard Real-Time RTOS Scheduling Simulator & Verification
=========================================================

Validates the schedulability, preemption, and priority inversion protection
of the FADEC RTOS task set (100 Hz control, 20 Hz fuel, 10 Hz telemetry)
under Rate Monotonic scheduling.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import pytest
import numpy as np

class RTOSSimulator:
    """Discrete event simulator for priority-based preemptive RTOS scheduling."""
    def __init__(self, tasks, context_switch=0.1, interrupt_latency=0.05):
        self.tasks = tasks  # list of dicts: {'name', 'period', 'wcet', 'priority', 'shared_resource': None}
        self.context_switch = context_switch
        self.interrupt_latency = interrupt_latency

    def run_simulation(self, duration_ms, enable_priority_inheritance=True):
        time = 0.0
        step = 0.05  # 50 microsecond time step
        
        # State tracking
        ready_queue = []  # list of tasks currently ready to execute
        running_task = None
        task_states = {t['name']: {
            'remaining_wcet': 0.0,
            'next_release': 0.0,
            'current_deadline': 0.0,
            'lock_held': None,
            'waiting_for_resource': None,
            'active_priority': t['priority'],  # 0 is highest
            'deadline_misses': 0,
            'completions': 0
        } for t in self.tasks}
        
        events_log = []
        resource_owner = {}  # resource_name -> task_name

        while time < duration_ms:
            # 1. Release periodic tasks
            for t in self.tasks:
                state = task_states[t['name']]
                if time >= state['next_release']:
                    if state['remaining_wcet'] > 0:
                        state['deadline_misses'] += 1
                        events_log.append((time, f"⚠ DEADLINE MISS: {t['name']}"))
                    
                    state['remaining_wcet'] = t['wcet']
                    state['current_deadline'] = time + t['period']
                    state['next_release'] = time + t['period']
                    if t['name'] not in ready_queue:
                        ready_queue.append(t['name'])
                    events_log.append((time, f"Release: {t['name']}"))

            # 2. Shared Resource & Priority Inheritance Logic
            # Simulate a lock dependency if defined
            for t in self.tasks:
                state = task_states[t['name']]
                # Simulate task requesting resource at 30% of its execution
                if state['remaining_wcet'] > 0 and state['remaining_wcet'] < 0.7 * t['wcet'] and t.get('needs_resource'):
                    res = t['needs_resource']
                    if res not in resource_owner:
                        resource_owner[res] = t['name']
                        state['lock_held'] = res
                        events_log.append((time, f"Lock Acquired: {t['name']} acquired {res}"))
                    elif resource_owner[res] != t['name']:
                        # Resource is held by another task (blocking)
                        state['waiting_for_resource'] = res
                        if t['name'] in ready_queue:
                            ready_queue.remove(t['name'])
                        events_log.append((time, f"Block: {t['name']} blocked on {res}"))
                        
                        # Apply Priority Inheritance
                        if enable_priority_inheritance:
                            owner_name = resource_owner[res]
                            owner_state = task_states[owner_name]
                            if owner_state['active_priority'] > state['active_priority']:
                                old_pri = owner_state['active_priority']
                                owner_state['active_priority'] = state['active_priority']
                                events_log.append((time, f"PIP: Elevated {owner_name} priority from {old_pri} to {state['active_priority']}"))

            # 3. Choose running task (Highest priority first, where 0 is highest)
            active_ready_tasks = [t_name for t_name in ready_queue if task_states[t_name]['waiting_for_resource'] is None]
            
            if active_ready_tasks:
                best_task_name = min(active_ready_tasks, key=lambda name: task_states[name]['active_priority'])
                best_task = next(t for t in self.tasks if t['name'] == best_task_name)
                
                # Context switch overhead
                if running_task != best_task_name:
                    if running_task is not None:
                        events_log.append((time, f"Preempt: {running_task} preempted by {best_task_name}"))
                    time += self.context_switch
                    running_task = best_task_name
                
                # Execute task
                state = task_states[best_task_name]
                state['remaining_wcet'] -= step
                
                # Check for completion
                if state['remaining_wcet'] <= 0:
                    state['remaining_wcet'] = 0.0
                    state['completions'] += 1
                    ready_queue.remove(best_task_name)
                    events_log.append((time, f"Complete: {best_task_name} finished cycle"))
                    running_task = None
                    
                    # Release lock if held
                    if state['lock_held']:
                        res = state['lock_held']
                        resource_owner.pop(res)
                        state['lock_held'] = None
                        events_log.append((time, f"Lock Released: {best_task_name} released {res}"))
                        
                        # Restore original priority
                        original_pri = next(t for t in self.tasks if t['name'] == best_task_name)['priority']
                        if state['active_priority'] != original_pri:
                            events_log.append((time, f"PIP Restore: {best_task_name} restored priority to {original_pri}"))
                            state['active_priority'] = original_pri
                            
                        # Wake up waiting tasks
                        for name, st in task_states.items():
                            if st['waiting_for_resource'] == res:
                                st['waiting_for_resource'] = None
                                ready_queue.append(name)
            else:
                running_task = None

            time += step

        return task_states, events_log


@pytest.fixture
def fadec_task_set():
    # 100 Hz FADEC core, 20 Hz fuel metering, 10 Hz telemetry
    return [
        {'name': 'FADEC_Control', 'period': 10.0, 'wcet': 2.5, 'priority': 0},
        {'name': 'Fuel_Metering', 'period': 50.0, 'wcet': 6.0, 'priority': 1},
        {'name': 'Telemetry',     'period': 100.0, 'wcet': 12.0, 'priority': 2}
    ]

def test_utilization_bounds(fadec_task_set):
    """Verify that task set total CPU utilization is within Rate Monotonic bounds."""
    utilization = sum(t['wcet'] / t['period'] for t in fadec_task_set)
    # Rate Monotonic Least Upper Bound for N=3 is N*(2^(1/N) - 1) = 3*(2^(1/3) - 1) = 0.7797
    rm_lub = 3.0 * (2.0**(1.0/3.0) - 1.0)
    
    assert utilization < 0.70, f"CPU utilization is too high: {utilization:.2f}"
    assert utilization < rm_lub, f"Utilization {utilization:.2f} exceeds RM LUB limit {rm_lub:.2f}"

def test_rtos_no_deadline_misses(fadec_task_set):
    """Simulate FADEC RTOS tasks under normal conditions and assert zero deadline misses."""
    sim = RTOSSimulator(fadec_task_set)
    states, log = sim.run_simulation(1000.0) # simulate for 1 second
    
    for name, st in states.items():
        assert st['deadline_misses'] == 0, f"Task {name} experienced {st['deadline_misses']} deadline misses!"
        assert st['completions'] > 0, f"Task {name} did not execute at all!"

def test_rtos_preemption_overload(fadec_task_set):
    """Verify that excessive context switching overhead causes deadline misses (proves simulator validity)."""
    # Set context switch to an extreme 8.0ms (leaving almost no time for execution)
    sim = RTOSSimulator(fadec_task_set, context_switch=8.0)
    states, log = sim.run_simulation(500.0)
    
    misses = sum(st['deadline_misses'] for st in states.values())
    assert misses > 0, "Extreme context switch overhead did not trigger deadline misses!"

def test_priority_inversion_and_inheritance():
    """
    Test Priority Inheritance Protocol (PIP).
    Without PIP, priority inversion can cause high-priority FADEC_Control to miss deadlines.
    With PIP, the low-priority Telemetry task inherits high priority to quickly release the lock.
    """
    # Telemetry needs FADEC_Bus, FADEC_Control also needs FADEC_Bus.
    # Fuel_Metering has medium priority and doesn't need FADEC_Bus.
    tasks = [
        {'name': 'FADEC_Control', 'period': 10.0, 'wcet': 3.0, 'priority': 0, 'needs_resource': 'FADEC_Bus'},
        {'name': 'Fuel_Metering', 'period': 25.0, 'wcet': 8.0, 'priority': 1},
        {'name': 'Telemetry',     'period': 50.0, 'wcet': 15.0, 'priority': 2, 'needs_resource': 'FADEC_Bus'}
    ]
    
    # Run WITHOUT Priority Inheritance -> should miss deadline
    sim_no_pip = RTOSSimulator(tasks)
    states_no_pip, log_no_pip = sim_no_pip.run_simulation(200.0, enable_priority_inheritance=False)
    misses_no_pip = sum(st['deadline_misses'] for st in states_no_pip.values())
    
    # Run WITH Priority Inheritance -> should resolve and have fewer/zero misses
    sim_pip = RTOSSimulator(tasks)
    states_pip, log_pip = sim_pip.run_simulation(200.0, enable_priority_inheritance=True)
    misses_pip = sum(st['deadline_misses'] for st in states_pip.values())
    
    assert misses_no_pip > 0, "No priority inversion deadline misses without PIP!"
    assert misses_pip < misses_no_pip, f"Priority inheritance did not reduce misses: {misses_pip} vs {misses_no_pip}"
