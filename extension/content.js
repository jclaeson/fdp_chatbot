/**
 * Content script injected into developer.fedex.com pages
 * Adds quick access button to trigger assistant
 */

// Create floating button
function createFloatingButton() {
    const button = document.createElement('div');
    button.id = 'fedex-assistant-btn';
    button.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
        </svg>
    `;
    button.title = 'Open FedEx API Assistant';

    button.addEventListener('click', () => {
        chrome.runtime.sendMessage({ type: 'OPEN_POPUP' });
    });

    document.body.appendChild(button);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createFloatingButton);
} else {
    createFloatingButton();
}
