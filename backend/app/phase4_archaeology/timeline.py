from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any
from backend.app.models.schemas import CommitRecord, SoftwareTimeline, TimelineMilestone, CommitCategory

class TimelineBuilder:
    """
    Synthesizes Git commit archaeology into high-level evolutionary milestones.
    Groups chronological eras (2022 -> 2026) and identifies architectural turning points.
    """

    def build_timeline(self, commits: List[CommitRecord]) -> SoftwareTimeline:
        if not commits:
            return SoftwareTimeline(
                total_commits=0,
                time_span="No commits found",
                milestones=[],
                category_distribution={}
            )

        # Sort commits chronologically (oldest to newest)
        sorted_commits = sorted(commits, key=lambda c: c.timestamp)
        
        first_date = sorted_commits[0].date[:10]
        last_date = sorted_commits[-1].date[:10]
        time_span = f"{first_date} to {last_date}"

        # Group by Year and Month / Quarter
        grouped: Dict[str, List[CommitRecord]] = defaultdict(list)
        category_dist: Dict[str, int] = defaultdict(int)

        for c in sorted_commits:
            dt = datetime.fromtimestamp(c.timestamp)
            key = f"{dt.year}-{dt.month:02d}"
            grouped[key].append(c)
            category_dist[c.category.value] += 1

        milestones: List[TimelineMilestone] = []

        for period, p_commits in sorted(grouped.items()):
            year, month = map(int, period.split("-"))
            cat_counts: Dict[str, int] = defaultdict(int)
            for c in p_commits:
                cat_counts[c.category.value] += 1

            # Identify key architectural commits
            key_commits = [
                c for c in p_commits
                if c.category in {
                    CommitCategory.FEATURE,
                    CommitCategory.REFACTOR,
                    CommitCategory.SECURITY,
                    CommitCategory.MIGRATION,
                    CommitCategory.PERFORMANCE
                }
            ]
            if not key_commits:
                key_commits = p_commits[:3]
            else:
                key_commits = key_commits[:5]

            # Generate headline for this milestone
            top_cat = max(cat_counts.items(), key=lambda x: x[1])[0] if cat_counts else "EVOLUTION"
            main_msg = key_commits[0].message.splitlines()[0] if key_commits else f"{len(p_commits)} updates"
            headline = f"[{top_cat}] {main_msg}"

            milestones.append(TimelineMilestone(
                year=year,
                month=month,
                period=period,
                commit_count=len(p_commits),
                top_categories=dict(cat_counts),
                key_commits=key_commits,
                headline=headline
            ))

        return SoftwareTimeline(
            total_commits=len(commits),
            time_span=time_span,
            milestones=milestones,
            category_distribution=dict(category_dist)
        )
