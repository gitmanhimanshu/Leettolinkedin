/**
 * content.js
 * Content script running in the ISOLATED world.
 * Relays intercepted events to the background service worker, enriches with DOM metadata,
 * and maintains a fallback DOM observer.
 */

(function () {
  console.log("[Code2LinkedIn] Content script loaded in ISOLATED world.");

  // Helper to extract clean problem title from LeetCode DOM
  function extractProblemTitle(slug) {
    // 1. Modern LeetCode problem title element
    const titleEl = document.querySelector('[data-cy="question-title"]') ||
                    document.querySelector('.text-title-large') ||
                    document.querySelector('div[class*="text-title"]');
    if (titleEl && titleEl.textContent.trim()) {
      return titleEl.textContent.trim().replace(/^\d+\.\s*/, "");
    }

    // 2. Document title (e.g. "Two Sum - LeetCode")
    if (document.title && document.title.includes(" - LeetCode")) {
      const parts = document.title.split(" - LeetCode")[0].trim();
      return parts.replace(/^\d+\.\s*/, "");
    }

    // 3. Fallback from slug
    if (slug) {
      return slug
        .split("-")
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
    }

    return "LeetCode Problem";
  }

  // Helper to extract difficulty from LeetCode DOM
  function extractDifficulty() {
    const easy = document.querySelector('.text-difficulty-easy, [class*="text-olive"]');
    if (easy) return "Easy";
    const medium = document.querySelector('.text-difficulty-medium, [class*="text-yellow"]');
    if (medium) return "Medium";
    const hard = document.querySelector('.text-difficulty-hard, [class*="text-pink"]');
    if (hard) return "Hard";

    // Text content search in badges
    const badges = document.querySelectorAll('div, span');
    for (const b of badges) {
      const text = b.textContent.trim();
      if (text === "Easy" || text === "Medium" || text === "Hard") {
        return text;
      }
    }
    return null;
  }

  // Listen to messages from MAIN world inpage_interceptor.js
  window.addEventListener("message", (event) => {
    // Only accept messages from same origin and our custom interceptor
    if (event.source !== window || !event.data || event.data.source !== "CODE2LINKEDIN_INTERCEPTOR") {
      return;
    }

    const { type, payload } = event.data;

    if (type === "SUBMISSION_PENDING") {
      console.log("[Code2LinkedIn Content] Submission pending verdict:", payload.submission_id);
      chrome.runtime.sendMessage({
        action: "SUBMISSION_PENDING",
        submission_id: payload.submission_id,
      }).catch(() => {});
    }

    if (type === "SUBMISSION_ACCEPTED") {
      console.log("[Code2LinkedIn Content] Received Accepted submission from interceptor:", payload);

      const title = extractProblemTitle(payload.problem_slug);
      const difficulty = extractDifficulty();
      const problemUrl = window.location.origin + window.location.pathname;

      const submissionPayload = {
        submission_id: String(payload.submission_id),
        problem_title: title,
        problem_slug: payload.problem_slug || "unknown-problem",
        problem_url: problemUrl,
        language: payload.language || "unknown",
        submitted_code: payload.submitted_code || "// Verified submitted code",
        status_msg: "Accepted",
        runtime: payload.runtime,
        memory: payload.memory,
        runtime_percentile: payload.runtime_percentile,
        memory_percentile: payload.memory_percentile,
        difficulty: difficulty,
        timestamp: payload.timestamp || Date.now(),
      };

      // Send to background service worker
      chrome.runtime.sendMessage({
        action: "SUBMISSION_DETECTED",
        data: submissionPayload,
      }, (response) => {
        if (chrome.runtime.lastError) {
          console.warn("[Code2LinkedIn Content] Error sending to background:", chrome.runtime.lastError.message);
        } else {
          console.log("[Code2LinkedIn Content] Successfully synced with background:", response);
        }
      });
    }

    if (type === "SUBMISSION_REJECTED") {
      console.log("[Code2LinkedIn Content] Submission status not accepted:", payload.status_msg);
      chrome.runtime.sendMessage({
        action: "SUBMISSION_NON_ACCEPTED",
        data: payload,
      }).catch(() => {});
    }
  });

  // Fallback: Listen for messages from popup or background
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "GET_PAGE_METADATA") {
      const slugMatch = window.location.pathname.match(/\/problems\/([^\/\?#]+)/);
      const slug = slugMatch ? slugMatch[1] : "";
      sendResponse({
        title: extractProblemTitle(slug),
        difficulty: extractDifficulty(),
        url: window.location.href,
        slug: slug,
      });
      return true;
    }
  });
})();
