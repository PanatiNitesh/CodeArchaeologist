# CodeArchaeologist — Improvement Plan

## Overview

This plan addresses five improvement dimensions in priority order:

1. **Developer value** — make the system more useful for real workflows, not just the sample repo
2. **Evidence grounding** — make every answer and score traceable to real source artefacts
3. **Change-impact analysis** — strengthen the blast radius and prediction pipeline
4. **Evaluation quality** — ensure the Phase 7 dashboard communicates true metrics
5. **Live demo clarity** — surface what the system already does well, but currently hides

The plan is scoped to the smallest set of changes that produce the largest improvement in each dimension.
No sub-task rewrites another sub-task's work; each is independently reviewable.

---

## Current State (as of latest external modifications)

The following improvements are already in place and must NOT be re-implemented:

- `arch_evaluator.py` and `blast_evaluator.py`: metric floors removed; honest 0.0 returned when ground truth is absent
- `change_predictor.py`: feature importance extracted from `model.coef_` instead of hardcoded dict
- `blast_calculator.py`: risk score formula is now repository-size normalized (ratio-based)
- `embeddings.py` and `vector_store.py`: neural embeddings (`use_neural=True` default), real BM25 index built
- `retriever.py`: true RRF fusion of dense + BM25 channels documented and implemented
- `rag_engine.py`: dynamic confidence scoring based on term coverage + retrieval scores
- `dependency_graph.py`: tsconfig.json path alias resolution implemented; class extends disambiguation improved
- `commit_miner.py`: rename tracking (`c.parents[0].diff(c)`, `-M`), max_commits raised to 2500
- `code_evolution.py`: SQL uses `f"%/{norm_path}"` (directory-bounded suffix) instead of `%filename%`
- `parser.py`: dual-engine — native Python `ast.parse` for `.py` files; TypeScript generics-aware regex engine
- `extractor.py`: multi-language extensions added (`.py`, `.java`, `.go`, `.rs`)
- `database.py`: WAL mode + busy_timeout + PRAGMA synchronous = NORMAL
- `pipeline.py`: `load_from_db()` method implemented; cold-start no longer re-runs full pipeline
- `main.py`: async ingest endpoint (`/api/ingest/async`) with task status polling; `get_or_load_pipeline` uses `load_from_db`
- `schemas.py`: `CommitRecord.file_statuses` field added
- `BOB_USAGE.md`: IBM Bob attribution document exists at repo root
- `README.md`: Bob integration section added; phase descriptions updated

---

## Sub-Tasks

---

### Sub-Task 1 — Scenario-Driven RAG Demo Buttons

**Status:** `[x] completed` (Preset suggestions rendered in AIChatDrawer)

**Intent**

The Evidence Assistant chat currently requires the user to type a question from scratch. For demo
and day-one developer value, the assistant should surface three pre-written scenario questions that
map directly to real commits and files in the sample repository. This is the single highest-ROI
demo improvement: it shows the RAG working on specific, verifiable answers without relying on
the evaluator to type the right question.

**Problem being solved**

`FileIntelligence.tsx` line 169 has a single hardcoded `"Explain the architecture..."` button.
`AIChatDrawer.tsx` opens with an empty input. Neither leads a first-time evaluator to the most
impressive capability — answering specific "why" questions with exact commit hash citations.

**Proposed solution**

Add three preset scenario buttons to the Evidence Assistant drawer. Each button populates the
question input and immediately submits. The three questions should be:

1. `"Why was Redis caching introduced and which commit first added it?"`
2. `"What caused the payment gateway timeout bug and how was it fixed?"`
3. `"Which security patches were applied to the authentication module?"`

These map to real commits in `sample_generator.py`:
- Redis: commit `"feat: introduce Redis caching layer and SessionService for high throughput"` (2024-03-12)
- Payment timeout: commit `"fix: resolve payment gateway timeout under heavy loads"` (2024-06-13)
- Security: commit `"sec: patch token verification and sanitize login inputs"` (2025-02-14)

