import pytest
from backend.app.phase3_graph.dependency_graph import DependencyGraphBuilder
from backend.app.phase3_graph.call_graph import CallGraphBuilder
from backend.app.models.schemas import ComponentType

def test_relative_import_resolution():
    builder = DependencyGraphBuilder()
    all_files = {"src/services/userService.ts", "src/models/user.ts", "src/utils/logger.ts"}
    
    # Relative from src/services/userService.ts
    resolved = builder.resolve_import_path("src/services/userService.ts", "../models/user", all_files)
    assert resolved == "src/models/user.ts"

def test_tsconfig_path_aliases():
    builder = DependencyGraphBuilder()
    builder.path_aliases = [
        ("@app/", ["src/app/"]),
        ("@shared/", ["src/shared/"]),
        ("~/", ["src/"])
    ]
    all_files = {
        "src/app/services/paymentService.ts",
        "src/shared/utils/dateHelper.ts",
        "src/config/database.ts"
    }
    
    # Path alias @app/
    resolved = builder.resolve_import_path("src/routes/api.ts", "@app/services/paymentService", all_files)
    assert resolved == "src/app/services/paymentService.ts"
    
    # Path alias @shared/
    resolved2 = builder.resolve_import_path("src/app/services/paymentService.ts", "@shared/utils/dateHelper", all_files)
    assert resolved2 == "src/shared/utils/dateHelper.ts"

def test_python_module_resolution():
    builder = DependencyGraphBuilder()
    all_files = {"backend/app/models/database.py", "backend/app/pipeline.py"}
    
    resolved = builder.resolve_import_path("backend/app/main.py", "backend.app.models.database", all_files)
    assert resolved == "backend/app/models/database.py"

def test_call_graph_symbol_collision_prevention():
    builder = CallGraphBuilder()
    
    # Two files both export a function named 'getUser'
    files_data = [
        {
            "path": "src/controllers/userController.ts",
            "component_type": ComponentType.CONTROLLER,
            "imports": [
                {"source": "../services/userService", "imported_names": ["getUser"]}
            ],
            "exports": [],
            "classes": [],
            "functions": [],
            "calls": ["getUser"]
        },
        {
            "path": "src/services/userService.ts",
            "component_type": ComponentType.SERVICE,
            "imports": [],
            "exports": [{"name": "getUser", "kind": "named", "line": 10}],
            "classes": [],
            "functions": [{"name": "getUser", "kind": "function"}],
            "calls": []
        },
        {
            "path": "src/legacy/oldUserHelper.ts",
            "component_type": ComponentType.UTILITY,
            "imports": [],
            "exports": [{"name": "getUser", "kind": "named", "line": 5}],
            "classes": [],
            "functions": [{"name": "getUser", "kind": "function"}],
            "calls": []
        }
    ]
    
    result = builder.build_call_graph(files_data)
    edges = result["call_edges"]
    
    # userController imports from ../services/userService, NOT legacy/oldUserHelper
    assert len(edges) == 1
    assert edges[0]["source"] == "src/controllers/userController.ts"
    assert edges[0]["target"] == "src/services/userService.ts"

def test_class_extends_import_disambiguation():
    builder = DependencyGraphBuilder()
    files_data = [
        # Subclass importing BaseService specifically from common/baseService
        {
            "path": "src/services/orderService.ts",
            "imports": [
                {"source": "../common/baseService", "imported_names": ["BaseService"]}
            ],
            "classes": [
                {"name": "OrderService", "super_class": "BaseService"}
            ],
            "exports": [{"name": "OrderService", "kind": "named"}],
            "functions": [],
            "calls": []
        },
        # The true target BaseService
        {
            "path": "src/common/baseService.ts",
            "imports": [],
            "classes": [{"name": "BaseService", "super_class": None}],
            "exports": [{"name": "BaseService", "kind": "named"}],
            "functions": [],
            "calls": []
        },
        # An unrelated file also named BaseService (e.g. legacy/legacyBase.ts)
        {
            "path": "src/legacy/legacyBase.ts",
            "imports": [],
            "classes": [{"name": "BaseService", "super_class": None}],
            "exports": [{"name": "BaseService", "kind": "named"}],
            "functions": [],
            "calls": []
        }
    ]

    graph = builder.build_graph("test_repo", files_data)
    extends_edges = [e for e in graph.edges if e.relation.value == "EXTENDS"]
    
    assert len(extends_edges) == 1
    assert extends_edges[0].source == "src/services/orderService.ts"
    # Must correctly connect to src/common/baseService.ts, NOT src/legacy/legacyBase.ts
    assert extends_edges[0].target == "src/common/baseService.ts"

def test_call_graph_multi_tier_flow_discovery():
    builder = CallGraphBuilder()
    files_data = [
        # Ingress component (FastAPI / CLI / Component)
        {
            "path": "src/api/routes.py",
            "component_type": ComponentType.COMPONENT,
            "imports": [
                {"source": "../services/checkout", "imported_names": ["process_order"]}
            ],
            "exports": [{"name": "order_endpoint", "kind": "function"}],
            "functions": [{"name": "order_endpoint", "kind": "function"}],
            "calls": ["process_order"],
            "classes": []
        },
        # Service tier
        {
            "path": "src/services/checkout.py",
            "component_type": ComponentType.SERVICE,
            "imports": [
                {"source": "../repositories/db", "imported_names": ["save_record"]}
            ],
            "exports": [{"name": "process_order", "kind": "function"}],
            "functions": [{"name": "process_order", "kind": "function"}],
            "calls": ["save_record"],
            "classes": []
        },
        # Repository tier
        {
            "path": "src/repositories/db.py",
            "component_type": ComponentType.REPOSITORY,
            "imports": [],
            "exports": [{"name": "save_record", "kind": "function"}],
            "functions": [{"name": "save_record", "kind": "function"}],
            "calls": [],
            "classes": []
        }
    ]

    result = builder.build_call_graph(files_data)
    flows = result["discovered_flows"]
    
    assert len(flows) >= 1
    # Multi-tier path routes.py -> checkout.py -> db.py must be discovered
    found_3_tier = any(
        "src/api/routes.py" in f["path"] and "src/repositories/db.py" in f["path"]
        for f in flows
    )
    assert found_3_tier

