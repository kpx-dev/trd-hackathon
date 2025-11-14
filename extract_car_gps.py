#!/usr/bin/env python3
"""
Extract GPS data for each car from the full telemetry datasets.
Creates individual car files for dynamic loading in the race replay app.
"""

import pandas as pd
import os
import sys
from pathlib import Path

def extract_car_gps_data():
    # Source files
    races = [
        {
            'source_file': "dataset/data_files/barber/R1_barber_telemetry_data.csv",
            'race_id': 'R1',
            'race_name': 'Race 1'
        },
        {
            'source_file': "dataset/data_files/barber/R2_barber_telemetry_data.csv",
            'race_id': 'R2',
            'race_name': 'Race 2'
        }
    ]

    # Output directory structure by track
    track_output_dir = "race_replay/car_data/barber"
    os.makedirs(track_output_dir, exist_ok=True)

    total_files_created = 0

    for race_info in races:
        print(f"\n=== Processing {race_info['race_name']} ===")

        if not os.path.exists(race_info['source_file']):
            print(f"Warning: Source file not found: {race_info['source_file']}")
            continue

        # Check file size
        file_size = os.path.getsize(race_info['source_file']) / (1024**3)  # GB
        print(f"Loading source dataset: {race_info['source_file']} ({file_size:.1f}GB)")

        try:
            # Read only GPS-related data to save memory
            print("Reading CSV file (this may take a moment for large files)...")
            df = pd.read_csv(race_info['source_file'])
            print(f"Loaded {len(df)} total records")

            # Filter for GPS telemetry only
            gps_data = df[df['telemetry_name'].isin(['VBOX_Lat_Min', 'VBOX_Long_Minutes'])].copy()
            print(f"Filtered to {len(gps_data)} GPS records")

            # Get unique car IDs for this race
            unique_cars = sorted(gps_data['vehicle_id'].unique())
            print(f"Found {len(unique_cars)} unique cars in {race_info['race_name']}")
            print(f"Cars: {', '.join(unique_cars)}")

            for i, car_id in enumerate(unique_cars, 1):
                print(f"Processing {car_id} ({i}/{len(unique_cars)})...")

                # Filter data for this car
                car_data = gps_data[gps_data['vehicle_id'] == car_id].copy()

                # Sample data for smaller files (every 5th point = 20% sampling)
                # This gives better resolution than current 1.69% while staying manageable
                car_data_sampled = car_data.iloc[::5].copy()

                # Sort by timestamp to ensure proper order
                car_data_sampled = car_data_sampled.sort_values('timestamp')

                # Save to track-specific directory with race prefix
                output_file = os.path.join(track_output_dir, f"{race_info['race_id']}_{car_id}_gps.csv")
                car_data_sampled.to_csv(output_file, index=False)

                file_size_kb = os.path.getsize(output_file) / 1024
                print(f"  Saved {len(car_data_sampled)} GPS points to {output_file} ({file_size_kb:.0f}KB)")
                total_files_created += 1

        except Exception as e:
            print(f"Error processing {race_info['race_name']}: {e}")
            continue

    print(f"\n=== GPS extraction complete! ===")
    print(f"Created {total_files_created} car files in: {track_output_dir}/")

    # List created files
    if os.path.exists(track_output_dir):
        files = sorted([f for f in os.listdir(track_output_dir) if f.endswith('_gps.csv')])
        total_size_mb = sum(os.path.getsize(os.path.join(track_output_dir, f)) for f in files) / (1024**2)
        print(f"Total storage used: {total_size_mb:.1f}MB")

        # Show sample of created files
        print("\nCreated files:")
        for f in files[:5]:
            print(f"  {f}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more files")

if __name__ == "__main__":
    print("Toyota GR Cup GPS Data Extractor")
    print("=" * 40)

    try:
        extract_car_gps_data()
        print("\n✅ Success! Data extraction completed successfully.")

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)