**Files to modify**

- `frontend/src/components/AIChatDrawer.tsx`

**Implementation approach**

1. Add a `SCENARIO_QUESTIONS` constant array — three objects each with `label` (short display name) and `question` (full query text)
2. Render the three scenario buttons above the text input when the chat history is empty
3. On click: set the question input value to `question`, then call `onAskQuestion` immediately
4. The buttons disappear once a question has been asked (hide when `messages.length > 0`)
5. No backend changes required

**Tests required**

- Manual: click each scenario button, confirm the question is submitted, confirm the response contains a commit hash from the sample repository
- Manual: confirm buttons are hidden after a message is sent

**Expected developer benefit**

A judge or evaluator can immediately click "Why was Redis introduced?" and see a response citing
commit `2024-03-12` by Amina Chen with file `src/auth/sessionService.ts` — without needing to
know any codebase details. This is the strongest 30-second demo moment the system has.

---

### Sub-Task 2 — Component Confidence Badge in FileTree and Inspector

**Status:** `[x] completed` (Confidence percentage badges visible in FileIntelligence inspector and FileTree explorer)

**Intent**

The `ComponentClassifier` returns a confidence float (0.60–0.98) for every file classification.
This value is stored in the database and returned in every `FileItem` response, but it is never
rendered anywhere in the UI. Surfacing it communicates that classification is probabilistic, not
oracle-based — a key differentiator from tools that silently label files.

**Problem being solved**

`FileTree.tsx` shows filename and component type but not confidence. `FileIntelligence.tsx` shows
the type badge but not the confidence score. The `component_confidence` field sits unused in every
`FileItem` object passed to both components.

**Proposed solution**

In the file inspector header card in `FileIntelligence.tsx`, add a small monospaced confidence
label next to the type badge, e.g.:

```
[Service]  91%
```

The colour of the percentage should be:
- Green (`text-emerald-400`): ≥ 0.88
- Yellow (`text-amber-400`): 0.70–0.87
- Zinc (`text-zinc-500`): < 0.70

Optionally add a tooltip: `"ML classification confidence"`

In `FileTree.tsx`, add the same small coloured percentage to the right of each row.

**Files to modify**

- `frontend/src/components/FileIntelligence.tsx`
- `frontend/src/components/FileTree.tsx`

**Implementation approach**

1. In `FileIntelligence.tsx`: find the `component_type` badge render (line 77 area); append
   `{(file.component_confidence * 100).toFixed(0)}%` using the colour rule above
2. In `FileTree.tsx`: read the `component_confidence` from each `FileItem`; render alongside
   the existing type indicator
3. No API changes — `component_confidence` is already in `FileItem` (see `client.ts` line 26)

**Tests required**

- Manual: select a file classified as `Service`; confirm badge shows `[Service] 88%` or similar
- Manual: select a file classified as `Utility` (fallback confidence 0.60); confirm it shows `60%` in zinc
- Manual: verify no layout regression on narrow inspector pane

**Expected developer benefit**

Makes the ML classification system transparent. Evaluators and developers understand immediately
that the system has high confidence (`95%`) on path-based matches but lower confidence (`60%`)
on utility fallbacks. Turns a black-box label into a credible probabilistic assertion.

---

### Sub-Task 3 — Feature Importance Mini Bar Chart in BlastRadiusModal

**Status:** `[x] completed` (Feature importance mini bars rendered from LogisticRegression model.coef_ in BlastRadiusModal)

**Intent**

The `ChangeImpactPrediction` response already contains `feature_importance` extracted from the
actual trained `LogisticRegression.coef_` (updated in `change_predictor.py`). This dict is
returned to the frontend but is not rendered anywhere. Displaying it as a mini bar chart makes
the ML model explainable and transparent — a direct answer to "how does this predictor work?"

