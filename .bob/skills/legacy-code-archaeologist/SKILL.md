---
name: legacy-code-archaeologist
description: Archaeological software evolution analysis, legacy code intent recovery, and architectural drift detection powered by IBM Bob 2.0.
version: 2.0.0
author: CodeArchaeologist Team
tags:
  - ibm-bob-2.0
  - legacy-modernization
  - software-archaeology
  - code-intelligence
---

# Legacy Code Archaeologist Skill (IBM Bob 2.0)

This skill enables IBM Bob 2.0 to act as a Chief Software Archaeologist on complex, multi-year legacy codebases. It guides Bob to reconstruct why code was written, recover lost architectural decisions, and map evolutionary drift across git history.

## When to Activate
Activate this skill when:
- Investigating legacy repositories with minimal documentation or departed authors.
- Answering questions regarding why specific libraries, patterns, or workarounds were introduced.
- Performing historical impact analysis on frequently refactored or bug-prone modules.
- Mapping high-risk architectural debt across services, controllers, and database layers.

## Core Capabilities
1. **Evolutionary Git Mining**:
   - Trace origin commits and historical revisions using directory-bounded matching to prevent false positives.
   - Follow file renames and moves across repository history using Git rename tracking (`-M`).
   - Identify author tenure, bus factor risks, and milestone commits.

2. **Dual-Engine AST Semantic Analysis**:
   - Native Python AST parse trees (`ast.parse`) for Python codebases.
   - Multi-line, generic-aware, and decorator-aware syntactic tokenization for TypeScript and JavaScript.
   - Disambiguate symbol name collisions using explicit import sources.

3. **Hybrid RAG Knowledge Retrieval**:
   - Query project memory using true Reciprocal Rank Fusion (RRF, k=60) combining dense semantic embeddings (`all-MiniLM-L6-v2`) and lexical BM25 matching.
   - Ground all explanations with verifiable file lines, commit hashes, author dates, and git messages.

## Execution Workflow
1. Run `GET /api/repo/{repo_id}/file-intelligence?file_path={target}` to inspect complete lifecycle metadata.
2. Query `POST /api/repo/{repo_id}/ask` with natural language prompts (e.g. "Why was Redis introduced?", "What caused the Stripe webhook refactor in 2023?").
3. Inspect evidence citations returned by the RAG engine before proposing any legacy code refactoring.
