import logging
from typing import Dict, Any, List, Set, Tuple
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

        chains = []

        # Trace calls from caller files to callee files
        for f in files_data:
            caller_file = f["path"]
            caller_comp = f.get("component_type", ComponentType.UNKNOWN)
            
            # Map of local import alias -> target file
            imported_symbols: Dict[str, str] = {}
            for imp in f.get("imports", []):
                source = imp.get("source", "")
                names = imp.get("imported_names", [])
                for name in names:
                    # Look up which file has this name
                    candidates = export_catalog.get(name, [])
                    if candidates:
                        imported_symbols[name] = candidates[0]

            # Examine all calls in this file
            for call in f.get("calls", []):
                target_symbol = call.split(".")[-1]
                target_file = imported_symbols.get(target_symbol)
                
                if not target_file and target_symbol in export_catalog:
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

        # Detect canonical architectural pipelines
        discovered_flows = []
        for controller in [f["path"] for f in files_data if f.get("component_type") == ComponentType.CONTROLLER]:
            paths = []
            for target in call_graph.nodes():
                if nx.has_path(call_graph, controller, target) and controller != target:
                    try:
                        all_p = list(nx.all_simple_paths(call_graph, controller, target, cutoff=4))
                        for p in all_p[:2]: # Top 2 paths
                            flow_summary = " -> ".join([
                                f"{file_map.get(node, {}).get('component_type', 'Node')} ({node.split('/')[-1]})"
                                for node in p
                            ])
                            paths.append({"path": p, "flow_summary": flow_summary})
                    except Exception:
                        pass
            if paths:
                discovered_flows.extend(paths[:3])

        return {
            "total_call_edges": call_graph.number_of_edges(),
            "discovered_flows": discovered_flows,
            "call_edges": [
                {"source": u, "target": v, "call": data.get("call")}
                for u, v, data in call_graph.edges(data=True)
            ]
        }
