"""
Shared pytest configuration.

Adds the backend directory to sys.path so unit tests can import
`app.*` modules without installing the package.

Usage:
    cd backend
    pytest tests/ -v
"""

import sys
from pathlib import Path

# Ensure `app` package is importable from the backend root
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))
