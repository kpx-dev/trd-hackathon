#!/usr/bin/env python3
"""
Test the racing agent's ability to extract lap numbers from context and use them correctly
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/gilesjm/Repo/trd-hackathon')

from racing_agent import get_racing_agent

def test_lap_extraction():
    """Test that the agent extracts and uses lap number from context"""

    print("🤖 Testing Racing Agent lap number extraction from context...")

    # Get the racing agent
    agent = get_racing_agent()

    print("✅ Agent loaded successfully")

    # Test with very explicit context that mirrors the user's real scenario
    question = """What are the current race positions?

Current situation context:
- Race: R1
- Vehicle: GR86-013-80
- Car Number: 80
- Current Lap Number: 4

LAP NUMBER EXTRACTION CRITICAL:
- When context includes "Current Lap Number: X" or similar lap information, ALWAYS extract that number
- Pass the lap number as the lap_number parameter to get_live_race_positions
- This ensures you get position data from the correct point in the race, not wrong timestamps
- Example: If context shows "Current Lap Number: 4", use get_live_race_positions(race_id="R1", vehicle_id="GR86-013-80", lap_number=4)"""

    print(f"❓ Testing with explicit lap extraction instructions:")
    print(f"Context clearly states: Current Lap Number: 4")
    print(f"Expected: Agent should use lap_number=4 parameter")
    print()

    try:
        result = agent(question)

        # Extract text from AgentResult object
        if result and hasattr(result, 'message') and 'content' in result.message:
            response = result.message['content'][0]['text']
            print("🎯 Agent Response:")
            print("-" * 60)
            print(response)
            print("-" * 60)

            # Check for lap references and position accuracy
            if "lap 4" in response.lower() or "current lap: 4" in response.lower():
                print("✅ SUCCESS: Agent correctly referenced lap 4")

                # Check if position makes sense for early race
                if "leading" in response.lower() and "lap 28" not in response.lower():
                    print("✅ Positions appear to use correct timing (no lap 28 reference)")
                elif "lap 28" in response.lower():
                    print("❌ FAILURE: Still shows lap 28 - lap parameter not working")
                else:
                    print("⚠️ Position data present but need to verify timing")

            else:
                print("❌ FAILURE: Agent did not correctly reference lap 4")

        else:
            print(f"🔧 Raw result: {result}")

    except Exception as e:
        print(f"❌ Error testing agent: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_lap_extraction()