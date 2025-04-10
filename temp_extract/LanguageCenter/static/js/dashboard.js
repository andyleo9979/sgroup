document.addEventListener('DOMContentLoaded', function() {
    // Initialize revenue chart if the canvas element exists
    const revenueChartEl = document.getElementById('revenueChart');
    if (revenueChartEl) {
        renderRevenueChart();
    }
    
    // Initialize course enrollments chart if the canvas element exists
    const enrollmentChartEl = document.getElementById('enrollmentChart');
    if (enrollmentChartEl) {
        renderEnrollmentChart();
    }
});

/**
 * Renders the monthly revenue chart
 */
function renderRevenueChart() {
    const revenueChartEl = document.getElementById('revenueChart');
    const revenueData = JSON.parse(revenueChartEl.getAttribute('data-revenue'));
    
    const months = revenueData.map(item => item.month);
    const revenues = revenueData.map(item => item.revenue);
    
    const revenueChart = new Chart(revenueChartEl, {
        type: 'bar',
        data: {
            labels: months,
            datasets: [{
                label: 'Monthly Revenue',
                data: revenues,
                backgroundColor: 'rgba(75, 192, 192, 0.5)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
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
                    text: 'Monthly Revenue (Last 6 Months)',
                    color: '#ffffff'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#e0e0e0',
                        callback: function(value) {
                            return '$' + value;
                        }
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
 * Renders the course enrollment distribution chart
 */
function renderEnrollmentChart() {
    const enrollmentChartEl = document.getElementById('enrollmentChart');
    const enrollmentData = JSON.parse(enrollmentChartEl.getAttribute('data-enrollments'));
    
    const courses = enrollmentData.map(item => item.course);
    const students = enrollmentData.map(item => item.students);
    
    // Generate an array of colors for the chart
    const backgroundColors = generateRandomColors(courses.length);
    
    const enrollmentChart = new Chart(enrollmentChartEl, {
        type: 'doughnut',
        data: {
            labels: courses,
            datasets: [{
                label: 'Student Enrollments',
                data: students,
                backgroundColor: backgroundColors,
                borderColor: 'rgba(255, 255, 255, 0.8)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e0e0e0',
                        padding: 15
                    }
                },
                title: {
                    display: true,
                    text: 'Course Enrollment Distribution',
                    color: '#ffffff'
                }
            }
        }
    });
}

/**
 * Generates random colors for chart segments
 * @param {number} count - Number of colors to generate
 * @returns {Array} Array of rgba color strings
 */
function generateRandomColors(count) {
    const predefinedColors = [
        'rgba(75, 192, 192, 0.8)',    // Teal
        'rgba(54, 162, 235, 0.8)',    // Blue
        'rgba(153, 102, 255, 0.8)',   // Purple
        'rgba(255, 159, 64, 0.8)',    // Orange
        'rgba(255, 99, 132, 0.8)',    // Red
        'rgba(255, 205, 86, 0.8)',    // Yellow
        'rgba(201, 203, 207, 0.8)',   // Grey
        'rgba(75, 255, 192, 0.8)',    // Mint
        'rgba(255, 99, 255, 0.8)',    // Pink
        'rgba(138, 43, 226, 0.8)'     // BlueViolet
    ];
    
    // Use predefined colors first, then generate random ones if needed
    const colors = [];
    for (let i = 0; i < count; i++) {
        if (i < predefinedColors.length) {
            colors.push(predefinedColors[i]);
        } else {
            // Generate a random color if we run out of predefined ones
            const r = Math.floor(Math.random() * 255);
            const g = Math.floor(Math.random() * 255);
            const b = Math.floor(Math.random() * 255);
            colors.push(`rgba(${r}, ${g}, ${b}, 0.8)`);
        }
    }
    
    return colors;
}

/**
 * Function to refresh notification count
 */
function refreshNotificationCount() {
    fetch('/notifications/count')
        .then(response => response.json())
        .then(data => {
            const notificationBadge = document.getElementById('notification-badge');
            if (notificationBadge) {
                if (data.count > 0) {
                    notificationBadge.textContent = data.count;
                    notificationBadge.classList.remove('d-none');
                } else {
                    notificationBadge.classList.add('d-none');
                }
            }
        })
        .catch(error => console.error('Error fetching notification count:', error));
}

// Refresh notification count every 60 seconds
setInterval(refreshNotificationCount, 60000);
