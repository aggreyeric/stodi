"""Stodi — run locally with ADK CLI or Web UI.

Usage:
    # Interactive CLI
    adk run stodi

    # Web UI
    adk web stodi --port 8000
"""

import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()

from stodi.agents.orchestrator import root_agent

if __name__ == "__main__":
    print("stodi — your autonomous study agent")
    print("Run with: adk run stodi")
    print("Web UI:   adk web stodi --port 8000")
