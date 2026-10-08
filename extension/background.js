/**
 * background.js
 * Chrome Extension Manifest V3 Service Worker.
 * Handles submission detection, screenshot capture, Cloudinary sync, AI caption generation, and LinkedIn publishing.
 * Supports configurable backend URL (Localhost or Vercel).
 */

const DEFAULT_BACKEND_URL = "https://backend-tau-five-76.vercel.app";

// Retrieve configured backend URL (e.g. localhost or Vercel)
async function getBackendUrl() {
  const data = await chrome.storage.local.get(["backend_url"]);
  if (!data.backend_url || data.backend_url.includes("127.0.0.1") || data.backend_url.includes("localhost")) {
    await chrome.storage.local.set({ backend_url: DEFAULT_BACKEND_URL });
    return DEFAULT_BACKEND_URL;
  }
  return data.backend_url.replace(/\/+$/, "");
}

// Helper to set extension action badge
function updateBadge(text, color) {
  chrome.action.setBadgeText({ text });
  if (color) {
    chrome.action.setBadgeBackgroundColor({ color });
  }
}

// Sync detected submission with FastAPI backend
async function syncWithBackend(submissionData) {
  try {
    const backendUrl = await getBackendUrl();
    const res = await fetch(`${backendUrl}/api/submissions/detect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(submissionData),
    });

    if (!res.ok) {
      throw new Error(`Backend returned status ${res.status}`);
    }

    const json = await res.json();
    return { success: true, backendRecord: json };
  } catch (err) {
    console.warn("[Code2LinkedIn Background] Backend sync error:", err.message);
    return { success: false, error: err.message };
  }
}

// Central Message Listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const { action, data, submission_id, caption, include_image, new_backend_url } = message;

  if (action === "SUBMISSION_PENDING") {
    updateBadge("...", "#F59E0B"); // Amber
    sendResponse({ status: "pending_recorded" });
    return true;
  }

  if (action === "SUBMISSION_NON_ACCEPTED") {
    updateBadge("", "#6B7280");
    sendResponse({ status: "ignored_non_accepted" });
    return true;
  }

  // 1. New Submission Detected
  if (action === "SUBMISSION_DETECTED") {
    chrome.storage.local.get(["latest_submission", "processed_ids"], async (storage) => {
      const processedIds = storage.processed_ids || [];
      const isDuplicate = processedIds.includes(data.submission_id);

      updateBadge("ACC", "#10B981");

      const backendResult = await syncWithBackend(data);

      const recordToStore = {
        ...data,
        is_duplicate: isDuplicate,
        backend_synced: backendResult.success,
        backend_record: backendResult.backendRecord || null,
        screenshot_data_url: null,
        cloudinary_url: null,
        caption: null,
        detected_at: new Date().toISOString(),
      };

      if (!isDuplicate) {
        processedIds.push(data.submission_id);
      }

      await chrome.storage.local.set({
        latest_submission: recordToStore,
        processed_ids: processedIds,
      });

      sendResponse({ status: "success", record: recordToStore });
    });
    return true;
  }

  // 2. Capture Screenshot of Visible Tab
  if (action === "CAPTURE_SCREENSHOT") {
    chrome.tabs.captureVisibleTab(null, { format: "png" }, async (dataUrl) => {
      if (chrome.runtime.lastError || !dataUrl) {
        sendResponse({ success: false, error: chrome.runtime.lastError?.message || "Capture failed" });
        return;
      }

      // Update local storage with screenshot
      chrome.storage.local.get(["latest_submission"], async (items) => {
        const sub = items.latest_submission;
        if (sub) {
          sub.screenshot_data_url = dataUrl;
          await chrome.storage.local.set({ latest_submission: sub });

          // Upload to Cloudinary via backend if submission exists
          try {
            const backendUrl = await getBackendUrl();
            const uploadRes = await fetch(`${backendUrl}/api/submissions/upload-screenshot`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                submission_id: sub.submission_id,
                image_data: dataUrl,
              }),
            });

            if (uploadRes.ok) {
              const uploadData = await uploadRes.json();
              sub.cloudinary_url = uploadData.cloudinary_url;
              await chrome.storage.local.set({ latest_submission: sub });
            }
          } catch (e) {
            console.warn("[Code2LinkedIn Background] Cloudinary upload via backend failed:", e);
          }
        }

        sendResponse({ success: true, dataUrl: dataUrl, cloudinary_url: sub?.cloudinary_url });
      });
    });
    return true;
  }

  // 3. Generate Analysis & Caption (Grok / Rule-based Fallback)
  if (action === "GENERATE_ANALYSIS") {
    (async () => {
      try {
        const backendUrl = await getBackendUrl();
        const res = await fetch(`${backendUrl}/api/submissions/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ submission_id: submission_id }),
        });

        if (!res.ok) {
          throw new Error(`Analyze API failed with status ${res.status}`);
        }

        const analysis = await res.json();

        // Update local storage with generated caption
        chrome.storage.local.get(["latest_submission"], async (items) => {
          const sub = items.latest_submission;
          if (sub) {
            sub.ai_analysis = analysis;
            sub.caption = analysis.linkedin_caption;
            await chrome.storage.local.set({ latest_submission: sub });
          }
        });

        sendResponse({ success: true, analysis: analysis });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  // 4. Publish to LinkedIn
  if (action === "PUBLISH_LINKEDIN") {
    (async () => {
      try {
        const backendUrl = await getBackendUrl();
        const res = await fetch(`${backendUrl}/api/linkedin/publish`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            submission_id: submission_id,
            caption: caption,
            include_image: include_image !== false,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Publish failed with status ${res.status}`);
        }

        const pubResult = await res.json();
        updateBadge("POST", "#38BDF8"); // Sky blue badge for published

        // Update local storage
        chrome.storage.local.get(["latest_submission"], async (items) => {
          const sub = items.latest_submission;
          if (sub) {
            sub.linkedin_post_id = pubResult.post_id;
            sub.published = true;
            await chrome.storage.local.set({ latest_submission: sub });
          }
        });

        sendResponse({ success: true, result: pubResult });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  // 5. Query Backend & LinkedIn Status
  if (action === "GET_STATUS") {
    (async () => {
      let backendHealthy = false;
      let linkedinStatus = { configured: false, authorized: false, member_name: null };
      const backendUrl = await getBackendUrl();

      try {
        const res = await fetch(`${backendUrl}/api/health`, { method: "GET" });
        if (res.ok) {
          const healthJson = await res.json();
          backendHealthy = healthJson.status === "healthy";
        }
      } catch (e) {
        backendHealthy = false;
      }

      if (backendHealthy) {
        try {
          const liRes = await fetch(`${backendUrl}/api/auth/linkedin/status`, { method: "GET" });
          if (liRes.ok) {
            linkedinStatus = await liRes.json();
          }
        } catch (e) {}
      }

      chrome.storage.local.get(["latest_submission", "backend_url"], (items) => {
        sendResponse({
          backendOnline: backendHealthy,
          backendUrl: items.backend_url || DEFAULT_BACKEND_URL,
          linkedinStatus: linkedinStatus,
          latestSubmission: items.latest_submission || null,
        });
      });
    })();
    return true;
  }

  // 6. Save Backend URL Setting
  if (action === "SET_BACKEND_URL") {
    const cleanUrl = (new_backend_url || DEFAULT_BACKEND_URL).trim().replace(/\/+$/, "");
    chrome.storage.local.set({ backend_url: cleanUrl }, () => {
      sendResponse({ status: "saved", backendUrl: cleanUrl });
    });
    return true;
  }

  // 7. Clear Submission
  if (action === "CLEAR_SUBMISSION") {
    chrome.storage.local.remove(["latest_submission"], () => {
      updateBadge("", "#000000");
      sendResponse({ status: "cleared" });
    });
    return true;
  }

  // 8. Mock Test Trigger
  if (action === "TRIGGER_MOCK_SUBMISSION") {
    const mockData = {
      submission_id: `mock_${Date.now()}`,
      problem_title: "Two Sum",
      problem_slug: "two-sum",
      problem_url: "https://leetcode.com/problems/two-sum/",
      language: "python3",
      submitted_code: `class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        seen = {}\n        for i, num in enumerate(nums):\n            diff = target - num\n            if diff in seen:\n                return [seen[diff], i]\n            seen[num] = i\n        return []`,
      status_msg: "Accepted",
      runtime: "45 ms",
      memory: "17.4 MB",
      runtime_percentile: 88.5,
      memory_percentile: 74.2,
      difficulty: "Easy",
      timestamp: Date.now(),
    };

    updateBadge("ACC", "#10B981");

    (async () => {
      const backendResult = await syncWithBackend(mockData);
      const record = {
        ...mockData,
        backend_synced: backendResult.success,
        backend_record: backendResult.backendRecord || null,
        screenshot_data_url: null,
        cloudinary_url: null,
        caption: null,
        detected_at: new Date().toISOString(),
      };
      await chrome.storage.local.set({ latest_submission: record });
      sendResponse({ status: "success", record });
    })();

    return true;
  }
});
