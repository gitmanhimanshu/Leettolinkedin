/**
 * inpage_interceptor.js
 * Runs in the page's MAIN world context to intercept LeetCode's network requests.
 * Captures the exact submitted source code and subsequent verdict polling response.
 */

(function () {
  const pendingSubmissions = new Map(); // submission_id -> { lang, typed_code, question_id, slug, timestamp }
  let latestSubmitPayload = null; // Stash latest submit payload while awaiting submission_id

  console.log("[Code2LinkedIn] Network interceptor initialized in MAIN world.");

  function notifyExtension(type, payload) {
    window.postMessage(
      {
        source: "CODE2LINKEDIN_INTERCEPTOR",
        type: type,
        payload: payload,
      },
      "*"
    );
  }

  // Helper to extract problem slug from current URL
  function extractSlugFromUrl(url) {
    const match = url.match(/\/problems\/([^\/\?#]+)/);
    return match ? match[1] : "";
  }

  // --- Intercept Fetch API ---
  const originalFetch = window.fetch;
  window.fetch = async function (...args) {
    const [resource, config] = args;
    const url = typeof resource === "string" ? resource : resource?.url || "";
    const method = (config?.method || (typeof resource === "object" ? resource.method : "GET") || "GET").toUpperCase();

    // 1. Intercept Submit Request
    if (url.includes("/submit") && method === "POST") {
      try {
        let bodyText = config?.body;
        if (bodyText) {
          const bodyData = typeof bodyText === "string" ? JSON.parse(bodyText) : bodyText;
          if (bodyData && bodyData.typed_code) {
            latestSubmitPayload = {
              lang: bodyData.lang || "unknown",
              typed_code: bodyData.typed_code,
              question_id: bodyData.question_id || null,
              slug: extractSlugFromUrl(url) || extractSlugFromUrl(window.location.href),
              timestamp: Date.now(),
            };
            console.log("[Code2LinkedIn] Intercepted submit request payload:", {
              lang: latestSubmitPayload.lang,
              codeLength: latestSubmitPayload.typed_code.length,
              slug: latestSubmitPayload.slug,
            });
          }
        }
      } catch (err) {
        console.warn("[Code2LinkedIn] Error parsing submit request body:", err);
      }
    }

    const response = await originalFetch.apply(this, args);

    // 2. Intercept Submit Response (contains submission_id)
    if (url.includes("/submit") && method === "POST") {
      try {
        const cloned = response.clone();
        cloned.json().then((data) => {
          if (data && data.submission_id && latestSubmitPayload) {
            const subId = String(data.submission_id);
            pendingSubmissions.set(subId, {
              ...latestSubmitPayload,
              submission_id: subId,
            });
            console.log("[Code2LinkedIn] Paired submission ID with payload:", subId);
            notifyExtension("SUBMISSION_PENDING", { submission_id: subId });
          }
        }).catch(() => {});
      } catch (err) {
        console.warn("[Code2LinkedIn] Error reading submit response:", err);
      }
    }

    // 3. Intercept Check / Verdict Polling Response
    if (url.includes("/check/") || (url.includes("/submissions/detail/") && url.includes("/check"))) {
      try {
        const cloned = response.clone();
        cloned.json().then((data) => {
          handleVerdictData(url, data);
        }).catch(() => {});
      } catch (err) {
        console.warn("[Code2LinkedIn] Error reading check response:", err);
      }
    }

    return response;
  };

  // --- Intercept XMLHttpRequest ---
  const originalOpen = XMLHttpRequest.prototype.open;
  const originalSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this._c2l_method = (method || "GET").toUpperCase();
    this._c2l_url = url ? url.toString() : "";
    return originalOpen.apply(this, [method, url, ...rest]);
  };

  XMLHttpRequest.prototype.send = function (body) {
    const url = this._c2l_url;
    const method = this._c2l_method;

    if (url.includes("/submit") && method === "POST" && body) {
      try {
        const bodyData = typeof body === "string" ? JSON.parse(body) : body;
        if (bodyData && bodyData.typed_code) {
          latestSubmitPayload = {
            lang: bodyData.lang || "unknown",
            typed_code: bodyData.typed_code,
            question_id: bodyData.question_id || null,
            slug: extractSlugFromUrl(url) || extractSlugFromUrl(window.location.href),
            timestamp: Date.now(),
          };
        }
      } catch (err) {
        console.warn("[Code2LinkedIn] XHR submit parse error:", err);
      }
    }

    this.addEventListener("load", function () {
      if (url.includes("/submit") && method === "POST") {
        try {
          const data = JSON.parse(this.responseText);
          if (data && data.submission_id && latestSubmitPayload) {
            const subId = String(data.submission_id);
            pendingSubmissions.set(subId, {
              ...latestSubmitPayload,
              submission_id: subId,
            });
            notifyExtension("SUBMISSION_PENDING", { submission_id: subId });
          }
        } catch (err) {}
      }

      if (url.includes("/check/")) {
        try {
          const data = JSON.parse(this.responseText);
          handleVerdictData(url, data);
        } catch (err) {}
      }
    });

    return originalSend.apply(this, arguments);
  };

  // --- Central Verdict Processor ---
  function handleVerdictData(url, data) {
    if (!data) return;

    // Check if verdict polling has finalized (state == "SUCCESS")
    if (data.state === "SUCCESS") {
      const subIdMatch = url.match(/\/detail\/([^\/\?#]+)\/check/);
      const submissionId = subIdMatch ? subIdMatch[1] : (data.submission_id ? String(data.submission_id) : null);

      const statusMsg = data.status_msg || (data.status_code === 10 ? "Accepted" : "Unknown");
      const isAccepted = statusMsg === "Accepted" || data.status_code === 10;

      // Retrieve verified submitted code
      let matchedSubmission = submissionId ? pendingSubmissions.get(String(submissionId)) : null;
      if (!matchedSubmission && latestSubmitPayload) {
        matchedSubmission = latestSubmitPayload;
      }

      const verifiedCode = matchedSubmission ? matchedSubmission.typed_code : "";
      const lang = matchedSubmission ? matchedSubmission.lang : (data.lang || "unknown");
      const slug = matchedSubmission ? matchedSubmission.slug : extractSlugFromUrl(window.location.href);

      const verdictPayload = {
        submission_id: submissionId || `sub_${Date.now()}`,
        status_msg: statusMsg,
        is_accepted: isAccepted,
        language: lang,
        submitted_code: verifiedCode,
        problem_slug: slug,
        runtime: data.status_runtime || (data.runtime ? `${data.runtime} ms` : null),
        memory: data.status_memory || (data.memory ? `${data.memory} MB` : null),
        runtime_percentile: data.runtime_percentile != null ? Number(data.runtime_percentile) : null,
        memory_percentile: data.memory_percentile != null ? Number(data.memory_percentile) : null,
        total_correct: data.total_correct != null ? data.total_correct : null,
        total_testcases: data.total_testcases != null ? data.total_testcases : null,
        timestamp: Date.now(),
      };

      if (isAccepted) {
        console.log("[Code2LinkedIn] Confirmed ACCEPTED submission:", verdictPayload.submission_id);
        notifyExtension("SUBMISSION_ACCEPTED", verdictPayload);
      } else {
        console.log(`[Code2LinkedIn] Submission finalized with status '${statusMsg}'. Ignoring per default settings.`);
        notifyExtension("SUBMISSION_REJECTED", verdictPayload);
      }

      // Cleanup pending cache
      if (submissionId) {
        pendingSubmissions.delete(String(submissionId));
      }
    }
  }
})();
