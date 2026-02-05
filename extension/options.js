/**
 * SearchSift Extension Options Page
 */

// Default settings
const DEFAULTS = {
  backendUrl: 'http://127.0.0.1:5050',
  apiKey: '',
  captureSearches: true,
  captureClicks: true,
  enabled: true,
  engineGoogle: true,
  engineBing: true,
  engineDuckDuckGo: true,
  engineStartPage: true,
  engineYahoo: true,
  engineOther: true,
};

// Elements
const backendUrlInput = document.getElementById('backendUrl');
const apiKeyInput = document.getElementById('apiKey');
const captureSearchesInput = document.getElementById('captureSearches');
const captureClicksInput = document.getElementById('captureClicks');
const enabledInput = document.getElementById('enabled');
const engineInputs = {
  google: document.getElementById('engineGoogle'),
  bing: document.getElementById('engineBing'),
  duckduckgo: document.getElementById('engineDuckDuckGo'),
  startpage: document.getElementById('engineStartPage'),
  yahoo: document.getElementById('engineYahoo'),
  other: document.getElementById('engineOther'),
};

const testBtn = document.getElementById('testBtn');
const testIndicator = document.getElementById('testIndicator');
const testText = document.getElementById('testText');
const saveBtn = document.getElementById('saveBtn');
const resetBtn = document.getElementById('resetBtn');
const messageDiv = document.getElementById('message');

/**
 * Load settings from storage
 */
async function loadSettings() {
  const settings = await chrome.storage.sync.get(DEFAULTS);

  backendUrlInput.value = settings.backendUrl;
  apiKeyInput.value = settings.apiKey;
  captureSearchesInput.checked = settings.captureSearches;
  captureClicksInput.checked = settings.captureClicks;
  enabledInput.checked = settings.enabled;
  engineInputs.google.checked = settings.engineGoogle;
  engineInputs.bing.checked = settings.engineBing;
  engineInputs.duckduckgo.checked = settings.engineDuckDuckGo;
  engineInputs.startpage.checked = settings.engineStartPage;
  engineInputs.yahoo.checked = settings.engineYahoo;
  engineInputs.other.checked = settings.engineOther;
}

/**
 * Save settings to storage
 */
async function saveSettings() {
  const settings = {
    backendUrl: backendUrlInput.value.trim(),
    apiKey: apiKeyInput.value.trim(),
    captureSearches: captureSearchesInput.checked,
    captureClicks: captureClicksInput.checked,
    enabled: enabledInput.checked,
    engineGoogle: engineInputs.google.checked,
    engineBing: engineInputs.bing.checked,
    engineDuckDuckGo: engineInputs.duckduckgo.checked,
    engineStartPage: engineInputs.startpage.checked,
    engineYahoo: engineInputs.yahoo.checked,
    engineOther: engineInputs.other.checked,
  };

  await chrome.storage.sync.set(settings);
  showMessage('Settings saved successfully!', 'success');
}

/**
 * Reset to default settings
 */
async function resetSettings() {
  await chrome.storage.sync.set(DEFAULTS);
  await loadSettings();
  showMessage('Settings reset to defaults', 'success');
}

/**
 * Test backend connection
 */
async function testConnection() {
  const url = backendUrlInput.value.trim();
  const apiKey = apiKeyInput.value.trim();

  if (!url) {
    showTestResult('error', 'Please enter a backend URL');
    return;
  }

  if (!apiKey) {
    showTestResult('error', 'Please enter an API key');
    return;
  }

  testIndicator.className = 'test-indicator';
  testText.textContent = 'Testing...';

  try {
    const response = await fetch(`${url}/health`, {
      headers: { 'X-API-Key': apiKey },
    });

    if (response.ok) {
      const data = await response.json();
      showTestResult('success', `Connected! Backend v${data.version || '1.0'}`);
    } else if (response.status === 401 || response.status === 403) {
      showTestResult('error', 'Invalid API key');
    } else {
      showTestResult('error', `Server error: ${response.status}`);
    }
  } catch (error) {
    showTestResult('error', 'Cannot reach backend');
  }
}

/**
 * Show test result
 */
function showTestResult(status, message) {
  testIndicator.className = `test-indicator ${status}`;
  testText.textContent = message;
}

/**
 * Show message banner
 */
function showMessage(text, type) {
  messageDiv.textContent = text;
  messageDiv.className = `message ${type}`;
  messageDiv.style.display = 'block';

  setTimeout(() => {
    messageDiv.style.display = 'none';
  }, 3000);
}

// Event listeners
saveBtn.addEventListener('click', saveSettings);
resetBtn.addEventListener('click', resetSettings);
testBtn.addEventListener('click', testConnection);

// Auto-save when API key or URL changes
apiKeyInput.addEventListener('change', saveSettings);
backendUrlInput.addEventListener('change', saveSettings);

// Load settings on page load
loadSettings();
