# 🏛️ CodeArchaeologist
> **AI-Powered Software Evolution & Legacy Code Intelligence**

```
                    CODEARCHAEOLOGIST
                           │
             ┌─────────────┼─────────────┐
             ↓             ↓             ↓
          SOURCE          GIT           DOCS
           CODE          HISTORY
             │             │
             ↓             ↓
          AST/ML       Commit Mining
             │             │
             ↓             ↓
       Dependency      Evolution
          Graph           Graph
             │             │
             └──────┬──────┘
                    ↓
             KNOWLEDGE LAYER
                    │
             ┌──────┴──────┐
             ↓             ↓
         Vector DB      Graph DB
             │             │
             └──────┬──────┘
                    ↓
                 RAG
                    ↓
                  LLM
                    ↓
        ┌───────────┼───────────┐
        ↓           ↓           ↓
    Explain      History    Blast Radius
        │           │           │
        └───────────┼───────────┘
                    ↓
             DEVELOPER UI
```

---

## 🌟 The Core Idea
Give **CodeArchaeologist** any GitHub repository or local codebase, and it systematically reconstructs:
1. **What the codebase does** (AST symbol parsing, functions, classes, calls, and component classification).
2. **How its architecture is connected** (Directed Dependency Graph & Multi-tier Call Chains).
3. **How it evolved over time** (Mining Git commit history, classifying milestones 2022–2026, and tracking per-file evolution).
4. **Why important changes happened** (Evidence-based RAG linking code lines, commit hashes, and commit rationale).
5. **What might break if modified** (Cascading Blast Radius & Machine Learning Change-Impact Prediction with calibrated probabilities).

---

## 🏗️ Architecture & The 8 Phases

| Phase | Title | Core Modules | Description |
|---|---|---|---|
| **Phase 1** | **Repository Ingestion** | `phase1_ingestion/` | Clones/loads repos, filters non-code directories (`node_modules`, `dist`, `coverage`), indexes `.js`, `.ts`, `.jsx`, `.tsx`, `.json`, `.md`, and creates relational DB storage. |
| **Phase 2** | **Code Understanding (AST)** | `phase2_ast/` | Parses functions, classes, imports, exports, and call expressions into semantic symbols. |
| **Phase 3** | **Software & Call Graph** | `phase3_graph/` | Builds NetworkX dependency graph (`IMPORTS`, `EXTENDS`, `CALLS`) and classifies components into Controller, Service, Repository, Model, Test, Middleware, Config, Utility. |
| **Phase 4** | **Software Archaeology** | `phase4_archaeology/` | Mines Git commit history, classifies commit categories (`FEATURE`, `BUG_FIX`, `REFACTOR`, `SECURITY`, `PERFORMANCE`, etc.), constructs chronological timeline eras, and traces per-file lifecycle. |
| **Phase 5** | **Knowledge Layer & RAG** | `phase5_knowledge_rag/` | Dense vector embeddings store (functions, classes, commits, docs) and Evidence-based RAG engine with verifiable file & commit citations. |
| **Phase 6** | **Blast Radius & ML Prediction** | `phase6_blast_radius/` | Cascading blast calculator (Direct vs Indirect dependents, affected APIs & Tests, Composite Risk Score) + ML Change-Impact Predictor. |
| **Phase 7** | **Evaluation Engine** | `phase7_evaluation/` | Precision, Recall, and F1 benchmarks for architecture dependency discovery and empirical historical multi-file commit backtesting. |
| **Phase 8** | **Developer Dashboard** | `frontend/` | Sleek dark-mode developer UI featuring interactive topology graph, file tree, evolution timeline, file intelligence inspector, and AI chat drawer. |

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend development, or run pre-built bundle directly via backend)

### 1. Run the Backend & Developer Dashboard
```bash
# From workspace root:
python backend/run.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser!

The server will automatically:
1. Initialize the SQLite relational and vector databases (`code_archaeologist.db`).
2. Generate and analyze the pre-baked **2022–2026 Enterprise E-Commerce Sample Repository** (with auth, payment, controller, service, tests, and evolution commits).
3. Serve the full interactive Developer Dashboard and REST APIs on port 8000.

### 2. Frontend Development Server (Optional)
If you want to edit or develop the React frontend with Vite hot-reloading:
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** (proxies automatically to backend on 8000).

---

## 💥 Phase 6: The Blast Radius & ML Prediction Engine

When you select a file (e.g. `src/users/userService.ts`):
1. **Direct Dependents (1-Hop)**: Files directly importing or invoking the file (e.g. `orderService.ts`, `userController.ts`, `paymentService.ts`, `payment.test.ts`).
2. **Indirect Dependents (Transitive)**: Downstream cascading files (e.g. `paymentController.ts`).
3. **Affected APIs**: Endpoints requiring regression verification.
4. **Affected Tests**: Test suites that must pass before deploying.
5. **Machine Learning Change Impact Model**: Combines historical co-change mining ($P(\text{CoChange}(A, B))$) with graph topological shortest path distance to rank predicted files with calibrated probability scores (e.g., `userController.ts: 94%`, `orderService.ts: 82%`).

---

## 🔍 Phase 5: Verifiable Evidence-Based RAG

Unlike standard chatbots that hallucinate vague answers, **CodeArchaeologist enforces strict evidence citations**:
```
Developer Question: "Why was Redis introduced?"

Answer:
Redis caching was introduced to support high-throughput session caching for authenticated users.

Evidence:
• File: src/auth/sessionService.ts (Lines 1-12)
• Commit: 3a9f1b ("feat: introduce Redis caching layer and SessionService for high throughput")
  Author: Amina Chen • Date: 2024-03-12
• Commit: 7e2c90 ("perf: optimize Redis session caching with multi-key batch pipeline")
```
Every evidence item includes clickable anchors to navigate directly to the source file or Git commit.

---

## 📊 Phase 7: Scientific Evaluation Suite

Navigate to **"Evaluation Suite"** in the top navigation to inspect live empirical metrics:
- **Step 17 (Architecture Graph F1)**: Measures Precision, Recall, and F1 of inferred dependencies vs ground-truth code imports.
- **Step 18 (Blast Radius Backtesting F1)**: Backtests historical multi-file commits:
  $$\text{Given Seed File } A \longrightarrow \text{Predict actual historical co-changes } \{B, C, D\}$$
  Measures Precision, Recall, and F1 on real historical commits.

---

## 🛠️ API Reference

- `POST /api/ingest` — Ingest any GitHub URL or local path.
- `POST /api/load-sample` — Load the 2022–2026 enterprise sample repository.
- `GET /api/repositories` — List all analyzed repositories.
- `GET /api/repo/{id}/files` — Get files with component classification.
- `GET /api/repo/{id}/graph` — Get the complete software architecture graph.
- `GET /api/repo/{id}/timeline` — Get chronological evolution milestones and classified commits.
- `GET /api/repo/{id}/file-intelligence?file_path=...` — Get deep file lifecycle, creation date, milestones, and bug fixes.
- `GET /api/repo/{id}/blast-radius?target_file=...` — Calculate cascading blast radius and risk score.
- `GET /api/repo/{id}/predict-impact?target_file=...` — ML change-impact probability predictions.
- `POST /api/repo/{id}/ask` — Evidence-based AI RAG chat.
- `GET /api/repo/{id}/evaluation` — Scientific evaluation metrics.
