import logging
from typing import List, Dict, Any
from backend.app.phase5_knowledge_rag.vector_store import LocalVectorStore

logger = logging.getLogger(__name__)

class HybridRetriever:
    """
    Combines semantic vector search, graph relations, and Git commit archaeology.
    """

    def __init__(self, vector_store: LocalVectorStore):
        self.vector_store = vector_store

    def retrieve_context(self, question: str, max_code: int = 4, max_commits: int = 3, max_docs: int = 2) -> Dict[str, Any]:
        """
        Retrieves matching code chunks, historical commits, and documentation snippets.
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
