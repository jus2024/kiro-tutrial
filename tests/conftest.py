"""Pytest configuration for test suite."""

import sys
from pathlib import Path

# Add project root so 'from src.xxx' imports work in test files
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Also add src/ so bare imports (from models.xxx, from services.xxx, etc.)
# work in Lambda handler code when invoked from tests
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
