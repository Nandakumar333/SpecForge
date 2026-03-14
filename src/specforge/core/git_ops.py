"""Git operations for SpecForge scaffold."""

from __future__ import annotations

import shutil
from pathlib import Path

from specforge.core.config import INIT_COMMIT_MESSAGE
from specforge.core.result import Err, Ok, Result


def is_git_available() -> bool:
    """Check if git is available in PATH."""
    return shutil.which("git") is not None


def is_inside_existing_repo(path: Path) -> bool:
    """Check if a path is inside an existing git repository."""
    try:
        from git import InvalidGitRepositoryError, Repo
        Repo(path, search_parent_directories=True)
        return True
    except (InvalidGitRepositoryError, Exception):
        return False


def init_repo(target_dir: Path) -> Result:
    """Initialize a git repo, stage all files, and commit."""
    try:
        from git import Repo
        existing = is_inside_existing_repo(target_dir)
        if existing:
            repo = Repo(target_dir, search_parent_directories=True)
        else:
            repo = Repo.init(target_dir)
        repo.index.add(["."])
        repo.index.commit(INIT_COMMIT_MESSAGE)
        return Ok("Git repository initialized and committed.")
    except Exception as exc:
        return Err(f"Git operation failed: {exc}")
