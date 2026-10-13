import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_requirements_file_exists_and_pinned():
    """Verify requirements.txt exists and has pinned versions (==) for all dependencies."""
    req_file = REPO_ROOT / "requirements.txt"
    assert req_file.exists(), "requirements.txt must exist at repo root"
    
    content = req_file.read_text(encoding="utf-8")
    required_packages = [
        "MetaTrader5",
        "numpy",
        "pandas",
        "scipy",
        "psutil",
        "pytest",
        "python-dotenv",
        "requests",
        "yfinance",
    ]
    for pkg in required_packages:
        pattern = rf"^{re.escape(pkg)}==[\w\.\-]+.*$"
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        assert match, f"{pkg} must be pinned with '==' in requirements.txt"


def test_pyproject_toml_has_dependencies():
    """Verify pyproject.toml defines project metadata and pinned dependencies."""
    pyproject_file = REPO_ROOT / "pyproject.toml"
    assert pyproject_file.exists(), "pyproject.toml must exist"
    
    content = pyproject_file.read_text(encoding="utf-8")
    assert "dependencies = [" in content, "pyproject.toml must declare dependencies under [project]"
    
    for pkg in ["MetaTrader5", "numpy", "pandas", "scipy", "psutil", "python-dotenv", "requests", "yfinance"]:
        assert pkg.lower() in content.lower(), f"{pkg} must be listed in pyproject.toml dependencies"
