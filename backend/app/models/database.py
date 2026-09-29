import sqlite3
import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent.parent / "code_archaeologist.db"

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DB_FILE)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode and concurrency pragmas to avoid 'database is locked' errors
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 60000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA busy_timeout = 60000;")
            cursor.executescript("""
            CREATE TABLE IF NOT EXISTS repositories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                url TEXT,
                default_branch TEXT,
                cloned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stats_json TEXT
            );

            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL,
                path TEXT NOT NULL,
                name TEXT NOT NULL,
                extension TEXT,
                size_bytes INTEGER,
                loc INTEGER,
                component_type TEXT,
                component_confidence REAL,
                content TEXT,
                FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS symbols (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                repo_id TEXT NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                start_line INTEGER,
                end_line INTEGER,
                params_json TEXT,
                calls_json TEXT,
                docstring TEXT,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS imports (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                repo_id TEXT NOT NULL,
                source TEXT NOT NULL,
                imported_names_json TEXT,
                raw TEXT,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS exports (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                repo_id TEXT NOT NULL,
                name TEXT NOT NULL,
                kind TEXT,
                line INTEGER,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS commits (
                id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL,
                hash TEXT NOT NULL,
                author TEXT,
                email TEXT,
                date_str TEXT,
                timestamp INTEGER,
                message TEXT,
                category TEXT,
                added_lines INTEGER,
                deleted_lines INTEGER,
                changed_files_json TEXT,
                FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS commit_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id TEXT NOT NULL,
                commit_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT,
                FOREIGN KEY (commit_id) REFERENCES commits(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                details_json TEXT,
                FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS vector_embeddings (
                id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                metadata_json TEXT,
                vector_blob BLOB,
                FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS background_tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                progress TEXT,
                repo_id TEXT,
                error TEXT,
                summary_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                visitor_id TEXT,
                event_type TEXT NOT NULL,
                repo_id TEXT,
                details_json TEXT,
                client_ip TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repo_id);
            CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
            CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);
            CREATE INDEX IF NOT EXISTS idx_symbols_repo ON symbols(repo_id);
            CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repo_id);
            CREATE INDEX IF NOT EXISTS idx_commit_files_path ON commit_files(file_path);
            CREATE INDEX IF NOT EXISTS idx_edges_repo ON graph_edges(repo_id);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON background_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics_events(created_at);
            CREATE INDEX IF NOT EXISTS idx_analytics_visitor ON analytics_events(visitor_id);
            """)
            conn.commit()

    def save_task(self, task_id: str, status: str, progress: Optional[str] = None, repo_id: Optional[str] = None, error: Optional[str] = None, summary: Optional[Dict[str, Any]] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO background_tasks (task_id, status, progress, repo_id, error, summary_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(task_id) DO UPDATE SET
                status=excluded.status,
                progress=excluded.progress,
                repo_id=excluded.repo_id,
                error=excluded.error,
                summary_json=excluded.summary_json,
                updated_at=CURRENT_TIMESTAMP
            """, (task_id, status, progress, repo_id, error, json.dumps(summary) if summary else None))
            conn.commit()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM background_tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("summary_json"):
                try:
                    res["summary"] = json.loads(res["summary_json"])
                except Exception:
                    pass
            return res

    def record_analytics_event(
        self,
        event_type: str,
        session_id: Optional[str] = None,
        visitor_id: Optional[str] = None,
        repo_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO analytics_events (session_id, visitor_id, event_type, repo_id, details_json, client_ip, user_agent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                session_id,
                visitor_id,
                event_type,
                repo_id,
                json.dumps(details) if details else None,
                client_ip,
                user_agent
            ))
            conn.commit()
            return cursor.lastrowid

    def get_analytics_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Overview counters
            cursor.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'page_view'")
            total_visits = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT visitor_id) FROM analytics_events WHERE visitor_id IS NOT NULL AND visitor_id != ''")
            unique_visitors = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'ai_query'")
            total_ai_queries = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'blast_radius'")
            total_blast_analyses = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type IN ('repo_ingest', 'load_sample')")
            total_repos_ingested = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM analytics_events")
            total_events = cursor.fetchone()[0]

            # Event breakdown
            cursor.execute("""
            SELECT event_type, COUNT(*) as cnt 
            FROM analytics_events 
            GROUP BY event_type 
            ORDER BY cnt DESC
            """)
            breakdown = {row["event_type"]: row["cnt"] for row in cursor.fetchall()}

            # Top repositories interacted with
            cursor.execute("""
            SELECT repo_id, COUNT(*) as cnt 
            FROM analytics_events 
            WHERE repo_id IS NOT NULL AND repo_id != '' 
            GROUP BY repo_id 
            ORDER BY cnt DESC 
            LIMIT 5
            """)
            top_repos = [{"repo_id": row["repo_id"], "count": row["cnt"]} for row in cursor.fetchall()]

            # Recent events (last 30)
            cursor.execute("""
            SELECT id, event_type, repo_id, details_json, created_at 
            FROM analytics_events 
            ORDER BY id DESC 
            LIMIT 30
            """)
            recent = []
            for r in cursor.fetchall():
                item = dict(r)
                if item.get("details_json"):
                    try:
                        item["details"] = json.loads(item["details_json"])
                    except Exception:
                        item["details"] = {}
                recent.append(item)

            # Daily stats (last 14 days)
            cursor.execute("""
            SELECT date(created_at) as day, 
                   COUNT(*) as total_events, 
                   COUNT(CASE WHEN event_type = 'page_view' THEN 1 END) as visits,
                   COUNT(DISTINCT visitor_id) as unique_visitors
            FROM analytics_events 
            GROUP BY day 
            ORDER BY day DESC 
            LIMIT 14
            """)
            daily = [dict(row) for row in cursor.fetchall()]

            return {
                "total_visits": total_visits,
                "unique_visitors": unique_visitors,
                "total_ai_queries": total_ai_queries,
                "total_blast_analyses": total_blast_analyses,
                "total_repos_ingested": total_repos_ingested,
                "total_events": total_events,
                "event_breakdown": breakdown,
                "top_repos": top_repos,
                "recent_events": recent,
                "daily_stats": daily
            }

db = DatabaseManager()

