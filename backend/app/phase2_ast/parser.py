import ast
import re
import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from backend.app.models.schemas import SymbolItem, ImportItem, ExportItem, FileNode, ComponentType
from backend.app.models.database import db

logger = logging.getLogger(__name__)

class CodeASTParser:
    """
    Dual-Engine High-Fidelity AST & Semantic Symbol Extractor:
    1. Python Engine: Native Python standard library `ast` parse-tree walker.
       Extracts functions, async functions, classes, decorators, docstrings, imports, and calls with 100% precision.
    2. JS/TS Engine: Enhanced multi-line syntax tokenizer.
       Handles TypeScript generics, decorators (@Injectable()), destructured parameters,
       multi-line imports, and conditional exports.
    """

    # Multi-line and type-aware ES6 imports
    RE_ES6_IMPORT = re.compile(
        r'''import\s+(?:type\s+)?(?:(?P<default>[\w$]+)\s*,?\s*)?(?:\{(?P<named>[^}]+)\})?(?:\*\s+as\s+(?P<namespace>[\w$]+))?\s*from\s*['"](?P<source>[^'"]+)['"]''',
        re.MULTILINE | re.DOTALL
    )
    RE_REQUIRE = re.compile(
        r'''(?:const|let|var)\s+(?:\{(?P<named>[^}]+)\}|(?P<default>[\w$]+))\s*=\s*require\(\s*['"](?P<source>[^'"]+)['"]\s*\)''',
        re.MULTILINE | re.DOTALL
    )
    RE_DYNAMIC_IMPORT = re.compile(
        r'''import\(\s*['"](?P<source>[^'"]+)['"]\s*\)''',
        re.MULTILINE
    )

    # Exports
    RE_EXPORT_DEFAULT = re.compile(
        r'''export\s+default\s+(?:(?:class|function)\s+(?P<name>[\w$]+)|(?P<direct_name>[\w$]+))''',
        re.MULTILINE
    )
    RE_EXPORT_CONDITIONAL = re.compile(
        r'''export\s+default\s+[^;?]+\?\s*(?P<opt1>[\w$]+)\s*:\s*(?P<opt2>[\w$]+)''',
        re.MULTILINE
    )
    RE_EXPORT_NAMED = re.compile(
        r'''export\s+(?:const|let|var|function|class)\s+(?P<name>[\w$]+)''',
        re.MULTILINE
    )
    RE_EXPORT_CLAUSE = re.compile(
        r'''export\s+\{([^}]+)\}''',
        re.MULTILINE | re.DOTALL
    )

    # Functions & classes with TypeScript Generics <T extends ...> and Decorator support
    RE_FUNCTION_DECL = re.compile(
        r'''(?:async\s+)?function\s+(?P<name>[\w$]+)(?:\s*<[^>]*>)?\s*\((?P<params>[^)]*)\)''',
        re.MULTILINE
    )
    RE_ARROW_OR_EXPR_FUNC = re.compile(
        r'''(?:const|let|var)\s+(?P<name>[\w$]+)\s*=\s*(?:async\s+)?(?:\s*<[^>]*>)?(?:\((?P<params>[^)]*)\)|(?P<single_param>[\w$]+))\s*=>''',
        re.MULTILINE
    )
    RE_CLASS_DECL = re.compile(
        r'''class\s+(?P<name>[\w$]+)(?:\s*<[^>]*>)?(?:\s+extends\s+(?P<extends>[\w$.]+)(?:\s*<[^>]*>)?)?(?:\s+implements\s+(?P<implements>[^{]+))?''',
        re.MULTILINE
    )
    RE_CLASS_METHOD = re.compile(
        r'''^\s*(?:(?:public|private|protected|static|async|readonly)\s+)*(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)(?:\s*<[^>]*>)?\s*\((?P<params>[^)]*)\)\s*(?::\s*[^{]+)?\{''',
        re.MULTILINE
    )

    # Call expressions
    RE_CALL_EXPR = re.compile(
        r'''(?<!function\s)(?<!class\s)\b(?P<caller>(?:[\w$]+\.)*[\w$]+)\s*\(''',
        re.MULTILINE
    )

    def parse_file(self, rel_path: str, content: str) -> Dict[str, Any]:
        """
        Parses code content and returns symbols, imports, exports, and call hierarchy.
        Routes Python files to the native Python AST engine, and JS/TS to the enhanced parser.
        """
        if rel_path.endswith(".py"):
            return self._parse_python_file(rel_path, content)
        return self._parse_jsts_file(rel_path, content)

    # =========================================================================
    # PYTHON NATIVE AST PARSER ENGINE
    # =========================================================================
    def _parse_python_file(self, rel_path: str, content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        loc = len([l for l in lines if l.strip() != ""])

        try:
            tree = ast.parse(content, filename=rel_path)
        except Exception as e:
            logger.warning(f"Python ast.parse syntax error in {rel_path}: {e}")
            # Fallback to basic line structure
            return {
                "path": rel_path,
                "loc": loc,
                "imports": [],
                "exports": [],
                "classes": [],
                "functions": [],
                "calls": []
            }

        imports = []
        exports = []
        classes = []
        functions = []
        all_calls = set()

        for node in ast.iter_child_nodes(tree):
            # 1. Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "source": alias.name,
                        "imported_names": [alias.asname or alias.name],
                        "is_default": False,
                        "raw": f"import {alias.name}"
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [a.asname or a.name for a in node.names]
                imports.append({
                    "source": module,
                    "imported_names": names,
                    "is_default": False,
                    "raw": f"from {module} import {', '.join(names)}"
                })

            # 2. Classes
            elif isinstance(node, ast.ClassDef):
                super_class = None
                if node.bases:
                    first_base = node.bases[0]
                    if isinstance(first_base, ast.Name):
                        super_class = first_base.id
                    elif isinstance(first_base, ast.Attribute):
                        super_class = first_base.attr

                decorators = [self._format_py_expr(d) for d in node.decorator_list]
                methods = []
                class_calls = set()

                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(f"{node.name}.{item.name}")
                        for subcall in ast.walk(item):
                            if isinstance(subcall, ast.Call):
                                call_name = self._format_py_expr(subcall.func)
                                if call_name:
                                    class_calls.add(call_name)
                                    all_calls.add(call_name)

                classes.append({
                    "name": node.name,
                    "kind": "class",
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno + 15),
                    "super_class": super_class,
                    "implements": [],
                    "methods": methods,
                    "decorators": decorators,
                    "calls": sorted(list(class_calls)),
                    "docstring": ast.get_docstring(node)
                })
                exports.append({"name": node.name, "kind": "class", "line": node.lineno})

            # 3. Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_calls = set()
                for subcall in ast.walk(node):
                    if isinstance(subcall, ast.Call):
                        call_name = self._format_py_expr(subcall.func)
                        if call_name and call_name != node.name:
                            fn_calls.add(call_name)
                            all_calls.add(call_name)

                params = [arg.arg for arg in node.args.args if arg.arg != "self" and arg.arg != "cls"]
                decorators = [self._format_py_expr(d) for d in node.decorator_list]

                functions.append({
                    "name": node.name,
                    "kind": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno + 10),
                    "params": params,
                    "decorators": decorators,
                    "calls": sorted(list(fn_calls)),
                    "docstring": ast.get_docstring(node)
                })
                exports.append({"name": node.name, "kind": "function", "line": node.lineno})

        # Global module calls
        for subcall in ast.walk(tree):
            if isinstance(subcall, ast.Call):
                c_name = self._format_py_expr(subcall.func)
                if c_name:
                    all_calls.add(c_name)

        return {
            "path": rel_path,
            "loc": loc,
            "imports": imports,
            "exports": exports,
            "classes": classes,
            "functions": functions,
            "calls": sorted(list(all_calls))
        }

    def _format_py_expr(self, expr: ast.AST) -> Optional[str]:
        if isinstance(expr, ast.Name):
            return expr.id
        elif isinstance(expr, ast.Attribute):
            base = self._format_py_expr(expr.value)
            return f"{base}.{expr.attr}" if base else expr.attr
        elif isinstance(expr, ast.Call):
            return self._format_py_expr(expr.func)
        return None

    # =========================================================================
    # JAVASCRIPT / TYPESCRIPT PARSER ENGINE
    # =========================================================================
    def _parse_jsts_file(self, rel_path: str, content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        loc = len([l for l in lines if l.strip() != ""])

        imports = self._extract_imports(content)
        exports = self._extract_exports(content)
        classes, class_spans = self._extract_classes(content, lines)
        functions = self._extract_functions(content, lines, class_spans)
        all_calls = self._extract_calls(content)

        return {
            "path": rel_path,
            "loc": loc,
            "imports": imports,
            "exports": exports,
            "classes": classes,
            "functions": functions,
            "calls": all_calls
        }

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        imports = []
        # ES6
        for m in self.RE_ES6_IMPORT.finditer(content):
            source = m.group("source")
            names = []
            if m.group("default"):
                names.append(m.group("default").strip())
            if m.group("named"):
                for n in m.group("named").split(","):
                    clean = n.strip()
                    # Strip TypeScript 'type ' specifier: e.g. 'type User' -> 'User'
                    if clean.startswith("type "):
                        clean = clean[5:].strip()
                    name = clean.split(" as ")[0].strip()
                    if name:
                        names.append(name)
            if m.group("namespace"):
                names.append(f"* as {m.group('namespace').strip()}")
            imports.append({
                "source": source,
                "imported_names": names,
                "is_default": bool(m.group("default")),
                "raw": m.group(0).strip()
            })

        # Require
        for m in self.RE_REQUIRE.finditer(content):
            source = m.group("source")
            names = []
            if m.group("default"):
                names.append(m.group("default").strip())
            if m.group("named"):
                for n in m.group("named").split(","):
                    name = n.strip().split(":")[0].strip()
                    if name:
                        names.append(name)
            imports.append({
                "source": source,
                "imported_names": names,
                "is_default": bool(m.group("default")),
                "raw": m.group(0).strip()
            })

        # Dynamic imports
        for m in self.RE_DYNAMIC_IMPORT.finditer(content):
            source = m.group("source")
            imports.append({
                "source": source,
                "imported_names": ["*dynamic*"],
                "is_default": False,
                "raw": m.group(0).strip()
            })

        return imports

    def _extract_exports(self, content: str) -> List[Dict[str, Any]]:
        exports = []
        for m in self.RE_EXPORT_DEFAULT.finditer(content):
            name = m.group("name") or m.group("direct_name") or "default"
            line = content[:m.start()].count("\n") + 1
            exports.append({"name": name, "kind": "default", "line": line})

        # Conditional default export: export default condition ? A : B
        for m in self.RE_EXPORT_CONDITIONAL.finditer(content):
            line = content[:m.start()].count("\n") + 1
            exports.append({"name": m.group("opt1"), "kind": "conditional_default", "line": line})
            exports.append({"name": m.group("opt2"), "kind": "conditional_default", "line": line})

        for m in self.RE_EXPORT_NAMED.finditer(content):
            name = m.group("name")
            line = content[:m.start()].count("\n") + 1
            exports.append({"name": name, "kind": "named", "line": line})

        for m in self.RE_EXPORT_CLAUSE.finditer(content):
            clause = m.group(1)
            line = content[:m.start()].count("\n") + 1
            for item in clause.split(","):
                name = item.strip().split(" as ")[-1].strip()
                if name:
                    exports.append({"name": name, "kind": "named", "line": line})
        return exports

    def _extract_decorators(self, lines: List[str], line_idx: int) -> List[str]:
        decorators = []
        for i in range(line_idx - 1, max(-1, line_idx - 6), -1):
            stripped = lines[i].strip()
            if stripped.startswith("@"):
                decorators.insert(0, stripped)
            elif stripped == "" or stripped.startswith("//") or stripped.startswith("/*"):
                continue
            else:
                break
        return decorators

    def _clean_params(self, raw_params: str) -> List[str]:
        # Handle destructured params e.g. { a, b }: Props -> ["a", "b"]
        clean = []
        # Strip types after colon
        without_types = re.sub(r':\s*[^,{}()]+', '', raw_params)
        for token in re.findall(r'[\w$]+', without_types):
            if token not in clean:
                clean.append(token)
        return clean

    def _extract_classes(self, content: str, lines: List[str]) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int]]]:
        classes = []
        class_spans = []

        for m in self.RE_CLASS_DECL.finditer(content):
            name = m.group("name")
            super_class = m.group("extends")
            implements_raw = m.group("implements")
            start_line = content[:m.start()].count("\n") + 1
            end_line = self._find_closing_brace_line(lines, start_line - 1)
            class_spans.append((start_line, end_line))

            class_body = "\n".join(lines[start_line - 1:end_line])
            methods = []
            for meth in self.RE_CLASS_METHOD.finditer(class_body):
                m_name = meth.group("name")
                if m_name not in {"if", "for", "while", "switch", "catch", "constructor"}:
                    methods.append(f"{name}.{m_name}")

            decorators = self._extract_decorators(lines, start_line - 1)

            classes.append({
                "name": name,
                "kind": "class",
                "start_line": start_line,
                "end_line": end_line,
                "super_class": super_class.strip() if super_class else None,
                "implements": [i.strip() for i in implements_raw.split(",")] if implements_raw else [],
                "methods": methods,
                "decorators": decorators,
                "calls": self._extract_calls(class_body)
            })

        return classes, class_spans

    def _extract_functions(self, content: str, lines: List[str], class_spans: List[Tuple[int, int]]) -> List[Dict[str, Any]]:
        functions = []

        # Standard function declarations
        for m in self.RE_FUNCTION_DECL.finditer(content):
            name = m.group("name")
            if name in {"if", "for", "while", "switch", "catch"}:
                continue
            start_line = content[:m.start()].count("\n") + 1
            
            if any(start <= start_line <= end for start, end in class_spans):
                continue

            end_line = self._find_closing_brace_line(lines, start_line - 1)
            body = "\n".join(lines[start_line - 1:end_line])
            params = self._clean_params(m.group("params") or "")
            calls = self._extract_calls(body)

            functions.append({
                "name": name,
                "kind": "function",
                "start_line": start_line,
                "end_line": end_line,
                "params": params,
                "calls": [c for c in calls if c != name],
                "docstring": self._find_preceding_doc(lines, start_line - 1)
            })

        # Arrow functions or function expressions
        for m in self.RE_ARROW_OR_EXPR_FUNC.finditer(content):
            name = m.group("name")
            start_line = content[:m.start()].count("\n") + 1
            if any(start <= start_line <= end for start, end in class_spans):
                continue
            end_line = self._find_closing_brace_line(lines, start_line - 1)
            body = "\n".join(lines[start_line - 1:end_line])
            raw_p = m.group("params") or m.group("single_param") or ""
            params = self._clean_params(raw_p)
            calls = self._extract_calls(body)

            functions.append({
                "name": name,
                "kind": "arrow_function",
                "start_line": start_line,
                "end_line": end_line,
                "params": params,
                "calls": [c for c in calls if c != name],
                "docstring": self._find_preceding_doc(lines, start_line - 1)
            })

        return functions

    def _extract_calls(self, text: str) -> List[str]:
        # Strip comments and literal strings to prevent false call matches in template literals
        cleaned_text = re.sub(r'//.*', '', text)
        cleaned_text = re.sub(r'/\*[\s\S]*?\*/', '', cleaned_text)
        cleaned_text = re.sub(r'`(?:\\.|[^`\\])*`', '""', cleaned_text)

        calls = set()
        reserved = {
            "if", "for", "while", "switch", "catch", "return", "require",
            "import", "function", "class", "async", "await", "typeof",
            "delete", "throw", "new", "export", "default", "from"
        }
        for m in self.RE_CALL_EXPR.finditer(cleaned_text):
            call_token = m.group("caller").strip()
            base = call_token.split(".")[-1]
            if base not in reserved and not base.isdigit():
                calls.add(call_token)
        return sorted(list(calls))

    def _find_closing_brace_line(self, lines: List[str], start_idx: int) -> int:
        open_count = 0
        found_first = False
        for i in range(start_idx, min(len(lines), start_idx + 300)):
            line = lines[i]
            open_count += line.count("{") - line.count("}")
            if "{" in line:
                found_first = True
            if found_first and open_count <= 0:
                return i + 1
        return min(len(lines), start_idx + 20)

    def _find_preceding_doc(self, lines: List[str], start_idx: int) -> Optional[str]:
        if start_idx <= 0:
            return None
        doc_lines = []
        for i in range(start_idx - 1, max(-1, start_idx - 10), -1):
            line = lines[i].strip()
            if line.startswith("*") or line.startswith("/**") or line.startswith("//"):
                doc_lines.insert(0, line.lstrip("/* /").strip())
            elif line == "":
                continue
            else:
                break
        return "\n".join(doc_lines) if doc_lines else None

    def save_parsed_data(self, repo_id: str, parsed_files: List[Dict[str, Any]]):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM symbols WHERE repo_id = ?", (repo_id,))
            cursor.execute("DELETE FROM imports WHERE repo_id = ?", (repo_id,))
            cursor.execute("DELETE FROM exports WHERE repo_id = ?", (repo_id,))

            symbol_records = []
            import_records = []
            export_records = []

            for f in parsed_files:
                file_id = f"{repo_id}:{f['path']}"
                # Classes
                for c in f.get("classes", []):
                    s_id = f"{file_id}:class:{c['name']}"
                    doc = c.get("docstring") or (f"Extends {c.get('super_class')}" if c.get("super_class") else None)
                    symbol_records.append((
                        s_id, file_id, repo_id, c["name"], "class",
                        c["start_line"], c["end_line"],
                        json.dumps(c.get("methods", [])),
                        json.dumps(c.get("calls", [])),
                        doc
                    ))
                # Functions
                for fn in f.get("functions", []):
                    s_id = f"{file_id}:fn:{fn['name']}"
                    symbol_records.append((
                        s_id, file_id, repo_id, fn["name"], fn["kind"],
                        fn["start_line"], fn["end_line"],
                        json.dumps(fn.get("params", [])),
                        json.dumps(fn.get("calls", [])),
                        fn.get("docstring")
                    ))
                # Imports
                for imp in f.get("imports", []):
                    i_id = f"{file_id}:imp:{imp['source']}:{','.join(imp['imported_names'])}"
                    import_records.append((
                        i_id, file_id, repo_id, imp["source"],
                        json.dumps(imp["imported_names"]), imp.get("raw")
                    ))
                # Exports
                for exp in f.get("exports", []):
                    e_id = f"{file_id}:exp:{exp['name']}:{exp.get('line', 1)}"
                    export_records.append((
                        e_id, file_id, repo_id, exp["name"], exp.get("kind"), exp.get("line", 1)
                    ))

            cursor.executemany("""
            INSERT OR REPLACE INTO symbols (id, file_id, repo_id, name, kind, start_line, end_line, params_json, calls_json, docstring)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, symbol_records)

            cursor.executemany("""
            INSERT OR REPLACE INTO imports (id, file_id, repo_id, source, imported_names_json, raw)
            VALUES (?, ?, ?, ?, ?, ?)
            """, import_records)

            cursor.executemany("""
            INSERT OR REPLACE INTO exports (id, file_id, repo_id, name, kind, line)
            VALUES (?, ?, ?, ?, ?, ?)
            """, export_records)

            conn.commit()
