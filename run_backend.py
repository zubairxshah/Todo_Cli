#!/usr/bin/env python
"""
Script to run the backend server using uvicorn.
Compatible with uvicorn>=0.27.0 and fastapi>=0.109.0
"""
import uvicorn
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.src.main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    # uvicorn.run with app module reference works with>=0.27.0
    uvicorn.run(
        "backend.src.main:app",
        host=host,
        port=port,
        reload=True,
        reload_includes=["*.py"],
        log_level="info"
    )