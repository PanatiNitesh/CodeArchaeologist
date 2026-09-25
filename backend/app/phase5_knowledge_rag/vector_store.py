import json
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from backend.app.models.database import db
from backend.app.phase5_knowledge_rag.embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)

class LocalVectorStore:
    def __init__(self, repo_id: str, use_neural: bool = True):
        self.repo_id = repo_id
        self.engine = EmbeddingEngine(use_neural=use_neural)
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
                fn_start = fn.get("start_line") or fn.get("line_start", 1)
                fn_end = fn.get("end_line") or fn.get("line_end", 1)
                fn_text = f"Function {fn['name']} in {path}. Parameters: ({', '.join(fn.get('params', []))}). Calls: ({', '.join(fn.get('calls', []))}). Doc: {fn.get('docstring') or 'None'}."
                self.records.append({
                    "id": f"fn:{path}:{fn['name']}",
                    "entity_type": "function",
                    "entity_id": f"{path}#{fn['name']}",
                    "title": f"Function {fn['name']}() [{path}]",
                    "content": fn_text,
                    "metadata": {"path": path, "function": fn["name"], "line_start": fn_start, "line_end": fn_end}
                })
                text_corpus.append(fn_text)

            # 4. Index classes
            for cls in f.get("classes", []):
                cls_start = cls.get("start_line") or cls.get("line_start", 1)
                cls_end = cls.get("end_line") or cls.get("line_end", 1)
                cls_text = f"Class {cls['name']} in {path}. Extends: {cls.get('super_class')}. Methods: ({', '.join(cls.get('methods', []))})."
                self.records.append({
                    "id": f"class:{path}:{cls['name']}",
                    "entity_type": "class",
                    "entity_id": f"{path}#{cls['name']}",
                    "title": f"Class {cls['name']} [{path}]",
                    "content": cls_text,
                    "metadata": {"path": path, "class": cls["name"], "line_start": cls_start, "line_end": cls_end}
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
            self._build_bm25_index(text_corpus)
            self._save_to_db()

    def _tokenize(self, text: str) -> List[str]:
        import re
        tokens = re.findall(r'[a-zA-Z0-9_$]+', text.lower())
        return [t for t in tokens if len(t) > 1]

    def _build_bm25_index(self, corpus: List[str]):
        """
        Builds BM25 inverted index for exact lexical keyword recall.
        """
        import math
        from collections import Counter, defaultdict

        self.tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        self.doc_lens = [len(doc) for doc in self.tokenized_corpus]
        self.avg_doc_len = sum(self.doc_lens) / max(1, len(self.doc_lens))
        self.corpus_size = len(corpus)

        self.df = defaultdict(int)
        for doc in self.tokenized_corpus:
            for term in set(doc):
                self.df[term] += 1

        self.idf = {}
        for term, freq in self.df.items():
            self.idf[term] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def bm25_search(self, query: str, top_k: int = 20, entity_type: Optional[str] = None) -> List[Tuple[int, float]]:
        """
        Computes Okapi BM25 lexical relevance score.
        """
        if not hasattr(self, 'tokenized_corpus') or not self.tokenized_corpus:
            return []

        from collections import Counter
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        k1 = 1.5
        b = 0.75
        scores = []

        for idx, doc_tokens in enumerate(self.tokenized_corpus):
            rec = self.records[idx]
            if entity_type and rec["entity_type"] != entity_type:
                continue

            tf_map = Counter(doc_tokens)
            doc_len = self.doc_lens[idx]
            score = 0.0

            for term in query_terms:
                if term in tf_map:
                    tf = tf_map[term]
                    idf = self.idf.get(term, 0.0)
                    denom = tf + k1 * (1.0 - b + b * (doc_len / max(1.0, self.avg_doc_len)))
                    score += idf * (tf * (k1 + 1.0)) / max(1e-6, denom)

            if score > 0:
                scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def dense_search(self, query: str, top_k: int = 20, entity_type: Optional[str] = None) -> List[Tuple[int, float]]:
        """
        Computes dense neural cosine similarity.
        """
        if self.matrix is None or len(self.records) == 0:
            return []

        query_vec = self.engine.embed_query(query)
        if np.linalg.norm(query_vec) == 0:
            return []

        scores = np.dot(self.matrix, query_vec)
        ranked_indices = np.argsort(scores)[::-1]

        results = []
        for idx in ranked_indices:
            rec = self.records[idx]
            if entity_type and rec["entity_type"] != entity_type:
                continue
            results.append((int(idx), float(scores[idx])))
            if len(results) >= top_k:
                break
        return results

    def search(self, query: str, top_k: int = 5, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        True Hybrid Search: Fuses Dense Semantic Search (SentenceTransformers) +
        Lexical BM25 Search using Reciprocal Rank Fusion (RRF, k=60).
        """
        if not self.records:
            return []

        # 1. Retrieve candidates from both dense neural and lexical BM25 systems
        dense_results = self.dense_search(query, top_k=max(20, top_k * 3), entity_type=entity_type)
        bm25_results = self.bm25_search(query, top_k=max(20, top_k * 3), entity_type=entity_type)

        # 2. Reciprocal Rank Fusion (RRF, standard smoothing k=60)
        rrf_k = 60
        rrf_scores: Dict[int, float] = {}
        dense_score_map = {idx: s for idx, s in dense_results}
        bm25_score_map = {idx: s for idx, s in bm25_results}

        for rank, (idx, _) in enumerate(dense_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (rrf_k + rank + 1))

        for rank, (idx, _) in enumerate(bm25_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (rrf_k + rank + 1))

        if not rrf_scores:
            # Fallback to plain top results if query was completely empty
            return [dict(r) for r in self.records[:top_k] if not entity_type or r["entity_type"] == entity_type]

        ranked_doc_ids = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)

        results = []
        for idx in ranked_doc_ids[:top_k]:
            item = dict(self.records[idx])
            item["score"] = round(rrf_scores[idx] * 100, 3) # Scaled RRF score
            item["retrieval_metadata"] = {
                "dense_cosine_sim": round(dense_score_map.get(idx, 0.0), 3),
                "bm25_score": round(bm25_score_map.get(idx, 0.0), 3),
                "rrf_score": round(rrf_scores[idx], 4),
                "retrieval_method": "Reciprocal Rank Fusion (Dense MiniLM + Lexical BM25)"
            }
            results.append(item)

        return results

    def _save_to_db(self):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR IGNORE INTO repositories (id, name, path)
            VALUES (?, ?, ?)
            """, (self.repo_id, self.repo_id, ""))
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
