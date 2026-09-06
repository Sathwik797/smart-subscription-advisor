/**
 * Spending Analytics JavaScript
 * Real data rendering, Chart.js integrations, and Monthly/Yearly toggle
 */

document.addEventListener("DOMContentLoaded", function () {
    const data = window.ANALYTICS_DATA || {};
    let categoryChartInstance = null;
    let trendChartInstance = null;
    let billingChartInstance = null;
    let currentView = "monthly"; // "monthly" or "yearly"

    function formatINR(val) {
        return Number(val || 0).toLocaleString("en-IN", {
            maximumFractionDigits: 0
        });
    }

    // -------------------------------------------------------------------------
    // 1. Monthly Spending Trend Chart
    // -------------------------------------------------------------------------
    const trendCanvas = document.getElementById("trendChart");
    if (trendCanvas && typeof Chart !== "undefined") {
        try {
            const months = data.trendMonths || [];
            const values = data.trendValuesMonthly || [];

            if (months.length > 0 && values.length > 0) {
                const ctx = trendCanvas.getContext("2d");
                trendChartInstance = new Chart(ctx, {
                    type: "bar",
                    data: {
                        labels: months,
                        datasets: [{
                            label: "Total Spend",
                            data: values,
                            backgroundColor: "#60A5FA",
                            hoverBackgroundColor: "#3B82F6",
                            borderRadius: 6,
                            borderSkipped: false,
                            barThickness: 32,
                            maxBarThickness: 44
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
                                titleFont: { family: "'Inter', sans-serif", size: 12, weight: "600" },
                                bodyFont: { family: "'Inter', sans-serif", size: 12 },
                                padding: 10,
                                cornerRadius: 6,
                                displayColors: false,
                                callbacks: {
                                    label: function (context) {
                                        return "₹" + formatINR(context.raw);
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
                                    font: { family: "'Inter', sans-serif", size: 11, weight: "500" },
                                    color: "#64748B"
                                }
                            },
                            y: {
                                beginAtZero: true,
                                border: {
                                    display: false
                                },
                                grid: {
                                    color: "#F1F5F9",
                                    drawBorder: false
                                },
                                ticks: {
                                    font: { family: "'Inter', sans-serif", size: 11 },
                                    color: "#94A3B8",
                                    callback: function (val) {
                                        return "₹" + formatINR(val);
                                    }
                                }
                            }
                        }
                    }
                });
            }
        } catch (err) {
            console.warn("Trend chart initialization skipped:", err);
        }
    }

    // -------------------------------------------------------------------------
    // 2. Spending by Category Donut Chart
    // -------------------------------------------------------------------------
    const categoryCanvas = document.getElementById("categoryChart");
    if (categoryCanvas && typeof Chart !== "undefined") {
        try {
            const categories = data.categoriesData || [];
            if (categories.length > 0) {
                const labels = categories.map(c => c.name);
                const values = categories.map(c => c.monthly_amount);
                const colors = categories.map(c => c.color);

                const ctx = categoryCanvas.getContext("2d");
                categoryChartInstance = new Chart(ctx, {
                    type: "doughnut",
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: colors,
                            borderColor: "#FFFFFF",
                            borderWidth: 2,
                            hoverOffset: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: "74%",
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                backgroundColor: "#0F172A",
                                padding: 10,
                                cornerRadius: 6,
                                callbacks: {
                                    label: function (context) {
                                        const cat = categories[context.dataIndex];
                                        return " ₹" + formatINR(context.raw) + " (" + (cat.percentage || 0) + "%)";
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

    // -------------------------------------------------------------------------
    // 3. Billing Cycle Analysis Donut Chart
    // -------------------------------------------------------------------------
    const billingCanvas = document.getElementById("billingChart");
    if (billingCanvas && typeof Chart !== "undefined") {
        try {
            const cycles = data.billingCycles || [];
            if (cycles.length > 0) {
                const labels = cycles.map(c => c.cycle);
                const values = cycles.map(c => c.count);
                const colors = cycles.map(c => c.color);

                const ctx = billingCanvas.getContext("2d");
                billingChartInstance = new Chart(ctx, {
                    type: "doughnut",
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: colors,
                            borderColor: "#FFFFFF",
                            borderWidth: 2,
                            hoverOffset: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: "74%",
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                backgroundColor: "#0F172A",
                                padding: 8,
                                cornerRadius: 6,
                                callbacks: {
                                    label: function (context) {
                                        const c = cycles[context.dataIndex];
                                        return " " + context.label + ": " + context.raw + " (" + (c.percentage || 0) + "%)";
                                    }
                                }
                            }
                        }
                    }
                });
            }
        } catch (err) {
            console.warn("Billing cycle chart initialization skipped:", err);
        }
    }

    // -------------------------------------------------------------------------
    // 4. Monthly / Yearly Analysis Switcher
    // -------------------------------------------------------------------------
    const btnMonthly = document.getElementById("btnViewMonthly");
    const btnYearly = document.getElementById("btnViewYearly");

    const kpiLabelSpend = document.getElementById("kpiLabelSpend");
    const kpiSpendValue = document.getElementById("kpiSpendValue");
    const kpiLabelAvg = document.getElementById("kpiLabelAvg");
    const kpiAvgValue = document.getElementById("kpiAvgValue");
    const kpiLabelSavings = document.getElementById("kpiLabelSavings");
    const kpiSavingsValue = document.getElementById("kpiSavingsValue");

    const catCenterTotal = document.getElementById("catCenterTotal");
    const catCenterLabel = document.getElementById("catCenterLabel");
    const thCostHeader = document.getElementById("thCostHeader");

    function setView(view) {
        currentView = view;
        const isMonthly = view === "monthly";

        if (btnMonthly && btnYearly) {
            btnMonthly.classList.toggle("active", isMonthly);
            btnYearly.classList.toggle("active", !isMonthly);
        }

        // Update KPI 1 (Current Spend)
        if (kpiLabelSpend && kpiSpendValue) {
            kpiLabelSpend.textContent = isMonthly ? "Current Monthly Spend" : "Projected Annual Spend";
            kpiSpendValue.textContent = formatINR(isMonthly ? data.totalMonthly : data.totalYearly);
        }

        // Update KPI 3 (Average Spend)
        if (kpiLabelAvg && kpiAvgValue) {
            kpiLabelAvg.textContent = isMonthly ? "Average Monthly Spend" : "Average Annual Spend";
            kpiAvgValue.textContent = formatINR(isMonthly ? data.avgMonthly : data.avgYearly);
        }

        // Update KPI 4 (Potential Savings)
        if (kpiLabelSavings && kpiSavingsValue) {
            kpiLabelSavings.textContent = isMonthly ? "Potential Monthly Savings" : "Potential Annual Savings";
            kpiSavingsValue.textContent = formatINR(isMonthly ? data.potentialMonthlySavings : data.potentialYearlySavings);
        }

        // Update Category Donut Center
        if (catCenterTotal && catCenterLabel) {
            catCenterTotal.textContent = "₹" + formatINR(isMonthly ? data.totalMonthly : data.totalYearly);
            catCenterLabel.textContent = isMonthly ? "Monthly Spend" : "Yearly Spend";
        }

        // Update Category Legend amounts
        const catAmountBoxes = document.querySelectorAll(".cat-amount-box");
        catAmountBoxes.forEach(box => {
            const val = isMonthly ? box.getAttribute("data-monthly-val") : box.getAttribute("data-yearly-val");
            box.textContent = "₹" + formatINR(val);
        });

        // Update Category Donut Chart
        if (categoryChartInstance && data.categoriesData) {
            const newValues = data.categoriesData.map(c => isMonthly ? c.monthly_amount : c.yearly_amount);
            categoryChartInstance.data.datasets[0].data = newValues;
            categoryChartInstance.update();
        }

        // Update Top Subscriptions table
        if (thCostHeader) {
            thCostHeader.textContent = isMonthly ? "Monthly Cost" : "Annual Cost";
        }
        const subRows = document.querySelectorAll(".sub-table-row");
        subRows.forEach(row => {
            const costCell = row.querySelector(".sub-cost-cell");
            if (costCell) {
                const val = isMonthly ? row.getAttribute("data-monthly") : row.getAttribute("data-yearly");
                costCell.textContent = "₹" + formatINR(val);
            }
        });
    }

    if (btnMonthly && btnYearly) {
        btnMonthly.addEventListener("click", () => setView("monthly"));
        btnYearly.addEventListener("click", () => setView("yearly"));
    }

    // -------------------------------------------------------------------------
    // 5. Sidebar AI Advisor & Chatbot Launcher Trigger
    // -------------------------------------------------------------------------
    const sidebarAiAdvisor = document.getElementById("sidebarAiAdvisor");
    const chatbotLauncher = document.getElementById("chatbotLauncher");

    if (sidebarAiAdvisor && chatbotLauncher) {
        sidebarAiAdvisor.addEventListener("click", function (e) {
            e.preventDefault();
            chatbotLauncher.click();
        });
    }
});
