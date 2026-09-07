/**
 * Smart Subscription Advisor - Settings Page Controller
 * Handles local persistence of notification/subscription preferences and save feedback.
 */
document.addEventListener('DOMContentLoaded', () => {
    const STORAGE_KEY = 'smartSubscriptionAdvisor.settings';

    // Controls
    const emailToggle = document.getElementById('toggleEmailNotif');
    const renewalToggle = document.getElementById('toggleRenewalReminders');
    const subInsightsToggle = document.getElementById('toggleSubInsights');
    const themeSelect = document.getElementById('themeSelect');
    const languageSelect = document.getElementById('languageSelect');
    const renewalWarningSelect = document.getElementById('renewalWarningSelect');
    const spendingInsightsToggle = document.getElementById('toggleSpendingInsights');
    const usageInsightsToggle = document.getElementById('toggleUsageInsights');
    const saveBtn = document.getElementById('saveSettingsBtn');
    const toast = document.getElementById('settingsToast');

    // Default configuration
    const defaults = {
        emailNotifications: true,
        renewalReminders: true,
        subscriptionInsights: true,
        theme: 'light',
        language: 'en-US',
        renewalWarning: '7',
        spendingInsights: true,
        usageInsights: true
    };

    /**
     * Load settings from localStorage
     */
    function loadSettings() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            const settings = stored ? { ...defaults, ...JSON.parse(stored) } : defaults;

            if (emailToggle) emailToggle.checked = settings.emailNotifications;
            if (renewalToggle) renewalToggle.checked = settings.renewalReminders;
            if (subInsightsToggle) subInsightsToggle.checked = settings.subscriptionInsights;
            if (themeSelect) themeSelect.value = settings.theme;
            if (languageSelect) languageSelect.value = settings.language;
            if (renewalWarningSelect) renewalWarningSelect.value = settings.renewalWarning;
            if (spendingInsightsToggle) spendingInsightsToggle.checked = settings.spendingInsights;
            if (usageInsightsToggle) usageInsightsToggle.checked = settings.usageInsights;
        } catch (err) {
            console.warn('Could not read settings from localStorage', err);
        }
    }

    /**
     * Collect current UI values
     */
    function getCurrentSettings() {
        return {
            emailNotifications: emailToggle ? emailToggle.checked : true,
            renewalReminders: renewalToggle ? renewalToggle.checked : true,
            subscriptionInsights: subInsightsToggle ? subInsightsToggle.checked : true,
            theme: themeSelect ? themeSelect.value : 'light',
            language: languageSelect ? languageSelect.value : 'en-US',
            renewalWarning: renewalWarningSelect ? renewalWarningSelect.value : '7',
            spendingInsights: spendingInsightsToggle ? spendingInsightsToggle.checked : true,
            usageInsights: usageInsightsToggle ? usageInsightsToggle.checked : true
        };
    }

    /**
     * Save settings to localStorage
     */
    function saveSettings(showFeedback = true) {
        try {
            const current = getCurrentSettings();
            localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
            if (showFeedback) {
                showToast('Settings saved successfully!');
            }
        } catch (err) {
            console.warn('Could not save settings to localStorage', err);
        }
    }

    /**
     * Show non-intrusive floating toast
     */
    let toastTimeout;
    function showToast(message) {
        if (!toast) return;
        const msgEl = document.getElementById('toastMsg');
        if (msgEl) msgEl.textContent = message;

        toast.classList.add('show');
        clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);

        if (saveBtn) {
            const originalHtml = saveBtn.innerHTML;
            saveBtn.classList.add('saved-feedback');
            saveBtn.innerHTML = '<i class="bi bi-check-lg"></i> <span>Saved!</span>';
            setTimeout(() => {
                saveBtn.classList.remove('saved-feedback');
                saveBtn.innerHTML = originalHtml;
            }, 2000);
        }
    }

    // Auto-save on any change
    const interactiveElements = [
        emailToggle,
        renewalToggle,
        subInsightsToggle,
        themeSelect,
        languageSelect,
        renewalWarningSelect,
        spendingInsightsToggle,
        usageInsightsToggle
    ];

    interactiveElements.forEach(el => {
        if (el) {
            el.addEventListener('change', () => {
                saveSettings(false);
            });
        }
    });

    // Save button click
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            saveSettings(true);
        });
    }

    // Initialize
    loadSettings();
});
