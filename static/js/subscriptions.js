/**
 * Subscriptions Management Workspace JavaScript
 * Client interactions, search/filter behaviors, and AI Advisor launcher
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. AI Advisor Launcher Integration
    const btnAskAiAdvisor = document.getElementById("btnAskAiAdvisor");
    const sidebarAiAdvisor = document.getElementById("sidebarAiAdvisor");
    const chatbotLauncher = document.getElementById("chatbotLauncher");

    if (chatbotLauncher) {
        if (btnAskAiAdvisor) {
            btnAskAiAdvisor.addEventListener("click", function (e) {
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

    // 2. Search Field Keyup / Enter handler
    const searchField = document.querySelector(".filter-search-field");
    const filterForm = document.getElementById("subscriptionFilterForm");

    if (searchField && filterForm) {
        let debounceTimer = null;
        searchField.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                filterForm.submit();
            }
        });

        searchField.addEventListener("input", function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                filterForm.submit();
            }, 600);
        });
    }

    // 3. View More Tips Handler
    const viewMoreTipsBtn = document.getElementById("viewMoreTipsBtn");
    if (viewMoreTipsBtn && chatbotLauncher) {
        viewMoreTipsBtn.addEventListener("click", function (e) {
            e.preventDefault();
            chatbotLauncher.click();
        });
    }
});
