import os
import json
import networkx as nx
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from backend.app.models.schemas import RelationType, ComponentType, GraphNode, GraphEdge, SoftwareGraph
from backend.app.models.database import db

class DependencyGraphBuilder:
    def __init__(self):
        pass

    def resolve_import_path(self, current_file: str, import_source: str, all_files: Set[str]) -> Optional[str]:
        """
        Resolves relative import paths like './auth', '../utils/helper' to an existing repo relative file path.
        """
        if not import_source.startswith("."):
            # Check for path aliases like '@/...' or 'src/...'
            clean_alias = import_source.lstrip("@/").lstrip("~/")
            for ext in ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"]:
                candidate = f"src/{clean_alias}{ext}"
                if candidate in all_files:
                    return candidate
                candidate2 = f"{clean_alias}{ext}"
                if candidate2 in all_files:
                    return candidate2
            return None # External package (e.g. 'express', 'react')

        current_dir = Path(current_file).parent
        resolved_base = (current_dir / import_source).as_posix()
        # Normalize relative dots
        norm_path = Path(os.path.normpath(resolved_base)).as_posix()

        # Try various standard JS/TS extension candidates
        candidates = [
            norm_path,
            f"{norm_path}.ts",
            f"{norm_path}.tsx",
            f"{norm_path}.js",
            f"{norm_path}.jsx",
            f"{norm_path}.json",
            f"{norm_path}/index.ts",
            f"{norm_path}/index.tsx",
            f"{norm_path}/index.js",
            f"{norm_path}/index.jsx"
        ]

        for cand in candidates:
            if cand in all_files:
                return cand
        return None

    def build_graph(self, repo_id: str, files_data: List[Dict[str, Any]]) -> SoftwareGraph:
        """
        Builds a comprehensive directed graph of the software codebase.
        Nodes represent files, classes, and architectural components.
        Edges represent IMPORTS, USES, EXTENDS, CALLS.
        """
        G = nx.DiGraph()
        file_map = {f["path"]: f for f in files_data}
        all_file_paths = set(file_map.keys())

        # 1. Add all file nodes
        for f in files_data:
            path = f["path"]
            comp_type = f.get("component_type", ComponentType.UNKNOWN)
            G.add_node(
                path,
                label=Path(path).name,
                type="file",
                component_type=comp_type if isinstance(comp_type, str) else comp_type.value,
                path=path,
                loc=f.get("loc", 0)
            )

        edge_list: List[GraphEdge] = []

        # 2. Add edges based on imports & class inheritance
        for f in files_data:
            source_file = f["path"]
            
            # Imports
            for imp in f.get("imports", []):
                target_file = self.resolve_import_path(source_file, imp.get("source", ""), all_file_paths)
                if target_file and target_file != source_file:
                    G.add_edge(source_file, target_file, relation=RelationType.IMPORTS.value)
                    edge_list.append(GraphEdge(
                        source=source_file,
                        target=target_file,
                        relation=RelationType.IMPORTS,
                        details={"imported_names": imp.get("imported_names", [])}
                    ))

            # Class extends
            for cls in f.get("classes", []):
                super_class = cls.get("super_class")
                if super_class:
                    # Find which file exports this super_class
                    for other_file, odata in file_map.items():
                        if other_file != source_file:
                            exported_names = [e["name"] for e in odata.get("exports", [])] + [c["name"] for c in odata.get("classes", [])]
                            if super_class in exported_names:
                                G.add_edge(source_file, other_file, relation=RelationType.EXTENDS.value)
                                edge_list.append(GraphEdge(
                                    source=source_file,
                                    target=other_file,
                                    relation=RelationType.EXTENDS,
                                    details={"class": cls["name"], "super_class": super_class}
                                ))

        # 3. Calculate graph metrics
        in_degrees = dict(G.in_degree())
        out_degrees = dict(G.out_degree())
        degrees = dict(G.degree())

        graph_nodes: List[GraphNode] = []
        for node_id, data in G.nodes(data=True):
            graph_nodes.append(GraphNode(
                id=node_id,
                label=data.get("label", node_id),
                type=data.get("type", "file"),
                component_type=data.get("component_type"),
                path=data.get("path"),
                loc=data.get("loc"),
                degree=degrees.get(node_id, 0),
                in_degree=in_degrees.get(node_id, 0),
                out_degree=out_degrees.get(node_id, 0)
            ))

        stats = {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "density": nx.density(G) if G.number_of_nodes() > 1 else 0.0,
            "connected_components": nx.number_weakly_connected_components(G) if G.number_of_nodes() > 0 else 0
        }

        # Persist to database
        self._save_edges_to_db(repo_id, edge_list)

        return SoftwareGraph(nodes=graph_nodes, edges=edge_list, stats=stats)

    def _save_edges_to_db(self, repo_id: str, edges: List[GraphEdge]):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM graph_edges WHERE repo_id = ?", (repo_id,))
            records = [
                (
                    f"{repo_id}:{e.source}->{e.target}:{e.relation.value}",
                    repo_id,
                    e.source,
                    e.target,
                    e.relation.value,
                    1.0,
                    json.dumps(e.details or {})
                )
                for e in edges
            ]
            cursor.executemany("""
            INSERT OR REPLACE INTO graph_edges (id, repo_id, source, target, relation, weight, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records)
            conn.commit()
