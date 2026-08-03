document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.querySelector('.password-toggle');
    const password = document.getElementById('password');

    if (toggle && password) {
        toggle.addEventListener('click', function () {
            const hidden = password.type === 'password';
            password.type = hidden ? 'text' : 'password';
            this.setAttribute('aria-label', hidden ? 'Hide password' : 'Show password');
            this.setAttribute('aria-pressed', String(hidden));
            this.querySelector('i').className = hidden ? 'bi bi-eye-slash' : 'bi bi-eye';
        });
    }
});
