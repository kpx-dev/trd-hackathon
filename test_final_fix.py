#!/usr/bin/env python3
"""
Final test to ensure the racing agent correctly uses lap-based timestamp calculation
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/gilesjm/Repo/trd-hackathon')

from racing_agent import get_racing_agent

def test_final_fix():
    """Test the racing agent's new lap-based position calculation"""

    print("🤖 Final test: Racing Agent with corrected lap-based position calculation...")

    # Get the racing agent
    agent = get_racing_agent()

    print("✅ Agent loaded successfully")

    # Test exact scenario from user feedback
    question = """What are the current race positions?

Current situation context:
- Race: R1
- Vehicle: GR86-013-80
- Car Number: 80
- Current Lap Number: 4

CRITICAL: When lap number is provided in context (like "Current Lap Number: 4"), always pass it as lap_number parameter"""

    print(f"❓ Testing position calculation for lap 4:")
    print(f"Expected: Agent should reference lap 4 context, NOT lap 28")
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

            # Check for success indicators
            success_indicators = []
            failure_indicators = []

            # Check lap references
            if any(phrase in response.lower() for phrase in ["lap 4", "lap: 4", "on lap 4", "during lap 4"]):
                success_indicators.append("✅ Correctly referenced lap 4")

            if any(phrase in response.lower() for phrase in ["lap 28", "lap: 28", "on lap 28", "leading on lap 28"]):
                failure_indicators.append("❌ Still incorrectly mentioning lap 28")

            # Check position realism
            if "leading" in response.lower() and "race" in response.lower():
                failure_indicators.append("❌ Still claiming to be leading (should be mid/back of pack)")

            if any(phrase in response.lower() for phrase in ["19th", "position: 19", "finishing position"]):
                success_indicators.append("✅ Correctly identified realistic position")

            # Summary
            print("\n" + "="*60)
            if success_indicators and not failure_indicators:
                print("🎉 SUCCESS: All fixes working correctly!")
                for indicator in success_indicators:
                    print(f"   {indicator}")
            elif success_indicators:
                print("⚠️ PARTIAL SUCCESS: Some improvements but issues remain")
                for indicator in success_indicators:
                    print(f"   {indicator}")
                for indicator in failure_indicators:
                    print(f"   {indicator}")
            else:
                print("❌ FAILURE: Core issues still present")
                for indicator in failure_indicators:
                    print(f"   {indicator}")
            print("="*60)

        else:
            print(f"🔧 Raw result: {result}")

    except Exception as e:
        print(f"❌ Error testing agent: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_final_fix()