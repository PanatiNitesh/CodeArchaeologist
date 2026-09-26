import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List
from backend.app.models.schemas import EvidenceItem, CommitRecord, CommitCategory
from backend.app.phase5_knowledge_rag.grounding import GroundingEnforcer, GroundingVerificationResult
from backend.app.phase5_knowledge_rag.rag_engine import EvidenceRAGEngine
from backend.app.phase5_knowledge_rag.retriever import HybridRetriever
from backend.app.phase5_knowledge_rag.vector_store import LocalVectorStore

@pytest.fixture
def sample_evidence() -> List[EvidenceItem]:
    return [
        EvidenceItem(
            file_path="src/services/authService.ts",
            line_start=15,
            line_end=45,
            snippet="export function authenticateUser(token: string) { return jwt.verify(token, SECRET_KEY); }",
            relevance_reason="Defines authenticateUser function relevant to query."
        ),
        EvidenceItem(
            file_path="src/services/paymentService.ts",
            commit_hash="a1b2c3d",
            commit_message="feat: migrate Stripe payment provider to v3 webhooks",
            commit_date="2023-08-14",
            snippet="Commit a1b2c3d by Alice on 2023-08-14: feat: migrate Stripe payment provider. Changed files: src/services/paymentService.ts",
            relevance_reason="Historical milestone introduced Stripe webhook change."
        )
    ]

def test_missing_evidence_returns_explicit_insufficient_evidence():
    """
    When no code or commit evidence is available, the system must immediately
    return an explicit 'Insufficient evidence' response with zero confidence.
    """
    mock_retriever = MagicMock()
    mock_retriever.retrieve_context.return_value = {
        "code": [],
        "commits": [],
        "docs": [],
        "counts": {"code": 0, "commits": 0, "docs": 0}
    }

    engine = EvidenceRAGEngine(mock_retriever)
    response = engine.answer_question("How does quantum encryption work in this repo?")

    assert "Insufficient Evidence" in response.answer or "insufficient evidence" in response.answer.lower()
    assert response.confidence_score == 0.0
    assert len(response.evidence) == 0

def test_irrelevant_distractor_evidence_triggers_insufficient_evidence():
    """
    When retrieved evidence has zero term overlap and low retrieval similarity,
    the sufficiency gate must reject the query as insufficient evidence.
    """
    mock_retriever = MagicMock()
    # Unrelated items retrieved as low-score fallbacks
    mock_retriever.retrieve_context.return_value = {
        "code": [{
            "content": "export function renderButton() { return '<button>Click</button>'; }",
            "metadata": {"path": "src/ui/Button.tsx", "function": "renderButton", "line_start": 5, "line_end": 15},
            "score": 5.0,
            "retrieval_metadata": {"dense_cosine_sim": 0.08}
        }],
        "commits": [],
        "docs": [],
        "counts": {"code": 1, "commits": 0, "docs": 0}
    }

    engine = EvidenceRAGEngine(mock_retriever)
    # Query completely unrelated to UI buttons
    response = engine.answer_question("Why was Kafka partition rebalancing timeout increased?")

    assert "Insufficient Evidence" in response.answer or "insufficient evidence" in response.answer.lower()
    assert response.confidence_score == 0.0
    assert len(response.evidence) == 0

def test_unsafe_fallbacks_are_removed(sample_evidence):
    """
    Verify that 'unknown', 'HEAD', 'git', 'history', and arbitrary 1..20 line ranges
    are never injected into EvidenceItem objects.
    """
    mock_retriever = MagicMock()
    mock_retriever.retrieve_context.return_value = {
        "code": [
            # Code without path or with 'unknown'
            {
                "content": "function mystery() {}",
                "metadata": {"path": "unknown", "line_start": 1, "line_end": 20}
            },
            # Valid code without line_start/end
            {
                "content": "export const API_URL = 'https://api.example.com';",
                "metadata": {"path": "src/config/constants.ts"}
            }
        ],
        "commits": [
            # Commit with 'HEAD' or 'unknown' hash
            {
                "content": "random commit",
                "metadata": {"commit_hash": "HEAD", "changed_files": ["git"]}
            },
            # Valid commit with empty changed_files
            {
                "content": "valid commit",
                "metadata": {"commit_hash": "c987654", "title": "fix: resolve memory leak", "changed_files": []}
            }
        ],
        "docs": [],
        "counts": {"code": 2, "commits": 2, "docs": 0}
    }

    engine = EvidenceRAGEngine(mock_retriever)
    context = mock_retriever.retrieve_context("constants memory leak")
    
    # Check EvidenceItem objects built in engine
    response = engine.answer_question("constants memory leak")
    
    for ev in response.evidence:
        assert ev.file_path != "unknown"
        assert ev.file_path != "git"
        assert ev.file_path != "history"
        if ev.commit_hash:
            assert ev.commit_hash != "HEAD"
            assert ev.commit_hash != "unknown"

