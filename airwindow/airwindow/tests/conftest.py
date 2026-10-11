import os
import sys

os.environ.pop("TABLE_NAME", None)  # tests use the in-memory store
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
