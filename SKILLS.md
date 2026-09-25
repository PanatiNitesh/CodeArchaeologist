# IBM Bob 2.0 Custom Skills Reference

This repository integrates directly with **IBM Bob 2.0** as its core autonomous developer and software archaeology orchestrator. The following custom skills and automation hooks are defined in `.bob/`:

---

## 1. `legacy-code-archaeologist`
- **Location**: [`.bob/skills/legacy-code-archaeologist/SKILL.md`](file:///.bob/skills/legacy-code-archaeologist/SKILL.md)
- **Role**: Discovers why legacy code was written, recovers lost architecture decisions, tracks file evolution, and resolves architectural drift.
- **Key Methods**:
  - `git_history_archaeology`: Mines git commit history with rename detection (`-M`) and directory-bounded path matching.
  - `dual_ast_parse`: Direct parse-tree extraction for Python (`ast.parse`) and enhanced TypeScript/JavaScript syntactic tokenization.
  - `evidence_rag_query`: Reciprocal Rank Fusion (RRF) retrieval fusing dense neural embeddings (`all-MiniLM-L6-v2`) and BM25 lexical search.

---

## 2. `blast-radius-guard`
- **Location**: [`.bob/skills/blast-radius-guard/SKILL.md`](file:///.bob/skills/blast-radius-guard/SKILL.md)
- **Role**: Simulates cascading blast radius and predicts change-impact likelihood before code refactoring.
- **Key Methods**:
  - `calculate_blast_radius`: Inverts the directed dependency graph to trace 1-hop direct dependents, multi-hop indirect dependents, downstream API routes, and test suites.
  - `predict_change_impact`: Uses an empirical LogisticRegression model trained on historical co-changes and topological graph distance with normalized feature coefficients.
  - `calibrated_risk_score`: Normalizes risk across repository scale (5 files to 500+ files) and API exposure.

---

## 3. IBM Bob 2.0 Lifecycle Hooks
Defined in [`.bob/hooks.json`](file:///.bob/hooks.json):
1. **`pre-refactor-blast-check`**: Simulates blast radius prior to modifying critical files.
2. **`post-ingest-graph-refresh`**: Reconstructs dependency graphs with tsconfig path aliases.
3. **`on-pr-review-impact-prediction`**: Evaluates git diffs to forecast co-change regressions.
4. **`evidence-grounded-qa`**: RAG query grounding with line numbers, commit hashes, and author dates.
