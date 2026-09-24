import json
from collections import Counter
from typing import Dict, Any, List, Optional
from backend.app.models.schemas import FileEvolution, CommitRecord, CommitCategory
from backend.app.models.database import db

class CodeEvolutionArchaeologist:
    """
    Connects code files and symbols directly to their Git evolutionary history.
    Finds origin, major architectural changes, bug fixes, refactors, and author tenure.
    """

    def get_file_evolution(self, repo_id: str, file_path: str) -> FileEvolution:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Query all commits that touched this file (using exact match or suffix match)
            norm_path = file_path.replace("\\", "/")
            name = norm_path.split("/")[-1]

            rows = cursor.execute("""
            SELECT c.* FROM commits c
            JOIN commit_files cf ON c.id = cf.commit_id
            WHERE c.repo_id = ? AND (cf.file_path = ? OR cf.file_path LIKE ?)
            ORDER BY c.timestamp ASC
            """, (repo_id, norm_path, f"%{name}")).fetchall()

            commits: List[CommitRecord] = []
            for r in rows:
                commits.append(CommitRecord(
                    commit_id=r["hash"],
                    short_hash=r["hash"][:7],
                    author=r["author"],
                    author_email=r["email"],
                    date=r["date_str"],
                    timestamp=r["timestamp"],
                    message=r["message"],
                    category=CommitCategory(r["category"]),
                    changed_files=json.loads(r["changed_files_json"] or "[]"),
                    added_lines=r["added_lines"],
                    deleted_lines=r["deleted_lines"]
                ))

            if not commits:
                # Return empty evolution profile
                return FileEvolution(
                    file_path=file_path,
                    created_date="Unknown",
                    created_commit=None,
                    created_by=None,
                    total_revisions=0,
                    total_authors=0,
                    authors=[],
                    major_milestones=[],
                    bug_fixes=[],
                    refactors=[],
                    recent_changes=[]
                )

            first_commit = commits[0]
            authors_counter = Counter([c.author for c in commits])
            authors_list = [a for a, _ in authors_counter.most_common()]

            bug_fixes = [c for c in commits if c.category == CommitCategory.BUG_FIX]
            refactors = [c for c in commits if c.category == CommitCategory.REFACTOR]
            
            # Formulate major milestones (e.g. 2023-08 -> Stripe integration)
            major_milestones = []
            for c in commits:
                if c.category in {
                    CommitCategory.FEATURE,
                    CommitCategory.REFACTOR,
                    CommitCategory.PERFORMANCE,
                    CommitCategory.SECURITY
                } or c == first_commit:
                    first_line = c.message.splitlines()[0]
                    # Format as: YYYY-MM -> Description
                    date_short = c.date[:7]
                    major_milestones.append({
                        "date": date_short,
                        "full_date": c.date,
                        "hash": c.short_hash,
                        "type": c.category.value,
                        "description": first_line,
                        "author": c.author
                    })

            return FileEvolution(
                file_path=file_path,
                created_date=first_commit.date,
                created_commit=first_commit.short_hash,
                created_by=first_commit.author,
                total_revisions=len(commits),
                total_authors=len(authors_list),
                authors=authors_list,
                major_milestones=major_milestones,
                bug_fixes=bug_fixes[:10],
                refactors=refactors[:10],
                recent_changes=commits[-10:][::-1] # most recent first
            )