def test_grounding_verifier_detects_fabricated_citations(sample_evidence):
    """
    Detects when an LLM cites evidence identifiers that do not exist (e.g. [E99]).
    """
    hallucinated_prose = (
        "Authentication is handled by jwt.verify in authService.ts [E1]. "
        "Furthermore, Redis session caching was configured in cacheManager.ts [E99]."
    )

    result = GroundingEnforcer.verify_grounding(hallucinated_prose, sample_evidence)
    
    assert not result.is_grounded
    assert "E99" in result.fabricated_citations
    assert "Fabricated evidence citations" in result.rejection_reason

def test_grounding_verifier_detects_fabricated_file_paths(sample_evidence):
    """
    Detects when an LLM introduces imaginary file paths not present in the evidence.
    """
    hallucinated_prose = (
        "The JWT token is verified inside authService.ts [E1]. "
        "User permissions are subsequently loaded from src/security/permissionResolver.ts."
    )

    result = GroundingEnforcer.verify_grounding(hallucinated_prose, sample_evidence)
    
    assert not result.is_grounded
    assert any("permissionResolver.ts" in p for p in result.fabricated_paths)
    assert "Fabricated file paths" in result.rejection_reason

def test_grounding_verifier_detects_fabricated_commit_hashes(sample_evidence):
    """
    Detects when an LLM hallucinates fake commit hashes.
    """
    hallucinated_prose = (
        "Stripe payment provider was migrated to v3 webhooks [E2]. "
        "Later, commit 9f8e7d6c5b fixed the transaction race condition."
    )

    result = GroundingEnforcer.verify_grounding(hallucinated_prose, sample_evidence)
    
    assert not result.is_grounded
    assert any("9f8e7d6c5b" in c.lower() for c in result.fabricated_commits)
    assert "Fabricated commit hashes" in result.rejection_reason

def test_grounding_verifier_detects_unsupported_claims(sample_evidence):
    """
    Detects when an LLM claims technical mechanisms or capabilities completely absent
    from the cited evidence snippets.
    """
    unsupported_prose = (
        "The system uses OAuth2 PKCE flow with asymmetric RSA keys and automatic token rotation [E1]. "
        "It persists active sessions directly into Cassandra NoSQL clusters [E1]."
    )

    result = GroundingEnforcer.verify_grounding(unsupported_prose, sample_evidence)
    
    assert not result.is_grounded
    assert len(result.unsupported_claims) > 0
    assert result.grounding_score < 0.65

def test_valid_grounded_answer_passes_verification(sample_evidence):
    """
    A well-grounded answer citing valid evidence items and staying faithful
    to the snippets passes verification with high grounding score.
    """
    valid_prose = (
        "1. Core Implementation:\n"
        "User authentication is implemented in `src/services/authService.ts` via the `authenticateUser` function, "
        "which validates bearer tokens using `jwt.verify` with `SECRET_KEY` [E1].\n\n"
        "2. Historical Evolution:\n"
        "Commit `a1b2c3d` by Alice migrated the Stripe payment provider to support v3 webhooks in `src/services/paymentService.ts` [E2].\n\n"
        "3. Verifiable Conclusion:\n"
        "Both authentication token validation and payment webhook handling are established across these modules [E1, E2]."
    )

    result = GroundingEnforcer.verify_grounding(valid_prose, sample_evidence)

    assert result.is_grounded
    assert len(result.fabricated_citations) == 0
    assert len(result.fabricated_paths) == 0
    assert len(result.fabricated_commits) == 0
    assert result.grounding_score >= 0.70
    assert len(result.verified_evidence) == 2