**Problem being solved**

`BlastRadiusModal.tsx` renders `predictions.model_name` (e.g., `"LogisticRegression (Trained on
Git History)"`) but ignores `predictions.feature_importance`. The dict contains the four weight
keys: `co_change_frequency`, `jaccard_overlap`, `graph_closeness`, `direct_link`, `same_dir`.

**Proposed solution**

Below the `model_name` label in `BlastRadiusModal.tsx`, render a compact 5-row mini bar chart
block. Each row shows:
- Feature name (human-readable label, e.g., "Co-Change Frequency")
- A horizontal progress bar scaled to the weight value
- The percentage label on the right (e.g., `42%`)

Use existing Tailwind colour conventions: `bg-indigo-500` for the fill bar, `text-zinc-400` for
labels. The block should be collapsed under a `"Model Feature Weights"` heading.

**Files to modify**

- `frontend/src/components/BlastRadiusModal.tsx`

**Implementation approach**

1. Locate the section rendering `predictions.model_name` (around line 98)
2. Below it, add a `FeatureImportanceBar` inline component (no new file needed)
3. Map the `feature_importance` dict keys to human-readable names:
   - `co_change_frequency` → `"Co-Change Frequency"`
   - `jaccard_overlap` → `"Jaccard Co-Change Coefficient"`
   - `graph_closeness` → `"Graph Topological Closeness"`
   - `direct_link` → `"Direct Dependency Link"`
   - `same_dir` → `"Same Module Directory"`
4. Sort by value descending for visual clarity
5. Scale bar widths to the highest weight value (not 100%, so relative magnitudes are visible)

**Tests required**

- Manual: open blast radius modal on any file; confirm feature weights block appears
- Manual: when `model` is `None` (Bayesian fallback), confirm fallback weights still render
  (the backend returns the fallback array in that case)
- Manual: verify bars are proportional and sum to approximately 100%

**Expected developer benefit**

Converts the ML model from a black box into an interpretable system. A judge asking "why is
this file predicted to be impacted?" can see `"Co-Change Frequency: 42%"` and immediately
understand the dominant signal driving the prediction.

---

### Sub-Task 4 — Graph Edge-Type Legend in ArchitectureGraph

**Status:** `[x] completed` (Imports, Extends, Calls, and Blast Impact edge legends displayed in ArchitectureGraph footer)

**Intent**

The topology graph renders three visually distinct edge types:
- `IMPORTS` edges: solid line
- `EXTENDS` edges: dashed line (`strokeDasharray="3 3"`)
- Blast impact edges: red solid line

The bottom legend shows only node type colours. There is no legend for edge types, making
the graph uninterpretable to a first-time viewer without reading the source code.

**Problem being solved**

`ArchitectureGraph.tsx` lines 417-435 contain the footer legend, which only shows node colours.
The edge type visual distinction (dashes for inheritance) is defined at line 292 but never
explained. A judge watching the demo cannot tell the difference between a dependency and an
inheritance relationship.

**Proposed solution**

Extend the existing footer legend bar with a right-side section showing three edge-type entries:

```
── Imports    - - Extends    ━━ Blast Impact
```

Each entry is a small inline SVG path sample next to a label, styled consistently with the
existing legend items.

**Files to modify**

- `frontend/src/components/ArchitectureGraph.tsx`

**Implementation approach**

1. In the footer `<div>` starting at line 417, add a second `flex items-center gap-3` group
   on the right side
2. Render three legend entries using inline `<svg>` segments with appropriate `stroke`,
   `strokeDasharray`, and colours to match the actual edge render logic
3. Keep the entries concise and at the same `text-[10px]` font size as existing legend items
4. No state changes or props changes required

**Tests required**

- Manual: verify the legend appears in the footer bar without overflowing on narrow screens
- Manual: select a file; confirm the "Blast Impact" legend entry is the same red colour as the
  highlighted blast edges in the graph

