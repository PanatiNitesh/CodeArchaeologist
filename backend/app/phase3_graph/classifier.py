import re
from pathlib import Path
from typing import Dict, Any, Tuple
from backend.app.models.schemas import ComponentType

class ComponentClassifier:
    """
    Hybrid Rule-based + Structural Heuristics Architecture Component Classifier.
    Classifies files into Controller, Service, Repository, Model, Component, Utility, Test, Config, Middleware.
    """

    PATTERNS = [
        (ComponentType.TEST, [
            r'(\.test|\.spec|_test|_spec)\.[jt]sx?$',
            r'/__tests__/',
            r'/tests?/'
        ]),
        (ComponentType.CONTROLLER, [
            r'controller\.[jt]sx?$',
            r'/controllers?/',
            r'/routes?/',
            r'/api/'
        ]),
        (ComponentType.SERVICE, [
            r'service\.[jt]sx?$',
            r'/services?/',
            r'/usecases?/'
        ]),
        (ComponentType.REPOSITORY, [
            r'repository\.[jt]sx?$',
            r'/repositor(y|ies)/',
            r'/dao/',
            r'/data-access/'
        ]),
        (ComponentType.MODEL, [
            r'model\.[jt]sx?$',
            r'schema\.[jt]sx?$',
            r'entity\.[jt]sx?$',
            r'/models?/',
            r'/entities?/',
            r'/schemas?/'
        ]),
        (ComponentType.MIDDLEWARE, [
            r'middleware\.[jt]sx?$',
            r'interceptor\.[jt]sx?$',
            r'/middlewares?/',
            r'/guards?/'
        ]),
        (ComponentType.COMPONENT, [
            r'/components?/',
            r'/views?/',
            r'/pages?/',
            r'/ui/',
            r'\.tsx$',
            r'\.jsx$'
        ]),
        (ComponentType.CONFIGURATION, [
            r'config\.[jt]sx?$',
            r'/config/',
            r'tsconfig.*\.json$',
            r'package\.json$',
            r'\.env',
            r'webpack\.',
            r'vite\.config'
        ]),
        (ComponentType.UTILITY, [
            r'util(s)?\.[jt]sx?$',
            r'helper(s)?\.[jt]sx?$',
            r'/utils?/',
            r'/helpers?/',
            r'/lib/',
            r'/common/'
        ])
    ]

    def classify_file(self, rel_path: str, content: str, parsed_info: Dict[str, Any]) -> Tuple[ComponentType, float]:
        path_lower = rel_path.lower()

        # Step 1: Check high confidence filename / path regex
        for comp_type, regexes in self.PATTERNS:
            for r in regexes:
                if re.search(r, path_lower):
                    return comp_type, 0.95

        # Step 2: Structural AST analysis
        calls = set(parsed_info.get("calls", []))
        imports = [imp.get("source", "").lower() for imp in parsed_info.get("imports", [])]
        classes = [c.get("name", "").lower() for c in parsed_info.get("classes", [])]

        # Test detection
        if any(c in calls for c in ["describe", "it", "test", "expect", "assert"]):
            return ComponentType.TEST, 0.98

        # Controller / Route detection
        if any("router" in imp or "express" in imp or "fastify" in imp or "koa" in imp for imp in imports):
            if any("get" in calls or "post" in calls or "put" in calls or "delete" in calls):
                return ComponentType.CONTROLLER, 0.88

        # Middleware detection
        if any("next" in fn.get("params", []) for fn in parsed_info.get("functions", [])):
            return ComponentType.MIDDLEWARE, 0.85

        # UI Component detection (JSX / React)
        if parsed_info.get("path", "").endswith((".tsx", ".jsx")) or "react" in "".join(imports):
            return ComponentType.COMPONENT, 0.90

        # Repository / DB layer detection
        db_indicators = {"prisma", "typeorm", "mongoose", "sequelize", "knex", "pg", "sql", "db"}
        if any(any(dbi in imp for dbi in db_indicators) for imp in imports) or any(dbi in c.lower() for dbi in db_indicators for c in calls):
            return ComponentType.REPOSITORY, 0.82

        # Model detection
        if any(c.endswith("model") or c.endswith("schema") or c.endswith("entity") for c in classes):
            return ComponentType.MODEL, 0.85

        # Service detection
        if any(c.endswith("service") for c in classes) or "service" in path_lower:
            return ComponentType.SERVICE, 0.88

        # Fallback to Utility
        return ComponentType.UTILITY, 0.60
