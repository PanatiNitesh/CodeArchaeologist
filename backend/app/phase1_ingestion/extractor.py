import os
from pathlib import Path
from typing import List, Dict, Any, Generator

IGNORE_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "coverage",
    ".next",
    "out",
    ".cache",
    ".vscode",
    ".idea",
    "vendor",
    "tmp",
    "temp",
    "__pycache__"
}

ALLOWED_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".java",
    ".go",
    ".rs",
    ".json",
    ".md",
    ".mjs",
    ".cjs"
}

class RepoExtractor:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)

    def extract_files(self) -> List[Dict[str, Any]]:
        """
        Traverses the repository and collects target files,
        ignoring specified directories and extensions.
        """
        collected_files = []

        for root, dirs, files in os.walk(self.repo_path):
            # Modify dirs in-place to avoid descending into ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in ALLOWED_EXTENSIONS:
                    full_path = Path(root) / file
                    try:
                        size = full_path.stat().st_size
                        # Guard against OOM memory spikes: skip oversized/bundled files (> 500 KB)
                        if size > 500 * 1024:
                            continue
                        rel_path = full_path.relative_to(self.repo_path).as_posix()
                        
                        # Read file safely
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()

                        lines = content.splitlines()
                        loc = len([line for line in lines if line.strip() != ""])

                        collected_files.append({
                            "rel_path": rel_path,
                            "name": file,
                            "extension": ext,
                            "size_bytes": size,
                            "loc": loc,
                            "content": content,
                            "full_path": str(full_path)
                        })
                    except Exception as e:
                        # Log error and skip corrupt or unreadable file
                        continue

        # Sort files deterministically
        collected_files.sort(key=lambda x: x["rel_path"])
        return collected_files
