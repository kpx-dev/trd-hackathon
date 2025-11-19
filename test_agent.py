#!/usr/bin/env python3
"""
Test the racing agent with the new live position tool
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/gilesjm/Repo/trd-hackathon')

from racing_agent import get_racing_agent

def test_agent_positions():
    """Test the racing agent's ability to get live race positions"""

    print("🤖 Testing Racing Agent with live position capability...")

    # Get the racing agent
    agent = get_racing_agent()

    print("✅ Agent loaded successfully with 7 data tools")

    # Test a question about race positions
    question = "What are the current race positions in R1 at timestamp 2025-09-05T00:50:02.742Z? Show me the top 5 cars."

    print(f"❓ Testing question: {question}")

    try:
        result = agent(question)

        # Extract text from AgentResult object
        if result and hasattr(result, 'message') and 'content' in result.message:
            response = result.message['content'][0]['text']
            print("🎯 Agent Response:")
            print("-" * 50)
            print(response)
            print("-" * 50)
        else:
            print(f"🔧 Raw result: {result}")

    except Exception as e:
        print(f"❌ Error testing agent: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent_positions()