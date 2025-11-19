#!/usr/bin/env python3
"""
Test the racing agent with position questions
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/gilesjm/Repo/trd-hackathon')

from racing_agent import get_racing_agent

def test_agent_multiple_questions():
    """Test the racing agent's ability to answer various position questions"""

    print("🤖 Testing Racing Agent with various position questions...")

    # Get the racing agent
    agent = get_racing_agent()

    print("✅ Agent loaded successfully with 7 data tools")

    questions = [
        "What are the current race positions in R1 at timestamp 2025-09-05T01:00:00.000Z? Show me the top 5 cars.",
        "Who is leading the race in R1 at 2025-09-05T01:00:00.000Z?",
        "What position is car #13 in at timestamp 2025-09-05T01:00:00.000Z in R1?",
        "How far behind is car #5 compared to the race leader at 2025-09-05T01:00:00.000Z in R1?"
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"❓ Question {i}: {question}")
        print('='*60)

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
            print(f"❌ Error testing question {i}: {str(e)}")
            import traceback
            traceback.print_exc()

        print()  # Add spacing between questions

if __name__ == "__main__":
    test_agent_multiple_questions()