/**
 * popup.js
 * Controller for Code2LinkedIn extension popup.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const backendStatusEl = document.getElementById("backend-status");
  const backendStatusText = document.getElementById("backend-status-text");

  const liAccountName = document.getElementById("li-account-name");
  const btnLiConnect = document.getElementById("btn-li-connect");

  const emptyState = document.getElementById("empty-state");
  const submissionCard = document.getElementById("submission-card");

  const subTitleLink = document.getElementById("sub-title-link");
  const subDifficulty = document.getElementById("sub-difficulty");
  const subStatus = document.getElementById("sub-status");
  const subId = document.getElementById("sub-id");
  const subLang = document.getElementById("sub-lang");
  const subRuntime = document.getElementById("sub-runtime");
  const subMemory = document.getElementById("sub-memory");
  const subCode = document.getElementById("sub-code");

  const screenshotImg = document.getElementById("screenshot-img");
  const screenshotPlaceholder = document.getElementById("screenshot-placeholder");
  const cloudinaryTag = document.getElementById("cloudinary-tag");
  const btnCaptureScreenshot = document.getElementById("btn-capture-screenshot");

  const btnGenerateCaption = document.getElementById("btn-generate-caption");
  const captionInput = document.getElementById("caption-input");

  const btnPublishLinkedin = document.getElementById("btn-publish-linkedin");
  const publishSuccessBanner = document.getElementById("publish-success-banner");

  const btnMockTest = document.getElementById("btn-mock-test");
  const btnClear = document.getElementById("btn-clear");
  const btnCopyCode = document.getElementById("btn-copy-code");

  let currentSubmissionId = null;

  function renderStatus() {
    chrome.runtime.sendMessage({ action: "GET_STATUS" }, (response) => {
      if (chrome.runtime.lastError || !response) {
        updateBackendStatus(false);
        showEmpty();
        return;
      }

      updateBackendStatus(response.backendOnline);
      updateLinkedInStatus(response.linkedinStatus);

      if (response.latestSubmission) {
        showSubmission(response.latestSubmission);
      } else {
        showEmpty();
      }
    });
  }

  function updateBackendStatus(isOnline) {
    backendStatusEl.className = "status-pill " + (isOnline ? "status-online" : "status-offline");
    backendStatusText.textContent = isOnline ? "Backend Live" : "Backend Offline";
  }

  function updateLinkedInStatus(liStatus) {
    if (liStatus && liStatus.authorized) {
      liAccountName.textContent = liStatus.member_name ? `Connected: ${liStatus.member_name}` : "Connected to LinkedIn";
      btnLiConnect.textContent = "Re-connect";
    } else {
      liAccountName.textContent = "LinkedIn Not Connected";
      btnLiConnect.textContent = "Connect";
    }
  }

  function showEmpty() {
    emptyState.classList.remove("hidden");
    submissionCard.classList.add("hidden");
    currentSubmissionId = null;
  }

  function showSubmission(sub) {
    emptyState.classList.add("hidden");
    submissionCard.classList.remove("hidden");
    currentSubmissionId = sub.submission_id;

    subTitleLink.textContent = sub.problem_title || sub.problem_slug || "LeetCode Problem";
    subTitleLink.href = sub.problem_url || `https://leetcode.com/problems/${sub.problem_slug}/`;

    subDifficulty.textContent = sub.difficulty || "LeetCode";
    subStatus.textContent = sub.status_msg || "Accepted";

    subId.textContent = `#${sub.submission_id}`;
    subLang.textContent = sub.language || "unknown";

    const runtimeText = sub.runtime
      ? `${sub.runtime}${sub.runtime_percentile ? ` (${sub.runtime_percentile}%)` : ""}`
      : "N/A";
    subRuntime.textContent = runtimeText;

    const memoryText = sub.memory
      ? `${sub.memory}${sub.memory_percentile ? ` (${sub.memory_percentile}%)` : ""}`
      : "N/A";
    subMemory.textContent = memoryText;

    subCode.textContent = sub.submitted_code || "// No code captured";

    // Screenshot handling
    if (sub.screenshot_data_url || sub.cloudinary_url) {
      screenshotImg.src = sub.screenshot_data_url || sub.cloudinary_url;
      screenshotImg.classList.remove("hidden");
      screenshotPlaceholder.classList.add("hidden");
    } else {
      screenshotImg.classList.add("hidden");
      screenshotPlaceholder.classList.remove("hidden");
    }

    if (sub.cloudinary_url) {
      cloudinaryTag.classList.remove("hidden");
      cloudinaryTag.textContent = "Cloudinary Synced";
      cloudinaryTag.className = "sync-tag sync-success";
    } else {
      cloudinaryTag.classList.add("hidden");
    }

    // Caption handling
    if (sub.caption) {
      captionInput.value = sub.caption;
    }

    // Published status
    if (sub.published) {
      publishSuccessBanner.classList.remove("hidden");
      publishSuccessBanner.textContent = `🎉 Published to LinkedIn (ID: ${sub.linkedin_post_id || 'Active'})`;
    } else {
      publishSuccessBanner.classList.add("hidden");
    }
  }

  // Capture Screenshot Button
  btnCaptureScreenshot.addEventListener("click", () => {
    btnCaptureScreenshot.disabled = true;
    btnCaptureScreenshot.textContent = "Capturing & Uploading...";

    chrome.runtime.sendMessage({ action: "CAPTURE_SCREENSHOT" }, (response) => {
      btnCaptureScreenshot.disabled = false;
      btnCaptureScreenshot.textContent = "📸 Recapture Screenshot";

      if (response && response.success) {
        screenshotImg.src = response.dataUrl;
        screenshotImg.classList.remove("hidden");
        screenshotPlaceholder.classList.add("hidden");

        if (response.cloudinary_url) {
          cloudinaryTag.classList.remove("hidden");
          cloudinaryTag.textContent = "Cloudinary Synced";
          cloudinaryTag.className = "sync-tag sync-success";
        }
      } else {
        alert("Failed to capture screenshot: " + (response?.error || "Unknown error"));
      }
    });
  });

  // Generate AI / Fallback Caption Button
  btnGenerateCaption.addEventListener("click", () => {
    if (!currentSubmissionId) return;

    btnGenerateCaption.disabled = true;
    btnGenerateCaption.textContent = "Generating...";

    chrome.runtime.sendMessage({
      action: "GENERATE_ANALYSIS",
      submission_id: currentSubmissionId,
    }, (response) => {
      btnGenerateCaption.disabled = false;
      btnGenerateCaption.textContent = "✨ Re-generate Caption";

      if (response && response.success && response.analysis) {
        captionInput.value = response.analysis.linkedin_caption;
      } else {
        alert("Caption generation failed: " + (response?.error || "Backend unreachable"));
      }
    });
  });

  // Publish to LinkedIn Button
  btnPublishLinkedin.addEventListener("click", () => {
    if (!currentSubmissionId) return;
    const captionText = captionInput.value.trim();
    if (!captionText) {
      alert("Please generate or enter a caption before publishing.");
      return;
    }

    btnPublishLinkedin.disabled = true;
    btnPublishLinkedin.textContent = "Publishing to LinkedIn...";

    chrome.runtime.sendMessage({
      action: "PUBLISH_LINKEDIN",
      submission_id: currentSubmissionId,
      caption: captionText,
      include_image: true,
    }, (response) => {
      btnPublishLinkedin.disabled = false;
      btnPublishLinkedin.textContent = "🚀 Approve & Publish to LinkedIn";

      if (response && response.success) {
        publishSuccessBanner.classList.remove("hidden");
        publishSuccessBanner.textContent = `🎉 Published to LinkedIn (ID: ${response.result.post_id || 'Success'})`;
        alert("Success: " + (response.result.message || "Post published successfully!"));
      } else {
        alert("LinkedIn Publication Error: " + (response?.error || "Failed to publish"));
      }
    });
  });

  // Mock Test Button
  btnMockTest.addEventListener("click", () => {
    btnMockTest.disabled = true;
    btnMockTest.textContent = "Testing...";
    chrome.runtime.sendMessage({ action: "TRIGGER_MOCK_SUBMISSION" }, (response) => {
      btnMockTest.disabled = false;
      btnMockTest.textContent = "🧪 Test Detection (Mock Data)";
      if (response?.record) {
        showSubmission(response.record);
      }
    });
  });

  // Clear Button
  btnClear.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "CLEAR_SUBMISSION" }, () => {
      showEmpty();
    });
  });

  // Copy Code Button
  btnCopyCode.addEventListener("click", () => {
    const code = subCode.textContent;
    if (code) {
      navigator.clipboard.writeText(code).then(() => {
        const orig = btnCopyCode.textContent;
        btnCopyCode.textContent = "Copied!";
        setTimeout(() => { btnCopyCode.textContent = orig; }, 1500);
      });
    }
  });

  renderStatus();
});
