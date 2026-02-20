/**
 * Frontend JavaScript for FedEx API Chatbot portal
 */

const API_BASE_URL = 'http://localhost:8000';
const AUTH_KEY = 'fedex_api_auth';

let currentConversationId = null;

// Check authentication
function isAuthenticated() {
    const authToken = localStorage.getItem(AUTH_KEY);
    const expiryTime = localStorage.getItem('fedex_api_auth_expiry');

    if (!authToken || !expiryTime) {
        return false;
    }

    if (Date.now() > parseInt(expiryTime)) {
        localStorage.removeItem(AUTH_KEY);
        localStorage.removeItem('fedex_api_auth_expiry');
        return false;
    }

    return true;
}

// DOM elements
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const quickQuestions = document.querySelectorAll('.quick-q');
const modelIndicator = document.getElementById('model-indicator');
const statusIndicator = document.getElementById('status-indicator');
const docsCount = document.getElementById('docs-count');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check authentication first
    if (!isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    loadStats();
    checkHealth();

    // Event listeners
    sendBtn.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    quickQuestions.forEach(btn => {
        btn.addEventListener('click', () => {
            const question = btn.dataset.q;
            chatInput.value = question;
            handleSendMessage();
        });
    });

    // Logout functionality
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                localStorage.removeItem(AUTH_KEY);
                localStorage.removeItem('fedex_api_auth_expiry');
                window.location.href = 'login.html';
            }
        });
    }

    // Track downloads
    const downloadBtn = document.querySelector('a[download]');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', trackDownload);
    }
});

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        if (response.ok) {
            const stats = await response.json();
            if (docsCount) {
                animateNumber(docsCount, stats.documents_indexed);
            }

            // Animate download count from real data
            const downloadCount = document.getElementById('download-count');
            if (downloadCount) {
                animateNumber(downloadCount, stats.total_downloads);
            }
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            const health = await response.json();
            updateStatus(health.services);
        } else {
            setStatus('Server offline', 'error');
        }
    } catch (error) {
        setStatus('Server offline', 'error');
        console.error('Health check failed:', error);
    }
}

function updateStatus(services) {
    let status = 'Ready';
    if (services.ollama === 'available') {
        status = 'Ollama ready';
    } else if (services.claude === 'configured') {
        status = 'Claude ready';
    }
    setStatus(status, 'success');
}

function setStatus(text, type = 'info') {
    if (statusIndicator) {
        statusIndicator.textContent = text;
        statusIndicator.className = `status-${type}`;
    }
}

async function handleSendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Disable input
    chatInput.disabled = true;
    sendBtn.disabled = true;
    setStatus('Thinking...', 'info');

    // Add user message to chat
    addMessage(message, 'user');

    // Clear input
    chatInput.value = '';

    try {
        // Show loading indicator
        const loadingId = addLoadingMessage();

        // Send to API
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_id: currentConversationId,
            }),
        });

        // Remove loading indicator
        removeMessage(loadingId);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update conversation ID
        currentConversationId = data.conversation_id;

        // Update model indicator
        const modelName = data.model_used.includes('claude') ? 'Claude' : 'Ollama';
        if (modelIndicator) {
            modelIndicator.textContent = `Model: ${modelName}`;
        }

        // Add assistant message
        addMessage(data.message, 'assistant', {
            model: data.model_used,
            time: data.processing_time,
            sources: data.sources,
        });

        setStatus('Ready', 'success');

    } catch (error) {
        console.error('Error sending message:', error);
        addMessage(
            'Sorry, I encountered an error. Please make sure the server is running at http://localhost:8000',
            'assistant',
            { error: true }
        );
        setStatus('Error', 'error');
    } finally {
        // Re-enable input
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

function addMessage(content, role, metadata = {}) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Format content (simple markdown support)
    const formattedContent = formatMessage(content);
    const contentP = document.createElement('p');
    contentP.innerHTML = formattedContent;
    contentDiv.appendChild(contentP);

    // Add metadata
    if (metadata.model || metadata.time) {
        const metaP = document.createElement('p');
        metaP.className = 'message-meta';
        metaP.textContent = `${metadata.model || ''} • ${metadata.time || ''}s`;
        contentDiv.appendChild(metaP);
    }

    // Add sources
    if (metadata.sources && metadata.sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';

        const sourcesTitle = document.createElement('h4');
        sourcesTitle.textContent = 'Sources:';
        sourcesDiv.appendChild(sourcesTitle);

        metadata.sources.forEach(source => {
            const sourceLink = document.createElement('a');
            sourceLink.href = source.url;
            sourceLink.className = 'source-link';
            sourceLink.textContent = `${source.title} (${(source.relevance_score * 100).toFixed(0)}% relevant)`;
            sourceLink.target = '_blank';
            sourcesDiv.appendChild(sourceLink);
        });

        contentDiv.appendChild(sourcesDiv);
    }

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv;
}

function addLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant loading-message';
    messageDiv.id = 'loading-' + Date.now();

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = '<div class="loading-indicator"></div>';

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv.id;
}

function removeMessage(id) {
    const message = document.getElementById(id);
    if (message) {
        message.remove();
    }
}

function formatMessage(text) {
    // Simple markdown formatting
    let formatted = text
        // Code blocks
        .replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        // Line breaks
        .replace(/\n/g, '<br>');

    return formatted;
}

function animateNumber(element, target) {
    const duration = 1000;
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        const current = Math.floor(start + (target - start) * progress);
        element.textContent = current.toLocaleString();

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

async function trackDownload() {
    try {
        await fetch(`${API_BASE_URL}/track-download`, {
            method: 'POST'
        });
        console.log('Download tracked');
    } catch (error) {
        console.error('Failed to track download:', error);
    }
}

// Periodic health check
setInterval(checkHealth, 30000); // Every 30 seconds
