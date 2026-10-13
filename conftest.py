import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEPLOYMENT_MODE", "multi_user")
os.environ.setdefault("API_SECRET_KEY", "test-secret")
os.environ.setdefault("TEST_ALLOW_TENANT_OVERRIDES", "true")
os.environ.setdefault("DEFAULT_USER_ID", "test-user")
os.environ.setdefault("OMIMIND_MCP_UID", "test-user")
