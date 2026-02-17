// reset_password.js — Password strength + match validation for reset.html

document.addEventListener('DOMContentLoaded', function () {
    const newPwEl    = document.getElementById('new_password');
    const confirmEl  = document.getElementById('confirm_password');
    const toggleBtn  = document.getElementById('toggleNewPassword');
    const eyeIcon    = toggleBtn.querySelector('.eye-icon');
    const eyeOffIcon = toggleBtn.querySelector('.eye-off-icon');
    const strengthEl = document.getElementById('password-strength');
    const matchMsgEl = document.getElementById('password-match-msg');
    const submitBtn  = document.getElementById('reset-btn');

    // ── Show / hide password toggle ───────────────────────────────────
    toggleBtn.addEventListener('click', function () {
        const isHidden = newPwEl.type === 'password';
        newPwEl.type             = isHidden ? 'text' : 'password';
        eyeIcon.style.display    = isHidden ? 'none'  : 'block';
        eyeOffIcon.style.display = isHidden ? 'block' : 'none';
        toggleBtn.setAttribute(
            'aria-label',
            isHidden ? 'Hide password' : 'Show password'
        );
    });

    // ── Password strength meter ───────────────────────────────────────
    function getStrength(pw) {
        let score = 0;
        if (pw.length >= 8)                              score++;
        if (pw.length >= 12)                             score++;
        if (/[a-z]/.test(pw) && /[A-Z]/.test(pw))       score++;
        if (/\d/.test(pw))                               score++;
        if (/[^a-zA-Z\d]/.test(pw))                     score++;

        const levels = [
            { text: 'Too short',   color: '#e53e3e' },
            { text: 'Weak',        color: '#f56565' },
            { text: 'Fair',        color: '#ed8936' },
            { text: 'Good',        color: '#ecc94b' },
            { text: 'Strong',      color: '#48bb78' },
            { text: 'Very strong', color: '#38a169' },
        ];
        return { score, ...levels[Math.min(score, 5)] };
    }

    function renderStrength(pw) {
        if (!pw) { strengthEl.innerHTML = ''; return; }
        const s    = getStrength(pw);
        const bars = [1, 2, 3, 4].map(i => `
            <div style="flex:1;height:4px;
                 background:${s.score >= i ? s.color : '#e2e8f0'};
                 border-radius:2px;"></div>
        `).join('');
        strengthEl.innerHTML = `
            <div style="display:flex;gap:4px;margin-bottom:5px;">${bars}</div>
            <p style="margin:0;font-size:0.75rem;color:${s.color};
                       font-weight:500;">${s.text}</p>
        `;
    }

    // ── Match validation ──────────────────────────────────────────────
    function checkMatch() {
        const pw  = newPwEl.value;
        const cfm = confirmEl.value;
        if (!cfm) {
            matchMsgEl.textContent = '';
            submitBtn.disabled     = false;
            return;
        }
        if (pw === cfm) {
            matchMsgEl.textContent = '✓ Passwords match';
            matchMsgEl.style.color = '#38a169';
            submitBtn.disabled     = false;
        } else {
            matchMsgEl.textContent = '✗ Passwords do not match';
            matchMsgEl.style.color = '#e53e3e';
            submitBtn.disabled     = true;
        }
    }

    newPwEl.addEventListener('input', function () {
        renderStrength(this.value);
        checkMatch();
    });

    confirmEl.addEventListener('input', checkMatch);
});