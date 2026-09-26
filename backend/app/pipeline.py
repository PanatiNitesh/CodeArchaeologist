import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from backend.app.models.database import db
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
from backend.app.models.schemas import OverallEvaluation, SoftwareGraph, SoftwareTimeline, CommitRecord, CommitCategory, ComponentType

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
        self.software_graph = self.graph_builder.build_graph(self.repo_id, classified_files, repo_path=self.repo_path)
        
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
        rename_map = {}
        for commit in self.commits:
            for path, status in getattr(commit, "file_statuses", {}).items():
                if status and status.startswith("renamed_to:"):
                    new_path = status.replace("renamed_to:", "").replace("\\", "/")
                    rename_map[path.replace("\\", "/")] = new_path
        for old_p, new_p in list(rename_map.items()):
            while new_p in rename_map:
                new_p = rename_map[new_p]
            rename_map[old_p] = new_p

        file_meta_map = {f["path"]: f for f in classified_files}
        self.blast_calculator = BlastRadiusCalculator(self.nx_dep_graph, file_meta_map)
        self.change_predictor = MLChangeImpactPredictor(self.commits, self.nx_dep_graph, file_meta_map, rename_map=rename_map)

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

    def load_from_db(self) -> bool:
        """
        Restores full pipeline state directly from SQLite without re-running analysis.
        Returns True if successful, False if no persisted state exists.
        """
        try:
            repo_info = self.db_service.get_repository(self.repo_id)
            if not repo_info:
                return False

            with db.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Load files
                file_rows = cursor.execute("SELECT * FROM files WHERE repo_id = ?", (self.repo_id,)).fetchall()
                if not file_rows:
                    return False

                # 2. Load symbols
                symbol_rows = cursor.execute("SELECT * FROM symbols WHERE repo_id = ?", (self.repo_id,)).fetchall()
                symbols_by_path = {}
                for s in symbol_rows:
                    fpath = s["file_id"].split(":", 1)[1] if ":" in s["file_id"] else s["file_id"]
                    if fpath not in symbols_by_path:
                        symbols_by_path[fpath] = {"classes": [], "functions": []}
                    calls = json.loads(s["calls_json"] or "[]")
                    if s["kind"] == "class":
                        methods = json.loads(s["params_json"] or "[]")
                        super_class = s["docstring"].replace("Extends ", "") if s["docstring"] and s["docstring"].startswith("Extends ") else None
                        symbols_by_path[fpath]["classes"].append({
                            "name": s["name"],
                            "kind": "class",
                            "start_line": s["start_line"],
                            "end_line": s["end_line"],
                            "methods": methods,
                            "calls": calls,
                            "super_class": super_class
                        })
                    else:
                        params = json.loads(s["params_json"] or "[]")
                        symbols_by_path[fpath]["functions"].append({
                            "name": s["name"],
                            "kind": s["kind"],
                            "start_line": s["start_line"],
                            "end_line": s["end_line"],
                            "params": params,
                            "calls": calls,
                            "docstring": s["docstring"]
                        })

                # 3. Load imports
                import_rows = cursor.execute("SELECT * FROM imports WHERE repo_id = ?", (self.repo_id,)).fetchall()
                imports_by_path = {}
                for imp in import_rows:
                    fpath = imp["file_id"].split(":", 1)[1] if ":" in imp["file_id"] else imp["file_id"]
                    if fpath not in imports_by_path:
                        imports_by_path[fpath] = []
                    imports_by_path[fpath].append({
                        "source": imp["source"],
                        "imported_names": json.loads(imp["imported_names_json"] or "[]"),
                        "raw": imp["raw"]
                    })

                # 4. Load exports
                export_rows = cursor.execute("SELECT * FROM exports WHERE repo_id = ?", (self.repo_id,)).fetchall()
                exports_by_path = {}
                for exp in export_rows:
                    fpath = exp["file_id"].split(":", 1)[1] if ":" in exp["file_id"] else exp["file_id"]
                    if fpath not in exports_by_path:
                        exports_by_path[fpath] = []
                    exports_by_path[fpath].append({
                        "name": exp["name"],
                        "kind": exp["kind"],
                        "line": exp["line"]
                    })

                # Reconstruct files_data
                reconstructed_files = []
                for fr in file_rows:
                    p = fr["path"]
                    syms = symbols_by_path.get(p, {"classes": [], "functions": []})
                    ctype = fr["component_type"]
                    try:
                        enum_ctype = ComponentType(ctype) if ctype in [c.value for c in ComponentType] else ComponentType.UNKNOWN
                    except Exception:
                        enum_ctype = ComponentType.UNKNOWN

                    reconstructed_files.append({
                        "path": p,
                        "rel_path": p,
                        "name": fr["name"],
                        "extension": fr["extension"],
                        "size_bytes": fr["size_bytes"],
                        "loc": fr["loc"],
                        "component_type": enum_ctype,
                        "component_confidence": fr["component_confidence"],
                        "content": fr["content"],
                        "full_path": str(Path(self.repo_path) / p),
                        "classes": syms["classes"],
                        "functions": syms["functions"],
                        "imports": imports_by_path.get(p, []),
                        "exports": exports_by_path.get(p, []),
                        "calls": [c for fn in syms["functions"] for c in fn.get("calls", [])] + [c for cls in syms["classes"] for c in cls.get("calls", [])]
                    })
                self.files_data = reconstructed_files

                # 5. Build Graph
                self.software_graph = self.graph_builder.build_graph(self.repo_id, self.files_data, repo_path=self.repo_path)
                import networkx as nx
                G = nx.DiGraph()
                for node in self.software_graph.nodes:
                    G.add_node(node.id, component_type=node.component_type, loc=node.loc)
                for edge in self.software_graph.edges:
                    G.add_edge(edge.source, edge.target, relation=edge.relation.value)
                self.nx_dep_graph = G

                # 6. Load commits
                commit_rows = cursor.execute("SELECT * FROM commits WHERE repo_id = ? ORDER BY timestamp ASC", (self.repo_id,)).fetchall()
                reconstructed_commits = []
                for cr in commit_rows:
                    cat = cr["category"]
                    reconstructed_commits.append(CommitRecord(
                        commit_id=cr["hash"],
                        short_hash=cr["hash"][:7],
                        author=cr["author"] or "Unknown",
                        author_email=cr["email"] or "",
                        date=cr["date_str"],
                        timestamp=cr["timestamp"],
                        message=cr["message"],
                        category=CommitCategory(cat) if cat in [c.value for c in CommitCategory] else CommitCategory.OTHER,
                        changed_files=json.loads(cr["changed_files_json"] or "[]"),
                        added_lines=cr["added_lines"] or 0,
                        deleted_lines=cr["deleted_lines"] or 0
                    ))
                self.commits = reconstructed_commits
                self.timeline = self.timeline_builder.build_timeline(self.commits)

                # 7. Initialize Vector Store & RAG Engine
                self.vector_store = LocalVectorStore(self.repo_id)
                self.vector_store.index_repository(self.files_data, self.commits, [])
                retriever = HybridRetriever(self.vector_store)
                self.rag_engine = EvidenceRAGEngine(retriever)

                # 8. Initialize Blast Radius & ML Predictor
                rename_rows = cursor.execute(
                    "SELECT file_path, status FROM commit_files WHERE repo_id = ? AND status LIKE 'renamed_to:%'",
                    (self.repo_id,)
                ).fetchall()
                rename_map = {}
                for r in rename_rows:
                    old_p = r["file_path"].replace("\\", "/")
                    new_p = r["status"].replace("renamed_to:", "").replace("\\", "/")
                    rename_map[old_p] = new_p
                for old_p, new_p in list(rename_map.items()):
                    while new_p in rename_map:
                        new_p = rename_map[new_p]
                    rename_map[old_p] = new_p

                file_meta_map = {f["path"]: f for f in self.files_data}
                self.blast_calculator = BlastRadiusCalculator(self.nx_dep_graph, file_meta_map)
                self.change_predictor = MLChangeImpactPredictor(self.commits, self.nx_dep_graph, file_meta_map, rename_map=rename_map)

                # 9. Evaluation
                arch_metrics = self.arch_evaluator.evaluate_graph(self.nx_dep_graph, self.files_data)
                blast_eval = BlastRadiusEvaluator(self.change_predictor, self.blast_calculator)
                blast_metrics = blast_eval.evaluate_historical_commits(self.commits)
                self.evaluation_result = OverallEvaluation(
                    architecture_eval=arch_metrics,
                    blast_radius_eval=blast_metrics,
                    commit_count_evaluated=len(self.commits),
                    summary=(
                        f"Evaluated on {len(self.files_data)} source files and {len(self.commits)} Git commits. "
                        f"Architecture Discovery F1: {arch_metrics.f1_score:.3f}. "
                        f"Historical Blast Radius Impact F1: {blast_metrics.f1_score:.3f}."
                    )
                )

            logger.info(f"Successfully reloaded pipeline for {self.repo_id} from SQLite database.")
            return True
        except Exception as e:
            logger.warning(f"Could not restore pipeline for {self.repo_id} from database: {e}", exc_info=True)
            return False
