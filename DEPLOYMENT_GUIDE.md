# 🚀 Hugging Face Spaces Deployment Guide

This repository is fully configured for deployment on **Hugging Face Spaces** using a high-performance multi-stage **Docker** container.

---

## 📋 What Has Been Configured

1. **`Dockerfile`**:
   - **Stage 1 (Node.js)**: Builds the Vite + React frontend into production assets.
   - **Stage 2 (Python 3.11 slim)**:
     - Installs `git` (required by `GitPython`).
     - Pre-installs lightweight CPU-only PyTorch.
     - Pre-downloads `SentenceTransformer('all-MiniLM-L6-v2')` model weights so initial startup and RAG queries are instantaneous.
     - Configures user `user` (UID `1000`) for Hugging Face security standards.
     - Binds FastAPI to port `7860`.
2. **`README.md` Frontmatter**:
   - Hugging Face Space metadata (`sdk: docker`, `app_port: 7860`).
3. **`backend/run.py` & `backend/app/main.py`**:
   - Configured to bind `0.0.0.0` and port `7860` dynamically.
   - Added Single Page Application (SPA) catch-all routing so page refreshes and direct URLs work seamlessly.

---

## 🛠️ Step-by-Step Deployment Instructions

### Method A: Connect Your GitHub Repository to Hugging Face (Recommended)

This automatically deploys and updates the Space whenever you push to GitHub:

1. **Push your latest changes to GitHub**:
   ```bash
   git add .
   git commit -m "Configure Hugging Face Spaces Docker deployment"
   git push origin main
   ```
2. **Go to Hugging Face**:
   - Navigate to [huggingface.co/new-space](https://huggingface.co/new-space).
   - Enter **Space name** (e.g., `CodeArchaeologist`).
   - Select **License**: MIT (or Apache 2.0).
   - Select **Space SDK**: **Docker** (Blank).
   - Choose **Public** visibility.
   - Click **Create Space**.
3. **Link to GitHub**:
   - In your newly created Space, go to **Settings** (tab at the top right).
   - Scroll down to the **GitHub** section and click **Connect to GitHub**.
   - Select repository: `PanatiNitesh/CodeArchaeologist`.
   - Hugging Face will automatically clone, build the Docker container, and launch your application!

---

### Method B: Push Directly to Hugging Face Git Remote

If you prefer pushing directly to Hugging Face without linking GitHub:

1. **Create the Space on Hugging Face**:
   - Go to [huggingface.co/new-space](https://huggingface.co/new-space).
   - Select **Space SDK**: **Docker** (Blank).
   - Click **Create Space**.
2. **Add the Hugging Face Remote locally**:
   ```bash
   # Replace <your-hf-username> with your Hugging Face username
   git remote add hf https://huggingface.co/spaces/<your-hf-username>/CodeArchaeologist
   ```
3. **Commit and Push**:
   ```bash
   git add .
   git commit -m "Deploy CodeArchaeologist to Hugging Face"
   git push hf main --force
   ```
   *(When prompted for password, use your Hugging Face Access Token with Write permissions from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)).*

---

## 🔍 Verifying the Deployment

Once the build finishes on Hugging Face (usually takes 2-3 minutes on the initial build):
1. The status will turn to **Running** (green dot).
2. The UI will display the **CodeArchaeologist** dashboard.
3. Test by clicking **Load Enterprise Sample Repo** in the header or pasting any public GitHub repository URL into the ingestion field.