**Expected developer benefit**

The graph becomes self-documenting. A reviewer can immediately understand that dashed lines
indicate inheritance relationships, solid lines are imports, and red lines show blast reach.
This is especially important when demoing the `EXTENDS` edges from the sample repo's class hierarchy.

---

### Sub-Task 5 — Evaluation Dashboard: Honest Empty-State and Computation Provenance

**Status:** `[x] completed` (Wired handleReRun to live evaluation API, added calculation provenance ribbon and zero ground-truth notice)

**Intent**

The Phase 7 Evaluation Dashboard must clearly communicate:
1. When metrics are real (backtested on historical commits) vs. when there is insufficient data
2. The fact that metrics were computed live on this specific repository and commit set
3. The architecture evaluator's zero-result case, which now correctly returns `0.0` instead of
   hardcoded constants

The current `EvaluationDashboard.tsx` (post-update) has a `handleReRun` mock that randomises
`computeDuration` with `Math.random()` and uses `setTimeout(550ms)` — this simulates
recomputation but does not actually call the API. It needs to call the real `/api/repo/{id}/evaluation`
endpoint instead.

**Problem being solved**

1. `EvaluationDashboard.tsx` `handleReRun` (line 33-40): uses `setTimeout(550)` + `Math.random()`
   to fake a recompute. This is misleading — clicking "Re-run Evaluation" does nothing real.
2. When `architecture_eval.tested_samples === 0`, the dashboard currently shows `0.0%` precision
   with no explanation. A judge seeing this will think the system is broken.
3. There is no indication of which repository or how many commits backed the evaluation.

**Proposed solution**

A. **Wire `handleReRun` to the real API**

   The `EvaluationDashboard` needs an `onReRunEvaluation` callback prop that calls
   `api.getEvaluation(repoId)` from the parent `App.tsx`. This is a real API call that returns
   the latest evaluation. The loading state (`isRecomputing`) is set while waiting.

B. **Empty-state explanation for zero ground truth**

   When `architecture_eval.tested_samples === 0`, render an informational callout:
   > "No explicit relative imports were resolved for ground-truth edge comparison.
   > Architecture Discovery F1 cannot be computed for this repository structure."

   This is honest and informative rather than confusing.

C. **Provenance header**

   Show: `"Evaluated on {commit_count_evaluated} commits • {architecture_eval.tested_samples} ground-truth edges"`
   This directly anchors the metrics to the actual data that produced them.

**Files to modify**

- `frontend/src/components/EvaluationDashboard.tsx`
- `frontend/src/App.tsx` (add `onReRunEvaluation` prop and handler)

**Implementation approach**

1. In `App.tsx`: add `handleReRunEvaluation` async function that calls `api.getEvaluation(currentRepoId)`
   and updates `evaluation` state; pass it as `onReRunEvaluation` prop to `EvaluationDashboard`
2. In `EvaluationDashboard.tsx`: replace the `setTimeout` mock with a real call to the passed
   `onReRunEvaluation()` callback; track real loading state
3. Add the zero-sample empty state explanation conditionally when `tested_samples === 0`
4. Add the provenance string to the Summary Box section

**Tests required**

- Manual: open evaluation dashboard; click "Re-run"; verify the UI shows a loading state and then
  updates with the same (or recalculated) values from the real API
- Manual: on a repository with no relative imports, verify the architecture panel shows the
  empty-state explanation, not just `0.0%` with no context

**Expected developer benefit**

Eliminates the fake "Re-run Evaluation" interaction. Makes the evaluation dashboard a real live
instrument rather than a display of precomputed static values. The provenance string lets any
judge verify that the metrics are real — "Evaluated on 10 commits • 7 ground-truth edges" is
verifiable against the visible timeline.

---

### Sub-Task 6 — Pre-Seeded GitHub Repo Quick-Ingest Buttons

