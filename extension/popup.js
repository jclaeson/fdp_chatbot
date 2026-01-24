/**
 * Chrome Extension Popup Script
 */

const API_BASE_URL = 'http://localhost:8000';

let conversationId = null;

// DOM elements
const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const statusText = document.getElementById('status-text');
const statusDot = document.querySelector('.status-dot');
const modelUsed = document.getElementById('model-used');
const responseTime = document.getElementById('response-time');
const quickActions = document.querySelectorAll('.quick-action');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadChatHistory();
    checkServerStatus();

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    quickActions.forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            messageInput.value = query;
            sendMessage();
        });
    });
});

async function checkServerStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            setStatus('Connected', true);
        } else {
            setStatus('Server error', false);
        }
    } catch (error) {
        setStatus('Offline - Start server', false);
    }
}

function setStatus(text, online) {
    statusText.textContent = text;
    if (online) {
        statusDot.classList.remove('offline');
    } else {
        statusDot.classList.add('offline');
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    // Disable input
    messageInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(message, 'user');
    messageInput.value = '';

    // Save to history
    saveChatHistory();

    try {
        // Show loading
        const loadingId = addLoadingMessage();

        // Send to API
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId,
            }),
        });

        // Remove loading
        removeMessage(loadingId);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Update conversation ID
        conversationId = data.conversation_id;

        // Update stats
        const model = data.model_used.includes('claude') ? 'Claude' : 'Ollama';
        modelUsed.textContent = `Model: ${model}`;
        responseTime.textContent = `${data.processing_time}s`;

        // Add response
        addMessage(data.message, 'assistant', {
            model: data.model_used,
            sources: data.sources,
        });

        // Save to history
        saveChatHistory();

    } catch (error) {
        console.error('Error:', error);
        addMessage(
            'Sorry, I couldn\'t connect to the server. Make sure it\'s running at http://localhost:8000',
            'assistant',
            { error: true }
        );
        setStatus('Connection error', false);
    } finally {
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

function addMessage(content, role, metadata = {}) {
    // Remove welcome message if exists
    const welcome = chatContainer.querySelector('.welcome-message');
    if (welcome) {
        welcome.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = formatText(content);

    messageDiv.appendChild(bubble);

    // Add metadata for assistant messages
    if (role === 'assistant' && (metadata.model || metadata.sources)) {
        if (metadata.model) {
            const meta = document.createElement('div');
            meta.className = 'message-meta';
            meta.textContent = metadata.model;
            messageDiv.appendChild(meta);
        }

        if (metadata.sources && metadata.sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'message-sources';

            metadata.sources.forEach(source => {
                const link = document.createElement('a');
                link.href = source.url;
                link.className = 'source-link';
                link.textContent = `📄 ${source.title}`;
                link.target = '_blank';
                sourcesDiv.appendChild(link);
            });

            bubble.appendChild(sourcesDiv);
        }
    }

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    return messageDiv;
}

function addLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = 'loading-' + Date.now();

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = '<div class="loading"></div>';

    messageDiv.appendChild(bubble);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    return messageDiv.id;
}

function removeMessage(id) {
    const message = document.getElementById(id);
    if (message) {
        message.remove();
    }
}

function formatText(text) {
    return text
        .replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        .replace(/\n/g, '<br>');
}

function saveChatHistory() {
    const messages = Array.from(chatContainer.querySelectorAll('.message')).map(msg => ({
        role: msg.classList.contains('user') ? 'user' : 'assistant',
        content: msg.querySelector('.message-bubble').textContent,
    }));

    chrome.storage.local.set({
        chatHistory: messages,
        conversationId: conversationId,
    });
}

function loadChatHistory() {
    chrome.storage.local.get(['chatHistory', 'conversationId'], (result) => {
        if (result.conversationId) {
            conversationId = result.conversationId;
        }

        if (result.chatHistory && result.chatHistory.length > 0) {
            // Remove welcome message
            const welcome = chatContainer.querySelector('.welcome-message');
            if (welcome) {
                welcome.remove();
            }

            // Add messages
            result.chatHistory.forEach(msg => {
                addMessage(msg.content, msg.role);
            });
        }
    });
}

// Periodic status check
setInterval(checkServerStatus, 30000); // Every 30 seconds
