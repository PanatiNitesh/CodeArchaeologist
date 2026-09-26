import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from backend.app.models.schemas import EvidenceItem

logger = logging.getLogger(__name__)

@dataclass
class GroundingVerificationResult:
    """
    Detailed audit result from verifying prose against structured EvidenceItem objects.
    """
    is_grounded: bool
    grounding_score: float  # 0.0 to 1.0
    unsupported_claims: List[str] = field(default_factory=list)
    fabricated_citations: List[str] = field(default_factory=list)
    fabricated_paths: List[str] = field(default_factory=list)
    fabricated_commits: List[str] = field(default_factory=list)
    fabricated_line_ranges: List[str] = field(default_factory=list)
    verified_evidence: List[EvidenceItem] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    sanitized_answer: Optional[str] = None


class GroundingEnforcer:
    """
    Robust Grounding Enforcement Layer for CodeArchaeologist RAG.
    
    Guarantees:
    1. Answers must be grounded strictly in the supplied EvidenceItem objects.
    2. Identifies and rejects unsupported claims, fabricated citations, hallucinated file paths,
       and invented commit hashes.
    3. Traces factual claims to specific evidence catalog identifiers ([E1], [E2], etc.).
    4. Enforces explicit 'Insufficient evidence' responses when retrieval is missing or inadequate.
    """

    STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
        "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
        "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
        "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
        "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
        "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
        "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me",
        "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
        "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
        "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
        "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
        "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
        "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
        "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
        "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't",
        "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
    }

    @classmethod
    def check_evidence_sufficiency(
        cls,
        question: str,
        context: Dict[str, Any],
        evidence: List[EvidenceItem]
    ) -> Tuple[bool, str]:
        """
        Validates whether retrieved context and structured evidence are sufficient to answer
        the question without requiring the LLM to speculate or hallucinate.
        """
        if not evidence:
            return False, "No matching code references or Git milestones were found in the repository."

        # Extract meaningful tokens from query
        q_tokens = cls._extract_meaningful_tokens(question)
        if not q_tokens:
            return True, "Query contains only generic tokens; proceeding with retrieved evidence."

        # Check keyword coverage in evidence items
        matched_tokens: Set[str] = set()
        for ev in evidence:
            ev_corpus = f"{ev.file_path} {ev.snippet} {ev.commit_message or ''} {ev.relevance_reason or ''}".lower()
            for token in q_tokens:
                if token in ev_corpus:
                    matched_tokens.add(token)

        coverage = len(matched_tokens) / max(1, len(q_tokens))
        
        # Check if any retrieval score indicates relevance
        max_score = 0.0
        for cat in ["code", "commits", "docs"]:
            for item in context.get(cat, []):
                meta = item.get("retrieval_metadata", {})
                if "dense_cosine_sim" in meta:
                    max_score = max(max_score, float(meta["dense_cosine_sim"]))
                elif "score" in item:
                    val = float(item["score"])
                    max_score = max(max_score, val / 100.0 if val > 1.0 else val)

        # Sufficiency threshold: At least 15% term coverage or a retrieval score above 0.25
        if coverage < 0.15 and max_score < 0.25 and len(matched_tokens) == 0:
            return False, (
                f"Retrieved items have insufficient relevance to '{question}' "
                f"(term overlap: {coverage:.1%}, max retrieval score: {max_score:.2f})."
            )

        return True, "Evidence is sufficient for grounded answer synthesis."

    @classmethod
    def format_evidence_catalog(cls, evidence: List[EvidenceItem]) -> str:
        """
        Formats structured EvidenceItem objects into an unambiguous, numbered catalog
        with explicit [E1], [E2] labels that the LLM must cite.
        """
        catalog_lines = ["### EVIDENCE CATALOG (Ground Truth - Citations Required)"]
        for idx, ev in enumerate(evidence, 1):
            item_header = f"[E{idx}]"
            details = []
            if ev.file_path:
                lines_str = f" (Lines {ev.line_start}-{ev.line_end})" if ev.line_start and ev.line_end else ""
                details.append(f"File: {ev.file_path}{lines_str}")
            if ev.commit_hash:
                date_str = f", Date: {ev.commit_date}" if ev.commit_date else ""
                details.append(f"Commit: {ev.commit_hash}{date_str}")
            if ev.commit_message:
                details.append(f"Commit Message: \"{ev.commit_message}\"")

            header_str = f"{item_header} {' | '.join(details)}"
            catalog_lines.append(header_str)
            catalog_lines.append(f"Snippet:\n{ev.snippet.strip()}")
            if ev.relevance_reason:
                catalog_lines.append(f"Relevance: {ev.relevance_reason}")
            catalog_lines.append("")  # Blank separator

        return "\n".join(catalog_lines)

    @classmethod
    def build_grounded_system_prompt(cls) -> str:
        """
        Generates strict grounding rules for the LLM.
        """
        return (
            "You are CodeArchaeologist, a high-assurance codebase intelligence system.\n"
            "CRITICAL INSTRUCTIONS FOR EVIDENCE GROUNDING:\n"
            "1. You must answer the question using ONLY the facts explicitly provided in the EVIDENCE CATALOG.\n"
            "2. EVERY factual statement, claim, file name, line range, or commit reference MUST be followed by "
            "one or more citation tags referencing the exact evidence items supporting it, e.g. [E1] or [E1, E2].\n"
            "3. NEVER invent, extrapolate, or assume file paths, line ranges, commit hashes, author names, dates, "
            "or technical mechanisms that do not appear in the EVIDENCE CATALOG.\n"
            "4. If the provided evidence catalog does not contain enough facts to answer the question, or if key details "
            "are missing, you MUST explicitly state: 'Insufficient evidence: [reason]'.\n"
            "5. Do NOT cite any evidence tag (such as [E99]) that does not exist in the EVIDENCE CATALOG.\n"
            "6. Any claim not anchored to an [E#] citation will be rejected by the grounding verification layer."
        )

    @classmethod
    def verify_grounding(
        cls,
        prose: str,
        evidence: List[EvidenceItem],
        question: str = ""
    ) -> GroundingVerificationResult:
        """
        Validates prose against the provided EvidenceItem catalog.
        
        Checks:
        1. Insufficient evidence detection: If LLM declared insufficient evidence, accept it.
        2. Citation existence: All [E#] tags must map to an item in 1..len(evidence).
        3. Fabricated file paths: Any mentioned file path must exist in evidence catalog.
        4. Fabricated commit hashes: Any mentioned commit hash must exist in evidence catalog.
        5. Fabricated line ranges: Line numbers mentioned for a file must match evidence items.
        6. Claim traceability: Substantive factual claims must be anchored to citation tags
           and backed by snippet terms.
        """
        if not prose or not prose.strip():
            return GroundingVerificationResult(
                is_grounded=False,
                grounding_score=0.0,
                rejection_reason="Empty response generated."
            )

        # 1. Check for explicit insufficient evidence response
        insufficient_indicators = [
            "insufficient evidence",
            "insufficient context",
            "cannot be determined from the provided evidence",
            "not enough evidence",
            "no direct evidence",
            "not mentioned in the provided evidence"
        ]
        prose_lower = prose.lower()
        if any(ind in prose_lower for ind in insufficient_indicators):
            return GroundingVerificationResult(
                is_grounded=True,
                grounding_score=1.0,
                verified_evidence=[],
                sanitized_answer=prose.strip()
            )

        num_evidence = len(evidence)
        valid_evidence_tags = {f"E{i}": i - 1 for i in range(1, num_evidence + 1)}

        # Known valid entities from evidence catalog
        valid_paths = {ev.file_path.replace("\\", "/").lower() for ev in evidence if ev.file_path}
        valid_filenames = {ev.file_path.replace("\\", "/").split("/")[-1].lower() for ev in evidence if ev.file_path}
        valid_hashes = set()
        for ev in evidence:
            if ev.commit_hash:
                h = ev.commit_hash.lower()
                valid_hashes.add(h)
                if len(h) >= 7:
                    valid_hashes.add(h[:7])
                    valid_hashes.add(h[:8])

        # 2. Extract and validate [E#] citations
        citation_matches = re.findall(r'\[(?:Evidence\s*|E)?(\d+)\]', prose, re.IGNORECASE)
        cited_indices: Set[int] = set()
        fabricated_citations: List[str] = []

        for c in citation_matches:
            c_tag = f"E{c}"
            if c_tag in valid_evidence_tags:
                cited_indices.add(valid_evidence_tags[c_tag])
            else:
                fabricated_citations.append(c_tag)

        # 3. Detect fabricated file paths mentioned in text
        # Regex matches paths with file extensions or directory paths (e.g., src/foo/bar.ts, app/models/schemas.py)
        path_pattern = re.compile(r'\b([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,8})\b')
        potential_paths = path_pattern.findall(prose)
        fabricated_paths: List[str] = []
        
        # Ignored common words or markdown artefacts with dots
        ignored_extensions = {"md", "txt"}  # README.md is common, but let's check properly
        for p in potential_paths:
            normalized_p = p.replace("\\", "/").lower()
            fname = normalized_p.split("/")[-1]
            # Ignore version numbers like v1.5 or floating points or standard markdown formatting
            if re.match(r'^\d+\.\d+', p) or normalized_p.startswith("http") or normalized_p.endswith((".com", ".org", ".io")):
                continue
            # If it's a file path like something.ts or something.py
            if any(normalized_p.endswith(ext) for ext in [".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".cpp", ".c", ".h", ".json", ".yaml", ".yml"]):
                if normalized_p not in valid_paths and fname not in valid_filenames:
                    fabricated_paths.append(p)

        # 4. Detect fabricated commit hashes
        # Regex matches standalone hex hashes of length 7 to 40
        hash_pattern = re.compile(r'\b([0-9a-fA-F]{7,40})\b')
        potential_hashes = hash_pattern.findall(prose)
        fabricated_commits: List[str] = []
        for h in potential_hashes:
            h_lower = h.lower()
            # Avoid matching common words that look like hex (e.g. "decade", "defaced") unless in commit context
            is_valid = any(h_lower.startswith(vh) or vh.startswith(h_lower) for vh in valid_hashes)
            if not is_valid and not valid_hashes:
                fabricated_commits.append(h)
            elif not is_valid and valid_hashes:
                fabricated_commits.append(h)

        # 5. Detect fabricated line ranges
        # e.g., L100-L150 or lines 100-150
        line_pattern = re.compile(r'(?:L|lines?\s*)(\d+)\s*(?:-|–|to)\s*(?:L|lines?\s*)?(\d+)', re.IGNORECASE)
        line_matches = line_pattern.findall(prose)
        fabricated_line_ranges: List[str] = []
        for l_start_s, l_end_s in line_matches:
            l_start, l_end = int(l_start_s), int(l_end_s)
            matched_evidence_line = False
            for ev in evidence:
                if ev.line_start is not None and ev.line_end is not None:
                    # Allow slight tolerance if within the range
                    if abs(ev.line_start - l_start) <= 5 and abs(ev.line_end - l_end) <= 5:
                        matched_evidence_line = True
                        break
            if not matched_evidence_line and any(ev.line_start is not None for ev in evidence):
                fabricated_line_ranges.append(f"L{l_start}-L{l_end}")

        # 6. Claim traceability and grounding check
        # Break into sentences and verify that sentences making factual claims are grounded
        sentences = cls._split_into_sentences(prose)
        unsupported_claims: List[str] = []
        grounded_sentences_count = 0
        substantive_sentences_count = 0

        for sentence in sentences:
            s_clean = sentence.strip()
            if not s_clean or len(s_clean) < 20:
                continue

            # Ignore structural headings and boilerplate
            if s_clean.startswith(("#", "-", "*", ">", "1.", "2.", "3.", "4.", "5.")):
                # Strip markdown bullet
                s_clean = re.sub(r'^[#\-*>\d.]+\s*', '', s_clean)
            if not s_clean or len(s_clean) < 20:
                continue

            substantive_sentences_count += 1

            # Check if sentence has citation tags
            s_citations = re.findall(r'\[(?:Evidence\s*|E)?(\d+)\]', sentence, re.IGNORECASE)
            valid_s_citations = [int(c) - 1 for c in s_citations if f"E{c}" in valid_evidence_tags]

            if valid_s_citations:
                # Validate that the sentence content actually has semantic overlap with the cited snippets
                s_tokens = cls._extract_meaningful_tokens(sentence)
                snippet_text = " ".join([
                    f"{evidence[idx].snippet} {evidence[idx].file_path} {evidence[idx].commit_message or ''}"
                    for idx in valid_s_citations if idx < len(evidence)
                ]).lower()
                
                # Check token overlap with cited snippets
                overlap = [t for t in s_tokens if t in snippet_text]
                if s_tokens and (len(overlap) / len(s_tokens) >= 0.20 or len(overlap) >= 2):
                    grounded_sentences_count += 1
                else:
                    unsupported_claims.append(f"{sentence} (Cites [E{','.join(s_citations)}] but terms are not found in cited snippet)")
            else:
                # No citation: Check if it's general introductory prose or an uncited factual assertion
                s_tokens = cls._extract_meaningful_tokens(sentence)
                all_evidence_text = " ".join([
                    f"{ev.snippet} {ev.file_path} {ev.commit_message or ''}" for ev in evidence
                ]).lower()
                overlap = [t for t in s_tokens if t in all_evidence_text]
                
                # If sentence mentions specific technical assertions, require grounding
                has_code_identifiers = bool(re.search(r'`[a-zA-Z0-9_$]+`|\b(?:function|class|method|commit|patch|bug)\b', sentence, re.IGNORECASE))
                if has_code_identifiers:
                    if s_tokens and (len(overlap) / len(s_tokens) >= 0.25 or len(overlap) >= 3):
                        grounded_sentences_count += 1
                    else:
                        unsupported_claims.append(f"{sentence} (Missing citation and unverified in evidence)")
                else:
                    # General bridging sentence
                    grounded_sentences_count += 1

        # Calculate score
        if substantive_sentences_count > 0:
            grounding_score = grounded_sentences_count / substantive_sentences_count
        else:
            grounding_score = 1.0 if not (fabricated_citations or fabricated_paths or fabricated_commits) else 0.0

        # Adjust score downwards for fabrications
        if fabricated_citations:
            grounding_score *= 0.5
        if fabricated_paths:
            grounding_score *= 0.5
        if fabricated_commits:
            grounding_score *= 0.5
        if fabricated_line_ranges:
            grounding_score *= 0.7

        grounding_score = round(max(0.0, min(1.0, grounding_score)), 2)

        # Grounding decision
        is_grounded = (
            grounding_score >= 0.65
            and not fabricated_citations
            and not fabricated_paths
            and not fabricated_commits
            and not fabricated_line_ranges
            and len(unsupported_claims) <= 1
        )

        rejection_reasons = []
        if fabricated_citations:
            rejection_reasons.append(f"Fabricated evidence citations: {', '.join(fabricated_citations)}")
        if fabricated_paths:
            rejection_reasons.append(f"Fabricated file paths: {', '.join(fabricated_paths)}")
        if fabricated_commits:
            rejection_reasons.append(f"Fabricated commit hashes: {', '.join(fabricated_commits)}")
        if fabricated_line_ranges:
            rejection_reasons.append(f"Fabricated line ranges: {', '.join(fabricated_line_ranges)}")
        if len(unsupported_claims) > 1:
            rejection_reasons.append(f"{len(unsupported_claims)} unsupported claims not traceable to evidence items")
        elif not is_grounded:
            rejection_reasons.append(f"Grounding score {grounding_score:.2f} below required threshold 0.65")

        rejection_reason = "; ".join(rejection_reasons) if rejection_reasons else None

        # Build list of verified evidence items actually cited or verified
        if cited_indices:
            verified_evidence = [evidence[i] for i in sorted(cited_indices) if i < len(evidence)]
        else:
            verified_evidence = evidence[:4]  # Top relevant evidence if no specific tags cited

        return GroundingVerificationResult(
            is_grounded=is_grounded,
            grounding_score=grounding_score,
            unsupported_claims=unsupported_claims,
            fabricated_citations=fabricated_citations,
            fabricated_paths=fabricated_paths,
            fabricated_commits=fabricated_commits,
            fabricated_line_ranges=fabricated_line_ranges,
            verified_evidence=verified_evidence,
            rejection_reason=rejection_reason,
            sanitized_answer=prose if is_grounded else None
        )

    @classmethod
    def enforce_grounding(
        cls,
        prose: str,
        evidence: List[EvidenceItem],
        question: str,
        local_fallback_fn: Callable[[], str]
    ) -> Tuple[str, List[EvidenceItem], float]:
        """
        Enforces grounding on LLM-generated prose.
        
        If the prose passes verification:
            Returns (prose, verified_evidence, grounding_score).
        If the prose fails verification (hallucinated citations, invented files/commits, unsupported claims):
            Rejects the ungrounded prose, logs the exact rejection reason, and falls back
            to the deterministic local synthesis path anchored directly to AST source coordinates.
        """
        audit = cls.verify_grounding(prose, evidence, question)

        if audit.is_grounded:
            return prose, audit.verified_evidence, audit.grounding_score

        logger.warning(
            f"Grounding enforcement REJECTED LLM response for query '{question}'. "
            f"Reason: {audit.rejection_reason}. Falling back to deterministic local synthesis."
        )

        # Fall back to deterministic, verified AST & Git archaeology
        fallback_answer = local_fallback_fn()
        return fallback_answer, evidence, 0.70

    @classmethod
    def _extract_meaningful_tokens(cls, text: str) -> Set[str]:
        tokens = re.findall(r'[a-zA-Z0-9_$]+', text.lower())
        return {t for t in tokens if len(t) > 2 and t not in cls.STOP_WORDS}

    @classmethod
    def _split_into_sentences(cls, text: str) -> List[str]:
        # Split on sentence endings while keeping markdown structure
        cleaned = re.sub(r'\n+', ' ', text)
        sentences = re.split(r'(?<=[.!?])\s+', cleaned)
        return [s.strip() for s in sentences if s.strip()]