**Status:** `[x] completed` (1-click repository presets + async task ingestion with live progress status polling)

**Intent**

The `POST /api/ingest` endpoint already accepts GitHub URLs via `RepoCloner.clone_or_load()`.
The async variant (`/api/ingest/async`) allows non-blocking ingestion with status polling.
But the UI in `Header.tsx` only exposes a text input field — there are no quick-demo repo buttons.

Showing the system analyze a real, publicly-recognizable open-source repository is the single
most powerful proof that it works beyond the synthetic sample.

**Problem being solved**

Every live demo currently uses only the pre-baked `enterprise_ecommerce` sample. The ingest
flow exists but requires knowing a valid GitHub URL, waiting, and handling errors manually.
There is no "one-click demo on a real repo" path.

**Proposed solution**

Add three "Quick Demo" preset buttons alongside the existing ingest input in `Header.tsx`.
Each button targets a small, well-known JavaScript/TypeScript project:

1. **express/express** — the canonical Node.js HTTP framework (small, all-JS, well-structured)
2. **tj/commander.js** — small TS CLI library with services and controllers
3. **vercel/ms** — minimal utility library; shows the system on a tiny codebase

On click, each button:
1. Calls `api.ingest` (sync) or `api.ingestAsync` with the GitHub URL
2. Shows a loading message: `"Cloning expressjs/express and running 8-phase analysis..."`
3. On completion, switches the active repository to the newly ingested one

**Files to modify**

- `frontend/src/components/Header.tsx`
- `frontend/src/api/client.ts` (add `ingestAsync` and `getTaskStatus` API methods)

**Implementation approach**

1. In `client.ts`: add `ingestAsync(url)` calling `POST /api/ingest/async` (already implemented
   in `main.py`); add `getTaskStatus(taskId)` calling `GET /api/tasks/{taskId}`
2. In `Header.tsx`: add a `QUICK_DEMO_REPOS` array of `{label, url}` objects
3. Render the three buttons as secondary `btn-studio` buttons in the header ingest area
4. On click: call `ingestAsync`, then poll `getTaskStatus` every 2 seconds; show progress
   message from `task.progress`; on `"completed"`, call `onIngest` callback with `task.repo_id`
5. The existing `onIngest` prop in `App.tsx` already handles switching to the new repository

**Tests required**

- Manual: click "express/express" quick demo button; verify loading state appears with progress
  messages from the polling endpoint; verify that on completion, the architecture graph loads
  with the real express codebase
- Manual: verify the button is disabled while an ingest is in progress (prevents duplicate clicks)
- Manual: verify error state if the GitHub URL is unreachable

**Expected developer benefit**

Transforms the demo from "look at this sample I made" to "let me analyze a real GitHub repo
right now, live". The `express/express` repository has controllers, middleware, routes, and
a multi-year Git history — exactly the scenario CodeArchaeologist is designed for.

---

### Sub-Task 7 — Churn Metrics and Hotspot Indicator in FileIntelligence

**Status:** `[x] completed` (Added total_churn, churn_per_revision, and hotspot_score to schemas, code_evolution, and FileIntelligence UI)

**Intent**

The commit mining in `commit_miner.py` extracts `added_lines` and `deleted_lines` per commit
for every file. This data is already stored in `commits` table and returned in `FileEvolution`.
But neither the inspector panel nor the API response exposes two derived metrics that are highly
valuable to developers: total churn (additions + deletions across all revisions) and a
"hotspot score" (high churn + many bug fixes = regression-prone module).

**Problem being solved**

The "History" tab in `FileIntelligence.tsx` shows milestones and bug fixes but does not give
a developer a single-glance signal: "this file has been touched 12 times and had 3 bug fixes
— it is a regression hotspot." The data to compute this is already in the `FileEvolution`
response: `total_revisions`, `bug_fixes`, and the `recent_changes` commits with line counts.

**Proposed solution**

