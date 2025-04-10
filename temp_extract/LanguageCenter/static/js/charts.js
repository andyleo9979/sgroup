/**
 * Create a line chart
 * @param {string} canvasId - ID of the canvas element
 * @param {Array} labels - Array of labels for the x-axis
 * @param {Array} data - Array of data points for the y-axis
 * @param {string} label - Label for the dataset
 * @param {string} title - Title of the chart
 */
function createLineChart(canvasId, labels, data, label, title) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 2,
                tension: 0.3,
                pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#e0e0e0'
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: '#ffffff'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#e0e0e0'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: '#e0e0e0'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

/**
 * Create a doughnut chart
 * @param {string} canvasId - ID of the canvas element
 * @param {Array} labels - Array of labels
 * @param {Array} data - Array of data points
 * @param {string} title - Title of the chart
 */
function createDoughnutChart(canvasId, labels, data, title) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Generate colors for each segment
    const backgroundColors = [];
    for (let i = 0; i < data.length; i++) {
        const hue = (i * 137.5) % 360; // Use golden ratio to generate distinct colors
        backgroundColors.push(`hsla(${hue}, 70%, 60%, 0.8)`);
    }
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderColor: 'rgba(255, 255, 255, 0.8)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#e0e0e0',
                        padding: 15
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: '#ffffff'
                }
            }
        }
    });
}

/**
 * Create a bar chart
 * @param {string} canvasId - ID of the canvas element
 * @param {Array} labels - Array of labels for the x-axis
 * @param {Array} data - Array of data points for the y-axis
 * @param {string} label - Label for the dataset
 * @param {string} title - Title of the chart
 * @param {boolean} horizontal - Whether to display the chart horizontally
 */
function createBarChart(canvasId, labels, data, label, title, horizontal = false) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
        type: horizontal ? 'bar' : 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: horizontal ? 'y' : 'x',
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#e0e0e0'
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: '#ffffff'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#e0e0e0'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: '#e0e0e0'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

/**
 * Create a multi-dataset bar chart (for comparing multiple sets)
 * @param {string} canvasId - ID of the canvas element
 * @param {Array} labels - Array of labels for the x-axis
 * @param {Array} datasets - Array of dataset objects
 * @param {string} title - Title of the chart
 */
function createMultiBarChart(canvasId, labels, datasets, title) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Define a set of colors for the datasets
    const colors = [
        { backgroundColor: 'rgba(54, 162, 235, 0.5)', borderColor: 'rgba(54, 162, 235, 1)' },
        { backgroundColor: 'rgba(255, 99, 132, 0.5)', borderColor: 'rgba(255, 99, 132, 1)' },
        { backgroundColor: 'rgba(75, 192, 192, 0.5)', borderColor: 'rgba(75, 192, 192, 1)' },
        { backgroundColor: 'rgba(255, 159, 64, 0.5)', borderColor: 'rgba(255, 159, 64, 1)' },
        { backgroundColor: 'rgba(153, 102, 255, 0.5)', borderColor: 'rgba(153, 102, 255, 1)' }
    ];
    
    // Apply colors to datasets
    const chartDatasets = datasets.map((dataset, index) => {
        const colorIndex = index % colors.length;
        return {
            ...dataset,
            backgroundColor: colors[colorIndex].backgroundColor,
            borderColor: colors[colorIndex].borderColor,
            borderWidth: 1
        };
    });
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: chartDatasets
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#e0e0e0'
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: '#ffffff'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#e0e0e0'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: '#e0e0e0'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}
