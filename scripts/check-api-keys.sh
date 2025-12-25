#!/usr/bin/env bash
# Check that at least one API key is set for integration tests

set -e

if [ -z "$OPENAI_API_KEY" ] && [ -z "$GEMINI_API_KEY" ] && [ -z "$OPENROUTER_API_KEY" ]; then
    echo "ERROR: No API keys set for integration tests"
    echo "Set at least one: OPENAI_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY"
    exit 1
fi
