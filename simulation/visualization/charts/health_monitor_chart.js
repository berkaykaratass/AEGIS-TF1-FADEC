/**
 * @file health_monitor_chart.js
 * @brief Neuromorphic Multi-Sensor Health radar Visualizer
 * @details Implements a 5-axis radar chart showing power bands (Delta to Gamma)
 *          deviations against a calibrated healthy baseline profile.
 */

class HealthMonitorChart {
    constructor(radarCanvasId) {
        this.radarCtx = document.getElementById(radarCanvasId).getContext('2d');
        this.radarChart = null;
        
        this.initRadarChart();
    }

    initRadarChart() {
        const gridColor = 'rgba(0, 0, 0, 0.08)';
        const textColor = '#495057';

        this.radarChart = new Chart(this.radarCtx, {
            type: 'radar',
            data: {
                labels: [
                    'VIBRATION (Delta)',
                    'TEMPERATURE (Theta)',
                    'PRESSURE (Alpha)',
                    'HI-FREQ VIB (Beta)',
                    'ACOUSTIC (Gamma)'
                ],
                datasets: [
                    {
                        label: 'Calibrated Baseline',
                        data: [1.0, 1.0, 1.0, 1.0, 1.0],
                        borderColor: '#2e7d32',
                        borderWidth: 1.5,
                        backgroundColor: 'rgba(46, 125, 50, 0.05)',
                        pointRadius: 2
                    },
                    {
                        label: 'Active System State',
                        data: [1.0, 1.0, 1.0, 1.0, 1.0],
                        borderColor: '#e65100',
                        borderWidth: 2,
                        backgroundColor: 'rgba(230, 81, 0, 0.15)',
                        pointRadius: 3,
                        pointBackgroundColor: '#e65100'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        labels: { color: textColor, font: { size: 8 } }
                    },
                    title: {
                        display: true,
                        text: 'NEUROMORPHIC SENSOR HEALTH HARMONICS',
                        color: '#212529',
                        font: { size: 10, weight: 'bold' }
                    }
                },
                scales: {
                    r: {
                        angleLines: { color: gridColor },
                        grid: { color: gridColor },
                        pointLabels: { color: textColor, font: { size: 7, weight: '500' } },
                        ticks: { display: false },
                        suggestedMin: 0.0,
                        suggestedMax: 2.0
                    }
                }
            }
        });
    }

    update(activeBands, baselineBands) {
        this.radarChart.data.datasets[0].data = baselineBands;
        this.radarChart.data.datasets[1].data = activeBands;
        this.radarChart.update('none');
    }
}
