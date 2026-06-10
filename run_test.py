"""Stodi — end-to-end test runner.

Usage:
    cd learning_box
    source stodi/venv/bin/activate
    python stodi/run_test.py
"""

import os
import sys
import asyncio

# Ensure stodi package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'True'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'stodi-498317'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'

from google.adk import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


async def test_stodi():
    # Import the root agent
    from stodi.agents.orchestrator import root_agent

    # Load exam pack
    from stodi.agents.curriculum import load_pack
    load_result = load_pack('waec', 'mathematics')
    print(f"📚 {load_result}\n")

    # Set up session
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="stodi",
        user_id="test_student",
    )

    runner = Runner(
        agent=root_agent,
        app_name="stodi",
        session_service=session_service,
    )

    # Test conversation
    queries = [
        "Hi! I'm preparing for WAEC Maths. What topics should I focus on?",
        "Give me a quiz on Logarithms",
        "I think the answer is 6",
    ]

    for query in queries:
        print(f"👤 Student: {query}")
        content = types.Content(
            role="user",
            parts=[types.Part(text=query)],
        )

        response_text = ""
        async for event in runner.run_async(
            user_id="test_student",
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text

        print(f"🤖 Stodi: {response_text}\n")
        print("─" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_stodi())
