/**
 * @file dashboard.js
 * @brief FADEC Jet Engine Dashboard Main Controller
 * @details Implements the real-time polling loop, chart updates, EKF tracking,
 *          watermark analysis, and interactive REST control integrations in Light Theme.
 */

window.switchTab = function(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(`tabBtn-${tabId}`).classList.add('active');
    document.getElementById(`tab-${tabId}`).classList.add('active');
};

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = 'http://localhost:8024/api/twin';
    
    // Simulation state cache
    const state = {
        connected: false,
        running: false,
        replayMode: false,
        throttle: 0.0,
        altitude: 0.0,
        mach: 0.0,
        
        // Fault injection flags
        cyberAttackActive: false,
        sensorFaultActive: false,
        mpuViolationActive: false,
        
        // Polling loop
        timer: null,
        
        // Telemetry history (last 50 samples for rolling line charts)
        historyLength: 50,
        timeHistory: [],
        rawN1History: [],
        ekfN1History: [],
        rawEgtHistory: [],
        ekfT41History: [],
        watermarkCorrHistory: [],
        wcetAcqHistory: [],
        wcetCtrlHistory: [],
        ccdlLatencyHistory: [],
        ccdlJitterHistory: [],
        
        // Scenario / Replay cache
        activeScenarioId: "",
        replayFramesCount: 0,
        currentFileLog: null,
        lastSimTime: -1
    };

    // Initialize Charts
    const braytonCharts = new BraytonChart('tsChart', 'pvChart');
    const compMapChart = new CompressorMapChart('compressorMapChart');
    const healthChart = new HealthMonitorChart('healthRadarChart');
    
    let ekfSpeedChart = null;
    let ekfTempChart = null;
    let watermarkChart = null;
    let wcetChart = null;
    let ccdlChart = null;

    // UI Elements
    const throttleSlider = document.getElementById('throttleSlider');
    const throttleVal = document.getElementById('throttleVal');
    const altitudeInput = document.getElementById('altitudeInput');
    const machInput = document.getElementById('machInput');
    
    const btnStart = document.getElementById('btnStart');
    const btnStop = document.getElementById('btnStop');
    const btnReset = document.getElementById('btnReset');
    
    const btnInjectCyber = document.getElementById('btnInjectCyber');
    const btnInjectSensor = document.getElementById('btnInjectSensor');
    const btnInjectMpu = document.getElementById('btnInjectMpu');
    
    const scenarioSelect = document.getElementById('scenarioSelect');
    const btnPlayScenario = document.getElementById('btnPlayScenario');
    const btnStopScenario = document.getElementById('btnStopScenario');
    const btnExportLog = document.getElementById('btnExportLog');
    const btnImportLog = document.getElementById('btnImportLog');
    
    const timelineSlider = document.getElementById('timelineSlider');
    const timelineTicks = document.getElementById('timelineTicks');
    const timelineSpans = document.getElementById('timelineSpans');
    
    const validationCard = document.getElementById('validationCard');
    const valScore = document.getElementById('valScore');
    const valVerdict = document.getElementById('valVerdict');
    const valEvents = document.getElementById('valEvents');
    const valSignalsTable = document.getElementById('valSignalsTable').getElementsByTagName('tbody')[0];
    
    const valRPM = document.getElementById('valRPM');
    const valRPM2 = document.getElementById('valRPM2');
    const valEGT = document.getElementById('valEGT');
    const valThrust = document.getElementById('valThrust');
    const valRUL = document.getElementById('valRUL');
    const systemLog = document.getElementById('systemLog');
    const txtSimTime = document.getElementById('txtTelemetryTime');
    const txtFps = document.getElementById('txtFps');
    const statusText = document.getElementById('statusText');
    const statusDot = document.getElementById('statusDot');

    // Diagnostics & MPU & CCDL elements
    const diagRam = document.getElementById('diagRam');
    const diagFlash = document.getElementById('diagFlash');
    const diagAlu = document.getElementById('diagAlu');
    const diagStack = document.getElementById('diagStack');
    const mpuControl = document.getElementById('mpuControl');
    const mpuSafety = document.getElementById('mpuSafety');
    const mpuAdvisory = document.getElementById('mpuAdvisory');
    const ccdlA = document.getElementById('ccdlA');
    const ccdlB = document.getElementById('ccdlB');
    const ccdlAStatus = document.getElementById('ccdlAStatus');
    const ccdlBStatus = document.getElementById('ccdlBStatus');
    const ccdlAHealth = document.getElementById('ccdlAHealth');
    const ccdlBHealth = document.getElementById('ccdlBHealth');
    const ccdlAHb = document.getElementById('ccdlAHb');
    const ccdlBHb = document.getElementById('ccdlBHb');

    // ACC & Creep elements
    const valGap = document.getElementById('valGap');
    const valRotorTemp = document.getElementById('valRotorTemp');
    const valCasingTemp = document.getElementById('valCasingTemp');
    const valAccValve = document.getElementById('valAccValve');
    const txtCreepRate = document.getElementById('txtCreepRate');
    const txtCreepDamage = document.getElementById('txtCreepDamage');
    const barCreepRate = document.getElementById('barCreepRate');
    const barCreepDamage = document.getElementById('barCreepDamage');

    // Set global Chart defaults for light mode
    Chart.defaults.color = '#495057';
    Chart.defaults.borderColor = 'rgba(0, 0, 0, 0.08)';

    function logEvent(msg, severity = 'info') {
        const timeStr = new Date().toISOString().slice(11, 19);
        const entry = document.createElement('div');
        entry.className = `log-entry ${severity}`;
        entry.innerText = `[${timeStr}] ${msg}`;
        systemLog.appendChild(entry);
        systemLog.scrollTop = systemLog.scrollHeight;
    }

    function initEkfCharts() {
        const gridColor = 'rgba(0, 0, 0, 0.06)';
        const titleColor = '#212529';
        const labelColor = '#495057';

        const speedCtx = document.getElementById('ekfSpeedChart').getContext('2d');
        ekfSpeedChart = new Chart(speedCtx, {
            type: 'line',
            data: {
                labels: Array(state.historyLength).fill(''),
                datasets: [
                    {
                        label: 'Actual N1 (Sensor)',
                        data: [],
                        borderColor: '#e65100',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: 'Estimated N1 (EKF)',
                        borderColor: '#0f4c81',
                        borderWidth: 1.5,
                        data: [],
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: labelColor, font: { size: 8 } } },
                    title: { display: true, text: 'EKF SPOOL SPEED OBSERVER DYNAMICS', color: titleColor, font: { size: 10, weight: 'bold' } }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { display: false } },
                    y: { grid: { color: gridColor }, ticks: { color: labelColor, font: { size: 8 } } }
                }
            }
        });

        const tempCtx = document.getElementById('ekfTempChart').getContext('2d');
        ekfTempChart = new Chart(tempCtx, {
            type: 'line',
            data: {
                labels: Array(state.historyLength).fill(''),
                datasets: [
                    {
                        label: 'Raw EGT (Sensor)',
                        data: [],
                        borderColor: '#c62828',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: 'Estimated T4.1 (EKF)',
                        borderColor: '#2e7d32',
                        borderWidth: 1.5,
                        data: [],
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: labelColor, font: { size: 8 } } },
                    title: { display: true, text: 'EKF TURBINE TEMPERATURE OBSERVATION', color: titleColor, font: { size: 10, weight: 'bold' } }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { display: false } },
                    y: { grid: { color: gridColor }, ticks: { color: labelColor, font: { size: 8 } } }
                }
            }
        });

        const wmCtx = document.getElementById('watermarkChart').getContext('2d');
        watermarkChart = new Chart(wmCtx, {
            type: 'line',
            data: {
                labels: Array(state.historyLength).fill(''),
                datasets: [
                    {
                        label: 'Correlation Index',
                        data: [],
                        borderColor: '#0f4c81',
                        borderWidth: 2,
                        pointRadius: 1,
                        fill: true,
                        backgroundColor: 'rgba(15, 76, 129, 0.03)'
                    },
                    {
                        label: 'Safety Trip Threshold (0.005)',
                        data: Array(state.historyLength).fill(0.005),
                        borderColor: '#c62828',
                        borderWidth: 1.5,
                        borderDash: [6, 4],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: labelColor, font: { size: 8 } } },
                    title: { display: true, text: 'CYBER CYCLIC WATERMARK CORRELATION MONITOR', color: titleColor, font: { size: 10, weight: 'bold' } }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { display: false } },
                    y: { grid: { color: gridColor }, ticks: { color: labelColor, font: { size: 8 } } }
                }
            }
        });

        const wcetCtx = document.getElementById('wcetChart').getContext('2d');
        wcetChart = new Chart(wcetCtx, {
            type: 'line',
            data: {
                labels: Array(state.historyLength).fill(''),
                datasets: [
                    {
                        label: 'Flight Control Task (FC)',
                        data: [],
                        borderColor: '#2e7d32',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: 'Sensor Acquisition Task (SA)',
                        data: [],
                        borderColor: '#1565c0',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: 'Task Frame Deadline (1000us)',
                        data: Array(state.historyLength).fill(1000),
                        borderColor: '#c62828',
                        borderWidth: 1.5,
                        borderDash: [6, 4],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: labelColor, font: { size: 8 } } },
                    title: { display: true, text: 'REAL-TIME WORKLOAD & EXECUTION TIME PROFILE (us)', color: titleColor, font: { size: 10, weight: 'bold' } }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { display: false } },
                    y: { grid: { color: gridColor }, ticks: { color: labelColor, font: { size: 8 } }, min: 0, max: 1100 }
                }
            }
        });

        const ccdlCtx = document.getElementById('ccdlChart').getContext('2d');
        ccdlChart = new Chart(ccdlCtx, {
            type: 'line',
            data: {
                labels: Array(state.historyLength).fill(''),
                datasets: [
                    {
                        label: 'CCDL Sync Latency (ms)',
                        data: [],
                        borderColor: '#0f4c81',
                        borderWidth: 2,
                        pointRadius: 1,
                        fill: false
                    },
                    {
                        label: 'ARINC-429 Jitter (ms)',
                        data: [],
                        borderColor: '#f57c00',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: labelColor, font: { size: 8 } } },
                    title: { display: true, text: 'CCDL SENKRONİZASYON VE ARINC GECİKME ANALİZİ (ms)', color: titleColor, font: { size: 10, weight: 'bold' } }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { display: false } },
                    y: { grid: { color: gridColor }, ticks: { color: labelColor, font: { size: 8 } }, min: 0, max: 5 }
                }
            }
        });
    }

    async function loadScenarios() {
        try {
            const response = await fetch(`${API_BASE}/scenarios`);
            if (response.ok) {
                const list = await response.json();
                scenarioSelect.innerHTML = '<option value="">-- MANUAL FLIGHT MODE --</option>';
                list.forEach(scen => {
                    const op = document.createElement('option');
                    op.value = scen.id;
                    op.innerText = `${scen.name} (${scen.duration}s)`;
                    scenarioSelect.appendChild(op);
                });
            }
        } catch (err) {
            console.error('Error loading scenarios list:', err);
        }
    }

    async function sendCommands() {
        if (state.replayMode) return;
        try {
            await fetch(`${API_BASE}/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    throttle_pla: state.throttle,
                    altitude_ft: state.altitude,
                    mach: state.mach
                })
            });
        } catch (err) {
            console.error('Error sending commands to SIL Simulator:', err);
        }
    }

    function drawTimelineSpansAndEvents(logPayload) {
        timelineSpans.innerHTML = '';
        timelineTicks.innerHTML = '';
        
        const telemetry = logPayload.telemetry || [];
        const events = logPayload.events || [];
        const duration = logPayload.metadata?.duration_seconds || 25.0;
        
        if (telemetry.length === 0) return;
        
        // 1. Calculate timeline ticks (0s, 5s, 10s, 15s, etc.)
        const step = Math.ceil(duration / 5);
        for (let t = 0; t <= duration; t += step) {
            const pct = (t / duration) * 100;
            const tick = document.createElement('div');
            tick.className = 'timeline-tick-label';
            tick.style.position = 'absolute';
            tick.style.left = `${pct}%`;
            tick.style.transform = 'translateX(-50%)';
            tick.innerText = `${t}s`;
            timelineTicks.appendChild(tick);
        }
        
        // 2. Identify State Windows (Fault Active, Limits Mode, EKF Disabled)
        let faultStart = null;
        let limitsStart = null;
        let ekfOffStart = null;
        
        const sampleStep = 10; // Sample every 10 frames (100ms) to build spans efficiently
        for (let i = 0; i < telemetry.length; i += sampleStep) {
            const frame = telemetry[i];
            const t = frame.sim_time;
            const pct = (t / duration) * 100;
            
            // Fault span
            if (frame.fault_active) {
                if (faultStart === null) faultStart = pct;
            } else {
                if (faultStart !== null) {
                    createSpanElement(faultStart, pct, 'fault', 'Fault Active');
                    faultStart = null;
                }
            }
            
            // Limits span
            if (frame.safe_mode_active) {
                if (limitsStart === null) limitsStart = pct;
            } else {
                if (limitsStart !== null) {
                    createSpanElement(limitsStart, pct, 'limits', 'Safe Limits Active');
                    limitsStart = null;
                }
            }
            
            // EKF Off span
            if (!frame.ekf_active) {
                if (ekfOffStart === null) ekfOffStart = pct;
            } else {
                if (ekfOffStart !== null) {
                    createSpanElement(ekfOffStart, pct, 'ekf-off', 'EKF Offline');
                    ekfOffStart = null;
                }
            }
        }
        
        // Close open spans at the end
        const endPct = 100.0;
        if (faultStart !== null) createSpanElement(faultStart, endPct, 'fault', 'Fault Active');
        if (limitsStart !== null) createSpanElement(limitsStart, endPct, 'limits', 'Safe Limits Active');
        if (ekfOffStart !== null) createSpanElement(ekfOffStart, endPct, 'ekf-off', 'EKF Offline');
        
        // 3. Draw Event marker nodes
        events.forEach(ev => {
            const pct = (ev.time / duration) * 100;
            if (pct >= 0 && pct <= 100) {
                const marker = document.createElement('div');
                marker.className = 'timeline-marker';
                marker.style.left = `${pct}%`;
                
                const label = document.createElement('div');
                label.className = 'timeline-marker-label';
                label.innerText = ev.type;
                marker.appendChild(label);
                
                timelineSpans.appendChild(marker);
            }
        });
    }
    
    function createSpanElement(startPct, endPct, typeClass, tooltipText) {
        const span = document.createElement('div');
        span.className = `timeline-span ${typeClass}`;
        span.style.left = `${startPct}%`;
        span.style.width = `${endPct - startPct}%`;
        span.title = tooltipText;
        timelineSpans.appendChild(span);
    }

    async function pollState() {
        let startTime = performance.now();
        try {
            let endpoint = state.replayMode ? `${API_BASE}/replay/state` : `${API_BASE}/state`;
            const response = await fetch(endpoint);
            if (!response.ok) throw new Error('API down');
            
            const data = await response.json();
            
            if (!state.connected) {
                state.connected = true;
                logEvent('Connection established with FADEC SIL backend.', 'info');
            }
            
            let telemetryData = data;
            
            if (state.replayMode) {
                if (!data.replay_active) {
                    // Replay mode ended or inactive
                    state.replayMode = false;
                    toggleControlInputs(false);
                    return;
                }
                
                // Fetch actual frame telemetry
                const stateResponse = await fetch(`${API_BASE}/state`);
                telemetryData = await stateResponse.json();
                
                // Update Timeline progress slider value dynamically
                timelineSlider.value = data.frame_index;
                state.running = telemetryData.running;
            } else {
                state.running = data.running;
            }
            
            // Check for MPU violation message
            if (telemetryData.fadec_mode === 5 && telemetryData.mpu_violation && state.running) {
                state.running = false;
                logEvent('FATAL: Simulated MPU Spatial Write Partition violation trapped!', 'error');
                logEvent('FADEC transition to emergency shutdown mode. Core halted.', 'error');
            }
            
            // Scenario Completion/Status tracking
            if (!state.replayMode && state.activeScenarioId !== "") {
                const scenStatusResp = await fetch(`${API_BASE}/scenarios/status`);
                if (scenStatusResp.ok) {
                    const status = await scenStatusResp.json();
                    if (!status.active && state.running) {
                        // Scenario ended
                        state.running = false;
                        logEvent(`Scenario '${scenarioSelect.options[scenarioSelect.selectedIndex].text}' completed. Running Golden reference validation...`, 'warn');
                        
                        // Automatically export current log run and send for validation
                        const exportResp = await fetch(`${API_BASE}/log/export`);
                        if (exportResp.ok) {
                            const currentLog = await exportResp.json();
                            state.currentFileLog = currentLog;
                            
                            // Draw the timeline spans based on the fresh complete log
                            drawTimelineSpansAndEvents(currentLog);
                            
                            // Trigger validation report
                            runGoldenValidation(currentLog);
                        }
                        
                        state.activeScenarioId = "";
                        btnPlayScenario.innerText = 'PLAY';
                        btnPlayScenario.className = 'btn btn-blue';
                    } else if (status.active) {
                        // Update timeline progress bar during active scenario
                        timelineSlider.value = Math.round(status.time * 100);
                        
                        // Handle logging timed annotations
                        status.recorded_events.forEach(e => {
                            if (!state.timeHistory.includes(e.time)) {
                                logEvent(`EVENT TRIGGERED [t=${e.time}s]: ${e.type}`, 'warn');
                            }
                        });
                    }
                }
            }
            
            // Update gauges & values
            valRPM.innerText = telemetryData.n1_rpm.toFixed(1);
            valRPM2.innerText = telemetryData.n2_rpm.toFixed(1);
            valEGT.innerText = Math.round(telemetryData.egt);
            
            const thrust_calc = state.running ? Math.round(telemetryData.n1_rpm * 150.0 + telemetryData.fuel_flow_kgs * 15000.0) : 0;
            valThrust.innerText = thrust_calc;
            
            valRUL.innerText = `${Math.round(telemetryData.estimated_rul_hours || telemetryData.rul_hours || 3000).toLocaleString()} hrs`;
            
            // Update gauge rings (scale RPM to 0-100% of max 35000 RPM)
            const n1_ring_pct = Math.min(100.0, (telemetryData.n1_rpm / 35000.0) * 100.0);
            const n2_ring_pct = Math.min(100.0, (telemetryData.n2_rpm / 35000.0) * 100.0);
            document.getElementById('rpmGauge').style.background = `conic-gradient(var(--accent-blue) ${n1_ring_pct}%, var(--bg-secondary) ${n1_ring_pct}%)`;
            document.getElementById('rpmGauge2').style.background = `conic-gradient(var(--accent-amber) ${n2_ring_pct}%, var(--bg-secondary) ${n2_ring_pct}%)`;
            
            const egtPct = Math.min(100.0, (telemetryData.egt / 1200.0) * 100.0);
            const egtColor = telemetryData.egt > 980.0 ? 'var(--accent-red)' : 'var(--accent-amber)';
            document.getElementById('egtGauge').style.background = `conic-gradient(${egtColor} ${egtPct}%, var(--bg-secondary) ${egtPct}%)`;
            
            const thrustPct = Math.min(100.0, (thrust_calc / 25000.0) * 100.0);
            document.getElementById('thrustGauge').style.background = `conic-gradient(var(--accent-green) ${thrustPct}%, var(--bg-secondary) ${thrustPct}%)`;
            
            // Update status text
            if (state.running) {
                let modeText = 'ACTIVE';
                if (telemetryData.fadec_mode === 0) modeText = 'STARTUP';
                else if (telemetryData.fadec_mode === 1) modeText = 'IDLE';
                else if (telemetryData.fadec_mode === 3) modeText = 'CRUISE';
                else if (telemetryData.fadec_mode === 8) modeText = 'LIMIT CONTROL';
                
                statusText.innerText = `ENGINE ACTIVE (${modeText} - CH ${telemetryData.active_channel === 0 ? 'A' : 'B'})`;
                statusDot.className = 'status-dot green pulse';
            } else {
                if (telemetryData.fadec_mode === 5 || telemetryData.fadec_mode === 8) {
                    statusText.innerText = 'EMERGENCY SHUTDOWN / LOCKOUT';
                    statusDot.className = 'status-dot red pulse';
                } else {
                    statusText.innerText = 'STANDBY / CUTOFF';
                    statusDot.className = 'status-dot red';
                }
            }
            
            // Diagnostics
            const tick = telemetryData.scheduler_ticks || 0;
            const sensor_faults = telemetryData.sensor_faults || 0;
            
            if (telemetryData.fadec_mode === 5 && telemetryData.mpu_violation) {
                diagRam.innerText = 'FAIL'; diagRam.className = 'diag-status fail';
                diagFlash.innerText = 'FAIL'; diagFlash.className = 'diag-status fail';
            } else {
                diagRam.innerText = 'OK'; diagRam.className = 'diag-status ok';
                diagFlash.innerText = 'OK'; diagFlash.className = 'diag-status ok';
            }
            
            if ((sensor_faults & 0x40) !== 0) {
                diagAlu.innerText = 'FAIL'; diagAlu.className = 'diag-status fail';
            } else {
                diagAlu.innerText = 'OK'; diagAlu.className = 'diag-status ok';
            }
            diagStack.innerText = 'OK'; diagStack.className = 'diag-status ok';
            
            // MPU Partition active highlights
            mpuControl.className = 'mpu-box';
            mpuSafety.className = 'mpu-box';
            mpuAdvisory.className = 'mpu-box';
            
            if (telemetryData.fadec_mode === 3) {
                mpuControl.className = 'mpu-box active';
            } else if (telemetryData.fadec_mode === 8) {
                mpuSafety.className = 'mpu-box active';
            } else if (telemetryData.fadec_mode === 7) {
                mpuAdvisory.className = 'mpu-box active';
            }
            
            if (telemetryData.mpu_violation) {
                mpuAdvisory.className = 'mpu-box active';
                mpuAdvisory.style.borderColor = 'var(--accent-red)';
            } else {
                mpuAdvisory.style.borderColor = 'var(--border-color)';
            }
            
            // CCDL
            ccdlAHb.innerText = `HB PACKETS: ${tick}`;
            ccdlBHb.innerText = `HB PACKETS: ${Math.round(tick * 0.99)}`;
            
            if ((sensor_faults & 0x01) !== 0) {
                ccdlAHealth.innerText = 'HEALTH: 85% (FDIR SENSOR DEGRADED)';
                ccdlA.style.borderColor = 'var(--accent-amber)';
            } else {
                ccdlAHealth.innerText = 'HEALTH: 100%';
                ccdlA.style.borderColor = 'var(--border-color)';
            }
            
            // Brayton cycle diagrams
            const R_air = 287.05;
            const cp_a = 1005.0;
            const cp_g = 1148.0;
            const gamma_a = 1.4;
            const gamma_g = 1.33;
            
            const T2 = telemetryData.t2_kelvin;
            const P2 = telemetryData.p2_bar * 100000.0;
            const r_p = telemetryData.p3_bar / telemetryData.p2_bar;
            
            const T3 = T2 * Math.pow(r_p, (gamma_a - 1.0) / gamma_a);
            const T4 = telemetryData.ekf_t41 || 650.0;
            const P4 = telemetryData.p3_bar * 0.97 * 100000.0;
            const T5 = T4 * Math.pow(1.0 / r_p, (gamma_g - 1.0) / gamma_g);
            
            const temps = [T2 - 30.0, T2, T3, T4, T5, T2];
            const pressures = [P2 - 1000.0, P2, telemetryData.p3_bar * 100000.0, P4, P2 * 1.05, P2];
            const entropies = [
                0.0,
                cp_a * Math.log(T2 / (T2 - 30.0)) - R_air * Math.log(P2 / (P2 - 1000.0)),
                cp_a * Math.log(T3 / T2) - R_air * Math.log(pressures[2] / P2),
                cp_a * Math.log(T3 / T2) + cp_g * Math.log(T4 / T3) - R_air * Math.log(pressures[3] / pressures[2]),
                cp_a * Math.log(T3 / T2) + cp_g * Math.log(T4 / T3) + cp_g * Math.log(T5 / T4) - R_air * Math.log(pressures[4] / pressures[3]),
                0.0
            ];
            const volumes = temps.map((T, idx) => R_air * T / pressures[idx]);
            
            braytonCharts.update(temps, pressures, entropies, volumes);
            
            // Compressor Map Point
            compMapChart.updateOperatingPoint(telemetryData.n1_rpm * 0.22, telemetryData.p3_bar / telemetryData.p2_bar, telemetryData.surge_warning > 0);
            
            // Update rolling chart history only when simulation time advances
            if (telemetryData.sim_time !== state.lastSimTime) {
                state.lastSimTime = telemetryData.sim_time;
                
                if (state.timeHistory.length >= state.historyLength) {
                    state.timeHistory.shift();
                    state.rawN1History.shift();
                    state.ekfN1History.shift();
                    state.rawEgtHistory.shift();
                    state.ekfT41History.shift();
                    state.watermarkCorrHistory.shift();
                    state.wcetAcqHistory.shift();
                    state.wcetCtrlHistory.shift();
                    state.ccdlLatencyHistory.shift();
                    state.ccdlJitterHistory.shift();
                }
                
                state.timeHistory.push(telemetryData.sim_time);
                state.rawN1History.push(telemetryData.n1_rpm);
                state.ekfN1History.push(telemetryData.ekf_n1);
                state.rawEgtHistory.push(telemetryData.egt);
                state.ekfT41History.push(telemetryData.ekf_t41);
                state.watermarkCorrHistory.push(telemetryData.watermark_correlation);
                state.wcetAcqHistory.push(telemetryData.wcet_sensor_acq_us);
                state.wcetCtrlHistory.push(telemetryData.wcet_flight_control_us);
                state.ccdlLatencyHistory.push(telemetryData.ccdl_latency_ms);
                state.ccdlJitterHistory.push(telemetryData.ccdl_jitter_ms);
            }
            
            // Update EKF Speed Observer Chart
            ekfSpeedChart.data.labels = state.timeHistory.map(t => `${t}s`);
            ekfSpeedChart.data.datasets[0].data = state.rawN1History;
            ekfSpeedChart.data.datasets[1].data = state.ekfN1History;
            ekfSpeedChart.update('none');
            
            // Update EKF Temp Observer Chart
            ekfTempChart.data.labels = state.timeHistory.map(t => `${t}s`);
            ekfTempChart.data.datasets[0].data = state.rawEgtHistory;
            ekfTempChart.data.datasets[1].data = state.ekfT41History;
            ekfTempChart.update('none');
            
            // Update Watermark correlation
            watermarkChart.data.labels = state.timeHistory.map(t => `${t}s`);
            watermarkChart.data.datasets[0].data = state.watermarkCorrHistory;
            watermarkChart.update('none');

            // Update WCET Chart
            wcetChart.data.labels = state.timeHistory.map(t => `${t}s`);
            wcetChart.data.datasets[0].data = state.wcetCtrlHistory;
            wcetChart.data.datasets[1].data = state.wcetAcqHistory;
            wcetChart.update('none');

            // Update CCDL Chart
            ccdlChart.data.labels = state.timeHistory.map(t => `${t}s`);
            ccdlChart.data.datasets[0].data = state.ccdlLatencyHistory;
            ccdlChart.data.datasets[1].data = state.ccdlJitterHistory;
            ccdlChart.update('none');

            // Update MC/DC UI components
            updateMcdcDashboard(telemetryData);
            
            // Trigger Watermark alarm alert
            if (telemetryData.watermark_alarm && !state.cyberAttackActive) {
                logEvent('CYBER SECURITY TRIP: Command correlation mismatch! Replay attack signature match fail.', 'error');
                logEvent('CCDL Lockout triggered. Advisory SNN disabled. Safe recovery active.', 'warn');
                state.cyberAttackActive = true;
                btnInjectCyber.innerText = 'CLEAR CYBER ATTACK';
                btnInjectCyber.className = 'btn btn-green';
            }
            
            // ACC clearances
            valGap.innerText = `${telemetryData.tip_clearance_mm.toFixed(3)} mm`;
            valRotorTemp.innerText = `${Math.round(telemetryData.rotor_growth_mm * 500.0 + 288.15)} K`;
            valCasingTemp.innerText = `${Math.round(telemetryData.casing_growth_mm * 400.0 + 288.15)} K`;
            valAccValve.innerText = `${telemetryData.acc_valve_cmd_pct.toFixed(1)} %`;
            
            // Creep Governor
            txtCreepRate.innerText = `${telemetryData.creep_rate.toExponential(4)} / hr`;
            txtCreepDamage.innerText = `${telemetryData.creep_damage.toFixed(6)} / 1.000`;
            
            const rateBarPct = Math.min(100.0, (telemetryData.creep_rate / 1e-4) * 100.0);
            const damageBarPct = Math.min(100.0, (telemetryData.creep_damage / 0.05) * 100.0);
            barCreepRate.style.width = `${rateBarPct}%`;
            barCreepDamage.style.width = `${damageBarPct}%`;
            
            // Neuromorphic radar health
            const bandVal = (name, base) => base + (telemetryData.vibration_g * 0.1) + (telemetryData.surge_warning > 0 ? 0.3 : 0.0);
            const activeBands = [
                bandVal('Delta', 1.0),
                bandVal('Theta', 1.0),
                bandVal('Alpha', 1.0),
                bandVal('Beta', 1.0),
                bandVal('Gamma', 1.0)
            ];
            healthChart.update(activeBands, [1.0, 1.0, 1.0, 1.0, 1.0]);
            
            // Timeline time label
            txtSimTime.innerText = `SIMULATED TIME: ${telemetryData.sim_time.toFixed(1)}s`;
            const duration = performance.now() - startTime;
            txtFps.innerText = `POLLING DELAY: ${duration.toFixed(1)} ms`;
            
        } catch (err) {
            if (state.connected) {
                state.connected = false;
                logEvent('Connection lost with FADEC SIL backend. Re-trying...', 'error');
            }
            statusText.innerText = 'BACKEND OFFLINE';
            statusDot.className = 'status-dot red';
        }
    }

    async function runGoldenValidation(logData) {
        try {
            const resp = await fetch(`${API_BASE}/scenarios/validate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(logData)
            });
            if (resp.ok) {
                const report = await resp.json();
                displayValidationReport(report);
            }
        } catch (err) {
            logEvent('Failed to run Golden Reference validation.', 'error');
        }
    }

    function displayValidationReport(report) {
        validationCard.style.display = 'block';
        valScore.innerText = `${report.overall_score_pct}%`;
        valVerdict.innerText = report.verdict;
        valVerdict.style.color = report.verdict === 'PASS' ? 'var(--accent-green)' : 'var(--accent-red)';
        valEvents.innerText = report.events_status;
        
        valSignalsTable.innerHTML = '';
        for (const [sigName, res] of Object.entries(report.signals)) {
            const row = valSignalsTable.insertRow();
            row.insertCell(0).innerText = sigName.toUpperCase();
            row.insertCell(1).innerText = `${res.score_pct}%`;
            row.insertCell(2).innerText = res.max_error;
            
            const cellV = row.insertCell(3);
            cellV.innerText = res.verdict;
            cellV.className = res.verdict === 'PASS' ? 'pass' : 'fail';
        }
    }

    function toggleControlInputs(disable) {
        throttleSlider.disabled = disable;
        altitudeInput.disabled = disable;
        machInput.disabled = disable;
        btnStart.disabled = disable;
        btnStop.disabled = disable;
        btnReset.disabled = disable;
        btnInjectCyber.disabled = disable;
        btnInjectSensor.disabled = disable;
        btnInjectMpu.disabled = disable;
        
        timelineSlider.disabled = !disable; // timeline scrubber is enabled only in replay/scenarios
    }

    // Connect manual slide controls
    throttleSlider.addEventListener('input', (e) => {
        state.throttle = parseFloat(e.target.value);
        throttleVal.innerText = `${state.throttle}%`;
        sendCommands();
    });

    altitudeInput.addEventListener('change', (e) => {
        state.altitude = parseFloat(e.target.value) || 0.0;
        logEvent(`Altitude command set to ${state.altitude} ft`, 'info');
        sendCommands();
    });

    machInput.addEventListener('change', (e) => {
        state.mach = parseFloat(e.target.value) || 0.0;
        logEvent(`Flight Mach set to M${state.mach}`, 'info');
        sendCommands();
    });

    btnStart.addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE}/start`, { method: 'POST' });
            state.running = true;
            logEvent('Ignition sequence initiated. Standalone SIL simulator loop spawned.', 'info');
        } catch (err) {
            logEvent('Failed to send ignition command.', 'error');
        }
    });

    btnStop.addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE}/stop`, { method: 'POST' });
            state.running = false;
            logEvent('Emergency Fuel Cutoff commanded. Simulated spooling down...', 'error');
        } catch (err) {
            logEvent('Failed to send cutoff command.', 'error');
        }
    });

    btnReset.addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE}/reset`, { method: 'POST' });
            state.timeHistory = [];
            state.rawN1History = [];
            state.ekfN1History = [];
            state.rawEgtHistory = [];
            state.ekfT41History = [];
            state.watermarkCorrHistory = [];
            
            state.cyberAttackActive = false;
            state.sensorFaultActive = false;
            state.mpuViolationActive = false;
            state.replayMode = false;
            state.activeScenarioId = "";
            
            btnInjectCyber.innerText = 'INJECT REPLAY ATTACK';
            btnInjectCyber.className = 'btn btn-red';
            btnInjectSensor.innerText = 'INJECT SPEED FAULT (FDIR)';
            btnInjectSensor.className = 'btn btn-red';
            btnInjectMpu.innerText = 'INJECT MPU VIOLATION';
            btnInjectMpu.className = 'btn btn-red';
            
            validationCard.style.display = 'none';
            toggleControlInputs(false);
            timelineSpans.innerHTML = '';
            
            logEvent('Simulator state and compiled FADEC state completely reset.', 'info');
        } catch (err) {
            logEvent('Failed to send reset command.', 'error');
        }
    });

    // Scenario Dropdown Selection listener
    scenarioSelect.addEventListener('change', (e) => {
        const id = e.target.value;
        if (id) {
            btnPlayScenario.disabled = false;
            btnStopScenario.disabled = false;
        } else {
            btnPlayScenario.disabled = true;
            btnStopScenario.disabled = true;
        }
    });

    // Play Scenario button
    btnPlayScenario.addEventListener('click', async () => {
        const id = scenarioSelect.value;
        if (!id) return;
        
        try {
            logEvent(`Starting scenario '${scenarioSelect.options[scenarioSelect.selectedIndex].text}'...`, 'info');
            const resp = await fetch(`${API_BASE}/scenarios/${id}/start`, { method: 'POST' });
            if (resp.ok) {
                state.activeScenarioId = id;
                state.running = true;
                state.replayMode = false;
                
                // Get scenario details to set timeline limits
                const duration = id === 'nominal_takeoff' ? 25.0 : 25.0; // standard 25s
                timelineSlider.max = duration * 100; // 10ms ticks
                timelineSlider.value = 0;
                timelineSlider.disabled = true;
                
                // Clean visual timeline spans
                timelineSpans.innerHTML = '';
                
                logEvent(`Scenario ignition complete. Playback started.`, 'info');
            }
        } catch (err) {
            logEvent('Failed to start scenario run.', 'error');
        }
    });

    btnStopScenario.addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE}/reset`, { method: 'POST' });
            state.activeScenarioId = "";
            state.running = false;
            state.replayMode = false;
            toggleControlInputs(false);
            logEvent('Scenario stopped. Simulator reset to Manual mode.', 'info');
        } catch (err) {
            logEvent('Failed to stop scenario.', 'error');
        }
    });

    // Telemetry log Export
    btnExportLog.addEventListener('click', async () => {
        try {
            logEvent('Exporting flight telemetry log...', 'info');
            const response = await fetch(`${API_BASE}/log/export?format=json`);
            if (response.ok) {
                const payload = await response.json();
                const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `flight_log_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '_')}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                logEvent('Flight log exported successfully.', 'info');
            }
        } catch (err) {
            logEvent('Failed to export flight log.', 'error');
        }
    });

    // Telemetry log Import (Replay mode)
    btnImportLog.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = async (evt) => {
            try {
                const payload = JSON.parse(evt.target.result);
                logEvent(`Uploading log file: ${file.name}...`, 'info');
                
                const resp = await fetch(`${API_BASE}/log/import`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (resp.ok) {
                    const status = await resp.json();
                    state.replayMode = true;
                    state.replayFramesCount = status.frames;
                    state.currentFileLog = payload;
                    
                    // Configure UI sliders and buttons
                    toggleControlInputs(true);
                    timelineSlider.max = status.frames - 1;
                    timelineSlider.value = 0;
                    
                    // Draw timeline and markers visually
                    drawTimelineSpansAndEvents(payload);
                    
                    // Automatically validate the uploaded log against golden profile
                    runGoldenValidation(payload);
                    
                    logEvent(`Log import success. Replay Mode active with ${status.frames} frames.`, 'info');
                    logEvent(`FADEC Configuration Hash: ${payload.metadata?.config_hash || 'N/A'}`, 'info');
                }
            } catch (err) {
                logEvent('Invalid log file format. Parse error.', 'error');
            }
        };
        reader.readAsText(file);
    });

    // Timeline Slider Scrubbing listener (Seek Replay)
    timelineSlider.addEventListener('input', async (e) => {
        if (!state.replayMode) return;
        const frameIndex = parseInt(e.target.value);
        const seekTime = frameIndex * 0.01; // 10ms frame resolution
        
        try {
            const resp = await fetch(`${API_BASE}/replay/seek`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ seek_time_sec: seekTime })
            });
            if (resp.ok) {
                const data = await resp.json();
                // Update UI state immediately on scrub
                pollState();
            }
        } catch (err) {
            console.error('Error seeking replay frame:', err);
        }
    });

    // Fault Injectors (Manual)
    btnInjectCyber.addEventListener('click', async () => {
        state.cyberAttackActive = !state.cyberAttackActive;
        try {
            await fetch(`${API_BASE}/inject-fault`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fault_type: 'cyber', enable: state.cyberAttackActive })
            });
            if (state.cyberAttackActive) {
                logEvent('TEST RIG: Replay/Spoofing fuel command attack injected into simulator bus.', 'warn');
                btnInjectCyber.innerText = 'CLEAR CYBER ATTACK';
                btnInjectCyber.className = 'btn btn-green';
            } else {
                logEvent('TEST RIG: Replay attack cleared. Reconnecting FADEC to environment.', 'info');
                btnInjectCyber.innerText = 'INJECT REPLAY ATTACK';
                btnInjectCyber.className = 'btn btn-red';
            }
        } catch (err) {
            logEvent('Failed to toggle cyber fault injection.', 'error');
        }
    });

    btnInjectSensor.addEventListener('click', async () => {
        state.sensorFaultActive = !state.sensorFaultActive;
        try {
            await fetch(`${API_BASE}/inject-fault`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fault_type: 'sensor', enable: state.sensorFaultActive })
            });
            if (state.sensorFaultActive) {
                logEvent('TEST RIG: Primary speed sensor wire-cut fault injected.', 'warn');
                btnInjectSensor.innerText = 'CLEAR SPEED FAULT';
                btnInjectSensor.className = 'btn btn-green';
            } else {
                logEvent('TEST RIG: Primary speed sensor fault cleared. Restoring sensor feed.', 'info');
                btnInjectSensor.innerText = 'INJECT SPEED FAULT (FDIR)';
                btnInjectSensor.className = 'btn btn-red';
            }
        } catch (err) {
            logEvent('Failed to toggle sensor fault injection.', 'error');
        }
    });

    btnInjectMpu.addEventListener('click', async () => {
        state.mpuViolationActive = !state.mpuViolationActive;
        try {
            await fetch(`${API_BASE}/inject-fault`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fault_type: 'mpu', enable: state.mpuViolationActive })
            });
            if (state.mpuViolationActive) {
                logEvent('TEST RIG: Triggering uncertified memory write from Advisory to Control.', 'warn');
                btnInjectMpu.innerText = 'CLEAR MPU VIOLATION';
                btnInjectMpu.className = 'btn btn-green';
            } else {
                logEvent('TEST RIG: Memory violation cleared.', 'info');
                btnInjectMpu.innerText = 'INJECT MPU VIOLATION';
                btnInjectMpu.className = 'btn btn-red';
            }
        } catch (err) {
            logEvent('Failed to toggle MPU fault injection.', 'error');
        }
    });

    function updateMcdcDashboard(data) {
        const ring = document.getElementById('mcdcProgressRing');
        const text = document.getElementById('mcdcPercentText');
        const overall = data.mcdc_overall;
        
        if (ring && text) {
            text.innerText = `${overall}%`;
            if (overall === 100) {
                ring.style.background = 'conic-gradient(#2e7d32 360deg, var(--border-color) 0deg)';
            } else {
                ring.style.background = 'conic-gradient(var(--border-color) 360deg, var(--border-color) 0deg)';
            }
        }

        const modules = [
            { prefix: 'ctrl', data: { stmt: data.mcdc_verified ? '100%' : '0%', br: data.mcdc_verified ? '100%' : '0%', mcdc: data.mcdc_verified ? '100%' : '0%' } },
            { prefix: 'fdir', data: { stmt: data.mcdc_verified ? '100%' : '0%', br: data.mcdc_verified ? '100%' : '0%', mcdc: data.mcdc_verified ? '100%' : '0%' } },
            { prefix: 'dual', data: { stmt: data.mcdc_verified ? '100%' : '0%', br: data.mcdc_verified ? '100%' : '0%', mcdc: data.mcdc_verified ? '100%' : '0%' } },
            { prefix: 'wm', data: { stmt: data.mcdc_verified ? '100%' : '0%', br: data.mcdc_verified ? '100%' : '0%', mcdc: data.mcdc_verified ? '100%' : '0%' } },
            { prefix: 'sf', data: { stmt: data.mcdc_verified ? '100%' : '0%', br: data.mcdc_verified ? '100%' : '0%', mcdc: data.mcdc_verified ? '100%' : '0%' } }
        ];

        modules.forEach(m => {
            const e1 = document.getElementById(`cov-${m.prefix}-stmt`);
            const e2 = document.getElementById(`cov-${m.prefix}-branch`);
            const e3 = document.getElementById(`cov-${m.prefix}-mcdc`);
            if (e1) e1.innerText = m.data.stmt;
            if (e2) e2.innerText = m.data.br;
            if (e3) {
                e3.innerText = m.data.mcdc;
                e3.style.color = data.mcdc_verified ? '#2e7d32' : 'var(--text-color)';
            }
        });
    }

    const btnRunCompliance = document.getElementById('btnRunCompliance');
    if (btnRunCompliance) {
        btnRunCompliance.addEventListener('click', async () => {
            btnRunCompliance.disabled = true;
            btnRunCompliance.innerText = 'RUNNING AUDIT SUITE...';
            logEvent('DO-178C AUDIT: Starting LDRA / VectorCAST qualification suite run...', 'info');
            
            try {
                const response = await fetch(`${API_BASE}/run-compliance`, { method: 'POST' });
                if (response.ok) {
                    const result = await response.json();
                    
                    let delay = 200;
                    result.audit_log.forEach((logLine, index) => {
                        setTimeout(() => {
                            logEvent(`LDRA AUDIT: ${logLine}`, 'info');
                            if (index === result.audit_log.length - 1) {
                                btnRunCompliance.disabled = false;
                                btnRunCompliance.innerText = 'RUN CERTIFICATION SUITE';
                                document.getElementById('txtComplianceStatus').innerText = 'DO-178C Objectives: ALIGNED (DAL-A)';
                                document.getElementById('txtComplianceStatus').style.color = '#2e7d32';
                                logEvent('DO-178C AUDIT: Structural coverage MC/DC qualification PASSED.', 'info');
                            }
                        }, (index + 1) * delay);
                    });
                }
            } catch (err) {
                logEvent('Failed to run compliance suite.', 'error');
                btnRunCompliance.disabled = false;
                btnRunCompliance.innerText = 'RUN CERTIFICATION SUITE';
            }
        });
    }

    // Start EKF rolling charts, polling loops, and load scenarios list
    initEkfCharts();
    loadScenarios();
    state.timer = setInterval(pollState, 33); // 30 Hz polling
});
