import git
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from backend.app.models.schemas import CommitRecord, CommitCategory
from backend.app.models.database import db
from backend.app.phase4_archaeology.commit_classifier import CommitClassifier

logger = logging.getLogger(__name__)

class CommitMiner:
    def __init__(self):
        self.classifier = CommitClassifier()

    def mine_commits(self, repo_id: str, repo_path: str, max_commits: int = 500) -> List[CommitRecord]:
        """
        Extracts historical git commits, changes, and categorizes intent.
        """
        try:
            repo = git.Repo(repo_path)
        except Exception as e:
            logger.error(f"Failed to open repo at {repo_path}: {e}")
            return []

        commits = []
        try:
            raw_commits = list(repo.iter_commits('HEAD', max_count=max_commits))
        except Exception as e:
            logger.warning(f"Could not iterate HEAD commits: {e}")
            return []

        for c in raw_commits:
            # Determine files changed & stats
            changed_files = []
            added = 0
            deleted = 0
            try:
                stats = c.stats
                changed_files = list(stats.files.keys())
                added = stats.total.get('insertions', 0)
                deleted = stats.total.get('deletions', 0)
            except Exception:
                # If stats fail, fallback to parent diff
                pass

            dt = datetime.fromtimestamp(c.committed_date)
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")

            category = self.classifier.classify_commit(c.message, changed_files)

            record = CommitRecord(
                commit_id=c.hexsha,
                short_hash=c.hexsha[:7],
                author=c.author.name or "Unknown",
                author_email=c.author.email or "",
                date=date_str,
                timestamp=c.committed_date,
                message=c.message.strip(),
                category=category,
                changed_files=changed_files,
                added_lines=added,
                deleted_lines=deleted
            )
            commits.append(record)

        self._save_commits_to_db(repo_id, commits)
        return commits

    def _save_commits_to_db(self, repo_id: str, commits: List[CommitRecord]):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM commits WHERE repo_id = ?", (repo_id,))
            cursor.execute("DELETE FROM commit_files WHERE repo_id = ?", (repo_id,))

            commit_rows = []
            file_rows = []

            for c in commits:
                commit_rows.append((
                    c.commit_id,
                    repo_id,
                    c.commit_id,
                    c.author,
                    c.author_email,
                    c.date,
                    c.timestamp,
                    c.message,
                    c.category.value,
                    c.added_lines,
                    c.deleted_lines,
                    json.dumps(c.changed_files)
                ))
                for f in c.changed_files:
                    file_rows.append((repo_id, c.commit_id, f, "modified"))

            cursor.executemany("""
            INSERT OR REPLACE INTO commits (id, repo_id, hash, author, email, date_str, timestamp, message, category, added_lines, deleted_lines, changed_files_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, commit_rows)

            cursor.executemany("""
            INSERT INTO commit_files (repo_id, commit_id, file_path, status)
            VALUES (?, ?, ?, ?)
            """, file_rows)

            conn.commit()
