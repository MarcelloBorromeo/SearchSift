/**
 * SearchSift Extension Popup
 */

const BACKEND_URL = 'http://127.0.0.1:5050';

// Elements
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const errorBox = document.getElementById('errorBox');
const bufferCount = document.getElementById('bufferCount');
const todayCount = document.getElementById('todayCount');
const clickCount = document.getElementById('clickCount');
const dashboardBtn = document.getElementById('dashboardBtn');
const settingsBtn = document.getElementById('settingsBtn');

/**
 * Check backend connection and API key
 */
async function checkStatus() {
  // Get API key
  const { apiKey } = await chrome.storage.sync.get(['apiKey']);

  if (!apiKey) {
    showStatus('warning', 'API key not configured');
    showError('Please configure your API key in Settings');
    return;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      headers: { 'X-API-Key': apiKey },
    });

    if (response.ok) {
      showStatus('connected', 'Connected to backend');
      hideError();
      fetchStats(apiKey);
    } else if (response.status === 401 || response.status === 403) {
      showStatus('warning', 'Invalid API key');
      showError('API key rejected by backend');
    } else {
      showStatus('disconnected', 'Backend error');
      showError(`Backend returned status ${response.status}`);
    }
  } catch (error) {
    showStatus('disconnected', 'Cannot reach backend');
    showError('Is the backend running? Start it with: flask run');
  }
}

/**
 * Fetch today's stats from backend
 */
async function fetchStats(apiKey) {
  try {
    const today = new Date().toISOString().split('T')[0];
    const response = await fetch(
      `${BACKEND_URL}/api/summary?start=${today}&end=${today}`,
      { headers: { 'X-API-Key': apiKey } }
    );

    if (response.ok) {
      const data = await response.json();
      todayCount.textContent = data.total_searches || 0;
      clickCount.textContent = data.total_clicks || 0;
    }
  } catch (error) {
    console.error('Failed to fetch stats:', error);
  }
}

/**
 * Get buffer count from background script
 */
async function getBufferCount() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });
    bufferCount.textContent = response?.bufferSize || 0;
  } catch (error) {
    console.error('Failed to get buffer count:', error);
  }
}

/**
 * Show status indicator
 */
function showStatus(state, text) {
  statusIndicator.className = `status-indicator ${state}`;
  statusText.textContent = text;
}

/**
 * Show error message
 */
function showError(message) {
  errorBox.textContent = message;
  errorBox.style.display = 'block';
}

/**
 * Hide error message
 */
function hideError() {
  errorBox.style.display = 'none';
}

// Event listeners
dashboardBtn.addEventListener('click', () => {
  chrome.tabs.create({ url: `${BACKEND_URL}/` });
});

settingsBtn.addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
});

document.getElementById('helpLink').addEventListener('click', (e) => {
  e.preventDefault();
  chrome.tabs.create({ url: `${BACKEND_URL}/help` });
});

// Initialize
checkStatus();
getBufferCount();
