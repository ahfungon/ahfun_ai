"""Verification script to check project setup and dependencies."""
import sys
import subprocess


def check_python_version():
    """Check Python version."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} is installed")
        return True
    else:
        print(f"✗ Python 3.9+ required, found {version.major}.{version.minor}.{version.micro}")
        return False


def check_redis():
    """Check if Redis is running."""
    print("\nChecking Redis connection...")
    try:
        import redis
        r = redis.from_url("redis://localhost:6379/0")
        r.ping()
        print("✓ Redis is running and accessible")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("  Please start Redis: docker run -d -p 6379:6379 redis:latest")
        return False


def check_imports():
    """Check if all required packages can be imported."""
    print("\nChecking package imports...")
    packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "alembic",
        "celery",
        "redis",
        "bcrypt",
        "httpx",
        "pydantic",
        "pydantic_settings",
        "pytest",
        "hypothesis"
    ]
    
    all_ok = True
    for package in packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError as e:
            print(f"✗ {package}: {e}")
            all_ok = False
    
    return all_ok


def check_project_structure():
    """Check if project structure is correct."""
    print("\nChecking project structure...")
    import os
    
    required_dirs = ["api", "services", "models", "workers", "config"]
    required_files = [
        "main.py",
        "requirements.txt",
        ".env",
        "config/settings.py",
        "models/database.py",
        "workers/celery_app.py",
        "workers/tasks.py"
    ]
    
    all_ok = True
    
    for dir_name in required_dirs:
        if os.path.isdir(dir_name):
            print(f"✓ {dir_name}/ directory exists")
        else:
            print(f"✗ {dir_name}/ directory missing")
            all_ok = False
    
    for file_name in required_files:
        if os.path.isfile(file_name):
            print(f"✓ {file_name} exists")
        else:
            print(f"✗ {file_name} missing")
            all_ok = False
    
    return all_ok


def check_config():
    """Check if configuration loads correctly."""
    print("\nChecking configuration...")
    try:
        from config.settings import settings
        print(f"✓ Configuration loaded")
        print(f"  - Database URL: {settings.database_url}")
        print(f"  - Redis URL: {settings.redis_url}")
        print(f"  - Summary Threshold: {settings.summary_threshold}")
        print(f"  - Closing Timeout: {settings.closing_timeout}s")
        print(f"  - Max Retries: {settings.max_retries}")
        return True
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False


def check_celery():
    """Check if Celery app loads correctly."""
    print("\nChecking Celery configuration...")
    try:
        from workers.celery_app import celery_app
        print(f"✓ Celery app loaded")
        print(f"  - Broker: {celery_app.conf.broker_url}")
        print(f"  - Backend: {celery_app.conf.result_backend}")
        return True
    except Exception as e:
        print(f"✗ Celery app failed: {e}")
        return False


def check_fastapi():
    """Check if FastAPI app loads correctly."""
    print("\nChecking FastAPI application...")
    try:
        from main import app
        print(f"✓ FastAPI app loaded")
        print(f"  - Title: {app.title}")
        print(f"  - Version: {app.version}")
        return True
    except Exception as e:
        print(f"✗ FastAPI app failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Dual Agent Chat Platform - Setup Verification")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        check_redis(),
        check_imports(),
        check_project_structure(),
        check_config(),
        check_celery(),
        check_fastapi()
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✓ All checks passed! Setup is complete.")
        print("\nNext steps:")
        print("1. Implement database models (Task 2)")
        print("2. Run: python main.py (to start API server)")
        print("3. Run: celery -A workers.celery_app worker --loglevel=info (to start worker)")
        print("4. Visit: http://localhost:8000/docs (for API documentation)")
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
