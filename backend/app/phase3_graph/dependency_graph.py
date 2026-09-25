import os
import re
import json
import networkx as nx
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from backend.app.models.schemas import RelationType, ComponentType, GraphNode, GraphEdge, SoftwareGraph
from backend.app.models.database import db

class DependencyGraphBuilder:
    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path
        self.path_aliases: List[Tuple[str, List[str]]] = []
        self.base_url: str = ""
        if repo_path:
            self.load_tsconfig(repo_path)

    def load_tsconfig(self, repo_path: str):
        """
        Parses tsconfig.json / jsconfig.json to discover compilerOptions.paths and baseUrl.
        """
        self.path_aliases = []
        self.base_url = ""
        tsconfig_candidates = [
            Path(repo_path) / "tsconfig.json",
            Path(repo_path) / "tsconfig.base.json",
            Path(repo_path) / "jsconfig.json"
        ]
        for cfg_file in tsconfig_candidates:
            if cfg_file.exists():
                try:
                    with open(cfg_file, "r", encoding="utf-8", errors="replace") as f:
                        raw_text = f.read()
                    # Strip standard JS single/multi-line comments for clean JSON parsing
                    cleaned = re.sub(r'//.*', '', raw_text)
                    cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)
                    # Strip trailing commas
                    cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)
                    data = json.loads(cleaned)
                    comp_opts = data.get("compilerOptions", {})
                    self.base_url = comp_opts.get("baseUrl", "").strip("./").strip("/")
                    paths = comp_opts.get("paths", {})
                    for alias_pat, target_pats in paths.items():
                        prefix = alias_pat.replace("*", "")
                        targets = [t.replace("*", "").strip("./") for t in target_pats]
                        self.path_aliases.append((prefix, targets))
                    if self.path_aliases:
                        break
                except Exception:
                    pass

    def resolve_import_path(self, current_file: str, import_source: str, all_files: Set[str]) -> Optional[str]:
        """
        Resolves relative import paths, tsconfig path aliases (@app/*, @shared/*, ~/*),
        and multi-language imports (TS/JS/Python) to an existing repo relative file path.
        """
        exts = ["", ".ts", ".tsx", ".js", ".jsx", ".py", "/index.ts", "/index.tsx", "/index.js", "/index.jsx", "/__init__.py"]

        # 1. Relative imports starting with '.'
        if import_source.startswith("."):
            current_dir = Path(current_file).parent
            resolved_base = (current_dir / import_source).as_posix()
            norm_path = Path(os.path.normpath(resolved_base)).as_posix()
            for ext in exts:
                cand = f"{norm_path}{ext}"
                if cand in all_files:
                    return cand
            return None

        # 2. Check loaded tsconfig.json path aliases
        for prefix, targets in self.path_aliases:
            if import_source.startswith(prefix):
                suffix = import_source[len(prefix):]
                for target_prefix in targets:
                    combined = f"{target_prefix}{suffix}".strip("/")
                    if self.base_url and not combined.startswith(self.base_url):
                        candidate_bases = [f"{self.base_url}/{combined}", combined]
                    else:
                        candidate_bases = [combined]
                    for base in candidate_bases:
                        for ext in exts:
                            cand = f"{base}{ext}"
                            if cand in all_files:
                                return cand

        # 3. Standard TypeScript/JavaScript alias conventions (@/, ~/, @app/, @shared/, etc.)
        clean_alias = import_source.lstrip("@/").lstrip("~/")
        for candidate_root in ["src", "app", "lib", ""]:
            for ext in exts:
                base = f"{candidate_root}/{clean_alias}".strip("/") if candidate_root else clean_alias
                cand = f"{base}{ext}"
                if cand in all_files:
                    return cand

        # 4. Multi-language Python module import resolution (e.g. 'app.models.database' -> 'app/models/database.py')
        as_py_path = import_source.replace(".", "/")
        for prefix in ["", "src/", "backend/"]:
            for ext in [".py", "/__init__.py"]:
                cand = f"{prefix}{as_py_path}{ext}".strip("/")
                if cand in all_files:
                    return cand

        return None

    def build_graph(self, repo_id: str, files_data: List[Dict[str, Any]], repo_path: Optional[str] = None) -> SoftwareGraph:
        """
        Builds a comprehensive directed graph of the software codebase.
        Nodes represent files, classes, and architectural components.
        Edges represent IMPORTS, USES, EXTENDS, CALLS.
        """
        if repo_path and not self.path_aliases:
            self.load_tsconfig(repo_path)
        elif not self.path_aliases and files_data:
            first_full = files_data[0].get("full_path")
            first_rel = files_data[0].get("path") or files_data[0].get("rel_path")
            if first_full and first_rel:
                try:
                    inferred_root = str(Path(first_full).resolve().parents[len(Path(first_rel).parts) - 1])
                    self.load_tsconfig(inferred_root)
                except Exception:
                    pass

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

        # Pre-index exported classes and names across all files for O(1) fallback lookup
        class_export_catalog: Dict[str, List[str]] = {}
        for fpath, fdata in file_map.items():
            for exp in fdata.get("exports", []):
                class_export_catalog.setdefault(exp["name"], []).append(fpath)
            for c in fdata.get("classes", []):
                class_export_catalog.setdefault(c["name"], []).append(fpath)

        # 2. Add edges based on imports & class inheritance
        for f in files_data:
            source_file = f["path"]
            
            # Map imported names to resolved file path for exact O(1) superclass matching
            imported_symbol_to_target: Dict[str, str] = {}

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
                    # Record imported symbols for exact class resolution
                    for sym in imp.get("imported_names", []):
                        clean_sym = sym.split(" as ")[-1].strip()
                        imported_symbol_to_target[clean_sym] = target_file

            # Class extends - resolved via explicit file imports first, then catalog
            for cls in f.get("classes", []):
                super_class = cls.get("super_class")
                if not super_class:
                    continue

                # Clean super_class if qualified (e.g., 'models.BaseService' -> 'BaseService')
                clean_super = super_class.split(".")[-1].strip()
                target_file = imported_symbol_to_target.get(super_class) or imported_symbol_to_target.get(clean_super)

                # If not found in explicit imports, consult pre-indexed catalog
                if not target_file:
                    candidates = class_export_catalog.get(clean_super, [])
                    candidates = [c for c in candidates if c != source_file]
                    if len(candidates) == 1:
                        target_file = candidates[0]
                    elif len(candidates) > 1:
                        # Disambiguate by directory proximity if multiple classes share common names
                        src_dir = str(Path(source_file).parent)
                        same_dir = [c for c in candidates if str(Path(c).parent) == src_dir]
                        if len(same_dir) == 1:
                            target_file = same_dir[0]
                        # Otherwise leave unresolved to avoid false-positive edge creation

                if target_file and target_file != source_file:
                    G.add_edge(source_file, target_file, relation=RelationType.EXTENDS.value)
                    edge_list.append(GraphEdge(
                        source=source_file,
                        target=target_file,
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
            cursor.execute("""
            INSERT OR IGNORE INTO repositories (id, name, path)
            VALUES (?, ?, ?)
            """, (repo_id, repo_id, ""))
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
