import logging
from typing import List, Dict, Any, Set
from backend.app.models.schemas import EvaluationMetrics, OverallEvaluation
from backend.app.phase6_blast_radius.change_predictor import MLChangeImpactPredictor
from backend.app.phase6_blast_radius.blast_calculator import BlastRadiusCalculator

logger = logging.getLogger(__name__)

class BlastRadiusEvaluator:
    """
    Backtests Blast Radius and Change Impact prediction against empirical historical multi-file Git commits.
    Measures Precision, Recall, and F1 across past code evolution.
    """

    def __init__(self, predictor: MLChangeImpactPredictor, blast_calc: BlastRadiusCalculator):
        self.predictor = predictor
        self.blast_calc = blast_calc

    def evaluate_historical_commits(self, commits: List[Any], min_files_changed: int = 2) -> EvaluationMetrics:
        # Filter commits touching at least 2 files
        multi_file_commits = [
            c for c in commits
            if len(set([f.replace("\\", "/") for f in c.changed_files])) >= min_files_changed
        ]

        if not multi_file_commits:
            return EvaluationMetrics(
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                tested_samples=0,
                details={"note": "No multi-file commits found in repository history to evaluate co-change blast radius."}
            )

        precisions = []
        recalls = []
        f1s = []
        detailed_runs = []

        # Run experiment on up to 25 historical commits
        sample_commits = multi_file_commits[:25]

        for commit in sample_commits:
            all_changed = list(set([f.replace("\\", "/") for f in commit.changed_files]))
            if len(all_changed) < 2:
                continue

            # Pick A as seed input
            seed_file = all_changed[0]
            # Ground truth actual co-affected files: {B, C, D}
            actual_affected = set(all_changed[1:])

            # Ask model to predict given only seed_file
            prediction = self.predictor.predict_impact(seed_file, top_n=max(5, len(actual_affected) * 2))
            predicted_set = set([p.file_path for p in prediction.predicted_files])

            # Also check structural blast radius
            blast_result = self.blast_calc.calculate_blast_radius(seed_file)
            predicted_set.update(blast_result.direct_affected_files)

            tp = len(predicted_set.intersection(actual_affected))
            fp = len(predicted_set - actual_affected)
            fn = len(actual_affected - predicted_set)

            p = tp / max(1, tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / max(1, tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

            precisions.append(p)
            recalls.append(r)
            f1s.append(f1)

            detailed_runs.append({
                "commit_hash": commit.short_hash,
                "commit_msg": commit.message.splitlines()[0],
                "seed_file": seed_file,
                "ground_truth_count": len(actual_affected),
                "predicted_count": len(predicted_set),
                "true_positives": tp,
                "precision": round(p, 3),
                "recall": round(r, 3),
                "f1": round(f1, 3)
            })

        avg_p = sum(precisions) / max(1, len(precisions)) if precisions else 0.0
        avg_r = sum(recalls) / max(1, len(recalls)) if recalls else 0.0
        avg_f1 = (2 * avg_p * avg_r) / (avg_p + avg_r) if (avg_p + avg_r) > 0 else 0.0

        return EvaluationMetrics(
            precision=round(avg_p, 3),
            recall=round(avg_r, 3),
            f1_score=round(avg_f1, 3),
            tested_samples=len(precisions),
            details={
                "evaluated_commits": len(precisions),
                "top_runs": detailed_runs[:5]
            }
        )
