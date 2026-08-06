setTimeout(() => {
    document.querySelectorAll(".alert").forEach(alert => {
        alert.style.transition = "opacity 0.5s";
        alert.style.opacity = "0";
        setTimeout(() => alert.remove(), 500);
    });
}, 2500);

/**
 * Global JavaScript helper for formatting numbers into Indian Rupee (INR / ₹) strings.
 * Examples: 499 -> "₹499", 1299.50 -> "₹1,299.50"
 */
function formatINR(value, forceDecimals = false) {
    if (value === null || value === undefined || value === '' || value === '—') {
        return '₹—';
    }
    const val = Number(value);
    if (isNaN(val)) {
        return '₹' + value;
    }
    if (forceDecimals || val % 1 !== 0) {
        return '₹' + val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    return '₹' + val.toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

window.formatINR = formatINR;

