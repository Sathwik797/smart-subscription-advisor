document.addEventListener("DOMContentLoaded", function () {

    const chartCanvas = document.getElementById("categoryChart");

    if (chartCanvas) {
        const labels = JSON.parse(chartCanvas.dataset.labels);
        const values = JSON.parse(chartCanvas.dataset.values);

        new Chart(chartCanvas, {
            type: "pie",
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        "#36A2EB",
                        "#FF6384",
                        "#FFCE56",
                        "#4BC0C0",
                        "#9966FF",
                        "#FF9F40"
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom"
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const val = context.parsed || 0;
                                return ` ${label}: ${typeof formatINR === 'function' ? formatINR(val) : '₹' + val}`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Monthly Cost by Subscription (Bar Chart)
    const costCanvas = document.getElementById("costChart");

    if (costCanvas) {
        const labels = JSON.parse(costCanvas.dataset.labels);
        const values = JSON.parse(costCanvas.dataset.values);

        new Chart(costCanvas, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Monthly Cost (₹)",
                    data: values,
                    backgroundColor: "#36A2EB"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` Cost: ${typeof formatINR === 'function' ? formatINR(context.raw) : '₹' + context.raw}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return typeof formatINR === 'function' ? formatINR(value) : '₹' + value;
                            }
                        }
                    }
                }
            }
        });
    }

    var date = new Date();
    var target = document.getElementById('dashboardDate');

    if (target) {
        target.textContent = date.toLocaleDateString(undefined, {
            weekday: 'long',
            month: 'short',
            day: 'numeric'
        });
    }
});
