#!/bin/bash
# Stodi Local Dev Server
# Usage: ./start_local.sh

cd "$(dirname "$0")"
source venv/bin/activate

export GOOGLE_GENAI_USE_VERTEXAI=True
export GOOGLE_CLOUD_PROJECT=stodi-498317
export GOOGLE_CLOUD_LOCATION=us-central1

echo "╔══════════════════════════════════════════════════╗"
echo "║           S T O D I   L O C A L                  ║"
echo "║     http://127.0.0.1:8080                        ║"
echo "╚══════════════════════════════════════════════════╝"

adk web . --port 8080
