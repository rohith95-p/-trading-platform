#!/usr/bin/env python3
"""
Pre-deployment verification script for Railway deployment.
Checks if all required files and configurations are in place.
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} MISSING: {filepath}")
        return False

def check_directory_exists(dirpath: str, description: str) -> bool:
    """Check if a directory exists."""
    if os.path.isdir(dirpath):
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description} MISSING: {dirpath}")
        return False

def check_file_content(filepath: str, search_text: str, description: str) -> bool:
    """Check if a file contains specific text."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if search_text in content:
                print(f"✅ {description}")
                return True
            else:
                print(f"❌ {description} - text not found: {search_text}")
                return False
    except Exception as e:
        print(f"❌ {description} - error reading file: {e}")
        return False

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Railway Deployment Readiness Check")
    print("=" * 60)
    print()
    
    checks_passed = 0
    checks_total = 0
    
    # Check required files
    print("📁 Checking Required Files...")
    print("-" * 60)
    
    files_to_check = [
        ("Dockerfile.backend", "Backend Dockerfile"),
        ("requirements.txt", "Python dependencies"),
        ("src/main.py", "FastAPI application"),
        (".env.railway.example", "Railway environment example"),
        ("docs/RAILWAY_DEPLOYMENT_GUIDE.md", "Deployment guide"),
        ("docs/TASK_6.1_RAILWAY_SETUP.md", "Task 6.1 guide"),
        ("RAILWAY_SETUP_README.md", "Setup README"),
    ]
    
    for filepath, description in files_to_check:
        checks_total += 1
        if check_file_exists(filepath, description):
            checks_passed += 1
    
    print()
    
    # Check required directories
    print("📂 Checking Required Directories...")
    print("-" * 60)
    
    directories_to_check = [
        ("src", "Source code directory"),
        ("src/api", "API endpoints directory"),
        ("src/intelligence", "Intelligence module directory"),
        ("tests", "Tests directory"),
        ("docs", "Documentation directory"),
    ]
    
    for dirpath, description in directories_to_check:
        checks_total += 1
        if check_directory_exists(dirpath, description):
            checks_passed += 1
    
    print()
    
    # Check Dockerfile content
    print("🐳 Checking Dockerfile Configuration...")
    print("-" * 60)
    
    dockerfile_checks = [
        ("Dockerfile.backend", "python:3.11", "Python 3.11 base image"),
        ("Dockerfile.backend", "requirements.txt", "Requirements installation"),
        ("Dockerfile.backend", "uvicorn", "Uvicorn server command"),
        ("Dockerfile.backend", "EXPOSE 8000", "Port 8000 exposed"),
    ]
    
    for filepath, search_text, description in dockerfile_checks:
        checks_total += 1
        if check_file_content(filepath, search_text, description):
            checks_passed += 1
    
    print()
    
    # Check main.py content
    print("🚀 Checking FastAPI Application...")
    print("-" * 60)
    
    main_py_checks = [
        ("src/main.py", "FastAPI", "FastAPI import"),
        ("src/main.py", "/health", "Health check endpoint"),
        ("src/main.py", "CORSMiddleware", "CORS middleware"),
        ("src/main.py", "lifespan", "Lifespan events"),
    ]
    
    for filepath, search_text, description in main_py_checks:
        checks_total += 1
        if check_file_content(filepath, search_text, description):
            checks_passed += 1
    
    print()
    
    # Check requirements.txt content
    print("📦 Checking Python Dependencies...")
    print("-" * 60)
    
    requirements_checks = [
        ("requirements.txt", "fastapi", "FastAPI framework"),
        ("requirements.txt", "uvicorn", "Uvicorn server"),
        ("requirements.txt", "sqlalchemy", "SQLAlchemy ORM"),
        ("requirements.txt", "redis", "Redis client"),
        ("requirements.txt", "psycopg2", "PostgreSQL driver"),
    ]
    
    for filepath, search_text, description in requirements_checks:
        checks_total += 1
        if check_file_content(filepath, search_text, description):
            checks_passed += 1
    
    print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Checks Passed: {checks_passed}/{checks_total}")
    print()
    
    if checks_passed == checks_total:
        print("✅ ALL CHECKS PASSED!")
        print()
        print("Your backend is ready for Railway deployment.")
        print()
        print("Next steps:")
        print("1. Read: docs/TASK_6.1_RAILWAY_SETUP.md")
        print("2. Create Railway account at: https://railway.app")
        print("3. Follow the step-by-step guide")
        print()
        return 0
    else:
        print(f"❌ {checks_total - checks_passed} CHECKS FAILED")
        print()
        print("Please fix the issues above before deploying to Railway.")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
