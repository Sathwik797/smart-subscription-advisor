document.addEventListener("DOMContentLoaded", function () {

    // 1. Spending by Category (Donut Chart)
    const chartCanvas = document.getElementById("categoryChart");

    if (chartCanvas && chartCanvas.style.display !== "none") {
        try {
            const labels = JSON.parse(chartCanvas.dataset.labels || "[]");
            const values = JSON.parse(chartCanvas.dataset.values || "[]");

            if (values && values.length > 0 && typeof Chart !== "undefined") {
                // Curated slate / stone monochromatic fintech tones
                const categoryPalette = [
                    "#2563EB", // Financial Blue
                    "#38BDF8", // Sky
                    "#F97316", // Amber / Orange
                    "#94A3B8", // Slate Muted
                    "#EF4444", // Coral
                    "#64748B", // Slate Dark
                    "#CBD5E1"  // Slate Light
                ];

                new Chart(chartCanvas, {
                    type: "doughnut",
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: categoryPalette.slice(0, Math.max(values.length, 1)),
                            borderColor: "#FFFFFF",
                            borderWidth: 2,
                            hoverOffset: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: "70%",
                        plugins: {
                            legend: {
                                position: "bottom",
                                labels: {
                                    boxWidth: 10,
                                    boxHeight: 10,
                                    padding: 14,
                                    usePointStyle: true,
                                    pointStyle: "circle",
                                    font: {
                                        family: "'Inter', sans-serif",
                                        size: 12,
                                        weight: "500"
                                    },
                                    color: "#475569"
                                }
                            },
                            tooltip: {
                                backgroundColor: "#0F172A",
                                padding: 10,
                                cornerRadius: 6,
                                titleFont: { family: "'Inter', sans-serif", size: 12, weight: "600" },
                                bodyFont: { family: "'Inter', sans-serif", size: 12, weight: "500" },
                                callbacks: {
                                    label: function (context) {
                                        const label = context.label || "";
                                        const val = context.parsed || 0;
                                        return ` ${label}: ₹${Number(val).toLocaleString("en-IN")}`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
        } catch (err) {
            console.warn("Category chart initialization skipped:", err);
        }
    }

    // 2. Monthly Spending Distribution / Trend (Bar Chart)
    const costCanvas = document.getElementById("costChart");

    if (costCanvas && costCanvas.style.display !== "none") {
        try {
            const labels = JSON.parse(costCanvas.dataset.labels || "[]");
            const values = JSON.parse(costCanvas.dataset.values || "[]");

            if (values && values.length > 0 && typeof Chart !== "undefined") {
                new Chart(costCanvas, {
                    type: "bar",
                    data: {
                        labels: labels,
                        datasets: [{
                            label: "Monthly Cost",
                            data: values,
                            backgroundColor: "#0F172A",
                            hoverBackgroundColor: "#1E293B",
                            borderRadius: 4,
                            borderSkipped: false,
                            maxBarThickness: 36
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
                                backgroundColor: "#0F172A",
                                padding: 10,
                                cornerRadius: 6,
                                titleFont: { family: "'Inter', sans-serif", size: 12, weight: "600" },
                                bodyFont: { family: "'Inter', sans-serif", size: 12, weight: "500" },
                                callbacks: {
                                    label: function (context) {
                                        return ` Monthly Cost: ₹${Number(context.raw || 0).toLocaleString("en-IN")}`;
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                grid: {
                                    display: false,
                                    drawBorder: false
                                },
                                ticks: {
                                    font: {
                                        family: "'Inter', sans-serif",
                                        size: 11,
                                        weight: "500"
                                    },
                                    color: "#64748B",
                                    maxRotation: 0,
                                    autoSkip: true,
                                    maxTicksLimit: 8
                                }
                            },
                            y: {
                                beginAtZero: true,
                                grid: {
                                    color: "#F1F5F9",
                                    drawBorder: false
                                },
                                ticks: {
                                    font: {
                                        family: "'Inter', sans-serif",
                                        size: 11,
                                        weight: "500"
                                    },
                                    color: "#64748B",
                                    callback: function (value) {
                                        return "₹" + Number(value).toLocaleString("en-IN");
                                    }
                                }
                            }
                        }
                    }
                });
            }
        } catch (err) {
            console.warn("Cost chart initialization skipped:", err);
        }
    }

    // 3. Live Formatted Date
    const target = document.getElementById("dashboardDate");
    if (target) {
        const today = new Date();
        target.textContent = today.toLocaleDateString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
            year: "numeric"
        });
    }

    // 4. Quick Action AI Recommendations & Sidebar AI Advisor Integration
    const quickActionAi = document.getElementById("quickActionAi");
    const sidebarAiAdvisor = document.getElementById("sidebarAiAdvisor");
    const chatbotLauncher = document.getElementById("chatbotLauncher");

    if (chatbotLauncher) {
        if (quickActionAi) {
            quickActionAi.addEventListener("click", function (e) {
                e.preventDefault();
                chatbotLauncher.click();
            });
        }
        if (sidebarAiAdvisor) {
            sidebarAiAdvisor.addEventListener("click", function (e) {
                e.preventDefault();
                chatbotLauncher.click();
            });
        }
    }
});
