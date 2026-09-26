import json
import logging
from typing import Dict, Any, List, Optional
from backend.app.models.database import db

logger = logging.getLogger(__name__)

class RepoDatabaseService:
    def __init__(self, database_manager=None):
        self.db = database_manager or db

    def save_repository(self, repo_id: str, name: str, path: str, url: str, default_branch: str, stats: Dict[str, Any]):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO repositories (id, name, path, url, default_branch, stats_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                path=excluded.path,
                url=excluded.url,
                default_branch=excluded.default_branch,
                stats_json=excluded.stats_json
            """, (repo_id, name, path, url, default_branch, json.dumps(stats)))
            conn.commit()

    def save_files(self, repo_id: str, files: List[Dict[str, Any]]):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure repository record exists to satisfy foreign key constraints
            cursor.execute("""
            INSERT OR IGNORE INTO repositories (id, name, path)
            VALUES (?, ?, ?)
            """, (repo_id, repo_id, ""))
            # Remove previous file records for clean re-ingestion
            cursor.execute("DELETE FROM files WHERE repo_id = ?", (repo_id,))
            
            records = [
                (
                    f"{repo_id}:{f.get('rel_path', f.get('path'))}",
                    repo_id,
                    f.get('rel_path', f.get('path')),
                    f["name"],
                    f["extension"],
                    f["size_bytes"],
                    f["loc"],
                    f.get("component_type", "Unknown") if isinstance(f.get("component_type"), str) else f.get("component_type", "Unknown").value if hasattr(f.get("component_type"), "value") else "Unknown",
                    f.get("component_confidence", 0.0),
                    f["content"]
                )
                for f in files
            ]
            cursor.executemany("""
            INSERT INTO files (id, repo_id, path, name, extension, size_bytes, loc, component_type, component_confidence, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            conn.commit()

    def get_repository(self, repo_id: str) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "name": row["name"],
                "path": row["path"],
                "url": row["url"],
                "default_branch": row["default_branch"],
                "cloned_at": row["cloned_at"],
                "stats": json.loads(row["stats_json"]) if row["stats_json"] else {}
            }

    def list_repositories(self) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT * FROM repositories ORDER BY cloned_at DESC").fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "path": r["path"],
                    "url": r["url"],
                    "default_branch": r["default_branch"],
                    "cloned_at": r["cloned_at"],
                    "stats": json.loads(r["stats_json"]) if r["stats_json"] else {}
                }
                for r in rows
            ]

    def get_files_for_repo(self, repo_id: str) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("""
            SELECT id, repo_id, path, name, extension, size_bytes, loc, component_type, component_confidence
            FROM files WHERE repo_id = ? ORDER BY path ASC
            """, (repo_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_file_content(self, repo_id: str, path: str) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT * FROM files WHERE repo_id = ? AND path = ?", (repo_id, path)).fetchone()
            if row:
                return dict(row)
            return None
