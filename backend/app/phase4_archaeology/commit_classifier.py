import re
from typing import Tuple, Dict, Any
from backend.app.models.schemas import CommitCategory

class CommitClassifier:
    """
    NLP and Rule-based Commit Intent Classifier.
    Categorizes commits into: FEATURE, BUG_FIX, REFACTOR, SECURITY, PERFORMANCE,
    DOCUMENTATION, DEPENDENCY, MIGRATION, TEST.
    """

    PATTERNS = [
        (CommitCategory.SECURITY, [
            r'\b(security|vulnerab|cve|xss|csrf|sanitize|auth(entication)? bypass|patch)\b',
            r'\bsec(\([^\)]+\))?:'
        ]),
        (CommitCategory.PERFORMANCE, [
            r'\b(perf|performance|optimiz|latency|speedup|caching|memleak|throttle)\b',
            r'\bperf(\([^\)]+\))?:'
        ]),
        (CommitCategory.BUG_FIX, [
            r'\b(fix|bug|issue|resolve|remedy|hotfix|crash|broken|error|fault)\b',
            r'\bfix(\([^\)]+\))?:'
        ]),
        (CommitCategory.TEST, [
            r'\b(test|spec|coverage|mock|jest|cypress|vitest|e2e|unit-test)\b',
            r'\btest(\([^\)]+\))?:'
        ]),
        (CommitCategory.REFACTOR, [
            r'\b(refactor|clean|cleanup|reorganiz|modular|structure|restructure|renam)\b',
            r'\brefactor(\([^\)]+\))?:'
        ]),
        (CommitCategory.MIGRATION, [
            r'\b(migrat|schema|alter table|flyway|liquibase|database upgrade)\b'
        ]),
        (CommitCategory.DEPENDENCY, [
            r'\b(dep|bump|upgrade|package\.json|yarn\.lock|npm|dependency|dependabot)\b',
            r'\bchore\(deps\):'
        ]),
        (CommitCategory.DOCUMENTATION, [
            r'\b(doc|docs|readme|changelog|license|guide|comment)\b',
            r'\bdocs(\([^\)]+\))?:'
        ]),
        (CommitCategory.FEATURE, [
            r'\b(feat|feature|add|implement|introduce|support|create|new)\b',
            r'\bfeat(\([^\)]+\))?:'
        ]),
    ]

    def classify_commit(self, message: str, changed_files: list = None) -> CommitCategory:
        msg_lower = message.strip().lower()

        # Check conventional commit prefixes
        if msg_lower.startswith("feat"):
            return CommitCategory.FEATURE
        if msg_lower.startswith("fix"):
            return CommitCategory.BUG_FIX
        if msg_lower.startswith("refactor"):
            return CommitCategory.REFACTOR
        if msg_lower.startswith("test"):
            return CommitCategory.TEST
        if msg_lower.startswith("docs"):
            return CommitCategory.DOCUMENTATION
        if msg_lower.startswith("perf"):
            return CommitCategory.PERFORMANCE

        # Check file extensions (e.g. only test files modified)
        if changed_files:
            if all(".test." in f or ".spec." in f for f in changed_files):
                return CommitCategory.TEST
            if all(f.endswith(".md") or "doc" in f.lower() for f in changed_files):
                return CommitCategory.DOCUMENTATION

        # Pattern match keywords
        for category, regex_list in self.PATTERNS:
            for r in regex_list:
                if re.search(r, msg_lower):
                    return category

        return CommitCategory.OTHER
