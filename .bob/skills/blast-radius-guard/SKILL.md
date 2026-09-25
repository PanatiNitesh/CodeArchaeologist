---
name: blast-radius-guard
description: Pre-refactoring cascading blast radius simulation, topological ripple analysis, and ML change-impact prediction powered by IBM Bob 2.0.
version: 2.0.0
author: CodeArchaeologist Team
tags:
  - ibm-bob-2.0
  - blast-radius
  - risk-assessment
  - change-prediction
---

# Blast Radius Guard Skill (IBM Bob 2.0)

This skill enables IBM Bob 2.0 to act as an automated architectural risk guardian before any file or module is modified, refactored, or deprecated.

## When to Activate
Activate this skill when:
- Reviewing pull requests or planning code refactoring in core services or database models.
- Estimating the testing and QA scope for proposed code changes.
- Determining which downstream API endpoints or test suites are vulnerable to regressions.
- Evaluating change-impact probabilities using trained historical co-change models.

## Core Capabilities
1. **Topological Ripple Effect**:
   - Inverts the directed dependency graph to trace 1-hop direct dependents and multi-hop transitive dependents.
   - Detects all impacted API route controllers and candidate regression test suites.

2. **Calibrated & Normalized Risk Scoring**:
   - Computes a repository-size normalized composite risk score (0 to 100) balancing relative blast breadth, API exposure criticality, and absolute dependency volume.
   - Categorizes risk objectively into LOW, MEDIUM, HIGH, and CRITICAL.

3. **Machine Learning Change-Impact Prediction**:
   - Scores candidate files using a trained LogisticRegression model with empirical feature weights derived from real git co-change history and graph distance.
   - Provides transparent, human-interpretable reasoning for every predicted co-affected file.

## Execution Workflow
1. Request blast radius simulation via `GET /api/repo/{repo_id}/blast-radius?target_file={file_path}`.
2. Query ML impact predictions via `GET /api/repo/{repo_id}/predict-impact?target_file={file_path}`.
3. Validate that all high-risk downstream API routes have corresponding test suites identified prior to code modification.
