/**
 * Background service worker for Chrome extension
 */

// Listen for extension installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('FedEx API Assistant installed');
});

// Handle messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'QUERY_API') {
        // Forward query to backend API
        fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: request.message,
                conversation_id: request.conversationId,
            }),
        })
            .then(response => response.json())
            .then(data => sendResponse({ success: true, data }))
            .catch(error => sendResponse({ success: false, error: error.message }));

        return true; // Keep channel open for async response
    }
});
