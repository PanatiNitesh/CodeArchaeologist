import logging
from typing import Dict, Any, List, Set, Tuple, Optional
import networkx as nx
from backend.app.models.schemas import RelationType, ComponentType

logger = logging.getLogger(__name__)

class CallGraphBuilder:
    """
    Builds function and component call graphs across the codebase.
    Discovers multi-tier flows: API -> Controller -> Service -> Repository -> Database.
    """

    ARCH_TIERS = {
        ComponentType.CONTROLLER: 1,
        ComponentType.MIDDLEWARE: 2,
        ComponentType.SERVICE: 3,
        ComponentType.REPOSITORY: 4,
        ComponentType.MODEL: 5,
        ComponentType.UTILITY: 6,
        ComponentType.COMPONENT: 2
    }

    def _match_candidate_by_source(self, candidates: List[str], source: str, caller_file: str) -> Optional[str]:
        if not candidates or not source:
            return None

        clean_source = source.strip("./").strip("~/").strip("@/")
        source_base = clean_source.split("/")[-1].split(".")[0]

        # 1. Exact or suffix path match
        for cand in candidates:
            cand_norm = cand.replace("\\", "/")
            cand_no_ext = cand_norm.rsplit(".", 1)[0]
            if cand_no_ext.endswith(clean_source) or cand_no_ext.endswith(source.lstrip(".")):
                return cand

        # 2. File basename match
        matching_base = [
            cand for cand in candidates
            if cand.replace("\\", "/").rsplit("/", 1)[-1].split(".")[0] == source_base
        ]
        if len(matching_base) == 1:
            return matching_base[0]
        elif len(matching_base) > 1:
            caller_dir = caller_file.rsplit("/", 1)[0] if "/" in caller_file else ""
            for cand in matching_base:
                if caller_dir and caller_dir in cand:
                    return cand
            return matching_base[0]

        return None

    def build_call_graph(self, files_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        call_graph = nx.DiGraph()
        file_map = {f["path"]: f for f in files_data}
        
        # Build symbol catalog: (symbol_name -> list of files exporting it)
        export_catalog: Dict[str, List[str]] = {}
        for f in files_data:
            path = f["path"]
            for exp in f.get("exports", []):
                export_catalog.setdefault(exp["name"], []).append(path)
            for cls in f.get("classes", []):
                export_catalog.setdefault(cls["name"], []).append(path)
                for meth in cls.get("methods", []):
                    export_catalog.setdefault(meth.split(".")[-1], []).append(path)
            for fn in f.get("functions", []):
                export_catalog.setdefault(fn["name"], []).append(path)

        # Trace calls from caller files to callee files
        for f in files_data:
            caller_file = f["path"]
            caller_comp = f.get("component_type", ComponentType.UNKNOWN)
            
            # Map of local import alias -> target file (disambiguated by source)
            imported_symbols: Dict[str, str] = {}
            for imp in f.get("imports", []):
                source = imp.get("source", "")
                names = imp.get("imported_names", [])
                is_local = source.startswith(".") or source.startswith("@") or source.startswith("~") or "/" in source
                
                for name in names:
                    clean_name = name.split(" as ")[-1].strip()
                    candidates = export_catalog.get(clean_name, [])
                    if not candidates:
                        continue
                    
                    matched = self._match_candidate_by_source(candidates, source, caller_file)
                    if matched:
                        imported_symbols[clean_name] = matched
                    elif is_local and len(candidates) == 1:
                        imported_symbols[clean_name] = candidates[0]
                    # If multiple candidates and no source match, avoid collision

            # Examine all calls in this file
            for call in f.get("calls", []):
                parts = call.split(".")
                target_file = None
                
                if len(parts) > 1:
                    qualifier = parts[0]
                    method = parts[-1]
                    if qualifier in imported_symbols:
                        target_file = imported_symbols[qualifier]
                    elif method in imported_symbols:
                        target_file = imported_symbols[method]
                else:
                    target_symbol = parts[0]
                    target_file = imported_symbols.get(target_symbol)

                if not target_file:
                    target_symbol = parts[-1]
                    if target_symbol in export_catalog:
                        candidates = export_catalog[target_symbol]
                        if len(candidates) == 1 and candidates[0] != caller_file:
                            target_file = candidates[0]

                if target_file and target_file != caller_file:
                    target_comp = file_map.get(target_file, {}).get("component_type", ComponentType.UNKNOWN)
                    call_graph.add_edge(
                        caller_file,
                        target_file,
                        caller_comp=str(caller_comp),
                        target_comp=str(target_comp),
                        call=call
                    )

        # Detect canonical architectural pipelines across multi-tier layers
        discovered_flows = []
        flow_candidates = []

        # 1. Identify entry / ingress candidate nodes
        ingress_types = {
            ComponentType.CONTROLLER,
            ComponentType.COMPONENT,
            ComponentType.MIDDLEWARE
        }
        
        entry_nodes = [
            f["path"] for f in files_data
            if f.get("component_type") in ingress_types and f["path"] in call_graph
        ]

        # 2. Add structural roots (nodes that call others but are not called by internal code)
        structural_roots = [
            n for n in call_graph.nodes()
            if call_graph.in_degree(n) == 0 and call_graph.out_degree(n) > 0
        ]
        
        for root in structural_roots:
            if root not in entry_nodes:
                entry_nodes.append(root)

        # 3. If still empty, select top caller nodes by out-degree
        if not entry_nodes and call_graph.number_of_nodes() > 0:
            sorted_by_out = sorted(call_graph.nodes(), key=lambda n: call_graph.out_degree(n), reverse=True)
            entry_nodes = [n for n in sorted_by_out if call_graph.out_degree(n) > 0][:5]

        # 4. Trace downstream architectural paths from entry nodes
        seen_paths = set()
        for entry in entry_nodes[:8]:
            for target in call_graph.nodes():
                if entry == target or not nx.has_path(call_graph, entry, target):
                    continue
                try:
                    all_paths = list(nx.all_simple_paths(call_graph, entry, target, cutoff=5))
                    for p in all_paths:
                        p_tuple = tuple(p)
                        if p_tuple in seen_paths:
                            continue
                        seen_paths.add(p_tuple)

                        # Count distinct component types traversed
                        comp_types = [
                            str(file_map.get(node, {}).get("component_type", "Node"))
                            for node in p
                        ]
                        distinct_tiers = len(set(comp_types))
                        path_len = len(p)

                        flow_summary = " -> ".join([
                            f"{file_map.get(node, {}).get('component_type', 'Node')} ({node.split('/')[-1]})"
                            for node in p
                        ])
                        flow_candidates.append({
                            "path": p,
                            "flow_summary": flow_summary,
                            "length": path_len,
                            "distinct_tiers": distinct_tiers
                        })
                except Exception:
                    pass

        # Sort candidates prioritizing tier diversity and meaningful path length
        flow_candidates.sort(key=lambda x: (x["distinct_tiers"], x["length"]), reverse=True)
        discovered_flows = [
            {"path": c["path"], "flow_summary": c["flow_summary"]}
            for c in flow_candidates[:8]
        ]

        return {
            "total_call_edges": call_graph.number_of_edges(),
            "discovered_flows": discovered_flows,
            "call_edges": [
                {"source": u, "target": v, "call": data.get("call")}
                for u, v, data in call_graph.edges(data=True)
            ]
        }
