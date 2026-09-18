"""Compatibility entry point for the explicit two-step improvement/revision workflow.

Runs the isolated HTTP Ollama MOCK browser test, not actual model inference.
"""

from browser_revisions import main

if __name__ == "__main__":
    main()
