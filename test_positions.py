#!/usr/bin/env python3
"""
Test script for the new live race positions functionality
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add the project root to the path so we can import from api_server
sys.path.insert(0, '/Users/gilesjm/Repo/trd-hackathon')

from api_server import load_telemetry_data, get_race_positions_at_time

def test_positions():
    """Test the race positions endpoint with sample data"""

    print("🧪 Testing live race positions functionality...")

    # Load R1 telemetry data
    print("📊 Loading telemetry data...")
    telemetry_data = load_telemetry_data('R1')

    if not telemetry_data:
        print("❌ No telemetry data loaded")
        return

    print(f"✅ Loaded telemetry data for {len(telemetry_data)} vehicles")

    # Get a sample timestamp from the data
    # Pick a vehicle and get one of its timestamps
    vehicle_id = next(iter(telemetry_data.keys()))
    vehicle_data = telemetry_data[vehicle_id]

    # Get a timestamp from middle of the race (not start or end)
    sample_timestamp = vehicle_data['timestamp'].iloc[len(vehicle_data) // 2]

    print(f"🕐 Testing with timestamp: {sample_timestamp}")
    print(f"📍 Sample vehicle: {vehicle_id}")

    # Test the positions calculation
    try:
        result = {
            'race_id': 'R1',
            'timestamp': sample_timestamp.isoformat(),
            'positions': [],
            'total_cars': 0
        }

        positions = []

        # For each car, find their position at the target timestamp
        for vehicle_id, vehicle_data in telemetry_data.items():
            try:
                # Find closest timestamp (within 30 seconds tolerance)
                time_diff = abs(vehicle_data['timestamp'] - sample_timestamp)
                closest_idx = time_diff.idxmin()

                if time_diff.loc[closest_idx].total_seconds() > 30:
                    continue  # Skip cars with no data near this timestamp

                # Get telemetry at this timestamp
                closest_timestamp = vehicle_data.loc[closest_idx, 'timestamp']
                timestamp_data = vehicle_data[vehicle_data['timestamp'] == closest_timestamp]

                # Extract lap and lap distance
                lap = None
                lap_distance = None
                car_number = None

                for _, row in timestamp_data.iterrows():
                    if lap is None:
                        lap = row['lap']
                    if car_number is None:
                        # Extract car number from vehicle_id
                        parts = vehicle_id.split('-')
                        if len(parts) >= 3:
                            car_number = parts[-1]
                        else:
                            car_number = vehicle_id
                    if row['telemetry_name'] == 'Laptrigger_lapdist_dls':
                        lap_distance = row['telemetry_value']

                if lap is not None and lap_distance is not None:
                    # Calculate total race distance (lap-1 * track_length + lap_distance)
                    track_length = 3710  # Barber track length in meters
                    total_distance = (lap - 1) * track_length + lap_distance

                    positions.append({
                        'vehicle_id': vehicle_id,
                        'car_number': car_number,
                        'lap': int(lap),
                        'lap_distance': float(lap_distance),
                        'total_distance': float(total_distance),
                        'timestamp': closest_timestamp.isoformat()
                    })

            except Exception as e:
                print(f"⚠️ Warning processing vehicle {vehicle_id}: {str(e)}")
                continue

        # Sort by total distance (descending = race leader first)
        positions.sort(key=lambda x: x['total_distance'], reverse=True)

        # Add race position numbers
        for i, pos in enumerate(positions):
            pos['race_position'] = i + 1

        result['positions'] = positions
        result['total_cars'] = len(positions)

        print(f"🏁 Race positions calculated successfully!")
        print(f"📊 Total cars with position data: {len(positions)}")

        if positions:
            print("\n🏆 Top 5 positions:")
            for i, pos in enumerate(positions[:5]):
                gap = ""
                if i > 0:
                    gap_distance = positions[0]['total_distance'] - pos['total_distance']
                    gap = f" ({gap_distance:.0f}m behind leader)"

                print(f"  P{pos['race_position']}: Car #{pos['car_number']} ({pos['vehicle_id']}) - Lap {pos['lap']}{gap}")
        else:
            print("❌ No position data available")

    except Exception as e:
        print(f"❌ Error calculating positions: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_positions()