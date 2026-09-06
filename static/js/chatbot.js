/**
 * Subscription Advisor Chatbot Frontend Client
 *
 * Lightweight, accessible, framework-free assistant integration.
 * Safe DOM rendering (zero raw innerHTML on dynamic text).
 */

(function () {
    "use strict";

    // -------------------------------------------------------------------------
    // Configuration & Page Suggestions
    // -------------------------------------------------------------------------
    const SUGGESTIONS = {
        dashboard: [
            "How much am I spending each month?",
            "What renews this week?",
            "Where can I save money?",
            "What's my most expensive subscription?",
        ],
        subscriptions: [
            "Show my most expensive subscriptions",
            "Which subscriptions renew soon?",
            "How much do I spend on entertainment?",
            "Help me reduce my monthly spending",
        ],
        default: [
            "How much am I spending each month?",
            "What renews this week?",
            "Where can I save money?",
            "Show my most expensive subscriptions",
        ],
    };

    const GREETING_TEXT =
        "Hi! I'm your Smart Subscription Advisor assistant. Ask me about your subscriptions, spending, renewals, or savings within this app.";

    // -------------------------------------------------------------------------
    // DOM Elements
    // -------------------------------------------------------------------------
    const launcher = document.getElementById("chatbotLauncher");
    const panel = document.getElementById("chatbotPanel");
    const closeBtn = document.getElementById("chatbotClose");
    const messagesContainer = document.getElementById("chatbotMessages");
    const suggestionsContainer = document.getElementById("chatbotSuggestions");
    const form = document.getElementById("chatbotForm");
    const input = document.getElementById("chatbotInput");
    const sendBtn = document.getElementById("chatbotSend");

    if (!launcher || !panel || !messagesContainer || !form || !input || !sendBtn) {
        return; // Elements not present on this page
    }

    // Determine current page context
    const pageContext = panel.getAttribute("data-page") || "dashboard";

    // State
    let isOpen = false;
    let isLoading = false;
    let initialized = false;

    // -------------------------------------------------------------------------
    // Helpers: Safe DOM Building
    // -------------------------------------------------------------------------
    function getCurrentTimeFormatted() {
        try {
            const now = new Date();
            return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        } catch (_) {
            return "";
        }
    }

    function createMessageElement(sender, text, isError = false) {
        const msgWrapper = document.createElement("div");
        msgWrapper.className = `chatbot-msg chatbot-msg--${sender}${isError ? " chatbot-msg--error" : ""}`;

        const bubble = document.createElement("div");
        bubble.className = "chatbot-bubble";
        bubble.textContent = text; // Safe text rendering — never innerHTML

        const timeSpan = document.createElement("span");
        timeSpan.className = "chatbot-msg-time";
        timeSpan.textContent = getCurrentTimeFormatted();

        msgWrapper.appendChild(bubble);
        msgWrapper.appendChild(timeSpan);

        return msgWrapper;
    }

    function createTypingIndicator() {
        const typingWrapper = document.createElement("div");
        typingWrapper.id = "chatbotTyping";
        typingWrapper.className = "chatbot-msg chatbot-msg--assistant";

        const typingBubble = document.createElement("div");
        typingBubble.className = "chatbot-typing";

        const label = document.createElement("span");
        label.textContent = "Thinking";

        const dots = document.createElement("div");
        dots.className = "chatbot-typing-dots";
        for (let i = 0; i < 3; i++) {
            dots.appendChild(document.createElement("span"));
        }

        typingBubble.appendChild(label);
        typingBubble.appendChild(dots);
        typingWrapper.appendChild(typingBubble);

        return typingWrapper;
    }

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    function addMessage(sender, text, isError = false) {
        const el = createMessageElement(sender, text, isError);
        messagesContainer.appendChild(el);
        scrollToBottom();
    }

    // -------------------------------------------------------------------------
    // Suggestions Rendering
    // -------------------------------------------------------------------------
    function renderSuggestions() {
        if (!suggestionsContainer) return;
        suggestionsContainer.replaceChildren(); // Clear existing

        const chips = SUGGESTIONS[pageContext] || SUGGESTIONS.default;

        chips.forEach(function (text) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "chatbot-chip";
            btn.textContent = text;
            btn.addEventListener("click", function () {
                if (isLoading) return;
                sendMessage(text);
            });
            suggestionsContainer.appendChild(btn);
        });
    }

    function hideSuggestions() {
        if (suggestionsContainer) {
            suggestionsContainer.style.display = "none";
        }
    }

    // -------------------------------------------------------------------------
    // Open / Close Panel
    // -------------------------------------------------------------------------
    function openPanel() {
        if (isOpen) return;
        isOpen = true;
        panel.classList.add("is-open");
        panel.setAttribute("aria-hidden", "false");
        launcher.classList.add("is-active");
        launcher.setAttribute("aria-expanded", "true");
        launcher.setAttribute("aria-label", "Close Smart Subscription Advisor");

        if (!initialized) {
            // Render initial greeting and suggestion chips on first open
            addMessage("assistant", GREETING_TEXT);
            renderSuggestions();
            initialized = true;
        }

        // Focus input after CSS animation
        setTimeout(function () {
            input.focus();
            scrollToBottom();
        }, 120);
    }

    function closePanel() {
        if (!isOpen) return;
        isOpen = false;
        panel.classList.remove("is-open");
        panel.setAttribute("aria-hidden", "true");
        launcher.classList.remove("is-active");
        launcher.setAttribute("aria-expanded", "false");
        launcher.setAttribute("aria-label", "Open Smart Subscription Advisor");
        launcher.focus();
    }

    function togglePanel() {
        if (isOpen) {
            closePanel();
        } else {
            openPanel();
        }
    }

    // -------------------------------------------------------------------------
    // API Communication & Message Dispatch
    // -------------------------------------------------------------------------
    async function sendMessage(text) {
        const query = (text || input.value || "").trim();
        if (!query || isLoading) return;

        // Reset input UI
        input.value = "";
        input.style.height = "auto";
        sendBtn.disabled = true;

        // Display user message
        addMessage("user", query);
        hideSuggestions();

        // Show typing indicator
        isLoading = true;
        input.disabled = true;
        const typingEl = createTypingIndicator();
        messagesContainer.appendChild(typingEl);
        scrollToBottom();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    message: query,
                    page: pageContext,
                }),
            });

            // Remove typing indicator
            const existingTyping = document.getElementById("chatbotTyping");
            if (existingTyping) {
                existingTyping.remove();
            }

            if (response.status === 401) {
                addMessage("assistant", "Your session has expired. Please sign in again.", true);
            } else if (response.status === 400) {
                const errData = await response.json().catch(function () { return {}; });
                addMessage("assistant", errData.message || "Please enter a valid question.", true);
            } else if (response.status === 503) {
                addMessage("assistant", "I'm having trouble connecting right now. Please try again.", true);
            } else if (!response.ok) {
                addMessage("assistant", "I'm having trouble retrieving your subscription details. Please try again.", true);
            } else {
                const data = await response.json();
                if (data && data.success && data.data && typeof data.data.response === "string") {
                    addMessage("assistant", data.data.response);
                } else {
                    addMessage("assistant", "I couldn't process that response. Please try again.", true);
                }
            }
        } catch (err) {
            // Remove typing indicator on network error
            const existingTyping = document.getElementById("chatbotTyping");
            if (existingTyping) {
                existingTyping.remove();
            }
            addMessage("assistant", "I couldn't reach the assistant. Please check your connection and try again.", true);
        } finally {
            isLoading = false;
            input.disabled = false;
            input.focus();
            scrollToBottom();
        }
    }

    // -------------------------------------------------------------------------
    // Event Listeners
    // -------------------------------------------------------------------------
    launcher.addEventListener("click", togglePanel);
    if (closeBtn) {
        closeBtn.addEventListener("click", closePanel);
    }

    // Keyboard accessibility: Escape key closes panel
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && isOpen) {
            closePanel();
        }
    });

    // Form submission
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        sendMessage();
    });

    // Input interaction & auto-grow
    input.addEventListener("input", function () {
        const val = input.value.trim();
        sendBtn.disabled = val.length === 0 || isLoading;

        // Auto-expand textarea up to 80px
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 80) + "px";
    });

    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled && !isLoading) {
                sendMessage();
            }
        }
    });
})();
