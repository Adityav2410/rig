"""Build the sandbox image once (rig-sandbox), if Docker is available and it doesn't exist yet."""

import logging

from rig.sandbox.setup import ensure_sandbox_ready

if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    ensure_sandbox_ready()
