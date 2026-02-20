/**
 * Admin Dashboard JavaScript
 */

const API_BASE_URL = 'http://localhost:8000';
const ADMIN_AUTH_KEY = 'fedex_admin_auth';
const ADMIN_AUTH_EXPIRY = 'fedex_admin_auth_expiry';

// Check admin authentication on page load
document.addEventListener('DOMContentLoaded', () => {
    if (!isAdminAuthenticated()) {
        window.location.href = 'admin-login.html';
        return;
    }

    initializeDashboard();
});

function isAdminAuthenticated() {
    const authToken = localStorage.getItem(ADMIN_AUTH_KEY);
    const expiryTime = localStorage.getItem(ADMIN_AUTH_EXPIRY);

    if (!authToken || !expiryTime) {
        return false;
    }

    if (Date.now() > parseInt(expiryTime)) {
        localStorage.removeItem(ADMIN_AUTH_KEY);
        localStorage.removeItem(ADMIN_AUTH_EXPIRY);
        return false;
    }

    return true;
}

function initializeDashboard() {
    // Load all data
    loadStats();
    loadServerStatus();
    loadRecentQueries();

    // Setup event listeners
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    document.getElementById('restart-btn').addEventListener('click', handleRestart);
    document.getElementById('refresh-status-btn').addEventListener('click', loadServerStatus);

    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadStats();
        loadServerStatus();
        loadRecentQueries();
    }, 30000);
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/stats`);
        if (!response.ok) throw new Error('Failed to load stats');

        const stats = await response.json();

        // Update stat cards
        document.getElementById('total-requests').textContent = stats.total_requests.toLocaleString();
        document.getElementById('unique-users').textContent = stats.unique_users.toLocaleString();
        document.getElementById('avg-response-time').textContent = stats.avg_response_time.toFixed(2) + 's';
        document.getElementById('server-uptime').textContent = formatUptime(stats.uptime_seconds);

        // Update changes
        updateChange('requests-change', stats.requests_24h, 'requests today');
        updateChange('users-change', stats.users_24h, 'users today');
        updateChange('response-change', stats.response_time_trend, '% from yesterday', true);
        document.getElementById('uptime-info').textContent = `Started: ${new Date(stats.start_time).toLocaleString()}`;

    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function loadServerStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const health = await response.json();

        // Update API server status
        if (response.ok) {
            setStatus('api-status', 'online', 'Online');
        } else {
            setStatus('api-status', 'offline', 'Offline');
        }

        // Update service statuses
        setStatus('claude-status',
            health.services.claude === 'configured' ? 'online' : 'offline',
            health.services.claude === 'configured' ? 'Configured' : 'Unavailable'
        );

        setStatus('ollama-status',
            health.services.ollama === 'available' ? 'online' : 'offline',
            health.services.ollama === 'available' ? 'Available' : 'Unavailable'
        );

        setStatus('vector-status',
            health.services.vector_store !== 'error' ? 'online' : 'offline',
            health.services.vector_store || 'Error'
        );

    } catch (error) {
        console.error('Failed to load server status:', error);
        setStatus('api-status', 'offline', 'Offline');
    }
}

async function loadRecentQueries() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/recent-queries?limit=50`);
        if (!response.ok) throw new Error('Failed to load queries');

        const queries = await response.json();
        displayQueries(queries);

    } catch (error) {
        console.error('Failed to load queries:', error);
        document.getElementById('queries-container').innerHTML =
            '<div class="loading">Failed to load queries</div>';
    }
}

