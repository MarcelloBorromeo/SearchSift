/**
 * SearchSift Background Service Worker
 *
 * Handles:
 * - Receiving messages from content scripts
 * - Batching events (up to 20 items or 10 seconds)
 * - Sending to backend with exponential backoff retry
 * - Rate limiting (max 1 request per second)
 */

// Configuration
const CONFIG = {
  backendUrl: 'http://127.0.0.1:5050/ingest',
  batchSize: 20,
  batchTimeoutMs: 10000,
  maxRetries: 5,
  baseRetryDelayMs: 1000,
  minRequestIntervalMs: 1000, // Rate limit: 1 req/sec
  dedupeWindowMs: 5000, // Ignore duplicate query+url within 5s
  maxEventAgeMs: 10000, // Reject events older than 10s (idle detection)
};

// State
let eventBuffer = [];
let batchTimeout = null;
let lastRequestTime = 0;
let recentEvents = []; // For deduplication
let apiKey = null;

// Load API key from storage on startup
chrome.storage.sync.get(['apiKey'], (result) => {
  apiKey = result.apiKey || null;
  console.log('[SearchSift] API key loaded:', apiKey ? 'Yes' : 'No');
});

// Listen for API key changes
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'sync' && changes.apiKey) {
    apiKey = changes.apiKey.newValue;
    console.log('[SearchSift] API key updated');
  }
});

/**
 * Check if an event is a duplicate (same query+url within dedupeWindowMs)
 */
function isDuplicate(event) {
  const now = Date.now();
  const key = `${event.query}|${event.url}`;

  // Clean old entries
  recentEvents = recentEvents.filter(e => now - e.time < CONFIG.dedupeWindowMs);

  // Check for duplicate
  const isDupe = recentEvents.some(e => e.key === key);

  if (!isDupe) {
    recentEvents.push({ key, time: now });
  }

  return isDupe;
}

/**
 * Validate event timestamp (reject if older than maxEventAgeMs)
 */
function isValidTimestamp(timestamp) {
  const eventTime = new Date(timestamp).getTime();
  const now = Date.now();
  return (now - eventTime) <= CONFIG.maxEventAgeMs;
}

/**
 * Add event to buffer and trigger batch send if needed
 */
function bufferEvent(event) {
  // Validate timestamp (idle detection)
  if (!isValidTimestamp(event.timestamp)) {
    console.log('[SearchSift] Rejecting stale event:', event.timestamp);
    return;
  }

  // Check for duplicates
  if (isDuplicate(event)) {
    console.log('[SearchSift] Skipping duplicate event:', event.query);
    return;
  }

  eventBuffer.push(event);
  console.log('[SearchSift] Buffered event:', event.query, 'Buffer size:', eventBuffer.length);

  // Send immediately if batch is full
  if (eventBuffer.length >= CONFIG.batchSize) {
    flushBuffer();
  } else if (!batchTimeout) {
    // Set timeout to flush partial batch
    batchTimeout = setTimeout(flushBuffer, CONFIG.batchTimeoutMs);
  }
}

/**
 * Flush the event buffer to backend
 */
async function flushBuffer() {
  if (batchTimeout) {
    clearTimeout(batchTimeout);
    batchTimeout = null;
  }

  if (eventBuffer.length === 0) {
    return;
  }

  // Rate limiting: ensure minimum interval between requests
  const now = Date.now();
  const timeSinceLastRequest = now - lastRequestTime;
  if (timeSinceLastRequest < CONFIG.minRequestIntervalMs) {
    const delay = CONFIG.minRequestIntervalMs - timeSinceLastRequest;
    await new Promise(resolve => setTimeout(resolve, delay));
  }

  // Take events from buffer
  const eventsToSend = [...eventBuffer];
  eventBuffer = [];

  // Send with retry
  await sendWithRetry(eventsToSend);
}

/**
 * Send events to backend with exponential backoff retry
 */
async function sendWithRetry(events, attempt = 0) {
  if (!apiKey) {
    console.error('[SearchSift] No API key configured. Please set it in extension options.');
    // Put events back in buffer for later
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
      // Update badge to show success
      updateBadge(events.length, 'success');
    } else if (response.status === 401 || response.status === 403) {
      console.error('[SearchSift] Authentication failed. Check API key.');
      updateBadge('!', 'error');
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    console.error('[SearchSift] Send failed:', error.message);

    if (attempt < CONFIG.maxRetries) {
      // Exponential backoff
      const delay = CONFIG.baseRetryDelayMs * Math.pow(2, attempt);
      console.log(`[SearchSift] Retrying in ${delay}ms (attempt ${attempt + 1}/${CONFIG.maxRetries})`);

      await new Promise(resolve => setTimeout(resolve, delay));
      return sendWithRetry(events, attempt + 1);
    } else {
      console.error('[SearchSift] Max retries exceeded. Events lost:', events.length);
      updateBadge('!', 'error');
    }
  }
}

/**
 * Update extension badge to show status
 */
function updateBadge(text, status) {
  const color = status === 'success' ? '#22c55e' : '#ef4444';
  chrome.action.setBadgeText({ text: String(text) });
  chrome.action.setBadgeBackgroundColor({ color });

  // Clear badge after 3 seconds
  setTimeout(() => {
    chrome.action.setBadgeText({ text: '' });
  }, 3000);
}

/**
 * Handle messages from content scripts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
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

  return true; // Keep channel open for async response
});

// Handle extension install/update
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('[SearchSift] Extension installed');
    // Open options page for initial setup
    chrome.runtime.openOptionsPage();
  } else if (details.reason === 'update') {
    console.log('[SearchSift] Extension updated to version', chrome.runtime.getManifest().version);
  }
});

// Flush buffer before service worker terminates
self.addEventListener('beforeunload', () => {
  if (eventBuffer.length > 0) {
    flushBuffer();
  }
});

console.log('[SearchSift] Background service worker started');
