/**
 * @file compressor_map_chart.js
 * @brief Compressor Performance Map Visualizer
 * @details Plots multiple corrected speed lines, the surge limit boundary line,
 *          and maps the current FADEC operating point in real time.
 */

class CompressorMapChart {
    constructor(canvasId) {
        this.ctx = document.getElementById(canvasId).getContext('2d');
        this.chart = null;
        
        this.speedLines = this.generateMapData();
        this.surgeLine = this.generateSurgeLineData();
        
        this.initChart();
    }

    generateMapData() {
        const speeds = [50, 60, 70, 80, 90, 100, 110];
        const surgeFlows = {50: 4.5, 60: 6.0, 70: 8.2, 80: 11.0, 90: 14.5, 100: 18.2, 110: 21.0};
        const surgePRs = {50: 2.2, 60: 3.1, 70: 4.5, 80: 6.8, 90: 10.5, 100: 15.2, 110: 19.5};
        
        const datasets = [];

        speeds.forEach(speed => {
            const flowSurge = surgeFlows[speed];
            const prSurge = surgePRs[speed];
            const points = [];

            for (let i = 0; i <= 10; i++) {
                const t = i / 10.0;
                const flow = flowSurge + (t * (flowSurge * 0.4));
                const pr = prSurge - (t * (prSurge * 0.3));
                points.push({ x: flow, y: pr });
            }

            datasets.push({
                label: `N_corr ${speed}%`,
                data: points,
                showLine: true,
                borderColor: 'rgba(73, 80, 87, 0.2)',
                borderWidth: 1.5,
                pointRadius: 0,
                fill: false
            });
        });

        return datasets;
    }

    generateSurgeLineData() {
        const speeds = [50, 60, 70, 80, 90, 100, 110];
        const surgeFlows = [4.5, 6.0, 8.2, 11.0, 14.5, 18.2, 21.0];
        const surgePRs = [2.2, 3.1, 4.5, 6.8, 10.5, 15.2, 19.5];
        
        const points = [];
        for (let i = 0; i < speeds.length; i++) {
            points.push({ x: surgeFlows[i], y: surgePRs[i] });
        }

        return {
            label: 'Surge Boundary Limit',
            data: points,
            showLine: true,
            borderColor: '#c62828',
            borderWidth: 2,
            borderDash: [6, 4],
            pointRadius: 2,
            pointBackgroundColor: '#c62828',
            fill: false
        };
    }

    initChart() {
        const datasets = [...this.speedLines, this.surgeLine];
        const labelColor = '#495057';
        const gridColor = 'rgba(0, 0, 0, 0.06)';
        
        datasets.push({
            label: 'Operating Point',
            data: [{ x: 12.0, y: 5.0 }],
            pointRadius: 8,
            pointHoverRadius: 10,
            pointBackgroundColor: '#2e7d32',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            showLine: false
        });

        this.chart = new Chart(this.ctx, {
            type: 'scatter',
            data: { datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'COMPRESSOR OPERATING ENVELOPE MAP',
                        color: '#212529',
                        font: { size: 10, weight: 'bold' }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Corrected Mass Flow Wc (kg/s)', color: labelColor, font: { size: 8 } },
                        grid: { color: gridColor },
                        ticks: { color: labelColor, font: { size: 8 } },
                        min: 2,
                        max: 32
                    },
                    y: {
                        title: { display: true, text: 'Total Pressure Ratio (PR)', color: labelColor, font: { size: 8 } },
                        grid: { color: gridColor },
                        ticks: { color: labelColor, font: { size: 8 } },
                        min: 1,
                        max: 22
                    }
                }
            }
        });
    }

    updateOperatingPoint(flow, pr, isSurgeActive) {
        const opDatasetIdx = this.chart.data.datasets.length - 1;
        this.chart.data.datasets[opDatasetIdx].data = [{ x: flow, y: pr }];
        
        if (isSurgeActive) {
            this.chart.data.datasets[opDatasetIdx].pointBackgroundColor = '#c62828';
            this.chart.data.datasets[opDatasetIdx].pointBorderColor = '#c62828';
        } else {
            this.chart.data.datasets[opDatasetIdx].pointBackgroundColor = '#2e7d32';
            this.chart.data.datasets[opDatasetIdx].pointBorderColor = '#fff';
        }

        this.chart.update('none');
    }
}
