function selectUsername(username) {
    document.getElementById('username').value = username;
}

document.addEventListener('DOMContentLoaded', function () {
    const password = document.getElementById('password');
    const meter = document.querySelector('.strength-meter');
    const meterText = meter.querySelector('span');
    const bars = meter.querySelectorAll('i');

    document.querySelectorAll('.password-toggle').forEach(function (toggle) {
        toggle.addEventListener('click', function () {
            const input = document.getElementById(this.dataset.target);
            const hidden = input.type === 'password';
            input.type = hidden ? 'text' : 'password';
            this.setAttribute('aria-label', hidden ? 'Hide password' : 'Show password');
            this.setAttribute('aria-pressed', String(hidden));
            this.querySelector('i').className = hidden ? 'bi bi-eye-slash' : 'bi bi-eye';
        });
    });

    password.addEventListener('input', function () {
        const length = this.value.length;
        const level = length === 0 ? 0 : length < 6 ? 1 : length < 10 ? 2 : 3;
        const labels = ['Use 8 or more characters', 'Weak password', 'Medium password', 'Strong password'];
        meter.dataset.level = level;
        meterText.textContent = labels[level];
        bars.forEach(function (bar, index) {
            bar.classList.toggle('active', index < level);
        });
    });
});
