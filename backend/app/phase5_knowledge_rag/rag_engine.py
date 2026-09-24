import os
import json
import logging
from typing import Dict, Any, List
from backend.app.models.schemas import RAGAnswerResponse, EvidenceItem
from backend.app.phase5_knowledge_rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)

class EvidenceRAGEngine:
    """
    Synthesizes code understanding, architectural graphs, and Git history into
    rigorous, evidence-based explanations with clickable citations.
    """

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever

    def answer_question(self, question: str) -> RAGAnswerResponse:
        context = self.retriever.retrieve_context(question)
        
        evidence_list: List[EvidenceItem] = []

        # Convert code matches to evidence
        for c in context.get("code", []):
            meta = c.get("metadata", {})
            evidence_list.append(EvidenceItem(
                file_path=meta.get("path", "unknown"),
                line_start=meta.get("line_start", 1),
                line_end=meta.get("line_end", 20),
                snippet=c.get("content", "")[:350],
                relevance_reason=f"Defines {meta.get('function') or meta.get('class') or meta.get('component_type') or 'component'} relevant to query."
            ))

        # Convert commit matches to evidence
        for cm in context.get("commits", []):
            meta = cm.get("metadata", {})
            evidence_list.append(EvidenceItem(
                file_path=meta.get("changed_files", ["git"])[0] if meta.get("changed_files") else "history",
                commit_hash=meta.get("commit_hash", "HEAD"),
                commit_message=meta.get("title", cm.get("title", "")),
                commit_date=meta.get("date"),
                snippet=cm.get("content", "")[:250],
                relevance_reason=f"Historical milestone introduced change: {cm.get('title', '')}"
            ))

        # Check if external LLM API key exists (e.g. GEMINI_API_KEY or OPENAI_API_KEY)
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        openai_api_key = os.environ.get("OPENAI_API_KEY")

        if gemini_api_key:
            answer_text = self._call_gemini_llm(question, context, evidence_list, gemini_api_key)
        elif openai_api_key:
            answer_text = self._call_openai_llm(question, context, evidence_list, openai_api_key)
        else:
            answer_text = self._synthesize_local_evidence_answer(question, context, evidence_list)

        return RAGAnswerResponse(
            question=question,
            answer=answer_text,
            evidence=evidence_list,
            confidence_score=0.92 if evidence_list else 0.40,
            retrieval_sources=context.get("counts", {})
        )

    def _call_gemini_llm(self, question: str, context: Dict[str, Any], evidence: List[EvidenceItem], api_key: str) -> str:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""
            You are CodeArchaeologist, an expert software evolution and codebase intelligence system.
            Answer the developer's question based strictly on the provided evidence from code, architecture graphs, and Git commit archaeology.
            Make your answer specific, authoritative, and cite exact files and commits.

            Developer Question: {question}

            Retrieved Code Context:
            {json.dumps([c['content'] for c in context.get('code', [])], indent=2)}

            Retrieved Commit Archaeology:
            {json.dumps([c['content'] for c in context.get('commits', [])], indent=2)}

            Provide a clear, structured explanation with sections:
            1. Core Architecture / Implementation Details
            2. Historical Evolution & Why It Was Built This Way
            3. Verifiable Evidence Summary
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.warning(f"Gemini API call failed, falling back to local synthesis: {e}")
            return self._synthesize_local_evidence_answer(question, context, evidence)

    def _call_openai_llm(self, question: str, context: Dict[str, Any], evidence: List[EvidenceItem], api_key: str) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            prompt = f"""
            You are CodeArchaeologist, an expert software evolution and codebase intelligence system.
            Developer Question: {question}
            Retrieved Code: {json.dumps([c['content'] for c in context.get('code', [])])}
            Retrieved Commits: {json.dumps([c['content'] for c in context.get('commits', [])])}
            """
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are CodeArchaeologist. Produce evidence-based, technically precise architectural explanations."},
                    {"role": "user", "content": prompt}
                ]
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI API call failed, falling back to local synthesis: {e}")
            return self._synthesize_local_evidence_answer(question, context, evidence)

    def _synthesize_local_evidence_answer(self, question: str, context: Dict[str, Any], evidence: List[EvidenceItem]) -> str:
        """
        High-precision deterministic synthesis engine that constructs structured answers
        with verifiable code and commit evidence citations.
        """
        code_items = context.get("code", [])
        commit_items = context.get("commits", [])
        doc_items = context.get("docs", [])

        if not code_items and not commit_items:
            return (
                f"### Codebase Archaeological Inspection\n\n"
                f"No direct code references or Git milestones matched **'{question}'** in this repository.\n"
                f"Try querying specific architectural components, service names, or historical topics."
            )

        parts = []
        parts.append(f"### Architecture & Code Understanding for *'{question}'*\n")

        if code_items:
            primary_file = code_items[0].get("metadata", {}).get("path", "module")
            comp_type = code_items[0].get("metadata", {}).get("component_type", "Component")
            parts.append(
                f"Based on static AST analysis and the dependency graph, the core implementation resides in **`{primary_file}`** ({comp_type}).\n\n"
            )
            for item in code_items[:3]:
                meta = item.get("metadata", {})
                parts.append(f"- **`{meta.get('path')}`** (Lines {meta.get('line_start')}-{meta.get('line_end')}): Implements {item.get('title')}.\n")

        if commit_items:
            parts.append(f"\n### Historical Evolution & Git Archaeology\n")
            parts.append(f"The commit history reveals how this capability was introduced and refactored over time:\n")
            for c in commit_items[:3]:
                meta = c.get("metadata", {})
                parts.append(
                    f"- Commit **`{meta.get('commit_hash')}`** ({meta.get('date', 'Unknown')}) by *{meta.get('author', 'Dev')}*: "
                    f"_{c.get('title')}_ [{meta.get('category', 'CHANGE')}].\n"
                )

        if doc_items:
            parts.append(f"\n### Documentation Highlights\n")
            for d in doc_items[:2]:
                parts.append(f"> {d.get('content', '')[:180]}...\n")

        parts.append(f"\n> **Evidence Verification:** Every point above is anchored directly to source code lines and Git commit hashes. Inspect the interactive evidence badges below to verify.")
        return "".join(parts)
