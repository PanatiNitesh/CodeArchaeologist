import json
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from backend.app.models.database import db
from backend.app.phase5_knowledge_rag.embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)

class LocalVectorStore:
    def __init__(self, repo_id: str):
        self.repo_id = repo_id
        self.engine = EmbeddingEngine()
        self.records: List[Dict[str, Any]] = []
        self.matrix: Optional[np.ndarray] = None

    def index_repository(self, files_data: List[Dict[str, Any]], commits: List[Any], docs: List[Dict[str, Any]]):
        """
        Extracts chunks from functions, classes, files, docs, and commits,
        generates embeddings, and builds the vector index.
        """
        self.records = []
        text_corpus = []

        # 1. Index documentation / README
        for doc in docs:
            doc_path = doc.get("rel_path", doc.get("path", "README.md"))
            content = doc.get("content", "")
            # Split doc into paragraphs
            paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
            for i, p in enumerate(paragraphs[:15]):
                self.records.append({
                    "id": f"doc:{doc_path}:{i}",
                    "entity_type": "doc",
                    "entity_id": doc_path,
                    "title": f"Documentation: {doc_path}",
                    "content": p,
                    "metadata": {"path": doc_path, "line_start": 1, "line_end": len(content.splitlines())}
                })
                text_corpus.append(f"Documentation {doc_path}: {p}")

        # 2. Index files
        for f in files_data:
            path = f["path"]
            comp_type = f.get("component_type", "File")
            file_summary = f"{comp_type} file {path} LOC: {f.get('loc', 0)}. Exports: {', '.join([e['name'] for e in f.get('exports', [])])}."
            self.records.append({
                "id": f"file:{path}",
                "entity_type": "file",
                "entity_id": path,
                "title": f"File: {path} ({comp_type})",
                "content": f"{file_summary}\n{f.get('content', '')[:1000]}",
                "metadata": {"path": path, "component_type": str(comp_type), "line_start": 1, "line_end": f.get("loc", 1)}
            })
            text_corpus.append(f"{path} {file_summary}")

            # 3. Index functions and methods
            for fn in f.get("functions", []):
                fn_text = f"Function {fn['name']} in {path}. Parameters: ({', '.join(fn.get('params', []))}). Calls: ({', '.join(fn.get('calls', []))}). Doc: {fn.get('docstring') or 'None'}."
                self.records.append({
                    "id": f"fn:{path}:{fn['name']}",
                    "entity_type": "function",
                    "entity_id": f"{path}#{fn['name']}",
                    "title": f"Function {fn['name']}() [{path}]",
                    "content": fn_text,
                    "metadata": {"path": path, "function": fn["name"], "line_start": fn["start_line"], "line_end": fn["end_line"]}
                })
                text_corpus.append(fn_text)

            # 4. Index classes
            for cls in f.get("classes", []):
                cls_text = f"Class {cls['name']} in {path}. Extends: {cls.get('super_class')}. Methods: ({', '.join(cls.get('methods', []))})."
                self.records.append({
                    "id": f"class:{path}:{cls['name']}",
                    "entity_type": "class",
                    "entity_id": f"{path}#{cls['name']}",
                    "title": f"Class {cls['name']} [{path}]",
                    "content": cls_text,
                    "metadata": {"path": path, "class": cls["name"], "line_start": cls["start_line"], "line_end": cls["end_line"]}
                })
                text_corpus.append(cls_text)

        # 5. Index commits
        for c in commits[:100]: # top 100 recent commits
            commit_text = f"Commit {c.short_hash} by {c.author} on {c.date}: {c.message}. Category: {c.category.value}. Changed files: {', '.join(c.changed_files[:5])}."
            self.records.append({
                "id": f"commit:{c.commit_id}",
                "entity_type": "commit",
                "entity_id": c.commit_id,
                "title": f"Commit {c.short_hash}: {c.message.splitlines()[0]}",
                "content": commit_text,
                "metadata": {
                    "commit_hash": c.short_hash,
                    "full_hash": c.commit_id,
                    "author": c.author,
                    "date": c.date,
                    "category": c.category.value,
                    "changed_files": c.changed_files
                }
            })
            text_corpus.append(commit_text)

        if text_corpus:
            logger.info(f"Embedding {len(text_corpus)} items for knowledge store...")
            self.matrix = self.engine.fit_and_embed(text_corpus)
            self._save_to_db()

    def search(self, query: str, top_k: int = 5, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.matrix is None or len(self.records) == 0:
            return []

        query_vec = self.engine.embed_query(query)
        if np.linalg.norm(query_vec) == 0:
            return []

        # Cosine similarity
        scores = np.dot(self.matrix, query_vec)

        # Apply entity_type filter if specified
        results = []
        ranked_indices = np.argsort(scores)[::-1]

        for idx in ranked_indices:
            rec = self.records[idx]
            if entity_type and rec["entity_type"] != entity_type:
                continue
            item = dict(rec)
            item["score"] = float(scores[idx])
            results.append(item)
            if len(results) >= top_k:
                break

        return results

    def _save_to_db(self):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vector_embeddings WHERE repo_id = ?", (self.repo_id,))
            rows = [
                (
                    f"{self.repo_id}:{r['id']}",
                    self.repo_id,
                    r["entity_type"],
                    r["entity_id"],
                    r["title"],
                    r["content"],
                    json.dumps(r["metadata"]),
                    self.matrix[i].tobytes() if self.matrix is not None else None
                )
                for i, r in enumerate(self.records)
            ]
            cursor.executemany("""
            INSERT OR REPLACE INTO vector_embeddings (id, repo_id, entity_type, entity_id, title, content, metadata_json, vector_blob)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()
