import os
import sys

# Ensure serverless writable scratch directories are configured before any heavy imports
os.environ.setdefault("HF_HOME", "/tmp/huggingface")
os.environ.setdefault("TORCH_HOME", "/tmp/torch")
os.environ.setdefault("FASTEMBED_CACHE_DIR", "/tmp/fastembed_cache")
os.environ.setdefault("EMBEDDING_PROVIDER", "deterministic")
os.environ.setdefault("WEBHOOK_INBOX_DB_PATH", "/tmp/omimind_webhook_inbox.db")

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app

__all__ = ["app"]
