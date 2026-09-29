# ⚡ 24/7 Keep-Alive & Real-Time Analytics Guide

This guide explains how to prevent Render free tier spin-downs (cold starts) and how the newly integrated persistent Analytics & Visitor Tracking system works.

---

## 1. 🔄 Keeping the App Active 24/7 (Preventing Sleep / Cold Starts)

### Why Did You See the "Service Waking Up" Screen?
On Render's **Free Web Service** tier, services automatically spin down (hibernate) after **15 minutes of inactivity**. When a new visitor opens your app, Render triggers a **cold start** taking 30–50 seconds to initialize compute resources.

### Solution A: Free Automated HTTP Pinger (Recommended & 100% Free)
Set up a free ping monitor to hit your app's health endpoint every **10 minutes**. Because traffic arrives before the 15-minute inactivity mark, Render **never goes to sleep**:

1. **Option 1: [Cron-job.org](https://cron-job.org)** (Zero ads, 100% free):
   - Sign up at [cron-job.org](https://cron-job.org).
   - Click **Create Cronjob**.
   - **Title**: `CodeArchaeologist Keep-Alive`
   - **URL**: `https://<YOUR-RENDER-SUBDOMAIN>.onrender.com/api/ping` (or `/api/health`)
   - **Execution Schedule**: Every **10 minutes** (e.g. `*/10 * * * *`).
   - Click **Save**.

2. **Option 2: [UptimeRobot](https://uptimerobot.com)**:
   - Create a free account at [uptimerobot.com](https://uptimerobot.com).
   - Click **Add New Monitor**.
   - Monitor Type: `HTTP(s)`
   - Friendly Name: `CodeArchaeologist Render`
   - URL: `https://<YOUR-RENDER-SUBDOMAIN>.onrender.com/api/ping`
   - Monitoring Interval: `10 minutes` (or `5 minutes`).
   - Click **Create Monitor**.

> **Note on Free Hours**: Render provides 750 free instance hours per month on free accounts. A 730-hour month running 24/7 is completely covered for 1 free web service!

---

### Solution B: Built-in GitHub Actions Scheduled Pinger
This repository includes an automated workflow at [`.github/workflows/keep_alive.yml`](file:///.github/workflows/keep_alive.yml).

- Runs automatically every 10 minutes (`*/10 * * * *`).
- To point it to your Render deployment:
  1. In your GitHub repo, go to **Settings** > **Secrets and variables** > **Actions** > **Variables**.
  2. Click **New repository variable**.
  3. Name: `RENDER_APP_URL`
  4. Value: `https://<YOUR-RENDER-SUBDOMAIN>.onrender.com`
  5. Save! GitHub Actions will keep your instance warm 24/7.

---

### Solution C: Render Paid Plan
If you prefer not to use ping monitors, upgrading your Render Web Service to the **Starter Plan ($7/mo)** gives dedicated resources, no cold starts, and zero spin-downs.

---

## 2. 📊 Built-in Live Usage & Visitor Analytics

We have integrated a full-stack, privacy-compliant **Analytics and Telemetry Engine** backed by SQLite.

### 🌟 Features & Metrics Tracked:
- **Total Page Visits**: Tracks page views across sessions.
- **Unique Visitors**: Privacy-preserving anonymized client device hashes (GDPR-safe; no raw personal data stored).
- **Repositories Analyzed**: Tracks every repository ingested (GitHub URLs, local paths, enterprise demo).
- **AI Archaeological Inquiries**: Tracks questions submitted to the AI Evidence Assistant.
- **Blast Radius Simulations**: Tracks dependency impact simulations and ripple-effect forecasts.
- **Top Codebases**: Ranks the most frequently explored repositories.
- **Live Activity Stream**: Real-time event log displaying user interactions with timestamps.
- **Export Report**: 1-click clipboard export for hackathon presentations, client demos, or reports.

### 🖥️ How to View Analytics in the Dashboard:
1. Open your CodeArchaeologist app.
2. In the top navigation header, click the **Analytics** button (next to *Evaluation*).
3. The live Analytics modal will display all metrics, graphs, and the recent activity feed in real time.
4. Click **Refresh** to sync the latest metrics from the SQLite database.

### 🔌 API Endpoints:
- `POST /api/analytics/track`: Record client or server events.
  ```json
  {
    "event_type": "page_view",
    "session_id": "sess_12345",
    "visitor_id": "vis_abcdef",
    "repo_id": "sample_enterprise_ecommerce",
    "details": {}
  }
  ```
- `GET /api/analytics/stats`: Retrieve full aggregated usage statistics.

---

## 3. 🌐 Optional: Google Analytics 4 (GA4)

If you also wish to connect Google Analytics:
1. Add an environment variable in Render or your `.env`:
   ```bash
   VITE_GA_ID=G-XXXXXXXXXX
   ```
2. The frontend automatically loads `gtag.js` and sends standard page views and event sessions to Google Analytics alongside the internal SQLite analytics dashboard.
