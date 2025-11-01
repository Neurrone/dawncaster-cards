(function () {
  "use strict";

  const SQL_JS_VERSION = "1.8.0";
  const DEFAULT_DB_PATH = "dawncaster-cards.db";

  async function loadSqlDatabase({
    dbPath = DEFAULT_DB_PATH,
    sqlJsVersion = SQL_JS_VERSION,
  } = {}) {
    if (typeof initSqlJs !== "function") {
      throw new Error("sql.js library not loaded");
    }

    const SQL = await initSqlJs({
      locateFile: (file) =>
        `https://cdnjs.cloudflare.com/ajax/libs/sql.js/${sqlJsVersion}/${file}`,
    });

    // Bypass browser caching so each page load sees the latest generated SQLite DB.
    const response = await fetch(dbPath, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load database file");
    }

    const buffer = await response.arrayBuffer();
    return new SQL.Database(new Uint8Array(buffer));
  }

  function finalizeLoading({
    loadingId = "loading",
    filtersSelector = ".filters",
    resultsInfoId = "resultsInfo",
  } = {}) {
    const loadingElement = document.getElementById(loadingId);
    if (loadingElement) {
      loadingElement.style.display = "none";
    }

    if (filtersSelector) {
      const filters = document.querySelector(filtersSelector);
      if (filters) {
        filters.style.display = "";
      }
    }

    if (resultsInfoId) {
      const resultsInfo = document.getElementById(resultsInfoId);
      if (resultsInfo) {
        resultsInfo.style.display = "block";
      }
    }
  }

  function handleInitializationError(loadingId, error) {
    console.error("Error initializing database:", error);
    const loadingElement = document.getElementById(loadingId);
    if (loadingElement) {
      loadingElement.innerHTML = `<p class="error">Error loading database: ${error.message}</p>`;
    }
  }

  function attachFilterListeners(selectorOrElements, handler) {
    const elements = resolveElements(selectorOrElements);
    elements.forEach((element) => {
      element.addEventListener("change", handler);
    });
  }

  function setupDebouncedInput(selectorOrElement, handler, delay = 300) {
    const element = resolveElement(selectorOrElement);
    if (!element) {
      return () => {};
    }

    let timeoutId = null;
    element.addEventListener("input", () => {
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
      timeoutId = window.setTimeout(handler, delay);
    });

    return () => {
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }

  function resolveElements(selectorOrElements) {
    if (!selectorOrElements) {
      return [];
    }

    if (typeof selectorOrElements === "string") {
      return Array.from(document.querySelectorAll(selectorOrElements));
    }

    if (selectorOrElements instanceof Element) {
      return [selectorOrElements];
    }

    return Array.from(selectorOrElements);
  }

  function resolveElement(selectorOrElement) {
    if (!selectorOrElement) {
      return null;
    }

    if (typeof selectorOrElement === "string") {
      return document.querySelector(selectorOrElement);
    }

    if (selectorOrElement instanceof Element) {
      return selectorOrElement;
    }

    return null;
  }

  window.dawncasterCommon = {
    attachFilterListeners,
    finalizeLoading,
    handleInitializationError,
    loadSqlDatabase,
    setupDebouncedInput,
  };
})();
