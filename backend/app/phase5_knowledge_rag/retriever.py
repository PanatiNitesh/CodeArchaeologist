import logging
from typing import List, Dict, Any
from backend.app.phase5_knowledge_rag.vector_store import LocalVectorStore

logger = logging.getLogger(__name__)

class HybridRetriever:
    """
    True Multi-Channel Hybrid Retriever:
    Fuses Dense Neural Embeddings (SentenceTransformers all-MiniLM-L6-v2) and
    Lexical Okapi BM25 keyword matching via Reciprocal Rank Fusion (RRF, k=60).
    Retrieves and ranks cross-modal context: AST symbols, file source, git commits, and docs.
    """

    def __init__(self, vector_store: LocalVectorStore):
        self.vector_store = vector_store

    def retrieve_context(self, question: str, max_code: int = 4, max_commits: int = 3, max_docs: int = 2) -> Dict[str, Any]:
        """
        Executes hybrid dense + BM25 retrieval with Reciprocal Rank Fusion across:
        1. Code structures (functions, classes, files)
        2. Historical git commits & architectural milestones
        3. Project documentation & README files
        """
        # 1. Search code (functions, classes, files)
        code_matches = self.vector_store.search(question, top_k=max_code * 2)
        filtered_code = [m for m in code_matches if m["entity_type"] in {"function", "class", "file"}][:max_code]

        # 2. Search commits
        commit_matches = self.vector_store.search(question, top_k=max_commits, entity_type="commit")

        # 3. Search documentation
        doc_matches = self.vector_store.search(question, top_k=max_docs, entity_type="doc")

        return {
            "code": filtered_code,
            "commits": commit_matches,
            "docs": doc_matches,
            "counts": {
                "code": len(filtered_code),
                "commits": len(commit_matches),
                "docs": len(doc_matches)
            }
        }
