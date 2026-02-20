/**
 * Admin login page functionality
 */

const ADMIN_USERNAME = 'jclaeson';
const ADMIN_PASSWORD = 'FedExAdmin1234';
const ADMIN_AUTH_KEY = 'fedex_admin_auth';
const ADMIN_AUTH_EXPIRY = 'fedex_admin_auth_expiry';

// Check if already authenticated as admin
document.addEventListener('DOMContentLoaded', () => {
    if (isAdminAuthenticated()) {
        // Redirect to admin dashboard
        window.location.href = 'admin.html';
        return;
    }

    const loginForm = document.getElementById('admin-login-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const loginBtn = document.getElementById('login-btn');
    const errorMessage = document.getElementById('error-message');

    loginForm.addEventListener('submit', handleAdminLogin);

    // Clear error on input
    usernameInput.addEventListener('input', () => {
        errorMessage.classList.remove('show');
    });
    passwordInput.addEventListener('input', () => {
        errorMessage.classList.remove('show');
    });

    // Focus username field
    usernameInput.focus();
});

function handleAdminLogin(e) {
    e.preventDefault();

    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const loginBtn = document.getElementById('login-btn');
    const errorMessage = document.getElementById('error-message');

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    // Disable form
    usernameInput.disabled = true;
    passwordInput.disabled = true;
    loginBtn.disabled = true;
    loginBtn.textContent = 'Verifying...';

    // Simulate network delay
    setTimeout(() => {
        if (username === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
            // Set admin authentication token
            const expiryTime = Date.now() + (8 * 60 * 60 * 1000); // 8 hours
            localStorage.setItem(ADMIN_AUTH_KEY, 'admin_authenticated');
            localStorage.setItem(ADMIN_AUTH_EXPIRY, expiryTime.toString());

            // Track admin login
            trackAdminLogin(username);

            // Redirect to admin dashboard
            window.location.href = 'admin.html';
        } else {
            // Show error
            errorMessage.textContent = 'Invalid username or password. Access denied.';
            errorMessage.classList.add('show');

            // Re-enable form
            usernameInput.disabled = false;
            passwordInput.disabled = false;
            loginBtn.disabled = false;
            loginBtn.textContent = 'Access Dashboard';
            passwordInput.value = '';
            usernameInput.focus();
        }
    }, 500);
}

function isAdminAuthenticated() {
    const authToken = localStorage.getItem(ADMIN_AUTH_KEY);
    const expiryTime = localStorage.getItem(ADMIN_AUTH_EXPIRY);

    if (!authToken || !expiryTime) {
        return false;
    }

    // Check if expired
    if (Date.now() > parseInt(expiryTime)) {
        localStorage.removeItem(ADMIN_AUTH_KEY);
        localStorage.removeItem(ADMIN_AUTH_EXPIRY);
        return false;
    }

    return true;
}

async function trackAdminLogin(username) {
    try {
        await fetch('http://localhost:8000/api/track-admin-login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                timestamp: new Date().toISOString()
            })
        });
    } catch (error) {
        console.error('Failed to track admin login:', error);
    }
}
