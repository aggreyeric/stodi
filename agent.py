"""ADK entry point — this is what `adk web` looks for."""

import os
import sys

# Ensure parent is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stodi.agents.orchestrator import root_agent
