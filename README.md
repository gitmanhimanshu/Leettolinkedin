# Code2LinkedIn — Automated LeetCode-to-LinkedIn AI Agent

Code2LinkedIn is a production-grade developer tool that detects your LeetCode submissions directly from your browser, extracts and verifies the exact submitted source code, analyzes the algorithmic solution (via xAI's Grok API or intelligent rule-based fallback), captures a high-resolution screenshot of the Accepted result, uploads the image to Cloudinary, and drafts or publishes a professional LinkedIn post with the screenshot attached.

---

## 1. System Architecture & End-to-End Flow

```
[ LeetCode Tab (Chrome) ]
        │
        ▼ (Intercepts POST /problems/*/submit/)
  [ inpage_interceptor.js (MAIN World) ]
        │ captures exact typed_code, lang, slug, submission_id
        ▼ (Intercepts GET /submissions/detail/*/check/)
  [ inpage_interceptor.js ]
        │ confirms state == SUCCESS & status_msg == "Accepted"
        ▼ window.postMessage
  [ content.js (ISOLATED World) ]
        │ enriches with problem title, difficulty, URL
        ▼ chrome.runtime.sendMessage
  [ background.js (Service Worker) ]
        ├── Sets badge to "ACC" (Green)
        ├── Captures tab screenshot (chrome.tabs.captureVisibleTab)
        └── POST /api/submissions/detect ──▶ [ FastAPI Backend (:8000) ]
                                                    │
                                                    ├── 1. Grok / Fallback Engine (generates post caption & complexity)
                                                    ├── 2. Cloudinary Service (uploads screenshot & stores secure URL)
                                                    └── 3. LinkedIn Posts API (publishes commentary + uploaded image)
```

---

## 2. Directory Structure

```
code2linkedin/
├── .env                          # Local credentials (git-ignored)
├── .env.example                  # Environment template
├── .gitignore
├── README.md                     # Complete project documentation
├── t.txt                         # Specification prompt
├── backend/
│   ├── requirements.txt          # Python dependencies
│   ├── .env                      # Backend environment file
│   ├── app/
│   │   ├── main.py               # FastAPI entry point, CORS, and router mounts
│   │   ├── config.py             # Pydantic Settings & environment validation
│   │   ├── models/
│   │   │   └── submission.py     # Submission dataclass entity
│   │   ├── schemas/
│   │   │   ├── submission.py     # Submission validation models & ProcessingState enum
│   │   │   └── analysis.py       # GrokAnalysisResult & Post publish models
│   │   ├── routes/
│   │   │   ├── health.py         # GET /api/health
│   │   │   ├── submissions.py    # POST /detect, /manual, /analyze, /upload-screenshot
│   │   │   └── linkedin.py       # GET /api/auth/linkedin/*, POST /api/linkedin/publish
│   │   ├── repositories/
│   │   │   └── submission_repo.py# PyMongo + In-memory fallback repository
│   │   └── services/
│   │       ├── leetcode_service.py # Submission deduplication & state tracking
│   │       ├── grok_service.py     # xAI Grok API + Rule-based fallback engine
│   │       ├── screenshot_service.py # Pillow image validation & bytes decoding
│   │       ├── cloudinary_service.py # Cloudinary SDK image upload & asset management
│   │       └── linkedin_service.py   # LinkedIn OAuth 2.0 & official Posts API
│   └── tests/
│       ├── test_health.py        # Health & root route tests (2 tests)
│       ├── test_submissions.py   # Idempotency, validation & retrieval (6 tests)
│       ├── test_analysis.py      # Grok & rule-based fallback analysis (2 tests)
│       ├── test_screenshot.py    # Image validation & corrupted checks (3 tests)
│       └── test_linkedin.py      # OAuth status, redirect & draft post (3 tests)
└── extension/
    ├── manifest.json             # Manifest V3 (MAIN & ISOLATED world scripts)
    ├── inpage_interceptor.js     # Intercepts fetch/XHR /submit and /check responses
    ├── content.js                # Bridges page events with DOM metadata
    ├── background.js             # Service worker: badge, screenshots, sync, publish
    ├── popup.html                # Popup UI: Code, Screenshot, Caption editor, LinkedIn publish
    ├── popup.css                 # Dark theme styling
    ├── popup.js                  # Popup interactive controller
    └── icons/                    # icon16.png, icon48.png, icon128.png
```

---

## 3. How to Run the Project

### Step 1: Start Backend
In your terminal:
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
* **Docs URL:** `http://127.0.0.1:8000/docs`
* **Health Check:** `http://127.0.0.1:8000/api/health`

### Step 2: Load Extension in Chrome
1. Open Google Chrome and go to `chrome://extensions/`
2. Turn ON **Developer mode** (top right toggle).
3. Click **Load unpacked** and select the folder:
   `C:\Users\PUREWATERMART\OneDrive\Desktop\code2linkedin\extension`
4. The **Code2LinkedIn** extension icon will appear in your Chrome toolbar.

### Step 3: Connect LinkedIn (1-Time Setup)
1. Click the **Code2LinkedIn** icon in Chrome.
2. In the top banner, click **Connect**.
3. It will open LinkedIn's authorization page. Sign in and grant access (`openid`, `profile`, `w_member_social`).
4. You will see the confirmation: *"Connected to LinkedIn!"*.

### Step 4: Use it on LeetCode
1. Open any problem on LeetCode (e.g. `https://leetcode.com/problems/two-sum/`).
2. Write and click **Submit**.
3. Once LeetCode displays **Accepted**, the extension icon badge will turn **green ("ACC")**.
4. Open the extension popup:
   - Your verified code, runtime, and memory stats will be displayed.
   - Click **📸 Capture Current Tab Screenshot** to take a screenshot and sync it with Cloudinary.
   - Click **✨ Generate AI Caption** (generates a professional post via Grok or smart fallback).
   - Review or edit the caption in the text area.
   - Click **🚀 Approve & Publish to LinkedIn** to publish immediately!

---

## 4. Automated Test Suite (16/16 Passing)

Run the test suite at any time:
```powershell
python -m pytest backend/tests -v
```

All 16 unit and integration tests verify:
* Root & health endpoints.
* Valid Accepted submission registration & state machine.
* Idempotent deduplication via `submission_id`.
* Pydantic schema validation & rejecting empty code.
* Algorithmic code inspection & fallback caption generator.
* Pillow screenshot validation and dimension checks.
* LinkedIn OAuth login URL generation and draft-mode publishing.
