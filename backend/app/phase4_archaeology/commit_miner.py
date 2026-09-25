import git
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.app.models.schemas import CommitRecord, CommitCategory
from backend.app.models.database import db
from backend.app.phase4_archaeology.commit_classifier import CommitClassifier

logger = logging.getLogger(__name__)

class CommitMiner:
    def __init__(self):
        self.classifier = CommitClassifier()

    def mine_commits(self, repo_id: str, repo_path: str, max_commits: Optional[int] = 2500) -> List[CommitRecord]:
        """
        Extracts historical git commits, changes, rename events, and categorizes intent.
        Supports configurable max_commits (pass None for exhaustive mining).
        """
        try:
            repo = git.Repo(repo_path)
        except Exception as e:
            logger.error(f"Failed to open repo at {repo_path}: {e}")
            return []

        commits = []
        try:
            iter_args = {'rev': 'HEAD'}
            if max_commits and max_commits > 0:
                iter_args['max_count'] = max_commits
            raw_commits = list(repo.iter_commits(**iter_args))
        except Exception as e:
            logger.warning(f"Could not iterate HEAD commits: {e}")
            return []

        for c in raw_commits:
            changed_files = []
            file_statuses: Dict[str, str] = {}
            added = 0
            deleted = 0

            # 1. Inspect diff with Git rename tracking (-M)
            if c.parents:
                try:
                    diffs = c.parents[0].diff(c)
                    for d in diffs:
                        if d.renamed_file:
                            file_statuses[d.b_path] = f"renamed_from:{d.a_path}"
                            file_statuses[d.a_path] = f"renamed_to:{d.b_path}"
                            if d.b_path not in changed_files:
                                changed_files.append(d.b_path)
                            if d.a_path not in changed_files:
                                changed_files.append(d.a_path)
                        elif d.new_file:
                            file_statuses[d.b_path] = "added"
                            if d.b_path not in changed_files:
                                changed_files.append(d.b_path)
                        elif d.deleted_file:
                            file_statuses[d.a_path] = "deleted"
                            if d.a_path not in changed_files:
                                changed_files.append(d.a_path)
                        else:
                            p = d.b_path or d.a_path
                            if p:
                                file_statuses[p] = "modified"
                                if p not in changed_files:
                                    changed_files.append(p)
                except Exception:
                    pass

            # 2. Extract commit stats for total line insertions and deletions
            try:
                stats = c.stats
                if not changed_files:
                    changed_files = list(stats.files.keys())
                added = stats.total.get('insertions', 0)
                deleted = stats.total.get('deletions', 0)
            except Exception:
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
                deleted_lines=deleted,
                file_statuses=file_statuses
            )
            commits.append(record)

        self._save_commits_to_db(repo_id, commits)
        return commits

    def _save_commits_to_db(self, repo_id: str, commits: List[CommitRecord]):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR IGNORE INTO repositories (id, name, path)
            VALUES (?, ?, ?)
            """, (repo_id, repo_id, ""))
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
                    status = c.file_statuses.get(f, "modified")
                    file_rows.append((repo_id, c.commit_id, f, status))

            cursor.executemany("""
            INSERT OR REPLACE INTO commits (id, repo_id, hash, author, email, date_str, timestamp, message, category, added_lines, deleted_lines, changed_files_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, commit_rows)

            cursor.executemany("""
            INSERT INTO commit_files (repo_id, commit_id, file_path, status)
            VALUES (?, ?, ?, ?)
            """, file_rows)

            conn.commit()