function displayQueries(queries) {
    const container = document.getElementById('queries-container');

    if (!queries || queries.length === 0) {
        container.innerHTML = '<div class="loading">No queries yet</div>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'queries-table';

    table.innerHTML = `
        <thead>
            <tr>
                <th>Timestamp</th>
                <th>User</th>
                <th>Query</th>
                <th>Model</th>
                <th>Response Time</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            ${queries.map(q => `
                <tr>
                    <td>${formatTimestamp(q.timestamp)}</td>
                    <td>${maskIP(q.user_ip)}</td>
                    <td class="query-text" title="${escapeHtml(q.query)}">${escapeHtml(q.query)}</td>
                    <td>
                        <span class="model-badge ${q.model.includes('claude') ? 'claude' : 'ollama'}">
                            ${q.model.includes('claude') ? 'Claude' : 'Ollama'}
                        </span>
                    </td>
                    <td>${q.response_time.toFixed(2)}s</td>
                    <td>${q.status === 'success' ? '✓' : '✗'}</td>
                </tr>
            `).join('')}
        </tbody>
    `;

    container.innerHTML = '';
    container.appendChild(table);
}

function setStatus(elementId, type, text) {
    const element = document.getElementById(elementId);
    element.className = `status-indicator ${type}`;
    element.innerHTML = `<span class="status-dot"></span>${text}`;
}

function updateChange(elementId, value, suffix, isPercentage = false) {
    const element = document.getElementById(elementId);
    const displayValue = isPercentage ? `${value > 0 ? '+' : ''}${value.toFixed(1)}%` : value;
    element.textContent = `${displayValue} ${suffix}`;
    element.className = value > 0 ? 'stat-change positive' : 'stat-change';
}

function formatUptime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const days = Math.floor(hours / 24);

    if (days > 0) {
        return `${days}d ${hours % 24}h`;
    } else if (hours > 0) {
        return `${hours}h ${Math.floor((seconds % 3600) / 60)}m`;
    } else {
        return `${Math.floor(seconds / 60)}m`;
    }
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) {
        return 'Just now';
    } else if (diff < 3600000) {
        return `${Math.floor(diff / 60000)}m ago`;
    } else if (diff < 86400000) {
        return `${Math.floor(diff / 3600000)}h ago`;
    } else {
        return date.toLocaleString();
    }
}

function maskIP(ip) {
    if (!ip) return 'Unknown';
    const parts = ip.split('.');
    if (parts.length === 4) {
        return `${parts[0]}.${parts[1]}.xxx.xxx`;
    }
    return ip.substring(0, 10) + '...';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function handleLogout() {
    if (confirm('Are you sure you want to logout from admin dashboard?')) {
        localStorage.removeItem(ADMIN_AUTH_KEY);
        localStorage.removeItem(ADMIN_AUTH_EXPIRY);
        window.location.href = 'admin-login.html';
    }
}

async function handleRestart() {
    if (!confirm('Are you sure you want to restart the server? This may cause brief downtime.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/restart`, {
            method: 'POST'
        });

        if (response.ok) {
            alert('Server restart initiated. The server will be back online in a few moments.');
            setTimeout(() => {
                loadServerStatus();
            }, 5000);
        } else {
            alert('Failed to restart server. Please check the logs.');
        }
    } catch (error) {
        console.error('Failed to restart server:', error);
        alert('Failed to restart server. Error: ' + error.message);
    }
}

// Scraper functionality
async function loadScraperStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/scraper/status`);
        if (response.ok) {
            const status = await response.json();
            updateScraperStatus(status);
        }
    } catch (error) {
        console.error('Failed to load scraper status:', error);
    }
}

async function loadScraperConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/scraper/config`);
        if (response.ok) {
            const config = await response.json();
            document.getElementById('max-pages').value = config.max_pages;
            document.getElementById('max-depth').value = config.max_depth;
            document.getElementById('delay-ms').value = config.delay_ms;
            document.getElementById('start-urls').value = config.start_urls.join('\n');
        }
    } catch (error) {
        console.error('Failed to load scraper config:', error);
    }
}

function updateScraperStatus(status) {
    const statusEl = document.getElementById('scraper-status');
    const progressEl = document.getElementById('scraper-progress');

    statusEl.className = 'status-indicator';

    if (status.status === 'running') {
        statusEl.classList.add('online');
        statusEl.innerHTML = '<span class="status-dot"></span>Running';
        progressEl.textContent = `${status.pages_scraped} / ${status.total_pages} pages (${status.progress}%)`;
    } else if (status.status === 'completed') {
        statusEl.classList.add('online');
        statusEl.innerHTML = '<span class="status-dot"></span>Completed';
        progressEl.textContent = `${status.pages_scraped} pages scraped`;
    } else if (status.status === 'failed') {
        statusEl.classList.add('offline');
        statusEl.innerHTML = '<span class="status-dot"></span>Failed';
        progressEl.textContent = status.error || 'Unknown error';
    } else {
        statusEl.innerHTML = '<span class="status-dot"></span>Idle';
        progressEl.textContent = '';
    }
}

async function saveScraperConfig() {
    const config = {
        max_pages: parseInt(document.getElementById('max-pages').value),
        max_depth: parseInt(document.getElementById('max-depth').value),
        delay_ms: parseInt(document.getElementById('delay-ms').value),
        start_urls: document.getElementById('start-urls').value.split('\n').filter(url => url.trim()),
        use_playwright: true,
        include_patterns: ["/api/en-us/"],
        exclude_patterns: ["web-services", "wsdl", "soap", "/es-", "/fr-", "developer.fedex.com/login"]
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/scraper/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            alert('Configuration saved successfully!');
        } else {
            alert('Failed to save configuration');
        }
    } catch (error) {
        console.error('Failed to save config:', error);
        alert('Failed to save configuration: ' + error.message);
    }
}

