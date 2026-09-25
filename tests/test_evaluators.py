import pytest
import networkx as nx
from backend.app.phase7_evaluation.arch_evaluator import ArchitectureEvaluator
from backend.app.phase7_evaluation.blast_evaluator import BlastRadiusEvaluator
from backend.app.phase6_blast_radius.blast_calculator import BlastRadiusCalculator
from backend.app.phase6_blast_radius.change_predictor import MLChangeImpactPredictor
from backend.app.models.schemas import ComponentType, CommitRecord, CommitCategory

def test_architecture_evaluator_no_dishonest_floors():
    evaluator = ArchitectureEvaluator()
    
    # 1. Test empty ground truth case: Must return honest 0.0 with tested_samples=0
    G = nx.DiGraph()
    files_data = [{"path": "isolated.ts", "imports": []}]
    metrics = evaluator.evaluate_graph(G, files_data)
    
    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1_score == 0.0
    assert metrics.tested_samples == 0
    assert "No explicit local import statements found" in metrics.details["note"]
    
    # 2. Test verified graph evaluation: Must NOT clamp to max(0.70)
    G = nx.DiGraph()
    G.add_edge("src/a.ts", "src/b.ts")
    # Ground truth: a.ts imports b.ts AND c.ts (so c.ts is a false negative)
    files_data = [
        {
            "path": "src/a.ts",
            "imports": [
                {"source": "./b", "imported_names": ["b"]},
                {"source": "./c", "imported_names": ["c"]}
            ]
        },
        {"path": "src/b.ts", "imports": []},
        {"path": "src/c.ts", "imports": []}
    ]
    
    metrics = evaluator.evaluate_graph(G, files_data)
    # TP = 1 (a->b), FP = 0, FN = 1 (a->c)
    # Precision = 1.0, Recall = 0.5, F1 = (2 * 1.0 * 0.5) / 1.5 = 0.667
    assert metrics.precision == 1.0
    assert metrics.recall == 0.5
    assert metrics.f1_score == 0.667 # Truly computed, not clamped to 0.70

def test_blast_radius_evaluator_no_dishonest_floors():
    G = nx.DiGraph()
    file_metadata = {"src/a.ts": {}, "src/b.ts": {}}
    blast_calc = BlastRadiusCalculator(G, file_metadata)
    predictor = MLChangeImpactPredictor([], G, file_metadata)
    evaluator = BlastRadiusEvaluator(predictor, blast_calc)
    
    # Empty historical commits: Must return honest 0.0 with tested_samples=0, not fake 0.88
    metrics = evaluator.evaluate_historical_commits([])
    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1_score == 0.0
    assert metrics.tested_samples == 0
