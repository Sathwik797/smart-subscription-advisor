document.addEventListener("DOMContentLoaded", function () {

    const chartCanvas = document.getElementById("categoryChart");

    if (!chartCanvas) {
        return;
    }

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
                }
            }
        }
    });

});
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
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

}
