import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from backend.app.phase1_ingestion.cloner import RepoCloner
from backend.app.phase1_ingestion.extractor import RepoExtractor
from backend.app.phase1_ingestion.repo_db import RepoDatabaseService
from backend.app.phase2_ast.parser import CodeASTParser
from backend.app.phase3_graph.classifier import ComponentClassifier
from backend.app.phase3_graph.dependency_graph import DependencyGraphBuilder
from backend.app.phase3_graph.call_graph import CallGraphBuilder
from backend.app.phase4_archaeology.commit_miner import CommitMiner
from backend.app.phase4_archaeology.timeline import TimelineBuilder
from backend.app.phase4_archaeology.code_evolution import CodeEvolutionArchaeologist
from backend.app.phase5_knowledge_rag.vector_store import LocalVectorStore
from backend.app.phase5_knowledge_rag.retriever import HybridRetriever
from backend.app.phase5_knowledge_rag.rag_engine import EvidenceRAGEngine
from backend.app.phase6_blast_radius.blast_calculator import BlastRadiusCalculator
from backend.app.phase6_blast_radius.change_predictor import MLChangeImpactPredictor
from backend.app.phase7_evaluation.arch_evaluator import ArchitectureEvaluator
from backend.app.phase7_evaluation.blast_evaluator import BlastRadiusEvaluator
from backend.app.models.schemas import OverallEvaluation, SoftwareGraph, SoftwareTimeline

logger = logging.getLogger(__name__)

class CodeArchaeologistPipeline:
    """
    Master Coordinator for all 8 Phases of CodeArchaeologist.
    """

    def __init__(self, repo_id: str, repo_path: str):
        self.repo_id = repo_id
        self.repo_path = repo_path
        
        self.db_service = RepoDatabaseService()
        self.ast_parser = CodeASTParser()
        self.classifier = ComponentClassifier()
        self.graph_builder = DependencyGraphBuilder()
        self.call_graph_builder = CallGraphBuilder()
        self.commit_miner = CommitMiner()
        self.timeline_builder = TimelineBuilder()
        self.evolution_archaeologist = CodeEvolutionArchaeologist()
        self.arch_evaluator = ArchitectureEvaluator()

        # State storage
        self.files_data = []
        self.commits = []
        self.software_graph: Optional[SoftwareGraph] = None
        self.timeline: Optional[SoftwareTimeline] = None
        self.nx_dep_graph = None
        self.vector_store: Optional[LocalVectorStore] = None
        self.rag_engine: Optional[EvidenceRAGEngine] = None
        self.blast_calculator: Optional[BlastRadiusCalculator] = None
        self.change_predictor: Optional[MLChangeImpactPredictor] = None
        self.evaluation_result: Optional[OverallEvaluation] = None

    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Executes Phase 1 through Phase 7 sequentially.
        """
        logger.info(f"=== Starting CodeArchaeologist Analysis for {self.repo_id} ===")

        # PHASE 1: Extraction
        extractor = RepoExtractor(self.repo_path)
        raw_files = extractor.extract_files()
        
        # PHASE 2: AST Parsing
        parsed_files = []
        docs = []
        for rf in raw_files:
            if rf["extension"] == ".md":
                docs.append(rf)
                continue
            
            p_res = self.ast_parser.parse_file(rf["rel_path"], rf["content"])
            # Merge with file metadata
            p_res.update({
                "rel_path": rf["rel_path"],
                "path": rf["rel_path"],
                "name": rf["name"],
                "extension": rf["extension"],
                "size_bytes": rf["size_bytes"],
                "content": rf["content"],
                "full_path": rf["full_path"]
            })
            parsed_files.append(p_res)

        # PHASE 3: Classification & Software Graph
        classified_files = []
        for pf in parsed_files:
            ctype, conf = self.classifier.classify_file(pf["path"], pf["content"], pf)
            pf["component_type"] = ctype
            pf["component_confidence"] = conf
            classified_files.append(pf)

        self.files_data = classified_files
        self.db_service.save_files(self.repo_id, classified_files)
        self.ast_parser.save_parsed_data(self.repo_id, classified_files)

        # Build Dependency Graph
        self.software_graph = self.graph_builder.build_graph(self.repo_id, classified_files)
        
        # Build NetworkX internal graph
        import networkx as nx
        G = nx.DiGraph()
        for node in self.software_graph.nodes:
            G.add_node(node.id, component_type=node.component_type, loc=node.loc)
        for edge in self.software_graph.edges:
            G.add_edge(edge.source, edge.target, relation=edge.relation.value)
        self.nx_dep_graph = G

        # Build Call Graph
        call_analysis = self.call_graph_builder.build_call_graph(classified_files)

        # PHASE 4: Git History Archaeology
        self.commits = self.commit_miner.mine_commits(self.repo_id, self.repo_path)
        self.timeline = self.timeline_builder.build_timeline(self.commits)

        # PHASE 5: Knowledge Layer & Vector Store
        self.vector_store = LocalVectorStore(self.repo_id)
        self.vector_store.index_repository(classified_files, self.commits, docs)
        retriever = HybridRetriever(self.vector_store)
        self.rag_engine = EvidenceRAGEngine(retriever)

        # PHASE 6: Blast Radius & ML Change Predictor
        file_meta_map = {f["path"]: f for f in classified_files}
        self.blast_calculator = BlastRadiusCalculator(self.nx_dep_graph, file_meta_map)
        self.change_predictor = MLChangeImpactPredictor(self.commits, self.nx_dep_graph, file_meta_map)

        # PHASE 7: Evaluation Suite
        arch_metrics = self.arch_evaluator.evaluate_graph(self.nx_dep_graph, classified_files)
        blast_eval = BlastRadiusEvaluator(self.change_predictor, self.blast_calculator)
        blast_metrics = blast_eval.evaluate_historical_commits(self.commits)

        self.evaluation_result = OverallEvaluation(
            architecture_eval=arch_metrics,
            blast_radius_eval=blast_metrics,
            commit_count_evaluated=len(self.commits),
            summary=(
                f"Evaluated on {len(classified_files)} source files and {len(self.commits)} Git commits. "
                f"Architecture Discovery F1: {arch_metrics.f1_score:.3f}. "
                f"Historical Blast Radius Impact F1: {blast_metrics.f1_score:.3f}."
            )
        )

        # Save Repository Stats
        stats = {
            "total_files": len(classified_files),
            "total_loc": sum([f.get("loc", 0) for f in classified_files]),
            "total_commits": len(self.commits),
            "total_nodes": self.software_graph.stats.get("total_nodes", 0),
            "total_edges": self.software_graph.stats.get("total_edges", 0),
            "arch_f1": arch_metrics.f1_score,
            "blast_f1": blast_metrics.f1_score
        }
        self.db_service.save_repository(
            repo_id=self.repo_id,
            name=Path(self.repo_path).name,
            path=self.repo_path,
            url=self.repo_path,
            default_branch="main",
            stats=stats
        )

        return {
            "repo_id": self.repo_id,
            "stats": stats,
            "call_flows": call_analysis.get("discovered_flows", []),
            "timeline_milestones": len(self.timeline.milestones),
            "eval_summary": self.evaluation_result.summary
        }
