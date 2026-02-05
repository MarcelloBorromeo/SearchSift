/**
 * SearchSift Content Script
 *
 * Detects:
 * - Search form submissions
 * - Search query from URL parameters
 * - Clicks on search result links
 *
 * Supported search engines:
 * - Google, Bing, DuckDuckGo, StartPage, Yahoo,
 * - Yandex, Baidu, Ecosia, Qwant, Brave Search
 */

(function() {
  'use strict';

  // Prevent multiple injections
  if (window.__searchSiftInjected) return;
  window.__searchSiftInjected = true;

  // Search engine configurations
  const SEARCH_ENGINES = {
    google: {
      hostPatterns: [/\.google\./],
      queryParams: ['q'],
      searchInputSelectors: ['input[name="q"]', 'textarea[name="q"]'],
      resultLinkSelectors: ['#search a[href]', '#rso a[href]', 'a[data-ved]'],
      excludeLinkPatterns: [/google\.com\/search/, /google\.com\/url/, /^#/, /^javascript:/],
    },
    bing: {
      hostPatterns: [/\.bing\.com/],
      queryParams: ['q'],
      searchInputSelectors: ['input[name="q"]'],
      resultLinkSelectors: ['#b_results a[href]', '.b_algo a[href]'],
      excludeLinkPatterns: [/bing\.com\/search/, /^#/, /^javascript:/],
    },
    duckduckgo: {
      hostPatterns: [/duckduckgo\.com/],
      queryParams: ['q'],
      searchInputSelectors: ['input[name="q"]'],
      resultLinkSelectors: ['.result__a', 'a[data-testid="result-title-a"]'],
      excludeLinkPatterns: [/duckduckgo\.com/, /^#/, /^javascript:/],
    },
    startpage: {
      hostPatterns: [/startpage\.com/],
      queryParams: ['query', 'q'],
      searchInputSelectors: ['input[name="query"]', 'input[name="q"]'],
      resultLinkSelectors: ['.w-gl__result-title', 'a.result-link'],
      excludeLinkPatterns: [/startpage\.com/, /^#/, /^javascript:/],
    },
    yahoo: {
      hostPatterns: [/search\.yahoo\.com/],
      queryParams: ['p'],
      searchInputSelectors: ['input[name="p"]'],
      resultLinkSelectors: ['.algo-sr a[href]', 'a.ac-algo'],
      excludeLinkPatterns: [/yahoo\.com\/search/, /^#/, /^javascript:/],
    },
    yandex: {
      hostPatterns: [/yandex\.(com|ru)/],
      queryParams: ['text'],
      searchInputSelectors: ['input[name="text"]'],
      resultLinkSelectors: ['.serp-item a[href]', '.organic__url'],
      excludeLinkPatterns: [/yandex\.(com|ru)\/search/, /^#/, /^javascript:/],
    },
    baidu: {
      hostPatterns: [/baidu\.com/],
      queryParams: ['wd', 'word'],
      searchInputSelectors: ['input[name="wd"]', 'input[name="word"]'],
      resultLinkSelectors: ['.result a[href]', '.c-container a[href]'],
      excludeLinkPatterns: [/baidu\.com\/s/, /^#/, /^javascript:/],
    },
    ecosia: {
      hostPatterns: [/ecosia\.org/],
      queryParams: ['q'],
      searchInputSelectors: ['input[name="q"]'],
      resultLinkSelectors: ['.result__link', 'a[data-test-id="mainline-result-link"]'],
      excludeLinkPatterns: [/ecosia\.org\/search/, /^#/, /^javascript:/],
    },
    qwant: {
      hostPatterns: [/qwant\.com/],
      queryParams: ['q'],
      searchInputSelectors: ['input[name="q"]'],
      resultLinkSelectors: ['a[data-testid="webResult"]', '.result a'],
      excludeLinkPatterns: [/qwant\.com/, /^#/, /^javascript:/],
    },
    brave: {
      hostPatterns: [/search\.brave\.com/],
      queryParams: ['q'],
      searchInputSelectors: ['input[name="q"]'],
      resultLinkSelectors: ['.snippet a[href]', '.result-header a'],
      excludeLinkPatterns: [/brave\.com\/search/, /^#/, /^javascript:/],
    },
  };

  /**
   * Detect which search engine we're on
   */
  function detectSearchEngine() {
    const hostname = window.location.hostname;

    for (const [engine, config] of Object.entries(SEARCH_ENGINES)) {
      if (config.hostPatterns.some(pattern => pattern.test(hostname))) {
        return { name: engine, config };
      }
    }

    return null;
  }

  /**
   * Extract search query from URL parameters
   */
  function getQueryFromUrl(config) {
    const params = new URLSearchParams(window.location.search);

    for (const param of config.queryParams) {
      const value = params.get(param);
      if (value) {
        return value.trim();
      }
    }

    return null;
  }

  /**
   * Extract search query from input fields
   */
  function getQueryFromInput(config) {
    for (const selector of config.searchInputSelectors) {
      const input = document.querySelector(selector);
      if (input && input.value) {
        return input.value.trim();
      }
    }

    return null;
  }

  /**
   * Send event to background script
   */
  function sendEvent(eventData) {
    chrome.runtime.sendMessage({
      type: 'SEARCH_EVENT',
      data: eventData,
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('[SearchSift] Error sending event:', chrome.runtime.lastError.message);
      } else {
        console.log('[SearchSift] Event sent:', response?.status);
      }
    });
  }

  /**
   * Check if URL should be excluded
   */
  function shouldExcludeUrl(url, patterns) {
    return patterns.some(pattern => pattern.test(url));
  }

  /**
   * Main initialization
   */
  function init() {
    const engine = detectSearchEngine();
    if (!engine) {
      console.log('[SearchSift] Not a recognized search engine');
      return;
    }

    console.log('[SearchSift] Detected search engine:', engine.name);

    // Capture search query from URL on page load (search results page)
    const queryFromUrl = getQueryFromUrl(engine.config);
    if (queryFromUrl && isSearchResultsPage()) {
      console.log('[SearchSift] Captured search query:', queryFromUrl);
      sendEvent({
        type: 'search',
        query: queryFromUrl,
        url: window.location.href,
        engine: engine.name,
        timestamp: new Date().toISOString(),
      });
    }

    // Listen for form submissions
    setupFormListeners(engine);

    // Listen for clicks on search results
    setupClickListeners(engine);

    // Watch for dynamic content (SPA navigation)
    setupMutationObserver(engine);
  }

  /**
   * Check if current page is a search results page
   */
  function isSearchResultsPage() {
    const path = window.location.pathname;
    const search = window.location.search;

    // Common patterns for search results pages
    return (
      path.includes('/search') ||
      path.includes('/results') ||
      path === '/' && search.length > 0 ||
      search.includes('q=') ||
      search.includes('query=') ||
      search.includes('p=')
    );
  }

  /**
   * Set up listeners for search form submissions
   */
  function setupFormListeners(engine) {
    // Listen for form submit
    document.addEventListener('submit', (event) => {
      const form = event.target;
      const query = getQueryFromInput(engine.config);

      if (query) {
        console.log('[SearchSift] Form submitted with query:', query);
        sendEvent({
          type: 'search',
          query: query,
          url: window.location.href,
          engine: engine.name,
          timestamp: new Date().toISOString(),
        });
      }
    }, true);

    // Listen for Enter key in search inputs
    engine.config.searchInputSelectors.forEach(selector => {
      const inputs = document.querySelectorAll(selector);
      inputs.forEach(input => {
        input.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' && input.value.trim()) {
            console.log('[SearchSift] Enter pressed with query:', input.value);
            sendEvent({
              type: 'search',
              query: input.value.trim(),
              url: window.location.href,
              engine: engine.name,
              timestamp: new Date().toISOString(),
            });
          }
        });
      });
    });
  }

  /**
   * Set up listeners for clicks on search results
   */
  function setupClickListeners(engine) {
    document.addEventListener('click', (event) => {
      // Find the clicked link (or parent link)
      let link = event.target;
      while (link && link.tagName !== 'A') {
        link = link.parentElement;
      }

      if (!link || !link.href) return;

      const href = link.href;

      // Check if this is a search result link
      const isResultLink = engine.config.resultLinkSelectors.some(selector => {
        return link.matches(selector) || link.closest(selector);
      });

      if (!isResultLink) return;

      // Check if URL should be excluded
      if (shouldExcludeUrl(href, engine.config.excludeLinkPatterns)) return;

      // Get the search query
      const query = getQueryFromUrl(engine.config) || getQueryFromInput(engine.config);

      if (query) {
        console.log('[SearchSift] Result click:', href);
        sendEvent({
          type: 'click',
          query: query,
          url: href,
          engine: engine.name,
          timestamp: new Date().toISOString(),
        });
      }
    }, true);
  }

  /**
   * Watch for dynamic content changes (SPA navigation)
   */
  function setupMutationObserver(engine) {
    let lastUrl = window.location.href;

    // Check for URL changes
    const checkUrlChange = () => {
      if (window.location.href !== lastUrl) {
        lastUrl = window.location.href;

        const query = getQueryFromUrl(engine.config);
        if (query && isSearchResultsPage()) {
          console.log('[SearchSift] SPA navigation, new search:', query);
          sendEvent({
            type: 'search',
            query: query,
            url: window.location.href,
            engine: engine.name,
            timestamp: new Date().toISOString(),
          });
        }
      }
    };

    // Listen for history changes
    window.addEventListener('popstate', checkUrlChange);

    // Intercept history API
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = function(...args) {
      originalPushState.apply(this, args);
      setTimeout(checkUrlChange, 100);
    };

    history.replaceState = function(...args) {
      originalReplaceState.apply(this, args);
      setTimeout(checkUrlChange, 100);
    };
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
