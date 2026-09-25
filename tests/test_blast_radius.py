import pytest
import networkx as nx
from backend.app.phase6_blast_radius.blast_calculator import BlastRadiusCalculator
from backend.app.phase6_blast_radius.change_predictor import MLChangeImpactPredictor
from backend.app.models.schemas import ComponentType, RiskLevel, CommitRecord, CommitCategory

def test_blast_radius_calculation_and_size_normalization():
    # Build a directed graph:
    # A -> B -> C (A imports B, B imports C)
    # Modifying C impacts B (direct) and A (indirect)!
    G = nx.DiGraph()
    G.add_edge("src/controllers/orderController.ts", "src/services/orderService.ts")
    G.add_edge("src/services/orderService.ts", "src/models/orderModel.ts")
    G.add_edge("tests/order.test.ts", "src/services/orderService.ts")
    
    file_metadata = {
        "src/controllers/orderController.ts": {"component_type": ComponentType.CONTROLLER, "loc": 100},
        "src/services/orderService.ts": {"component_type": ComponentType.SERVICE, "loc": 150},
        "src/models/orderModel.ts": {"component_type": ComponentType.MODEL, "loc": 80},
        "tests/order.test.ts": {"component_type": ComponentType.TEST, "loc": 50}
    }
    
    calc = BlastRadiusCalculator(G, file_metadata)
    result = calc.calculate_blast_radius("src/models/orderModel.ts")
    
    assert "src/services/orderService.ts" in result.direct_affected_files
    assert "src/controllers/orderController.ts" in result.indirect_affected_files
    assert "src/controllers/orderController.ts" in result.affected_apis
    assert "tests/order.test.ts" in result.affected_tests
    assert result.total_impact_count == 3
    assert result.risk_score >= 50.0 # High/Critical risk because it cascades to API controller
    assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

def test_ml_change_predictor_empirical_coefficients():
    G = nx.DiGraph()
    G.add_edge("src/a.ts", "src/b.ts")
    
    file_metadata = {
        "src/a.ts": {"component_type": ComponentType.SERVICE},
        "src/b.ts": {"component_type": ComponentType.MODEL},
        "src/c.ts": {"component_type": ComponentType.UTILITY}
    }
    
    # Historical commits where a.ts and b.ts frequently co-changed
    commits = [
        CommitRecord(
            commit_id=f"hash_{i}",
            short_hash=f"h{i}",
            author="Developer",
            author_email="dev@example.com",
            date="2024-01-01 10:00:00",
            timestamp=1704096000 + i * 3600,
            message="Feature updates",
            category=CommitCategory.FEATURE,
            changed_files=["src/a.ts", "src/b.ts"],
            added_lines=10,
            deleted_lines=2
        )
        for i in range(15)
    ]
    
    predictor = MLChangeImpactPredictor(commits, G, file_metadata)
    prediction = predictor.predict_impact("src/a.ts")
    
    # Feature importance must not be hardcoded dummy numbers
    assert len(prediction.feature_importance) > 0
    total_weights = sum(prediction.feature_importance.values())
    assert 0.95 <= total_weights <= 1.05 # Normalized to ~100%
    
    # b.ts should be the highest predicted file
    predicted_paths = [p.file_path for p in prediction.predicted_files]
    assert "src/b.ts" in predicted_paths
    assert prediction.predicted_files[0].file_path == "src/b.ts"
    assert prediction.predicted_files[0].co_change_count == 15
