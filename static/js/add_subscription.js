/**
 * Smart Subscription Advisor - Add Subscription Enhancement
 * Implements smart service autocomplete, service logo preview,
 * automatic category mapping, and keyboard navigation.
 */
document.addEventListener("DOMContentLoaded", function () {

    // 1. Initialize Flatpickr for Date Inputs
    if (typeof flatpickr !== "undefined") {
        flatpickr("input[type='date']", {
            dateFormat: "Y-m-d",
            allowInput: false,
            clickOpens: true,
            disableMobile: true,
            defaultDate: "today"
        });
    }

    // 2. Service Metadata Catalog
    const POPULAR_SERVICES = [
        {
            name: "Netflix",
            category: "Entertainment",
            aliases: ["netflix", "net", "nfx", "streaming", "movies", "shows"],
            logoUrl: "/static/assets/logos/subscriptions/netflix.svg",
            popularity: 100
        },
        {
            name: "Spotify",
            category: "Entertainment",
            aliases: ["spotify", "spot", "music", "podcast", "songs"],
            logoUrl: "/static/assets/logos/subscriptions/spotify.svg",
            popularity: 95
        },
        {
            name: "YouTube Premium",
            category: "Entertainment",
            aliases: ["youtube", "youtube premium", "yt", "yt premium", "videos", "google youtube"],
            logoUrl: "/static/assets/logos/subscriptions/youtube.svg",
            popularity: 90
        },
        {
            name: "Amazon Prime",
            category: "Shopping",
            aliases: ["amazon", "amazon prime", "prime", "prime video", "shopping", "delivery"],
            logoUrl: "/static/assets/logos/subscriptions/amazon.svg",
            popularity: 88
        },
        {
            name: "Microsoft 365",
            category: "Productivity",
            aliases: ["microsoft", "microsoft 365", "m365", "office", "office 365", "msft", "word", "excel"],
            logoUrl: "/static/assets/logos/subscriptions/microsoft365.svg",
            popularity: 85
        },
        {
            name: "Canva",
            category: "Productivity",
            aliases: ["canva", "canva pro", "design", "graphic design", "templates"],
            logoUrl: "/static/assets/logos/subscriptions/canva.svg",
            popularity: 82
        },
        {
            name: "ChatGPT",
            category: "Productivity",
            aliases: ["chatgpt", "chat gpt", "openai", "chatgpt plus", "gpt", "ai", "llm"],
            logoUrl: "/static/assets/logos/subscriptions/chatgpt.svg",
            popularity: 84
        },
        {
            name: "Disney+",
            category: "Entertainment",
            aliases: ["disney", "disney+", "disney plus", "hotstar", "marvel", "pixar"],
            logoUrl: "/static/assets/logos/subscriptions/disneyplus.svg",
            popularity: 78
        },
        {
            name: "Apple Music",
            category: "Music",
            aliases: ["apple music", "apple", "itunes", "music", "songs"],
            logoUrl: "/static/assets/logos/subscriptions/applemusic.svg",
            popularity: 76
        },
        {
            name: "Adobe Creative Cloud",
            category: "Productivity",
            aliases: ["adobe", "adobe creative cloud", "photoshop", "illustrator", "premiere", "creative cloud", "cc"],
            logoUrl: "/static/assets/logos/subscriptions/adobe.svg",
            popularity: 74
        },
        {
            name: "Google One",
            category: "Utilities",
            aliases: ["google one", "google", "google drive", "gdrive", "storage", "cloud storage"],
            logoUrl: "/static/assets/logos/subscriptions/googleone.svg",
            popularity: 72
        },
        {
            name: "Dropbox",
            category: "Utilities",
            aliases: ["dropbox", "drop box", "cloud storage", "backup", "files"],
            logoUrl: "/static/assets/logos/subscriptions/dropbox.svg",
            popularity: 68
        },
        {
            name: "Notion",
            category: "Productivity",
            aliases: ["notion", "notes", "workspace", "wiki", "docs"],
            logoUrl: "/static/assets/logos/subscriptions/notion.svg",
            popularity: 70
        },
        {
            name: "Grammarly",
            category: "Productivity",
            aliases: ["grammarly", "writing", "spell check", "grammar"],
            logoUrl: "/static/assets/logos/subscriptions/grammarly.svg",
            popularity: 65
        },
        {
            name: "LinkedIn Premium",
            category: "Productivity",
            aliases: ["linkedin", "linkedin premium", "jobs", "networking", "in"],
            logoUrl: "/static/assets/logos/subscriptions/linkedin.svg",
            popularity: 67
        }
    ];

    // DOM Elements
    const serviceInput = document.getElementById("service-name");
    const logoIndicator = document.getElementById("serviceLogoIndicator");
    const dropdown = document.getElementById("serviceAutocompleteDropdown");
    const categorySelect = document.getElementById("category");
    const billingCycleSelect = document.getElementById("billing-cycle");

    // Ensure Billing Cycle Defaults to Monthly
    if (billingCycleSelect && !billingCycleSelect.value) {
        billingCycleSelect.value = "Monthly";
    }

    if (!serviceInput || !dropdown) {
        return;
    }

    let activeSuggestionIndex = -1;
    let currentSuggestions = [];

    // Helper: Reset Logo Indicator to Default Grid Icon
    function resetLogoIndicator() {
        if (!logoIndicator) return;
        logoIndicator.className = "service-logo-indicator";
        logoIndicator.innerHTML = '<i class="bi bi-grid-1x2"></i>';
    }

    // Helper: Set Logo Indicator to Known Brand (Official SVG logo)
    function setBrandLogoIndicator(service) {
        if (!logoIndicator) return;
        logoIndicator.className = "service-logo-indicator has-logo";
        logoIndicator.innerHTML = `<img src="${service.logoUrl}" alt="${service.name}" class="service-brand-logo">`;
    }

    // Helper: Set Logo Indicator to Graceful Initial Fallback
    function setFallbackLogoIndicator(text) {
        if (!logoIndicator) return;
        const initial = (text || "").trim().charAt(0).toUpperCase();
        if (initial) {
            logoIndicator.className = "service-logo-indicator brand-default";
            logoIndicator.innerHTML = '<span style="font-size:0.82rem;font-weight:700;color:#fff;">' + initial + '</span>';
        } else {
            resetLogoIndicator();
        }
    }

    // Helper: Find exact or best service match by name
    function findServiceByName(name) {
        if (!name) return null;
        const lower = name.trim().toLowerCase();
        return POPULAR_SERVICES.find(s => s.name.toLowerCase() === lower);
    }

    // Scoring algorithm ensuring prioritized suggestions:
    // "n" -> Netflix highly ranked
    // "ne" -> Netflix primary
    // "net" -> Netflix primary
    // "s" -> Spotify highly ranked
    // "you" -> YouTube Premium
    // "ama" -> Amazon Prime
    // "mic" -> Microsoft 365
    // "can" -> Canva
    // "cha" -> ChatGPT
    function scoreService(service, q) {
        const nameLower = service.name.toLowerCase();
        let score = 0;

        if (nameLower === q) {
            score = 2000;
        } else if (nameLower.startsWith(q)) {
            score = 1000 + service.popularity - nameLower.length;
        } else {
            // Check word starts in name (e.g. "Prime" in "Amazon Prime")
            const words = nameLower.split(/\s+/);
            const wordMatch = words.some(w => w.startsWith(q));
            if (wordMatch) {
                score = 800 + service.popularity;
            } else {
                // Check aliases
                const aliasStarts = service.aliases.some(a => a.startsWith(q));
                if (aliasStarts) {
                    score = 600 + service.popularity;
                } else if (nameLower.includes(q)) {
                    score = 400 + service.popularity - nameLower.indexOf(q);
                } else {
                    const aliasContains = service.aliases.some(a => a.includes(q));
                    if (aliasContains) {
                        score = 200 + service.popularity;
                    }
                }
            }
        }
        return score;
    }

    // Highlight matching part in service name
    function highlightMatch(text, query) {
        if (!query) return text;
        const idx = text.toLowerCase().indexOf(query.toLowerCase());
        if (idx === -1) return text;
        const before = text.substring(0, idx);
        const match = text.substring(idx, idx + query.length);
        const after = text.substring(idx + query.length);
        return before + '<span class="autocomplete-match">' + match + '</span>' + after;
    }

    // Render Suggestions in Dropdown
    function renderSuggestions(services, query) {
        currentSuggestions = services;
        activeSuggestionIndex = -1;

        if (services.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-empty">No recognized services. You can continue typing custom name.</div>';
            dropdown.style.display = "block";
            return;
        }

        let html = "";
        services.forEach((service, index) => {
            const highlightedName = highlightMatch(service.name, query);
            html += `
                <div class="autocomplete-item" data-index="${index}">
                    <div class="autocomplete-logo-box has-logo">
                        <img src="${service.logoUrl}" alt="${service.name}" class="service-brand-logo">
                    </div>
                    <div class="autocomplete-text">
                        <span class="autocomplete-name">${highlightedName}</span>
                        <span class="autocomplete-category">${service.category}</span>
                    </div>
                </div>
            `;
        });

        dropdown.innerHTML = html;
        dropdown.style.display = "block";

        // Bind Mouse Clicks
        const items = dropdown.querySelectorAll(".autocomplete-item");
        items.forEach(item => {
            item.addEventListener("mousedown", function (e) {
                e.preventDefault(); // Prevent input blur
                const idx = parseInt(this.getAttribute("data-index"), 10);
                selectService(currentSuggestions[idx]);
            });
        });
    }

    // Select Service and Apply Automatic Settings
    function selectService(service) {
        if (!service) return;

        // 1. Set service name
        serviceInput.value = service.name;

        // 2. Set logo indicator
        setBrandLogoIndicator(service);

        // 3. Automatically populate category
        if (categorySelect && service.category) {
            // Find option matching category
            const option = Array.from(categorySelect.options).find(
                opt => opt.value.toLowerCase() === service.category.toLowerCase()
            );
            if (option) {
                categorySelect.value = option.value;
                const categoryPill = document.getElementById("categoryStatusPill");
                if (categoryPill) {
                    categoryPill.textContent = "Auto-detected";
                }
            }
        }

        // 4. Close dropdown
        closeDropdown();

        // 5. Smoothly focus next field (monthly cost)
        const monthlyCostInput = document.getElementById("monthly-cost");
        if (monthlyCostInput) {
            monthlyCostInput.focus();
        }
    }

    function closeDropdown() {
        dropdown.style.display = "none";
        dropdown.innerHTML = "";
        activeSuggestionIndex = -1;
        currentSuggestions = [];
    }

    function updateActiveItem(index) {
        const items = dropdown.querySelectorAll(".autocomplete-item");
        items.forEach((item, idx) => {
            if (idx === index) {
                item.classList.add("active");
                item.scrollIntoView({ block: "nearest" });
            } else {
                item.classList.remove("active");
            }
        });
        activeSuggestionIndex = index;
    }

    // On Input Typing
    serviceInput.addEventListener("input", function () {
        const val = this.value.trim().toLowerCase();

        if (!val) {
            resetLogoIndicator();
            closeDropdown();
            return;
        }

        // Check if exact match exists currently
        const exactMatch = findServiceByName(this.value);
        if (exactMatch) {
            setBrandLogoIndicator(exactMatch);
        } else {
            setFallbackLogoIndicator(this.value);
        }

        // Rank services
        const scored = [];
        POPULAR_SERVICES.forEach(service => {
            const score = scoreService(service, val);
            if (score > 0) {
                scored.push({ service, score });
            }
        });

        scored.sort((a, b) => b.score - a.score);
        const topResults = scored.slice(0, 7).map(item => item.service);

        renderSuggestions(topResults, this.value.trim());
    });

    // Keyboard Navigation in Dropdown
    serviceInput.addEventListener("keydown", function (e) {
        const isDropdownVisible = dropdown.style.display === "block" && currentSuggestions.length > 0;

        if (e.key === "ArrowDown") {
            if (isDropdownVisible) {
                e.preventDefault();
                let nextIdx = activeSuggestionIndex + 1;
                if (nextIdx >= currentSuggestions.length) {
                    nextIdx = 0;
                }
                updateActiveItem(nextIdx);
            } else if (serviceInput.value.trim().length > 0) {
                // Re-trigger suggestions if input has value
                serviceInput.dispatchEvent(new Event("input"));
            }
        } else if (e.key === "ArrowUp") {
            if (isDropdownVisible) {
                e.preventDefault();
                let prevIdx = activeSuggestionIndex - 1;
                if (prevIdx < 0) {
                    prevIdx = currentSuggestions.length - 1;
                }
                updateActiveItem(prevIdx);
            }
        } else if (e.key === "Enter") {
            if (isDropdownVisible && activeSuggestionIndex >= 0 && activeSuggestionIndex < currentSuggestions.length) {
                e.preventDefault();
                e.stopPropagation();
                selectService(currentSuggestions[activeSuggestionIndex]);
                return;
            }
        } else if (e.key === "Escape") {
            closeDropdown();
        }
    });

    // On Blur / Change
    serviceInput.addEventListener("blur", function () {
        // Delay closing so mousedown event fires
        setTimeout(() => {
            closeDropdown();
            const matched = findServiceByName(serviceInput.value);
            if (matched) {
                setBrandLogoIndicator(matched);
                if (categorySelect && (!categorySelect.value || categorySelect.value === "Entertainment")) {
                    categorySelect.value = matched.category;
                    const categoryPill = document.getElementById("categoryStatusPill");
                    if (categoryPill) {
                        categoryPill.textContent = "Auto-detected";
                    }
                }
            } else if (serviceInput.value.trim()) {
                setFallbackLogoIndicator(serviceInput.value);
            } else {
                resetLogoIndicator();
            }
        }, 200);
    });

    // Mark category as custom if user manually modifies it
    if (categorySelect) {
        categorySelect.addEventListener("change", function () {
            const categoryPill = document.getElementById("categoryStatusPill");
            if (categoryPill) {
                categoryPill.textContent = "Custom";
            }
        });
    }

    // Close Dropdown When Clicking Outside
    document.addEventListener("click", function (e) {
        if (!e.target.closest(".service-autocomplete-wrap")) {
            closeDropdown();
        }
    });

    // General Enter Key Navigation Across Non-Autocomplete Fields
    const allFields = Array.from(document.querySelectorAll("input, select"));
    allFields.forEach((field, index) => {
        field.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                // If this is service input and dropdown is active, let serviceInput keydown handle it
                if (field === serviceInput && dropdown.style.display === "block" && activeSuggestionIndex >= 0) {
                    return;
                }
                if (field.type !== "submit" && field.tagName !== "BUTTON") {
                    e.preventDefault();
                    if (index + 1 < allFields.length) {
                        allFields[index + 1].focus();
                    }
                }
            }
        });
    });

    // =========================================================================
    // Frictionless Form Submission & Post-Save "Usage & Value" Step
    // =========================================================================
    const addForm = document.getElementById("addSubscriptionForm");
    const submitBtn = document.getElementById("btnSubmitSubscription");
    const postSaveCard = document.getElementById("postSaveUsageCard");
    const btnSkipUsage = document.getElementById("btnSkipUsage");
    const btnSaveUsage = document.getElementById("btnSaveUsage");
    const postSaveFreq = document.getElementById("post-save-frequency");
    const postSaveHours = document.getElementById("post-save-hours");

    let createdSubscriptionId = null;
    let redirectDestination = "/subscriptions";

    if (addForm) {
        addForm.addEventListener("submit", function (e) {
            e.preventDefault();

            if (!addForm.checkValidity()) {
                addForm.reportValidity();
                return;
            }

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Adding...';
            }

            const formData = new FormData(addForm);

            fetch(window.location.href, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json"
                }
            })
            .then(async response => {
                const data = await response.json().catch(() => null);
                if (response.ok && data && data.success) {
                    createdSubscriptionId = data.subscription_id;
                    if (data.redirect_url) {
                        redirectDestination = data.redirect_url;
                    }

                    // Hide initial fast creation form and display lightweight post-save step
                    addForm.style.display = "none";
                    if (postSaveCard) {
                        postSaveCard.style.display = "block";
                        postSaveCard.scrollIntoView({ behavior: "smooth", block: "center" });
                    }
                } else {
                    const errorMsg = (data && data.message) ? data.message : "Failed to add subscription. Please check your inputs.";
                    alert(errorMsg);
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<i class="bi bi-plus-lg"></i> Add Subscription';
                    }
                }
            })
            .catch(err => {
                console.error("Error creating subscription:", err);
                // Fallback to normal post
                addForm.submit();
            });
        });
    }

    // Skip Usage Step
    if (btnSkipUsage) {
        btnSkipUsage.addEventListener("click", function () {
            window.location.href = redirectDestination;
        });
    }

    // Save Optional Usage Details
    if (btnSaveUsage) {
        btnSaveUsage.addEventListener("click", function () {
            if (!createdSubscriptionId) {
                window.location.href = redirectDestination;
                return;
            }

            const freq = postSaveFreq ? postSaveFreq.value : "";
            const hours = postSaveHours ? postSaveHours.value : "";

            btnSaveUsage.disabled = true;
            btnSaveUsage.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Saving...';
            if (btnSkipUsage) btnSkipUsage.disabled = true;

            fetch(`/subscriptions/${createdSubscriptionId}/usage`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json"
                },
                body: JSON.stringify({
                    usage_frequency: freq || null,
                    usage_hours: hours ? parseFloat(hours) : null
                })
            })
            .then(() => {
                window.location.href = redirectDestination;
            })
            .catch(err => {
                console.error("Failed to save usage details:", err);
                window.location.href = redirectDestination;
            });
        });
    }

});