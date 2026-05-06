from pathlib import Path
from typing import List

EXCLUDED_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", "coverage", ".pytest_cache", ".mypy_cache",
    "vendor", "third_party", ".eggs", "eggs", "target", "out",
    ".idea", ".vscode", "tmp", "temp", "logs", "migrations"
}

EXCLUDED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".mp4",
    ".zip", ".tar", ".gz", ".rar", ".lock", ".sum",
    ".min.js", ".min.css", ".map", ".woff", ".woff2", ".ttf",
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".exe", ".bin"
}

SUPPORTED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
    ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".sh", ".bash",
    ".md", ".txt", ".rst", ".yaml", ".yml", ".toml", ".json",
    ".html", ".css", ".sql", ".graphql", ".proto"
}

MAX_FILE_BYTES = 200_000


def should_include_file(path: Path, repo_root: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return False
    if path.suffix not in SUPPORTED_EXTENSIONS:
        return False
    if path.suffix in EXCLUDED_EXTENSIONS:
        return False
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return False
    except OSError:
        return False
    return True


def get_indexable_files(repo_root: Path) -> List[Path]:
    files = []
    for path in repo_root.rglob("*"):
        if path.is_file() and should_include_file(path, repo_root):
            files.append(path)
    return files
