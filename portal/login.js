/**
 * Login page functionality
 */

const CORRECT_PASSWORD = 'PurplePromise';
const AUTH_KEY = 'fedex_api_auth';
const AUTH_EXPIRY = 'fedex_api_auth_expiry';

// Check if already authenticated
document.addEventListener('DOMContentLoaded', () => {
    if (isAuthenticated()) {
        // Redirect to main page
        window.location.href = 'home.html';
        return;
    }

    const loginForm = document.getElementById('login-form');
    const passwordInput = document.getElementById('password');
    const loginBtn = document.getElementById('login-btn');
    const errorMessage = document.getElementById('error-message');

    loginForm.addEventListener('submit', handleLogin);
    passwordInput.addEventListener('input', () => {
        errorMessage.classList.remove('show');
    });

    // Focus password field
    passwordInput.focus();
});

function handleLogin(e) {
    e.preventDefault();

    const passwordInput = document.getElementById('password');
    const loginBtn = document.getElementById('login-btn');
    const errorMessage = document.getElementById('error-message');
    const password = passwordInput.value;

    // Disable form
    passwordInput.disabled = true;
    loginBtn.disabled = true;
    loginBtn.textContent = 'Signing in...';

    // Simulate network delay
    setTimeout(() => {
        if (password === CORRECT_PASSWORD) {
            // Set authentication token
            const expiryTime = Date.now() + (24 * 60 * 60 * 1000); // 24 hours
            localStorage.setItem(AUTH_KEY, 'authenticated');
            localStorage.setItem(AUTH_EXPIRY, expiryTime.toString());

            // Track login
            trackLogin();

            // Redirect to main page
            window.location.href = 'home.html';
        } else {
            // Show error
            errorMessage.textContent = 'Incorrect password. Please try again.';
            errorMessage.classList.add('show');

            // Re-enable form
            passwordInput.disabled = false;
            loginBtn.disabled = false;
            loginBtn.textContent = 'Sign In';
            passwordInput.value = '';
            passwordInput.focus();
        }
    }, 500);
}

function isAuthenticated() {
    const authToken = localStorage.getItem(AUTH_KEY);
    const expiryTime = localStorage.getItem(AUTH_EXPIRY);

    if (!authToken || !expiryTime) {
        return false;
    }

    // Check if expired
    if (Date.now() > parseInt(expiryTime)) {
        localStorage.removeItem(AUTH_KEY);
        localStorage.removeItem(AUTH_EXPIRY);
        return false;
    }

    return true;
}

async function trackLogin() {
    try {
        await fetch('http://localhost:8000/api/track-login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                timestamp: new Date().toISOString()
            })
        });
    } catch (error) {
        console.error('Failed to track login:', error);
    }
}
