"""conftest.py — Make the project root importable from tests/."""
import sys
import os

# Add project root (one level up from tests/) to sys.path so that
# `import battle`, `import decision`, etc. work without installing the package.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
