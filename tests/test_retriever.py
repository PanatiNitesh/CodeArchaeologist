import pytest
from backend.app.phase5_knowledge_rag.vector_store import LocalVectorStore
from backend.app.phase5_knowledge_rag.retriever import HybridRetriever
from backend.app.models.schemas import CommitRecord, CommitCategory

def test_hybrid_rrf_and_bm25_retriever():
    store = LocalVectorStore("test_repo", use_neural=False) # Test with TF-IDF/BM25 baseline
    
    files_data = [
        {
            "path": "src/services/paymentService.ts",
            "component_type": "Service",
            "loc": 100,
            "content": "export function processStripePayment(token: string) { return stripe.charges.create(); }",
            "functions": [{"name": "processStripePayment", "params": ["token"], "calls": ["create"], "docstring": "Processes Stripe credit card charges."}],
            "classes": [],
            "exports": [{"name": "processStripePayment"}]
        },
        {
            "path": "src/services/authService.ts",
            "component_type": "Service",
            "loc": 50,
            "content": "export function authenticateUser(token: string) { return jwt.verify(token); }",
            "functions": [{"name": "authenticateUser", "params": ["token"], "calls": ["verify"], "docstring": "Validates user JWT bearer token."}],
            "classes": [],
            "exports": [{"name": "authenticateUser"}]
        }
    ]
    
    commits = [
        CommitRecord(
            commit_id="c123456",
            short_hash="c123456",
            author="Alice",
            author_email="alice@example.com",
            date="2023-05-10",
            timestamp=1683700000,
            message="feat: integrate Stripe payment gateway for subscription billing",
            category=CommitCategory.FEATURE,
            changed_files=["src/services/paymentService.ts"],
            added_lines=100,
            deleted_lines=0
        )
    ]
    
    docs = [
        {
            "rel_path": "README.md",
            "content": "# E-Commerce Billing Engine\n\nHandles customer payment processing with Stripe."
        }
    ]
    
    store.index_repository(files_data, commits, docs)
    retriever = HybridRetriever(store)
    
    # Query for 'Stripe payment'
    context = retriever.retrieve_context("Stripe payment subscription")
    
    assert context["counts"]["code"] > 0
    assert context["counts"]["commits"] > 0
    assert context["counts"]["docs"] > 0
    
    # Top code match must be paymentService.ts
    top_code = context["code"][0]
    assert "paymentService.ts" in top_code["entity_id"]
    assert "retrieval_metadata" in top_code
    assert "Reciprocal Rank Fusion" in top_code["retrieval_metadata"]["retrieval_method"]
