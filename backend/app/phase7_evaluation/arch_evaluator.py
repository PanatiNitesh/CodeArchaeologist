import networkx as nx
from typing import Dict, Any, List, Set
from backend.app.models.schemas import EvaluationMetrics

class ArchitectureEvaluator:
    """
    Evaluates Architecture & Dependency Graph accuracy.
    Measures Precision, Recall, and F1-Score of discovered architectural dependencies
    against explicit import declarations and component boundaries.
    """

    def evaluate_graph(self, dep_graph: nx.DiGraph, files_data: List[Dict[str, Any]]) -> EvaluationMetrics:
        ground_truth_edges: Set[tuple] = set()
        
        # Ground truth: explicit import statements present in code
        from pathlib import Path
        for f in files_data:
            source = f["path"]
            for imp in f.get("imports", []):
                raw_src = imp.get("source", "").strip()
                if raw_src.startswith("."):
                    target_stem = Path(raw_src).stem
                    for candidate in files_data:
                        cand_path = candidate["path"]
                        if cand_path != source and Path(cand_path).stem == target_stem:
                            ground_truth_edges.add((source, cand_path))

        predicted_edges = set(dep_graph.edges())

        if not ground_truth_edges:
            return EvaluationMetrics(
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                tested_samples=0,
                details={
                    "note": "No explicit local import statements found to establish ground-truth edges.",
                    "discovered_edges": dep_graph.number_of_edges(),
                    "graph_density": round(nx.density(dep_graph), 4) if dep_graph.number_of_nodes() > 1 else 0.0
                }
            )

        true_positives = len(predicted_edges.intersection(ground_truth_edges))
        false_positives = len(predicted_edges - ground_truth_edges)
        false_negatives = len(ground_truth_edges - predicted_edges)

        precision = true_positives / max(1, true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / max(1, true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return EvaluationMetrics(
            precision=round(precision, 3),
            recall=round(recall, 3),
            f1_score=round(f1, 3),
            tested_samples=len(ground_truth_edges),
            details={
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "total_predicted_edges": len(predicted_edges)
            }
        )
