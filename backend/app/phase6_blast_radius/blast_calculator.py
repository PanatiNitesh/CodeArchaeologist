import networkx as nx
from typing import Dict, Any, List, Set
from backend.app.models.schemas import BlastRadiusResult, RiskLevel, SoftwareGraph, GraphNode, GraphEdge, RelationType, ComponentType

class BlastRadiusCalculator:
    """
    Simulates the cascading blast radius of modifying a specific file or component.
    Tracks 1-hop direct dependents, transitive multi-hop dependents, affected APIs,
    and affected test suites. Computes an overall composite Risk Score.
    """

    def __init__(self, dependency_graph: nx.DiGraph, file_metadata: Dict[str, Dict[str, Any]]):
        self.dep_graph = dependency_graph
        self.file_metadata = file_metadata
        
        # Invert graph for dependent search: If A imports B (A -> B), modifying B impacts A!
        self.reverse_graph = self.dep_graph.reverse(copy=True)

    def calculate_blast_radius(self, target_file: str) -> BlastRadiusResult:
        if target_file not in self.reverse_graph:
            # If file has no registered graph node
            return BlastRadiusResult(
                target_file=target_file,
                direct_affected_files=[],
                indirect_affected_files=[],
                affected_apis=[],
                affected_tests=[],
                total_impact_count=0,
                risk_level=RiskLevel.LOW,
                risk_score=5.0,
                explanation=f"File {target_file} is an isolated node with no incoming dependencies."
            )

        # 1. Direct dependents (1-hop)
        direct_nodes = set(self.reverse_graph.successors(target_file))

        # 2. Transitive indirect dependents (2+ hops)
        all_reachable = set(nx.descendants(self.reverse_graph, target_file))
        indirect_nodes = all_reachable - direct_nodes

        # 3. Classify affected files into APIs and Tests
        affected_apis = []
        affected_tests = []
        
        for f in all_reachable:
            meta = self.file_metadata.get(f, {})
            comp_type = meta.get("component_type")
            path_lower = f.lower()

            if comp_type == ComponentType.TEST or ".test." in path_lower or ".spec." in path_lower:
                affected_tests.append(f)
            elif comp_type == ComponentType.CONTROLLER or "/api/" in path_lower or "/routes/" in path_lower:
                affected_apis.append(f)

        total_impact = len(all_reachable)

        # 4. Compute composite risk score (0 to 100)
        # Weights: direct (x4), indirect (x2), APIs (x6), tests (x1)
        raw_risk = (len(direct_nodes) * 5) + (len(indirect_nodes) * 2.5) + (len(affected_apis) * 8)
        
        # Normalization
        risk_score = min(100.0, max(5.0, raw_risk))

        if risk_score >= 70.0 or len(affected_apis) >= 3:
            risk_level = RiskLevel.CRITICAL if risk_score >= 85.0 else RiskLevel.HIGH
        elif risk_score >= 35.0:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # 5. Build Subgraph of Impact
        impact_nodes = list(all_reachable | {target_file})
        subG = self.reverse_graph.subgraph(impact_nodes)
        
        subgraph_nodes = []
        for n in subG.nodes():
            meta = self.file_metadata.get(n, {})
            subgraph_nodes.append(GraphNode(
                id=n,
                label=n.split("/")[-1],
                type="impact_target" if n == target_file else "affected",
                component_type=meta.get("component_type"),
                path=n,
                loc=meta.get("loc", 0)
            ))

        subgraph_edges = []
        for u, v in subG.edges():
            subgraph_edges.append(GraphEdge(
                source=u,
                target=v,
                relation=RelationType.IMPORTS
            ))

        impact_graph = SoftwareGraph(
            nodes=subgraph_nodes,
            edges=subgraph_edges,
            stats={"impacted_nodes": len(subgraph_nodes)}
        )

        explanation = (
            f"Modifying '{target_file}' directly impacts {len(direct_nodes)} dependent files "
            f"and cascades into {len(indirect_nodes)} downstream files, affecting {len(affected_apis)} API endpoints "
            f"and requiring validation of {len(affected_tests)} test suites. Assessed risk: {risk_level.value.upper()} ({risk_score:.1f}%)."
        )

        return BlastRadiusResult(
            target_file=target_file,
            direct_affected_files=sorted(list(direct_nodes)),
            indirect_affected_files=sorted(list(indirect_nodes)),
            affected_apis=sorted(affected_apis),
            affected_tests=sorted(affected_tests),
            total_impact_count=total_impact,
            risk_level=risk_level,
            risk_score=round(risk_score, 1),
            impact_graph=impact_graph,
            explanation=explanation
        )