def test_llm_hallucination_triggers_safe_fallback_in_rag_engine(sample_evidence):
    """
    When an LLM (e.g. Gemini / OpenAI) returns hallucinated claims or fabricated citations,
    EvidenceRAGEngine rejects the output and falls back to deterministic local synthesis.
    """
    mock_retriever = MagicMock()
    mock_retriever.retrieve_context.return_value = {
        "code": [{
            "content": "export function authenticateUser(token: string) { return jwt.verify(token); }",
            "title": "Function authenticateUser",
            "metadata": {"path": "src/services/authService.ts", "function": "authenticateUser", "line_start": 15, "line_end": 45},
            "score": 85.0
        }],
        "commits": [{
            "content": "Commit a1b2c3d: feat: migrate Stripe payment provider",
            "title": "feat: migrate Stripe payment provider",
            "metadata": {"commit_hash": "a1b2c3d", "date": "2023-08-14", "author": "Alice", "changed_files": ["src/services/paymentService.ts"]},
            "score": 80.0
        }],
        "docs": [],
        "counts": {"code": 1, "commits": 1, "docs": 0}
    }

    engine = EvidenceRAGEngine(mock_retriever)

    # Simulate Gemini returning hallucinated prose with fake file and fake citation
    fake_llm_prose = "We also have src/fake/billingEngine.ts running under commit deadbeef [E99]."
    
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        with patch.object(engine, "_call_gemini_llm") as mock_gemini:
            # Let's verify what happens when _call_gemini_llm runs enforce_grounding
            def gemini_side_effect(q, ctx, ev, key):
                return GroundingEnforcer.enforce_grounding(
                    prose=fake_llm_prose,
                    evidence=ev,
                    question=q,
                    local_fallback_fn=lambda: engine._synthesize_local_evidence_answer(q, ctx, ev)
                )
            mock_gemini.side_effect = gemini_side_effect
            
            response = engine.answer_question("authenticateUser Stripe")

            # Must have rejected fake_llm_prose and returned deterministic local synthesis!
            assert "deadbeef" not in response.answer
            assert "billingEngine.ts" not in response.answer
            assert "src/services/authService.ts" in response.answer
            assert response.confidence_score > 0.0

def test_local_offline_synthesis_path_preserved():
    """
    Verifies that the offline/local synthesis path continues to work flawlessly
    without any cloud API keys.
    """
    store = LocalVectorStore("test_local_rag", use_neural=False)
    files_data = [
        {
            "path": "src/auth/jwt.ts",
            "component_type": "Service",
            "loc": 60,
            "content": "export function verifyToken(t: string) { return jwt.decode(t); }",
            "functions": [{"name": "verifyToken", "start_line": 10, "end_line": 20, "params": ["t"], "calls": ["decode"]}],
            "classes": [],
            "exports": [{"name": "verifyToken"}]
        }
    ]
    commits = [
        CommitRecord(
            commit_id="f1e2d3c",
            short_hash="f1e2d3c",
            author="Bob",
            author_email="bob@example.com",
            date="2024-01-15",
            timestamp=1705300000,
            message="feat: implement jwt token verification",
            category=CommitCategory.FEATURE,
            changed_files=["src/auth/jwt.ts"],
            added_lines=60,
            deleted_lines=0
        )
    ]
    docs = [{"rel_path": "README.md", "content": "Authentication documentation."}]
    store.index_repository(files_data, commits, docs)
    retriever = HybridRetriever(store)
    engine = EvidenceRAGEngine(retriever)

    # Ensure no API keys in env
    with patch.dict("os.environ", {}, clear=True):
        response = engine.answer_question("jwt token verification")
        
        assert "Architectural Analysis" in response.answer
        assert "src/auth/jwt.ts" in response.answer
        assert "f1e2d3c" in response.answer
        assert len(response.evidence) > 0
        assert response.confidence_score > 0.5
