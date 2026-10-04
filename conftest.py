import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ.setdefault("API_SECRET_KEY", "test-secret")
