/**
 * @file brayton_chart.js
 * @brief T-s and P-v Thermodynamic Chart Controllers
 * @details Implements dynamic plotting of Brayton Cycle curves using Chart.js CDNs.
 */

class BraytonChart {
    constructor(tsCanvasId, pvCanvasId) {
        this.tsCtx = document.getElementById(tsCanvasId).getContext('2d');
        this.pvCtx = document.getElementById(pvCanvasId).getContext('2d');
        
        this.tsChart = null;
        this.pvChart = null;
        
        this.initCharts();
    }

    initCharts() {
        const gridColor = 'rgba(0, 0, 0, 0.06)';
        const titleColor = '#212529';
        const labelColor = '#495057';

        // 1. T-s Diagram Initialization
        this.tsChart = new Chart(this.tsCtx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Thermodynamic Path',
                    data: [],
                    showLine: true,
                    borderColor: '#0f4c81',
                    borderWidth: 2,
                    backgroundColor: 'rgba(15, 76, 129, 0.1)',
                    pointRadius: 4,
                    pointBackgroundColor: '#0f4c81'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'T-s DIAGRAM (TOTAL)',
                        color: titleColor,
                        font: { size: 10, weight: 'bold' }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Entropy s (J/kg*K)', color: labelColor, font: { size: 8 } },
                        grid: { color: gridColor },
                        ticks: { color: labelColor, font: { size: 8 } }
                    },
                    y: {
                        title: { display: true, text: 'Temp T (K)', color: labelColor, font: { size: 8 } },
                        grid: { color: gridColor },
                        ticks: { color: labelColor, font: { size: 8 } }
                    }
                }
            }
        });

        // 2. P-v Diagram Initialization
        this.pvChart = new Chart(this.pvCtx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Pressure Path',
                    data: [],
                    showLine: true,
                    borderColor: '#e65100',
                    borderWidth: 2,
                    backgroundColor: 'rgba(230, 81, 0, 0.1)',
                    pointRadius: 4,
                    pointBackgroundColor: '#e65100'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'P-v DIAGRAM (TOTAL)',
                        color: titleColor,
                        font: { size: 10, weight: 'bold' }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Vol v (m^3/kg)', color: labelColor, font: { size: 8 } },
                        grid: { color: gridColor },
                        ticks: { color: labelColor, font: { size: 8 } }
                    },
                    y: {
                        title: { display: true, text: 'Press P (kPa)', color: labelColor, font: { size: 8 } },
                        grid: { color: gridColor },
                        ticks: { color: labelColor, font: { size: 8 } }
                    }
                }
            }
        });
    }

    update(temperatures, pressures, entropies, volumes) {
        const tsData = [];
        const pvData = [];

        for (let i = 0; i < temperatures.length; i++) {
            tsData.push({ x: entropies[i], y: temperatures[i] });
            pvData.push({ x: volumes[i], y: pressures[i] / 1000.0 });
        }

        if (tsData.length > 0) {
            tsData.push({ x: tsData[0].x, y: tsData[0].y });
            pvData.push({ x: pvData[0].x, y: pvData[0].y });
        }

        this.tsChart.data.datasets[0].data = tsData;
        this.pvChart.data.datasets[0].data = pvData;

        this.tsChart.update('none');
        this.pvChart.update('none');
    }
}
