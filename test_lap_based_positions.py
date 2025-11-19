#!/usr/bin/env python3
"""
Test the racing agent with lap-based position questions to ensure it uses the correct timestamp
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/gilesjm/Repo/trd-hackathon')

from racing_agent import get_racing_agent

def test_lap_based_positions():
    """Test the racing agent's ability to use lap number for accurate position calculation"""

    print("🤖 Testing Racing Agent with lap-based position calculation...")

    # Get the racing agent
    agent = get_racing_agent()

    print("✅ Agent loaded successfully with 7 data tools")

    # Test a question with explicit lap context (mimicking UI context)
    question = """What are the current race positions?

Current situation context:
- Race: R1
- Vehicle: GR86-013-80
- Car Number: 80
- Current Lap Number: 4
- Current Speed: 85mph
- Current Gear: 3

IMPORTANT: To answer this question properly, you should use your tools:
- Use get_live_race_positions(race_id='R1', vehicle_id='GR86-013-80', lap_number=4) to get accurate position data from lap 4"""

    print(f"❓ Testing question with lap context:")
    print(f"Current Lap Number: 4")
    print(f"Vehicle: GR86-013-80")
    print()

    try:
        result = agent(question)

        # Extract text from AgentResult object
        if result and hasattr(result, 'message') and 'content' in result.message:
            response = result.message['content'][0]['text']
            print("🎯 Agent Response:")
            print("-" * 50)
            print(response)
            print("-" * 50)

            # Check if the response mentions lap 4 instead of lap 28 (the previous incorrect behavior)
            if "lap 4" in response.lower() or "lap: 4" in response.lower():
                print("✅ SUCCESS: Agent correctly referenced lap 4")
            elif "lap 28" in response.lower() or "lap: 28" in response.lower():
                print("❌ FAILURE: Agent still using incorrect lap 28")
            else:
                print("⚠️ WARNING: Could not determine if correct lap was used")

        else:
            print(f"🔧 Raw result: {result}")

    except Exception as e:
        print(f"❌ Error testing agent: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_lap_based_positions()