A. **Backend: add derived churn fields to `FileEvolution`**

   In `code_evolution.py`, compute and add three new fields to the returned `FileEvolution`:
   - `total_churn`: sum of `added_lines + deleted_lines` across all file-touching commits
   - `churn_per_revision`: `total_churn / total_revisions` (avg churn per edit)
   - `hotspot_score`: composite `(bug_fixes_count * 3 + refactors_count) / max(1, total_revisions)`
     normalized to 0–10 scale; higher = more attention-requiring

   Add these three fields to the `FileEvolution` Pydantic schema in `schemas.py`.

B. **Frontend: display in the Overview tab**

   In the stats grid at the top of `FileIntelligence.tsx` (currently showing Lines / Functions /
   Classes), add a fourth `"Churn"` cell showing `total_churn` with a small heat colour
   (amber if > 200, red if > 600, zinc otherwise).

   In the History tab header, add a hotspot badge: `🔥 Hotspot` (amber) if `hotspot_score > 4.0`,
   `⚠️ Watch` if 2.0–4.0, nothing if below 2.0.

**Files to modify**

- `backend/app/models/schemas.py` (add three optional fields to `FileEvolution`)
- `backend/app/phase4_archaeology/code_evolution.py` (compute churn fields)
- `frontend/src/api/client.ts` (add churn fields to `FileEvolution` interface)
- `frontend/src/components/FileIntelligence.tsx` (render churn metric and hotspot badge)

**Implementation approach**

1. In `schemas.py`: add `total_churn: int = 0`, `churn_per_revision: float = 0.0`,
   `hotspot_score: float = 0.0` as optional fields with defaults to `FileEvolution`
2. In `code_evolution.py`: after building the `commits` list, compute:
   - `total_churn = sum(c.added_lines + c.deleted_lines for c in commits)`
   - `churn_per_revision = total_churn / max(1, len(commits))`
   - `hotspot_score = min(10.0, ((len(bug_fixes) * 3 + len(refactors)) / max(1, len(commits))) * 10)`
   Include in the returned `FileEvolution` object
3. In `client.ts`: extend `FileEvolution` interface with the three new optional fields
4. In `FileIntelligence.tsx`: expand the stats grid; add conditional hotspot badge in History tab header

**Tests required**

- Manual: select `src/payment/paymentService.ts` from the sample repo; confirm the churn
  metric shows a nonzero value and the hotspot badge appears (it has bug fixes and refactors)
- Manual: select a file with no commits; confirm churn shows 0 and no hotspot badge appears

**Expected developer benefit**

Gives developers a scannable "regression risk" signal without needing to read individual commit
messages. "This service has been modified 7 times with 3 bug fixes — it is a hotspot" is
immediately actionable during code review.

---

### Sub-Task 8 — Blast Radius: Rename-Aware Dependent Lookup

**Status:** `[x] completed` (Built transitive rename_map in pipeline run & db reload; applied to co-change mining and feature extraction in ML predictor)

**Intent**

`commit_miner.py` now tracks file renames (`file_statuses` dict, `"renamed_from:old_path"`).
This data is stored in `CommitRecord.file_statuses` and in the `commit_files.status` column.
However, `BlastRadiusCalculator` uses only the current graph nodes — it has no awareness of
renamed files. If `authModule.ts` was renamed to `authService.ts` three commits ago, the
blast radius for `authService.ts` misses any historical co-changes that referenced the old name.

**Problem being solved**

`blast_calculator.py` and `change_predictor.py` operate exclusively on `file_metadata` keys
(current file paths). The co-change matrix in `MLChangeImpactPredictor._mine_co_changes()` will
miss co-changes where the old filename appears in a historical commit.

**Proposed solution**

Build a rename resolution map during pipeline construction and pass it to `BlastRadiusCalculator`
and `MLChangeImpactPredictor`. For a given target file `authService.ts`, also look up historical
co-changes under its known previous names.

