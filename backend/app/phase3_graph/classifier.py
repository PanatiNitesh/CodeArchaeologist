import re
from pathlib import Path
from typing import Dict, Any, Tuple
from backend.app.models.schemas import ComponentType

class ComponentClassifier:
    """
    Hybrid Rule-based + Structural Heuristics Architecture Component Classifier.
    Classifies files into Controller, Service, Repository, Model, Component, Utility, Test, Config, Middleware.
    """

    LANG_EXT = r'(?:\.[jt]sx?|\.py|\.go|\.java|\.rs)?$'

    PATTERNS = [
        (ComponentType.TEST, [
            r'(\.test|\.spec|_test|_spec)\.[a-zA-Z0-9]+$',
            r'/test_[a-zA-Z0-9_]+\.py$',
            r'/__tests__/',
            r'/tests?/'
        ]),
        (ComponentType.CONTROLLER, [
            r'controller' + LANG_EXT,
            r'/controllers?/',
            r'/routes?/',
            r'/endpoints?/',
            r'/api/'
        ]),
        (ComponentType.SERVICE, [
            r'service' + LANG_EXT,
            r'/services?/',
            r'/usecases?/'
        ]),
        (ComponentType.REPOSITORY, [
            r'repository' + LANG_EXT,
            r'/repositor(y|ies)/',
            r'/dao/',
            r'/data-access/'
        ]),
        (ComponentType.MODEL, [
            r'model' + LANG_EXT,
            r'schema' + LANG_EXT,
            r'entity' + LANG_EXT,
            r'/models?/',
            r'/entities?/',
            r'/schemas?/'
        ]),
        (ComponentType.MIDDLEWARE, [
            r'middleware' + LANG_EXT,
            r'interceptor' + LANG_EXT,
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
            r'config' + LANG_EXT,
            r'/config/',
            r'settings\.py$',
            r'tsconfig.*\.json$',
            r'package\.json$',
            r'requirements\.txt$',
            r'go\.mod$',
            r'Cargo\.toml$',
            r'\.env',
            r'webpack\.',
            r'vite\.config'
        ]),
        (ComponentType.UTILITY, [
            r'util(s)?' + LANG_EXT,
            r'helper(s)?' + LANG_EXT,
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
        if any(c in calls for c in ["describe", "it", "test", "expect", "assert"]) or any("pytest" in i or "unittest" in i for i in imports):
            return ComponentType.TEST, 0.98

        # Controller / Route detection
        if any(f in imp for imp in imports for f in ["router", "express", "fastify", "koa", "fastapi", "flask", "django"]):
            if any(verb in calls for verb in ["get", "post", "put", "delete", "route"]):
                return ComponentType.CONTROLLER, 0.88

        # Middleware detection
        if any("next" in fn.get("params", []) for fn in parsed_info.get("functions", [])):
            return ComponentType.MIDDLEWARE, 0.85

        # UI Component detection (JSX / React)
        if parsed_info.get("path", "").endswith((".tsx", ".jsx")) or "react" in "".join(imports):
            return ComponentType.COMPONENT, 0.90

        # Repository / DB layer detection
        db_indicators = {"prisma", "typeorm", "mongoose", "sequelize", "knex", "pg", "sql", "db", "sqlalchemy", "peewee", "tortoise"}
        if any(any(dbi in imp for dbi in db_indicators) for imp in imports) or any(dbi in c.lower() for dbi in db_indicators for c in calls):
            return ComponentType.REPOSITORY, 0.82

        # Model detection
        if any(c.endswith("model") or c.endswith("schema") or c.endswith("entity") or c.endswith("dto") for c in classes) or any("basemodel" in c for c in classes):
            return ComponentType.MODEL, 0.85

        # Service detection
        if any(c.endswith("service") for c in classes) or "service" in path_lower:
            return ComponentType.SERVICE, 0.88

        # Fallback to Utility
        return ComponentType.UTILITY, 0.60
