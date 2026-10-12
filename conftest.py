import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ.setdefault("API_SECRET_KEY", "test-secret")
os.environ.setdefault("TEST_ALLOW_TENANT_OVERRIDES", "true")
