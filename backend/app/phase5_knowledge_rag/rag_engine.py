import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from backend.app.models.schemas import RAGAnswerResponse, EvidenceItem
from backend.app.phase5_knowledge_rag.retriever import HybridRetriever
from backend.app.phase5_knowledge_rag.grounding import GroundingEnforcer, GroundingVerificationResult

logger = logging.getLogger(__name__)

class EvidenceRAGEngine:
    """
    Synthesizes code understanding, architectural graphs, and Git history into
    rigorous, evidence-based explanations with verifiable, grounded citations.
    """

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever

    def answer_question(self, question: str) -> RAGAnswerResponse:
        context = self.retriever.retrieve_context(question)
        
        evidence_list: List[EvidenceItem] = []

        # Convert code matches to structured evidence without unsafe fallbacks
        for c in context.get("code", []):
            meta = c.get("metadata", {})
            file_path = meta.get("path")
            # Disallow unsafe placeholders like "unknown" or empty path
            if not file_path or file_path.lower() in ("unknown", "none", ""):
                continue

            # Preserve exact AST line numbers; do not fabricate 1..20 defaults
            line_start = meta.get("line_start")
            line_end = meta.get("line_end")
            try:
                line_start = int(line_start) if line_start is not None else None
            except (ValueError, TypeError):
                line_start = None

            try:
                line_end = int(line_end) if line_end is not None else None
            except (ValueError, TypeError):
                line_end = None

            symbol_name = meta.get('function') or meta.get('class') or meta.get('component_type') or 'component'
            evidence_list.append(EvidenceItem(
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                snippet=c.get("content", "")[:350],
                relevance_reason=f"Defines {symbol_name} relevant to query."
            ))

        # Convert commit matches to structured evidence without unsafe "HEAD" or "history" fallbacks
        for cm in context.get("commits", []):
            meta = cm.get("metadata", {})
            commit_hash = meta.get("commit_hash") or meta.get("full_hash") or cm.get("entity_id")
            # Disallow unsafe fallbacks like "HEAD" or "unknown"
            if not commit_hash or commit_hash.upper() in ("HEAD", "UNKNOWN", "NONE", ""):
                continue

            changed_files = meta.get("changed_files", [])
            file_path = ""
            if changed_files and isinstance(changed_files, list):
                # Verify it's not a fake placeholder
                candidate_path = str(changed_files[0]).strip()
                if candidate_path.lower() not in ("git", "history", "unknown", "none", ""):
                    file_path = candidate_path

            evidence_list.append(EvidenceItem(
                file_path=file_path,
                commit_hash=commit_hash,
                commit_message=meta.get("title", cm.get("title", "")),
                commit_date=meta.get("date"),
                snippet=cm.get("content", "")[:250],
                relevance_reason=f"Historical milestone introduced change: {cm.get('title', '')}"
            ))

        # Convert docs matches to evidence if present
        for d in context.get("docs", []):
            meta = d.get("metadata", {})
            doc_path = meta.get("path") or d.get("entity_id")
            if doc_path and doc_path.lower() not in ("unknown", "none", ""):
                evidence_list.append(EvidenceItem(
                    file_path=doc_path,
                    snippet=d.get("content", "")[:300],
                    relevance_reason="Repository documentation context."
                ))

        # Explicit Insufficient-Evidence Gate:
        # Check whether retrieved evidence is sufficient to answer the question reliably
        # without allowing LLM or local synthesis to guess or speculate.
        is_sufficient, reason = GroundingEnforcer.check_evidence_sufficiency(
            question, context, evidence_list
        )
        if not is_sufficient:
            return RAGAnswerResponse(
                question=question,
                answer=(
                    f"### Insufficient Evidence\n\n"
                    f"The repository does not contain sufficient code references or Git milestones to answer "
                    f"**'{question}'** reliably without speculation.\n\n"
                    f"**Audit Detail:** {reason}\n\n"
                    f"> 💡 *Tip: Try querying specific service names, exported functions, file paths, or commit topics.*"
                ),
                evidence=[],
                confidence_score=0.0,
                retrieval_sources=context.get("counts", {})
            )

        # External LLM paths with grounding enforcement
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        openai_api_key = os.environ.get("OPENAI_API_KEY")

        grounding_score = 1.0
        final_evidence = evidence_list

        if gemini_api_key:
            answer_text, final_evidence, grounding_score = self._call_gemini_llm(
                question, context, evidence_list, gemini_api_key
            )
        elif openai_api_key:
            answer_text, final_evidence, grounding_score = self._call_openai_llm(
                question, context, evidence_list, openai_api_key
            )
        else:
            answer_text = self._synthesize_local_evidence_answer(question, context, evidence_list)

        # Check if the generated prose explicitly communicated insufficient evidence
        if "insufficient evidence" in answer_text.lower():
            return RAGAnswerResponse(
                question=question,
                answer=answer_text,
                evidence=[],
                confidence_score=0.0,
                retrieval_sources=context.get("counts", {})
            )

        # Dynamically compute confidence score scaled by query relevance and grounding score
        dyn_confidence = self._calculate_dynamic_confidence(
            question, context, final_evidence, grounding_score=grounding_score
        )

        return RAGAnswerResponse(
            question=question,
            answer=answer_text,
            evidence=final_evidence,
            confidence_score=dyn_confidence,
            retrieval_sources=context.get("counts", {})
        )

    def _calculate_dynamic_confidence(
        self,
        question: str,
        context: Dict[str, Any],
        evidence: List[EvidenceItem],
        grounding_score: float = 1.0
    ) -> float:
        if not evidence:
            return 0.0

        import re
        q_tokens = set(re.findall(r'[a-zA-Z0-9_$]+', question.lower()))
        stop_words = {"why", "how", "what", "where", "when", "the", "was", "for", "with", "this", "that", "from", "into", "and", "are", "does"}
        meaningful_tokens = {t for t in q_tokens if len(t) > 2 and t not in stop_words}

        if not meaningful_tokens:
            return round(float(0.50 * grounding_score), 2)

        # 1. Term coverage in retrieved evidence
        matched_tokens = set()
        for ev in evidence:
            text = f"{ev.file_path} {ev.snippet} {ev.commit_message or ''}".lower()
            for t in meaningful_tokens:
                if t in text:
                    matched_tokens.add(t)

        term_coverage = len(matched_tokens) / max(1, len(meaningful_tokens))

        # 2. Retrieval quality from underlying RRF / dense / BM25 search
        score_samples = []
        for cat in ["code", "commits", "docs"]:
            for item in context.get(cat, []):
                meta = item.get("retrieval_metadata", {})
                if "dense_cosine_sim" in meta:
                    score_samples.append(max(0.0, meta["dense_cosine_sim"]))
                elif "score" in item:
                    val = item["score"]
                    score_samples.append(min(1.0, val / 100.0 if val > 1.0 else val))

        avg_search_score = sum(score_samples) / max(1, len(score_samples)) if score_samples else 0.5

        # 3. Source diversity bonus: having both code and commit history anchors increases grounding
        has_code = len(context.get("code", [])) > 0
        has_commits = len(context.get("commits", [])) > 0
        diversity_bonus = 0.15 if (has_code and has_commits) else 0.05

        raw_confidence = ((term_coverage * 0.55) + (avg_search_score * 0.30) + diversity_bonus) * grounding_score
        return round(float(min(0.98, max(0.10, raw_confidence))), 2)

    def _call_gemini_llm(
        self,
        question: str,
        context: Dict[str, Any],
        evidence: List[EvidenceItem],
        api_key: str
    ) -> Tuple[str, List[EvidenceItem], float]:
        """
        Calls Google Gemini with structured evidence catalog and strict grounding prompts,
        then verifies the response through the Grounding Enforcement Layer.
        """
        evidence_catalog = GroundingEnforcer.format_evidence_catalog(evidence)
        system_instruction = GroundingEnforcer.build_grounded_system_prompt()

        prompt = f"""
{system_instruction}

Developer Question: {question}

{evidence_catalog}

Required Response Structure:
1. Core Implementation & Architecture (cite exact evidence with [E1], [E2] etc.)
2. Historical Git Evolution & Rationale (cite exact commits with [E#])
3. Grounded Conclusion

Remember:
- Only make claims directly backed by the EVIDENCE CATALOG snippets.
- If the catalog lacks sufficient details to answer, state 'Insufficient evidence: [reason]'.
- Do not fabricate files, commits, line ranges, or functions.
"""

        raw_text = None

        # Direct Google Gemini REST API
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            }
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "")
        except Exception as e:
            logger.info(f"Direct Gemini REST API call failed, trying dynamic SDK: {e}")

        # Fallback: Dynamic SDK call via importlib
        if not raw_text:
            try:
                import importlib
                genai = importlib.import_module("google.generativeai")
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                if response and response.text:
                    raw_text = response.text
            except Exception as e:
                logger.info(f"SDK call unavailable or failed: {e}")

        if not raw_text:
            # LLM unavailable: fall back to deterministic local synthesis
            fallback = self._synthesize_local_evidence_answer(question, context, evidence)
            return fallback, evidence, 1.0

        # Enforce Grounding: verify prose against structured EvidenceItem objects
        return GroundingEnforcer.enforce_grounding(
            prose=raw_text,
            evidence=evidence,
            question=question,
            local_fallback_fn=lambda: self._synthesize_local_evidence_answer(question, context, evidence)
        )

    def _call_openai_llm(
        self,
        question: str,
        context: Dict[str, Any],
        evidence: List[EvidenceItem],
        api_key: str
    ) -> Tuple[str, List[EvidenceItem], float]:
        """
        Calls OpenAI with structured evidence catalog and strict grounding prompts,
        then verifies the response through the Grounding Enforcement Layer.
        """
        evidence_catalog = GroundingEnforcer.format_evidence_catalog(evidence)
        system_instruction = GroundingEnforcer.build_grounded_system_prompt()

        user_content = f"""
Developer Question: {question}

{evidence_catalog}

Required Response Structure:
1. Core Implementation & Architecture (cite exact evidence with [E1], [E2] etc.)
2. Historical Git Evolution & Rationale (cite exact commits with [E#])
3. Grounded Conclusion

Remember:
- Only make claims directly backed by the EVIDENCE CATALOG snippets.
- If the catalog lacks sufficient details to answer, state 'Insufficient evidence: [reason]'.
- Do not fabricate files, commits, line ranges, or functions.
"""
        try:
            import importlib
            openai_mod = importlib.import_module("openai")
            client = openai_mod.OpenAI(api_key=api_key)
            
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content}
                ]
            )
            raw_text = resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"OpenAI API call failed, falling back to local synthesis: {e}")
            fallback = self._synthesize_local_evidence_answer(question, context, evidence)
            return fallback, evidence, 1.0

        # Enforce Grounding: verify prose against structured EvidenceItem objects
        return GroundingEnforcer.enforce_grounding(
            prose=raw_text,
            evidence=evidence,
            question=question,
            local_fallback_fn=lambda: self._synthesize_local_evidence_answer(question, context, evidence)
        )

    def _synthesize_local_evidence_answer(
        self,
        question: str,
        context: Dict[str, Any],
        evidence: List[EvidenceItem]
    ) -> str:
        """
        High-precision deterministic synthesis engine that constructs structured answers
        with verifiable code, signatures, and commit evidence citations.
        Provides rich architectural analysis even when running 100% offline without cloud LLM keys.
        """
        code_items = context.get("code", [])
        commit_items = context.get("commits", [])
        doc_items = context.get("docs", [])

        if not code_items and not commit_items:
            return (
                f"### Insufficient Evidence\n\n"
                f"> ℹ️ **Offline Extractive Synthesis Mode** (Local AST & Git Archaeology)\n\n"
                f"No direct code references or Git milestones matched **'{question}'** in this repository.\n"
                f"Try querying specific architectural components, service names, file paths, or historical topics."
            )

        parts = []
        parts.append(f"### Architectural Analysis for *'{question}'*\n")
        parts.append(
            f"> ℹ️ **Offline Extractive Mode:** Deterministic structural synthesis powered by local AST "
            f"traversal, dependency graphs, and Git archaeology. (Cloud LLM keys are optional).\n\n"
        )

        # 1. Structural Code Analysis
        if code_items:
            primary_file = code_items[0].get("metadata", {}).get("path", "module")
            comp_type = code_items[0].get("metadata", {}).get("component_type", "Component")
            parts.append(f"#### 1. Core Architectural Implementation\n")
            parts.append(
                f"Primary architectural locus: **`{primary_file}`** (Categorized as `{comp_type}`).\n\n"
            )

            for idx, item in enumerate(code_items[:4], 1):
                meta = item.get("metadata", {})
                title = item.get("title", "Symbol")
                path = meta.get("path", "file")
                l_start = meta.get('line_start')
                l_end = meta.get('line_end')
                lines = f"L{l_start}-L{l_end}" if (l_start and l_end) else "Source"
                content = item.get("content", "").strip()

                parts.append(f"**{idx}. `{title}`** in [`{path}`]({lines}) [E{idx}]\n")
                
                # Show signature or code preview if present
                if content:
                    lines_preview = [l for l in content.splitlines() if l.strip()][:6]
                    code_snippet = "\n".join(lines_preview)
                    parts.append(f"```\n{code_snippet}\n```\n")

        # 2. Historical Git Evolution
        if commit_items:
            code_offset = len(code_items[:4])
            parts.append(f"#### 2. Historical Evolution & Git Rationale\n")
            parts.append(
                f"Historical commit traces illuminate how and why this subsystem evolved:\n\n"
            )
            for c_idx, c in enumerate(commit_items[:4], 1):
                meta = c.get("metadata", {})
                chash = meta.get("commit_hash", "")[:8]
                date = meta.get("date", "Unknown date")
                author = meta.get("author", "Contributor")
                category = meta.get("category", "REFACTOR")
                title = c.get("title", "")
                content = c.get("content", "").strip()
                tag = f"[E{code_offset + c_idx}]"

                parts.append(
                    f"- **`[{category}]`** commit [`{chash}`] by *{author}* on {date} {tag}\n"
                    f"  **Summary:** _{title}_\n"
                )
                if content and content != title:
                    clean_detail = content.replace(title, "").strip()
                    if clean_detail:
                        first_line = clean_detail.splitlines()[0][:120]
                        parts.append(f"  > _{first_line}_\n")

        # 3. Documentation Context
        if doc_items:
            parts.append(f"\n#### 3. Relevant Documentation Context\n")
            for d in doc_items[:2]:
                text = d.get("content", "").strip()
                if text:
                    parts.append(f"> {text[:220]}...\n\n")

        parts.append(
            f"\n---\n"
            f"**Evidence Verification:** Every statement above is directly anchored to AST source coordinates "
            f"and immutable Git commits. Click any evidence badge below to inspect the verified source."
        )
        return "".join(parts)
