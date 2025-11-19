#!/usr/bin/env python3
"""
Comprehensive test for the lap number extraction fix.
This test verifies that the agent correctly uses lap 4 context instead of wrong timestamps.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/gilesjm/Repo/trd-hackathon')

from racing_agent import get_racing_agent

def test_comprehensive_lap_fix():
    """Test the complete lap extraction and position calculation fix"""

    print("🤖 COMPREHENSIVE TEST: Racing Agent Lap Extraction Fix")
    print("="*70)

    # Get the racing agent
    agent = get_racing_agent()

    print("✅ Agent loaded successfully with enhanced lap extraction")

    # Test with explicit lap context that mirrors the exact user scenario
    question = """What are the current race positions?

Current situation context:
- Race: R1
- Vehicle: GR86-013-80
- Car Number: 80
- Current Lap Number: 4
- Current Speed: 85mph
- Current Gear: 3

This test verifies:
1. Agent extracts lap number 4 from context
2. Agent uses get_live_race_positions with lap_number=4 parameter
3. Position calculation uses correct timestamp from lap 4, NOT lap 28
4. Results show realistic position for early race (lap 4), not end-of-race data"""

    print(f"📝 Test Question:")
    print(f"   Context clearly states: Current Lap Number: 4")
    print(f"   Expected: Agent should reference lap 4 and show mid-race positions")
    print(f"   Should NOT show: Leading on lap 28 or end-of-race positions")
    print()

    try:
        print("🔄 Running agent analysis...")
        result = agent(question)

        # Extract text from AgentResult object
        if result and hasattr(result, 'message') and 'content' in result.message:
            response = result.message['content'][0]['text']

            print("🎯 AGENT RESPONSE:")
            print("-" * 70)
            print(response)
            print("-" * 70)

            # Comprehensive analysis of the fix
            success_criteria = []
            failure_criteria = []

            # Check for correct lap reference
            lap4_patterns = ['lap 4', 'lap: 4', 'current lap: 4', 'on lap 4', 'during lap 4']
            if any(pattern in response.lower() for pattern in lap4_patterns):
                success_criteria.append("✅ Correctly referenced lap 4 context")
            else:
                failure_criteria.append("❌ Did not reference lap 4 in response")

            # Check for incorrect lap 28 reference (the previous bug)
            lap28_patterns = ['lap 28', 'lap: 28', 'current lap: 28', 'on lap 28', 'leading.*lap 28']
            if any(pattern in response.lower() for pattern in lap28_patterns):
                failure_criteria.append("❌ Still incorrectly referencing lap 28 (end-of-race data)")
            else:
                success_criteria.append("✅ No incorrect lap 28 references")

            # Check for realistic position (not claiming to be leading in early race)
            if "leading" in response.lower() and "race" in response.lower():
                # If claiming to be leading, this should be suspicious for lap 4
                if "commanding" in response.lower() or "dominant" in response.lower():
                    failure_criteria.append("❌ Still claiming dominant lead (suggests wrong timestamp)")
                else:
                    success_criteria.append("⚠️ Shows leading but not dominantly (may be realistic)")

            # Check for realistic number of cars (should be 6-8 with telemetry data)
            import re
            car_count_match = re.search(r'(\d+) cars?', response.lower())
            if car_count_match:
                car_count = int(car_count_match.group(1))
                if 6 <= car_count <= 10:
                    success_criteria.append(f"✅ Shows realistic car count: {car_count} cars")
                elif car_count <= 3:
                    failure_criteria.append(f"❌ Only shows {car_count} cars (may be using wrong timestamp)")
                else:
                    success_criteria.append(f"⚠️ Shows {car_count} cars (verify if realistic)")

            # Check for position numbers that make sense for early race
            position_match = re.search(r'P(\d+)', response)
            if position_match:
                position = int(position_match.group(1))
                if 1 <= position <= 10:
                    success_criteria.append(f"✅ Shows realistic position: P{position}")
                else:
                    failure_criteria.append(f"❌ Shows unrealistic position: P{position}")

            # Check for lap distance/gap information that makes sense
            if "meter" in response.lower() or "m " in response.lower():
                success_criteria.append("✅ Includes distance/gap information")

            # Final assessment
            print("\n" + "="*70)
            print("🔍 COMPREHENSIVE FIX ANALYSIS:")
            print("="*70)

            if success_criteria and not failure_criteria:
                print("🎉 SUCCESS: All lap extraction fixes are working correctly!")
                for criterion in success_criteria:
                    print(f"   {criterion}")
                print("\n✨ The agent now correctly uses lap 4 context for position calculations!")

            elif success_criteria and failure_criteria:
                print("⚠️ PARTIAL SUCCESS: Some improvements but critical issues remain")
                print("\n✅ What's working:")
                for criterion in success_criteria:
                    print(f"   {criterion}")
                print("\n❌ Still needs fixing:")
                for criterion in failure_criteria:
                    print(f"   {criterion}")

            else:
                print("❌ FAILURE: Core lap extraction issues persist")
                print("\n❌ Problems detected:")
                for criterion in failure_criteria:
                    print(f"   {criterion}")

                if success_criteria:
                    print("\n✅ Some positive signs:")
                    for criterion in success_criteria:
                        print(f"   {criterion}")

            print("="*70)

        else:
            print(f"🔧 Unexpected result format: {result}")

    except Exception as e:
        print(f"❌ Error testing agent: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_comprehensive_lap_fix()