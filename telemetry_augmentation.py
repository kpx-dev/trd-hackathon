#!/usr/bin/env python3
"""
Telemetry Data Augmentation System
==================================

This module provides functionality to augment racing telemetry data with precise
start/finish line crossing markers that align with official lap timing data.

The system detects when cars cross the start/finish line using GPS coordinates and
lap distance data, then creates synthetic telemetry records at the exact official
lap completion times.

Key Features:
- Non-intrusive: Adds synthetic records without modifying existing data
- GPS-based detection: Uses coordinates and lap distance correlation
- Temporal alignment: Matches telemetry crossings with official lap times
- API compatible: Works with existing telemetry data structure

Usage:
    from telemetry_augmentation import TelemetryAugmenter

    augmenter = TelemetryAugmenter()
    augmented_data = augmenter.augment_race_data('R1')
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import math
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelemetryAugmenter:
    """
    Augments racing telemetry data with start/finish line crossing markers
    """

    # Barber Motorsports Park start/finish line coordinates
    START_FINISH_LAT = 33.53260
    START_FINISH_LON = -86.61963

    # Detection parameters
    GPS_TOLERANCE = 0.0002  # ~20 meters in decimal degrees
    LAP_DISTANCE_THRESHOLD = 100  # meters from start/finish line
    MIN_LAP_DISTANCE_CHANGE = 3000  # minimum distance change to detect lap crossing

    def __init__(self, data_dir: str = "dataset/data_files/barber"):
        """
        Initialize the telemetry augmenter

        Args:
            data_dir: Directory containing telemetry and lap data files
        """
        self.data_dir = data_dir
        self.telemetry_files = {
            'R1': f"{data_dir}/R1_barber_telemetry_data.csv",
            'R2': f"{data_dir}/R2_barber_telemetry_data.csv"
        }
        self.lap_files = {
            'R1': {
                'start': f"{data_dir}/R1_barber_lap_start.csv",
                'end': f"{data_dir}/R1_barber_lap_end.csv",
                'time': f"{data_dir}/R1_barber_lap_time.csv"
            },
            'R2': {
                'start': f"{data_dir}/R2_barber_lap_start.csv",
                'end': f"{data_dir}/R2_barber_lap_end.csv",
                'time': f"{data_dir}/R2_barber_lap_time.csv"
            }
        }

    def calculate_gps_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula

        Args:
            lat1, lon1: First coordinate pair
            lat2, lon2: Second coordinate pair

        Returns:
            Distance in meters
        """
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in meters
        r = 6371000
        return c * r

    def is_near_start_finish(self, lat: float, lon: float) -> bool:
        """
        Check if GPS coordinates are near the start/finish line

        Args:
            lat, lon: GPS coordinates to check

        Returns:
            True if within tolerance of start/finish line
        """
        distance = self.calculate_gps_distance(
            lat, lon,
            self.START_FINISH_LAT, self.START_FINISH_LON
        )
        return distance <= (self.GPS_TOLERANCE * 111000)  # Convert degrees to meters approx

    def detect_start_finish_crossings(self, vehicle_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect start/finish line crossings in telemetry data

        Args:
            vehicle_data: Telemetry data for a single vehicle

        Returns:
            List of crossing events with timestamps and lap information
        """
        crossings = []

        # Get GPS and lap distance data
        gps_data = vehicle_data[
            vehicle_data['telemetry_name'].isin(['VBOX_Lat_Min', 'VBOX_Long_Minutes', 'Laptrigger_lapdist_dls'])
        ].copy()

        if gps_data.empty:
            logger.warning("No GPS data found for vehicle")
            return crossings

        # Pivot to get coordinates and lap distance by timestamp
        pivoted = gps_data.pivot_table(
            index=['timestamp', 'lap'],
            columns='telemetry_name',
            values='telemetry_value',
            aggfunc='first'
        ).reset_index()

        # Ensure we have all required columns
        required_cols = ['VBOX_Lat_Min', 'VBOX_Long_Minutes', 'Laptrigger_lapdist_dls']
        if not all(col in pivoted.columns for col in required_cols):
            logger.warning(f"Missing required GPS columns: {required_cols}")
            return crossings

        # Sort by timestamp
        pivoted = pivoted.sort_values('timestamp').reset_index(drop=True)

        # Track previous state
        prev_near_sf = False
        prev_lap_distance = None
        prev_lap = None

        for idx, row in pivoted.iterrows():
            lat = row['VBOX_Lat_Min']
            lon = row['VBOX_Long_Minutes']
            lap_distance = row['Laptrigger_lapdist_dls']
            current_lap = row['lap']
            timestamp = row['timestamp']

            # Skip if data is missing
            if pd.isna(lat) or pd.isna(lon) or pd.isna(lap_distance):
                continue

            # Check if currently near start/finish line
            near_sf = self.is_near_start_finish(lat, lon)

            # Detect crossing conditions
            crossing_detected = False
            crossing_type = None

            # Method 1: GPS proximity crossing (entering start/finish zone)
            if near_sf and not prev_near_sf:
                crossing_detected = True
                crossing_type = "gps_entry"

            # Method 2: Lap distance reset (major distance change indicating lap completion)
            if (prev_lap_distance is not None and
                prev_lap_distance > 3000 and  # Was far from start/finish
                lap_distance < self.LAP_DISTANCE_THRESHOLD):  # Now close to start/finish
                crossing_detected = True
                crossing_type = "lap_distance_reset"

            # Method 3: Lap number change
            if prev_lap is not None and current_lap != prev_lap:
                crossing_detected = True
                crossing_type = "lap_change"

            if crossing_detected:
                crossing = {
                    'timestamp': timestamp,
                    'lap_number': current_lap,
                    'detection_method': crossing_type,
                    'gps_lat': lat,
                    'gps_lon': lon,
                    'lap_distance': lap_distance,
                    'distance_to_sf_line': self.calculate_gps_distance(
                        lat, lon, self.START_FINISH_LAT, self.START_FINISH_LON
                    )
                }
                crossings.append(crossing)
                logger.info(f"Detected crossing: {crossing_type} at {timestamp} for lap {current_lap}")

            # Update previous state
            prev_near_sf = near_sf
            prev_lap_distance = lap_distance
            prev_lap = current_lap

        return crossings

    def load_official_lap_times(self, race_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load official lap timing data

        Args:
            race_id: Race identifier (R1, R2)

        Returns:
            Dictionary mapping vehicle_id to list of lap completion times
        """
        official_times = {}

        try:
            # Load lap time data
            lap_time_file = self.lap_files[race_id]['time']
            lap_data = pd.read_csv(lap_time_file)

            # Group by vehicle
            for vehicle_id, vehicle_laps in lap_data.groupby('vehicle_id'):
                official_times[vehicle_id] = []

                for _, lap_row in vehicle_laps.iterrows():
                    # Fix timestamp parsing - handle various timezone formats more robustly
                    timestamp_str = str(lap_row['timestamp']).strip()

                    # Handle double timezone suffixes - remove Z if we have +00:00
                    if '+00:00Z' in timestamp_str:
                        timestamp_str = timestamp_str.replace('+00:00Z', '+00:00')
                    elif timestamp_str.endswith('Z') and '+00:00' in timestamp_str:
                        timestamp_str = timestamp_str.rstrip('Z')

                    # Try different parsing methods
                    try:
                        completion_time = pd.to_datetime(timestamp_str, utc=True)
                    except Exception as e:
                        logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
                        # Try removing timezone suffixes and parsing as UTC
                        clean_timestamp = timestamp_str.rstrip('Z').replace('+00:00', '')
                        try:
                            completion_time = pd.to_datetime(clean_timestamp, utc=True)
                        except:
                            logger.error(f"Could not parse timestamp '{timestamp_str}' even after cleaning")
                            continue

                    lap_info = {
                        'lap_number': lap_row.get('lap_number', lap_row.get('lap')),
                        'completion_time': completion_time,
                        'lap_time_ms': lap_row.get('lap_time_ms'),
                        'lap_time': lap_row.get('lap_time')
                    }
                    official_times[vehicle_id].append(lap_info)

                # Sort by lap number
                official_times[vehicle_id].sort(key=lambda x: x['lap_number'])

            logger.info(f"Loaded official lap times for {len(official_times)} vehicles")

        except Exception as e:
            logger.error(f"Error loading official lap times: {e}")

        return official_times

    def align_crossings_with_official_times(
        self,
        detected_crossings: List[Dict[str, Any]],
        official_lap_times: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Align detected crossings with official lap completion times

        Args:
            detected_crossings: List of detected crossing events
            official_lap_times: List of official lap completion times

        Returns:
            List of aligned crossing events with official timestamps
        """
        aligned_crossings = []

        # Create mapping of lap numbers to official times
        official_by_lap = {
            lap['lap_number']: lap for lap in official_lap_times
        }

        for crossing in detected_crossings:
            lap_num = crossing['lap_number']

            if lap_num in official_by_lap:
                official_lap = official_by_lap[lap_num]

                aligned_crossing = crossing.copy()
                aligned_crossing.update({
                    'official_completion_time': official_lap['completion_time'],
                    'telemetry_timestamp': crossing['timestamp'],
                    'time_difference_seconds': (
                        official_lap['completion_time'] - crossing['timestamp']
                    ).total_seconds(),
                    'lap_time_ms': official_lap.get('lap_time_ms'),
                    'lap_time': official_lap.get('lap_time')
                })

                aligned_crossings.append(aligned_crossing)

        logger.info(f"Aligned {len(aligned_crossings)} crossings with official times")
        return aligned_crossings

    def create_lap_marker_records(
        self,
        aligned_crossings: List[Dict[str, Any]],
        vehicle_id: str
    ) -> List[Dict[str, Any]]:
        """
        Create synthetic telemetry records for start/finish line crossings

        Args:
            aligned_crossings: List of aligned crossing events
            vehicle_id: Vehicle identifier

        Returns:
            List of synthetic telemetry records
        """
        synthetic_records = []

        for crossing in aligned_crossings:
            # Extract vehicle number from vehicle_id
            vehicle_parts = vehicle_id.split('-')
            vehicle_number = int(vehicle_parts[-1]) if len(vehicle_parts) >= 3 else 0

            # Create lap completion marker record
            completion_record = {
                'expire_at': '',
                'lap': crossing['lap_number'],
                'meta_event': f"I_R06_{datetime.now().strftime('%Y-%m-%d')}",
                'meta_session': 'R1',  # This should be dynamic based on race_id
                'meta_source': 'augmentation:lap_marker',
                'meta_time': datetime.now().isoformat() + 'Z',
                'original_vehicle_id': vehicle_id,
                'outing': 0,
                'telemetry_name': 'lap_completion_marker',
                'telemetry_value': 'lap_completed',
                'timestamp': crossing['official_completion_time'].isoformat() + 'Z',
                'vehicle_id': vehicle_id,
                'vehicle_number': vehicle_number
            }

            # Create lap start marker record (for next lap)
            if crossing['lap_number'] < 20:  # Assume max 20 laps
                start_record = completion_record.copy()
                start_record.update({
                    'lap': crossing['lap_number'] + 1,
                    'telemetry_name': 'lap_start_marker',
                    'telemetry_value': 'lap_started',
                    'timestamp': (crossing['official_completion_time'] + timedelta(milliseconds=100)).isoformat() + 'Z'
                })

                synthetic_records.append(start_record)

            synthetic_records.append(completion_record)

        logger.info(f"Created {len(synthetic_records)} synthetic lap marker records")
        return synthetic_records

    def augment_vehicle_data(self, race_id: str, vehicle_id: str) -> Dict[str, Any]:
        """
        Augment telemetry data for a single vehicle

        Args:
            race_id: Race identifier
            vehicle_id: Vehicle identifier

        Returns:
            Dictionary containing original data plus synthetic lap markers
        """
        logger.info(f"Augmenting data for vehicle {vehicle_id} in race {race_id}")

        # Load telemetry data
        telemetry_file = self.telemetry_files[race_id]
        telemetry_data = pd.read_csv(telemetry_file)

        # Fix timestamp parsing - handle various timezone formats
        telemetry_data['timestamp'] = telemetry_data['timestamp'].apply(
            lambda x: str(x).rstrip('Z') if str(x).endswith('Z') else str(x)
        )
        telemetry_data['timestamp'] = pd.to_datetime(telemetry_data['timestamp'], utc=True)

        # Filter for this vehicle
        vehicle_data = telemetry_data[telemetry_data['vehicle_id'] == vehicle_id].copy()

        if vehicle_data.empty:
            logger.warning(f"No telemetry data found for vehicle {vehicle_id}")
            return {'original_records': 0, 'synthetic_records': 0, 'augmented_data': []}

        # Load official lap times
        official_lap_times = self.load_official_lap_times(race_id)
        vehicle_official_times = official_lap_times.get(vehicle_id, [])

        if not vehicle_official_times:
            logger.warning(f"No official lap times found for vehicle {vehicle_id}")
            return {'original_records': len(vehicle_data), 'synthetic_records': 0, 'augmented_data': vehicle_data.to_dict('records')}

        # Detect start/finish line crossings
        detected_crossings = self.detect_start_finish_crossings(vehicle_data)

        if not detected_crossings:
            logger.warning(f"No start/finish line crossings detected for vehicle {vehicle_id}")
            return {'original_records': len(vehicle_data), 'synthetic_records': 0, 'augmented_data': vehicle_data.to_dict('records')}

        # Align crossings with official times
        aligned_crossings = self.align_crossings_with_official_times(
            detected_crossings, vehicle_official_times
        )

        # Create synthetic lap marker records
        synthetic_records = self.create_lap_marker_records(aligned_crossings, vehicle_id)

        # Combine original and synthetic data
        original_records = vehicle_data.to_dict('records')
        augmented_data = original_records + synthetic_records

        # Sort by timestamp with robust parsing
        def safe_parse_timestamp(record):
            timestamp_str = str(record['timestamp'])
            # Handle double timezone suffixes
            if '+00:00Z' in timestamp_str:
                timestamp_str = timestamp_str.replace('+00:00Z', '+00:00')
            elif timestamp_str.endswith('Z') and '+00:00' in timestamp_str:
                timestamp_str = timestamp_str.rstrip('Z')
            try:
                return pd.to_datetime(timestamp_str, utc=True)
            except:
                # Fallback to string-based sorting if datetime parsing fails
                return timestamp_str

        augmented_data.sort(key=safe_parse_timestamp)

        result = {
            'original_records': len(original_records),
            'synthetic_records': len(synthetic_records),
            'detected_crossings': len(detected_crossings),
            'aligned_crossings': len(aligned_crossings),
            'augmented_data': augmented_data,
            'crossing_details': aligned_crossings
        }

        logger.info(f"Augmentation complete: {result['original_records']} original + {result['synthetic_records']} synthetic records")
        return result

    def augment_race_data(self, race_id: str) -> Dict[str, Any]:
        """
        Augment telemetry data for an entire race

        Args:
            race_id: Race identifier (R1, R2)

        Returns:
            Dictionary containing augmented data for all vehicles
        """
        logger.info(f"Starting augmentation for race {race_id}")

        # Load telemetry data to get vehicle list
        telemetry_file = self.telemetry_files[race_id]
        telemetry_data = pd.read_csv(telemetry_file)

        unique_vehicles = telemetry_data['vehicle_id'].unique()
        logger.info(f"Found {len(unique_vehicles)} vehicles in race {race_id}")

        race_results = {
            'race_id': race_id,
            'vehicles': {},
            'summary': {
                'total_vehicles': len(unique_vehicles),
                'successfully_augmented': 0,
                'total_original_records': 0,
                'total_synthetic_records': 0
            }
        }

        for vehicle_id in unique_vehicles:
            try:
                vehicle_result = self.augment_vehicle_data(race_id, vehicle_id)
                race_results['vehicles'][vehicle_id] = vehicle_result

                # Update summary
                if vehicle_result['synthetic_records'] > 0:
                    race_results['summary']['successfully_augmented'] += 1

                race_results['summary']['total_original_records'] += vehicle_result['original_records']
                race_results['summary']['total_synthetic_records'] += vehicle_result['synthetic_records']

            except Exception as e:
                logger.error(f"Error augmenting vehicle {vehicle_id}: {e}")
                race_results['vehicles'][vehicle_id] = {
                    'error': str(e),
                    'original_records': 0,
                    'synthetic_records': 0
                }

        logger.info(f"Race augmentation complete: {race_results['summary']}")
        return race_results


def main():
    """
    Example usage of the telemetry augmentation system
    """
    augmenter = TelemetryAugmenter()

    # Augment R1 race data
    results = augmenter.augment_race_data('R1')

    print(f"\nAugmentation Results for {results['race_id']}:")
    print(f"  Total vehicles: {results['summary']['total_vehicles']}")
    print(f"  Successfully augmented: {results['summary']['successfully_augmented']}")
    print(f"  Total original records: {results['summary']['total_original_records']}")
    print(f"  Total synthetic records: {results['summary']['total_synthetic_records']}")

    # Show details for each vehicle
    for vehicle_id, vehicle_data in results['vehicles'].items():
        if 'error' not in vehicle_data:
            print(f"\nVehicle {vehicle_id}:")
            print(f"  Original records: {vehicle_data['original_records']}")
            print(f"  Synthetic records: {vehicle_data['synthetic_records']}")
            print(f"  Detected crossings: {vehicle_data['detected_crossings']}")
            print(f"  Aligned crossings: {vehicle_data['aligned_crossings']}")

            if vehicle_data['crossing_details']:
                print("  Crossing details:")
                for crossing in vehicle_data['crossing_details'][:3]:  # Show first 3
                    time_diff = crossing.get('time_difference_seconds', 0)
                    print(f"    Lap {crossing['lap_number']}: {time_diff:.2f}s difference")


if __name__ == "__main__":
    main()