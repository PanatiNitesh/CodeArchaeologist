# IBM Bob 2.0 Integration & Architectural Attribution

> **Project:** CodeArchaeologist — Self-Updating Architecture Graph & Blast Radius Engine  
> **Development Framework:** Developed and accelerated with **IBM Bob 2.0**  
> **Repository:** [PanatiNitesh/CodeArchaeologist](https://github.com/PanatiNitesh/CodeArchaeologist)

---

## 1. Executive Summary

CodeArchaeologist was architected, engineered, and scientifically validated using **IBM Bob 2.0** as our primary agentic pair-programming system. IBM Bob was integrated across all 8 pipeline phases, leveraging multiple Bob execution modes, domain-specific Bob skills, and automated lifecycle hooks.

---

## 2. IBM Bob Modes Employed Across Pipeline Phases

| Development Phase | Bob Mode | How Bob Shaped the Architecture |
|---|---|---|
| **Phase 1: Ingestion & Cloning** | **Agent Mode** | Implemented non-blocking background cloning (`RepoCloner`), GitPython subprocess management, and SQLite WAL pragma configuration (`PRAGMA journal_mode = WAL; busy_timeout = 60000;`). |
| **Phase 2: High-Fidelity AST Parsing** | **Agent Mode** | Generated the dual-engine parser: native Python AST parse-tree walker (`ast.parse`) plus TypeScript/JavaScript parser supporting generics (`<T extends Base>`), NestJS/Angular decorators, and multi-line imports. |
| **Phase 3: Topological Graphs** | **Ask Mode** & **Plan Mode** | Guided the design of the directed dependency DAG (`SoftwareGraph`), disambiguating symbol collisions via import statements (`imp.source`), and creating generalized multi-tier flow discovery across Controllers, Services, and Repositories. |
| **Phase 4: Git Archaeology Mining** | **Agent Mode** | Built the chronological commit miner with rename tracking (`c.parents[0].diff(c)`), co-change matrix construction, and directory-bounded regex file matching (`f"%/{norm_path}"`). |
| **Phase 5: Hybrid Knowledge RAG** | **Plan Mode** & **Agent Mode** | Designed the multi-channel Reciprocal Rank Fusion (RRF, $k=60$) fusing dense SentenceTransformer embeddings (`all-MiniLM-L6-v2`) and a custom BM25 inverted index, backed by an offline extractive synthesis fallback. |
| **Phase 6: Blast Radius & ML Prediction** | **Ask Mode** | Formulated the Multi-Factor Architectural Risk Index (0–100) and trained the Logistic Regression Change-Impact Predictor directly on historical co-change tuples with transparent feature importance (`model.coef_`). |
| **Phase 7: Empirical Evaluation** | **Edit Mode** | Refactored evaluators to enforce scientific honesty, removing all metric floors (`max(0.70)`) and implementing dynamic live execution tracking. |
| **Phase 8: Interactive Studio UI** | **Agent Mode** | Crafted the dark-mode React studio with custom SVG curved Bezier splines, edge-type visual legends, component confidence badges, and 1-click GitHub ingestion presets. |

---

## 3. Dedicated Bob Skills Implemented

CodeArchaeologist implements first-class native Bob 2.0 skill specifications located in [`.bob/skills/`](file:///.bob/skills/):

### A. `legacy-code-archaeologist` ([SKILL.md](file:///.bob/skills/legacy-code-archaeologist/SKILL.md))
- **Role:** Deep forensic analysis of legacy software systems.
- **Capabilities:**
  - Identifies abandoned code modules (zero revisions in $>18$ months).
  - Traces code authors and tenure distribution.
  - Pinpoints regression hotspots and frequent bug-fix clusters.
  - Generates chronological evolution timelines from initial commit to present.

### B. `blast-radius-guard` ([SKILL.md](file:///.bob/skills/blast-radius-guard/SKILL.md))
- **Role:** CI/CD Pre-Merge Quality Gate and incident prevention.
- **Capabilities:**
  - Evaluates pull request changed files against downstream dependency graphs.
  - Identifies exposed public API endpoints and route handlers.
  - Recommends mandatory test suites before merging.
  - Blocks high-risk PR merges that lack sufficient caller test coverage.

---

## 4. Key Bob Prompts That Shaped Core Technical Decisions

Below are authentic prompt directives used with IBM Bob 2.0 during development:

1. **On Class Extends Disambiguation:**
   > *"In TypeScript and Python codebases, common class names like `BaseService` or `Repository` appear in multiple files. How should our dependency graph resolve `super_class` in $O(1)$ without matching the wrong file?"*  
   > **Outcome:** Bob recommended resolving `super_class` through explicit file `imports` first, before falling back to a pre-indexed directory-proximity catalog.

2. **On Offline Deterministic RAG Synthesis:**
   > *"When a developer runs CodeArchaeologist without a Google Gemini or OpenAI API key, how do we provide intelligent, verifiable architectural answers without hallucinating?"*  
   > **Outcome:** Bob designed the `_synthesize_local_evidence_answer()` engine, extracting actual AST signatures, function parameters, and commit messages with immutable source anchors.

3. **On Scientific Evaluation Honesty:**
   > *"Review Phase 7 evaluators. Ensure all metric floors like `max(0.70, precision)` are removed and edge cases return honest zero metrics when ground-truth is absent."*  
   > **Outcome:** Bob eliminated artificial clamping, creating an honest precision/recall benchmarking system validated by automated tests.

---

## 5. IBM Bob Lifecycle Hooks

The project integrates Bob automated hooks in [`.bob/hooks.json`](file:///.bob/hooks.json):
- **`pre-build`**: Validates AST parser grammar and dependency schema integrity.
- **`post-index`**: Executes Phase 7 empirical evaluation across the newly ingested repository.
- **`pre-merge`**: Runs the Blast Radius Guard quality gate before pull request merging.

---

## 6. Official IBM Bob Documentation Referenced
- [IBM Bob Documentation & Getting Started Guide](https://cloud.ibm.com/docs)
- [IBM Bob Custom Skills & Prompts Specification](https://github.com/IBM/bob)
- [Agentic Pair Programming Best Practices for Complex Software Graphs](https://ibm.com)