A. **Build rename chain in pipeline**

   In `pipeline.py`, after `commit_miner.mine_commits()`, build a `rename_map: Dict[str, str]`
   that maps old path → current path by scanning all `file_statuses` with `renamed_to:` prefix.

B. **Pass rename map to predictor**

   Pass `rename_map` to `MLChangeImpactPredictor.__init__`. In `_mine_co_changes()`, before
   updating `co_change_matrix`, normalize all file paths through the rename map so historical
   co-changes under old names accumulate into current-path counts.

C. **No blast_calculator change needed**

   The blast radius calculation is structural (graph-based) and only cares about current file
   paths. The rename fix only needs to apply to the historical co-change signal.

**Files to modify**

- `backend/app/pipeline.py` (build rename_map after commit mining)
- `backend/app/phase6_blast_radius/change_predictor.py` (accept and apply rename_map)

**Implementation approach**

1. In `pipeline.py`, after `self.commits = self.commit_miner.mine_commits(...)`, add:
   ```python
   rename_map = {}
   for commit in self.commits:
       for path, status in commit.file_statuses.items():
           if status.startswith("renamed_to:"):
               new_path = status.replace("renamed_to:", "")
               rename_map[path] = new_path
   ```
2. Pass `rename_map` to `MLChangeImpactPredictor(self.commits, self.nx_dep_graph, file_meta_map, rename_map=rename_map)`
3. In `change_predictor.py.__init__`: accept `rename_map: Dict[str, str] = None`; store as `self.rename_map`
4. In `_mine_co_changes()`: when building the file list per commit, normalize each file path:
   `f = self.rename_map.get(f, f)` before counting co-changes
5. Do the same normalization in `_extract_features` when looking up `co_change_matrix`

**Tests required**

- Unit: create two `CommitRecord` objects where commit A changed `["old.ts", "service.ts"]` and
  commit B changed `["new.ts", "controller.ts"]` with `file_statuses = {"old.ts": "renamed_to:new.ts"}`;
  verify that `co_change_matrix[("new.ts", "service.ts")] == 1`
- Manual: on the sample repo, confirm the co-change count for `authService.ts` accounts for any
  historical commits that referenced it before its current path was established

**Expected developer benefit**

Prevents silent information loss when a file has been renamed during its history. Ensures that
a file's full co-change history is used to predict blast radius, not just commits from after its
last rename. Particularly valuable for the "legacy codebase" use case the README targets.

---

## Execution Order

The sub-tasks are ordered by independence and dependency:

```
Sub-Task 1 (RAG Scenario Buttons)          — pure frontend, no deps
Sub-Task 2 (Confidence Badges)             — pure frontend, no deps
Sub-Task 3 (Feature Importance Bar Chart)  — pure frontend, no deps
Sub-Task 4 (Graph Edge Legend)             — pure frontend, no deps
Sub-Tasks 1-4 can be done in any order or in parallel.

Sub-Task 5 (Eval Dashboard wire-up)        — frontend + light App.tsx change
Sub-Task 6 (Quick Demo Buttons)            — frontend + client.ts

Sub-Task 7 (Churn Metrics)                 — backend schema + backend logic + frontend
Sub-Task 8 (Rename-Aware Co-Change)        — backend only, pipeline + predictor
```

Sub-Tasks 7 and 8 touch backend files and should be implemented after 1–6 are verified working.

---

## Non-Goals for This Plan

The following were considered but are explicitly out of scope:

- Replacing the JS/TS regex parser with tree-sitter or the TypeScript compiler API (high effort,
  marginal improvement on the sample repo demo; valid future work)
- Multi-repository blast radius (cross-repo dependency detection requires fundamentally different
  graph architecture)
- Real-time incremental re-analysis on new commits (requires file watcher infrastructure)
- Authentication or multi-user session isolation (not relevant for hackathon scope)
