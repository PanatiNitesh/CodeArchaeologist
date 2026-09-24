import os
import re
import git
import shutil
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cloned_repos"

class RepoCloner:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or CACHE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_repo_name(url_or_path: str) -> str:
        # e.g. https://github.com/user/project.git -> user_project
        cleaned = url_or_path.strip().rstrip("/")
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]
        match = re.search(r"[:/]([^/:]+)/([^/:]+)$", cleaned)
        if match:
            return f"{match.group(1)}_{match.group(2)}"
        return re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(cleaned).name)

    def clone_or_load(self, repo_url_or_path: str, force_reclone: bool = False) -> Tuple[str, str, Dict[str, Any]]:
        """
        Accepts either a GitHub URL or a local repository path.
        Returns (repo_id, local_path, metadata)
        """
        repo_url_or_path = repo_url_or_path.strip()
        local_path_candidate = Path(repo_url_or_path)

        if local_path_candidate.exists() and (local_path_candidate / ".git").exists():
            # It's an existing local repository!
            logger.info(f"Using local repository directly: {local_path_candidate}")
            repo_name = local_path_candidate.name
            repo_id = f"local_{self.sanitize_repo_name(str(local_path_candidate))}"
            repo = git.Repo(local_path_candidate)
            default_branch = repo.active_branch.name if not repo.head.is_detached else "main"
            return repo_id, str(local_path_candidate), {
                "name": repo_name,
                "url": repo_url_or_path,
                "default_branch": default_branch,
                "is_local": True
            }

        repo_name = self.sanitize_repo_name(repo_url_or_path)
        repo_id = f"gh_{repo_name}"
        destination = self.storage_dir / repo_name

        if destination.exists():
            if force_reclone:
                logger.info(f"Removing existing directory {destination} for reclone")
                shutil.rmtree(destination, ignore_errors=True)
            else:
                logger.info(f"Repository already cloned at {destination}")
                try:
                    repo = git.Repo(destination)
                    default_branch = repo.active_branch.name if not repo.head.is_detached else "main"
                    return repo_id, str(destination), {
                        "name": repo_name,
                        "url": repo_url_or_path,
                        "default_branch": default_branch,
                        "is_local": False
                    }
                except Exception as e:
                    logger.warning(f"Corrupted existing clone at {destination}, recloning... {e}")
                    shutil.rmtree(destination, ignore_errors=True)

        logger.info(f"Cloning {repo_url_or_path} into {destination}...")
        repo = git.Repo.clone_from(repo_url_or_path, destination)
        default_branch = repo.active_branch.name if not repo.head.is_detached else "main"

        return repo_id, str(destination), {
            "name": repo_name,
            "url": repo_url_or_path,
            "default_branch": default_branch,
            "is_local": False
        }
