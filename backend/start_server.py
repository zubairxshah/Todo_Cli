#!/usr/bin/env python3
import os
import subprocess
import sys

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")

    # Run uvicorn with the specified port
    cmd = [
        "uvicorn",
        "src.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--reload" if "dev" in sys.argv else ""  # Add reload for development
    ]

    # Remove empty strings from command
    cmd = [c for c in cmd if c]

    print(f"Executing command: {' '.join(cmd)}")
    subprocess.run(cmd)