async function startScrape() {
    if (!confirm('Start scraping FedEx Developer Portal? This may take several minutes.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/scraper/start`, {
            method: 'POST'
        });

        if (response.ok) {
            alert('Scraping started! Check status for progress.');
            // Poll for status updates
            const pollInterval = setInterval(async () => {
                await loadScraperStatus();
                const status = await fetch(`${API_BASE_URL}/api/admin/scraper/status`).then(r => r.json());
                if (status.status !== 'running') {
                    clearInterval(pollInterval);
                }
            }, 3000);
        } else {
            const error = await response.json();
            alert('Failed to start scraping: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Failed to start scrape:', error);
        alert('Failed to start scraping: ' + error.message);
    }
}

async function triggerIngestion() {
    if (!confirm('Ingest scraped documentation into vector store? This will add/update FedEx API docs for the chatbot.')) {
        return;
    }

    const outputDiv = document.getElementById('scraper-output');
    const outputText = document.getElementById('scraper-output-text');

    outputDiv.style.display = 'block';
    outputText.textContent = 'Ingesting documentation...\n';

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/scraper/ingest`, {
            method: 'POST'
        });

        const result = await response.json();

        if (response.ok) {
            outputText.textContent += '\n✅ Success!\n' + (result.output || result.message);
            alert('Documentation ingested successfully! The chatbot now has FedEx-specific knowledge.');
        } else {
            outputText.textContent += '\n❌ Failed:\n' + (result.error || result.detail);
            alert('Ingestion failed: ' + (result.error || result.detail));
        }
    } catch (error) {
        console.error('Failed to ingest:', error);
        outputText.textContent += '\n❌ Error: ' + error.message;
        alert('Failed to ingest: ' + error.message);
    }
}

async function scrapeAndIngest() {
    if (!confirm('Scrape FedEx Developer Portal AND ingest into vector store? This may take 10-15 minutes.')) {
        return;
    }

    // Save config first
    await saveScraperConfig();

    // Start scraping
    const outputDiv = document.getElementById('scraper-output');
    const outputText = document.getElementById('scraper-output-text');

    outputDiv.style.display = 'block';
    outputText.textContent = 'Starting scrape...\n';

    try {
        const scrapeResponse = await fetch(`${API_BASE_URL}/api/admin/scraper/start`, {
            method: 'POST'
        });

        if (!scrapeResponse.ok) {
            throw new Error('Failed to start scraping');
        }

        outputText.textContent += 'Scraping in progress...\n';

        // Poll until scraping completes
        let completed = false;
        while (!completed) {
            await new Promise(resolve => setTimeout(resolve, 5000));
            const statusResponse = await fetch(`${API_BASE_URL}/api/admin/scraper/status`);
            const status = await statusResponse.json();

            outputText.textContent += `Progress: ${status.pages_scraped} / ${status.total_pages} pages\n`;

            if (status.status === 'completed') {
                completed = true;
                outputText.textContent += '\n✅ Scraping completed!\n\nStarting ingestion...\n';

                // Trigger ingestion
                const ingestResponse = await fetch(`${API_BASE_URL}/api/admin/scraper/ingest`, {
                    method: 'POST'
                });

                const ingestResult = await ingestResponse.json();

                if (ingestResponse.ok) {
                    outputText.textContent += '\n✅ Ingestion complete!\n' + (ingestResult.output || ingestResult.message);
                    alert('Scrape & Ingest completed successfully!');
                } else {
                    outputText.textContent += '\n❌ Ingestion failed: ' + ingestResult.error;
                }
            } else if (status.status === 'failed') {
                outputText.textContent += '\n❌ Scraping failed: ' + status.error;
                break;
            }
        }
    } catch (error) {
        console.error('Failed:', error);
        outputText.textContent += '\n❌ Error: ' + error.message;
        alert('Failed: ' + error.message);
    }
}

// Event listeners for scraper buttons
document.getElementById('save-config-btn').addEventListener('click', saveScraperConfig);
document.getElementById('start-scrape-btn').addEventListener('click', startScrape);
document.getElementById('ingest-btn').addEventListener('click', triggerIngestion);
document.getElementById('scrape-and-ingest-btn').addEventListener('click', scrapeAndIngest);

// Load scraper status and config on page load
loadScraperStatus();
loadScraperConfig();

// Refresh scraper status periodically
setInterval(loadScraperStatus, 10000);
