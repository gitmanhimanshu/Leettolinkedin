"""Code2LinkedIn Backend Application Package."""

import os
import sys
import types

# Ensure 'backend' module is always aliasable even when root is backend/
if "backend" not in sys.modules:
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [backend_dir]
    sys.modules["backend"] = backend_pkg
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

__version__ = "1.0.0"

