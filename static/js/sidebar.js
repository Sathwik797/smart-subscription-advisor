/**
 * Global Authenticated Sidebar Navigation Controller
 * Handles expand/collapse toggle, localStorage persistence, and tooltips
 */

(function () {
    const STORAGE_KEY = "smartSubscriptionAdvisor.sidebarCollapsed";

    // Fast-apply stored state immediately if DOM already has body
    function applySavedState() {
        try {
            const isCollapsedSaved = localStorage.getItem(STORAGE_KEY);
            // Default to collapsed unless explicitly set to 'false'
            if (isCollapsedSaved === "false") {
                document.documentElement.classList.add("sidebar-expanded");
                if (document.body) {
                    document.body.classList.add("sidebar-expanded");
                }
            } else {
                document.documentElement.classList.remove("sidebar-expanded");
                if (document.body) {
                    document.body.classList.remove("sidebar-expanded");
                }
            }
        } catch (e) {
            // Fallback gracefully if localStorage is restricted
        }
    }

    applySavedState();

    document.addEventListener("DOMContentLoaded", function () {
        applySavedState();

        const sidebarToggle = document.getElementById("sidebarToggle");
        const appSidebar = document.getElementById("appSidebar");
        const sidebarAiAdvisor = document.getElementById("sidebarAiAdvisor");

        function updateToggleAttributes(isExpanded) {
            if (sidebarToggle) {
                sidebarToggle.setAttribute("aria-expanded", isExpanded ? "true" : "false");
                sidebarToggle.setAttribute(
                    "title",
                    isExpanded ? "Collapse navigation" : "Expand navigation"
                );
                sidebarToggle.setAttribute(
                    "aria-label",
                    isExpanded ? "Collapse navigation" : "Expand navigation"
                );
            }
        }

        const isCurrentlyExpanded = document.body.classList.contains("sidebar-expanded");
        updateToggleAttributes(isCurrentlyExpanded);

        if (sidebarToggle) {
            sidebarToggle.addEventListener("click", function (e) {
                e.preventDefault();
                const willExpand = !document.body.classList.contains("sidebar-expanded");

                if (willExpand) {
                    document.body.classList.add("sidebar-expanded");
                    document.documentElement.classList.add("sidebar-expanded");
                    try {
                        localStorage.setItem(STORAGE_KEY, "false");
                    } catch (err) {}
                } else {
                    document.body.classList.remove("sidebar-expanded");
                    document.documentElement.classList.remove("sidebar-expanded");
                    try {
                        localStorage.setItem(STORAGE_KEY, "true");
                    } catch (err) {}
                }

                updateToggleAttributes(willExpand);
            });
        }

        // Recommendations / AI Advisor Click Handler -> invokes existing chatbot
        if (sidebarAiAdvisor) {
            sidebarAiAdvisor.addEventListener("click", function (e) {
                e.preventDefault();
                const chatbotLauncher = document.getElementById("chatbotLauncher");
                if (chatbotLauncher) {
                    chatbotLauncher.click();
                }
            });
        }
    });
})();
