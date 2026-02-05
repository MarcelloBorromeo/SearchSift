/**
 * SearchSift Background Script (Firefox version)
 *
 * Firefox uses 'browser.*' APIs instead of 'chrome.*'
 * This script is adapted for Firefox Manifest V2.
 */

// Use browser API with chrome fallback for compatibility
const browserAPI = typeof browser !== 'undefined' ? browser : chrome;

// Configuration
const CONFIG = {
  backendUrl: 'http://127.0.0.1:5000/ingest',
  batchSize: 20,
  batchTimeoutMs: 10000,
  maxRetries: 5,
  baseRetryDelayMs: 1000,
  minRequestIntervalMs: 1000,
  dedupeWindowMs: 5000,
  maxEventAgeMs: 10000,
};

// State
let eventBuffer = [];
let batchTimeout = null;
let lastRequestTime = 0;
let recentEvents = [];
let apiKey = null;

// Load API key from storage
browserAPI.storage.sync.get(['apiKey']).then((result) => {
  apiKey = result.apiKey || null;
  console.log('[SearchSift] API key loaded:', apiKey ? 'Yes' : 'No');
});

// Listen for API key changes
browserAPI.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'sync' && changes.apiKey) {
    apiKey = changes.apiKey.newValue;
    console.log('[SearchSift] API key updated');
  }
});

/**
 * Check if an event is a duplicate
 */
function isDuplicate(event) {
  const now = Date.now();
  const key = `${event.query}|${event.url}`;

  recentEvents = recentEvents.filter(e => now - e.time < CONFIG.dedupeWindowMs);

  const isDupe = recentEvents.some(e => e.key === key);

  if (!isDupe) {
    recentEvents.push({ key, time: now });
  }

  return isDupe;
}

/**
 * Validate event timestamp
 */
function isValidTimestamp(timestamp) {
  const eventTime = new Date(timestamp).getTime();
  const now = Date.now();
  return (now - eventTime) <= CONFIG.maxEventAgeMs;
}

/**
 * Add event to buffer
 */
function bufferEvent(event) {
  if (!isValidTimestamp(event.timestamp)) {
    console.log('[SearchSift] Rejecting stale event:', event.timestamp);
    return;
  }

  if (isDuplicate(event)) {
    console.log('[SearchSift] Skipping duplicate event:', event.query);
    return;
  }

  eventBuffer.push(event);
  console.log('[SearchSift] Buffered event:', event.query, 'Buffer size:', eventBuffer.length);

  if (eventBuffer.length >= CONFIG.batchSize) {
    flushBuffer();
  } else if (!batchTimeout) {
    batchTimeout = setTimeout(flushBuffer, CONFIG.batchTimeoutMs);
  }
}

/**
 * Flush the event buffer
 */
async function flushBuffer() {
  if (batchTimeout) {
    clearTimeout(batchTimeout);
    batchTimeout = null;
  }

  if (eventBuffer.length === 0) {
    return;
  }

  const now = Date.now();
  const timeSinceLastRequest = now - lastRequestTime;
  if (timeSinceLastRequest < CONFIG.minRequestIntervalMs) {
    const delay = CONFIG.minRequestIntervalMs - timeSinceLastRequest;
    await new Promise(resolve => setTimeout(resolve, delay));
  }

  const eventsToSend = [...eventBuffer];
  eventBuffer = [];

  await sendWithRetry(eventsToSend);
}

/**
 * Send events with retry
 */
async function sendWithRetry(events, attempt = 0) {
  if (!apiKey) {
    console.error('[SearchSift] No API key configured.');
    eventBuffer = [...events, ...eventBuffer];
    return;
  }

  try {
    lastRequestTime = Date.now();

    const response = await fetch(CONFIG.backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: JSON.stringify({ events }),
    });

    if (response.ok) {
      console.log('[SearchSift] Successfully sent', events.length, 'events');
      updateBadge(events.length, 'success');
    } else if (response.status === 401 || response.status === 403) {
      console.error('[SearchSift] Authentication failed.');
      updateBadge('!', 'error');
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    console.error('[SearchSift] Send failed:', error.message);

    if (attempt < CONFIG.maxRetries) {
      const delay = CONFIG.baseRetryDelayMs * Math.pow(2, attempt);
      console.log(`[SearchSift] Retrying in ${delay}ms (attempt ${attempt + 1}/${CONFIG.maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, delay));
      return sendWithRetry(events, attempt + 1);
    } else {
      console.error('[SearchSift] Max retries exceeded.');
      updateBadge('!', 'error');
    }
  }
}

/**
 * Update extension badge
 */
function updateBadge(text, status) {
  const color = status === 'success' ? '#22c55e' : '#ef4444';
  browserAPI.browserAction.setBadgeText({ text: String(text) });
  browserAPI.browserAction.setBadgeBackgroundColor({ color });

  setTimeout(() => {
    browserAPI.browserAction.setBadgeText({ text: '' });
  }, 3000);
}

/**
 * Handle messages from content scripts
 */
browserAPI.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SEARCH_EVENT') {
    const event = {
      ...message.data,
      tabId: sender.tab?.id,
      windowId: sender.tab?.windowId,
      timestamp: message.data.timestamp || new Date().toISOString(),
    };

    bufferEvent(event);
    sendResponse({ status: 'buffered' });
  } else if (message.type === 'GET_STATUS') {
    sendResponse({
      bufferSize: eventBuffer.length,
      hasApiKey: !!apiKey,
    });
  }

  return true;
});

// Handle install/update
browserAPI.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('[SearchSift] Extension installed');
    browserAPI.runtime.openOptionsPage();
  }
});

console.log('[SearchSift] Background script started (Firefox)');
