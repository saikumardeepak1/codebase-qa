import subprocess
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from config import get_settings

settings = get_settings()


def validate_github_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc not in ("github.com", "www.github.com"):
        raise ValueError(f"Not a GitHub URL: {url}")
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub repo URL: {url}")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return f"https://github.com/{owner}/{repo}"


def url_to_repo_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def clone_repo(github_url: str, target_dir: Path) -> Path:
    clean_url = validate_github_url(github_url)
    if settings.github_token:
        parsed = urlparse(clean_url)
        clone_url = f"https://{settings.github_token}@{parsed.netloc}{parsed.path}"
    else:
        clone_url = clean_url

    repo_path = target_dir / "repo"
    repo_path.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", clone_url, str(repo_path)],
        capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")

    return repo_path
