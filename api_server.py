#!/usr/bin/env python3
"""
Telemetry API Server - Prototype
Serves full telemetry data without pre-processing via REST API
Demonstrates smooth playback with chunked data loading
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import json
from functools import lru_cache
import logging
import asyncio
from ai_assistant import get_racing_ai

app = Flask(__name__)
CORS(app)  # Enable CORS for browser requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data paths - Use absolute path from project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "dataset/data_files/barber")
TELEMETRY_FILES = {
    'R1': f"{DATA_DIR}/R1_barber_telemetry_data.csv",
    'R2': f"{DATA_DIR}/R2_barber_telemetry_data.csv"
}

LAP_FILES = {
    'R1': {
        'start': f"{DATA_DIR}/R1_barber_lap_start.csv",
        'end': f"{DATA_DIR}/R1_barber_lap_end.csv",
        'time': f"{DATA_DIR}/R1_barber_lap_time.csv"
    },
    'R2': {
        'start': f"{DATA_DIR}/R2_barber_lap_start.csv",
        'end': f"{DATA_DIR}/R2_barber_lap_end.csv",
        'time': f"{DATA_DIR}/R2_barber_lap_time.csv"
    }
}

BEST_LAPS_FILES = {
    'R1': f"{DATA_DIR}/99_Best 10 Laps By Driver_Race 1_Anonymized.CSV",
    'R2': f"{DATA_DIR}/99_Best 10 Laps By Driver_Race 2_Anonymized.CSV"
}

# Cache for loaded data (in production, would use Redis or similar)
telemetry_cache = {}
lap_cache = {}
best_laps_cache = {}

@lru_cache(maxsize=32)
def load_telemetry_data(race_id):
    """Load and cache full telemetry data for a race"""
    logger.info(f"Loading telemetry data for {race_id}")

    if race_id not in telemetry_cache:
        file_path = TELEMETRY_FILES[race_id]
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Telemetry file not found: {file_path}")

        df = pd.read_csv(file_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        # Group by vehicle for efficient access
        telemetry_cache[race_id] = {}
        for vehicle_id, vehicle_data in df.groupby('vehicle_id'):
            # Sort by timestamp for efficient time-based queries
            vehicle_data = vehicle_data.sort_values('timestamp')
            telemetry_cache[race_id][vehicle_id] = vehicle_data

        logger.info(f"Loaded {len(df)} telemetry records for {race_id}")

    return telemetry_cache[race_id]

@lru_cache(maxsize=16)
def load_lap_data(race_id):
    """Load and cache lap data for a race"""
    logger.info(f"Loading lap data for {race_id}")

    if race_id not in lap_cache:
        lap_cache[race_id] = {}

        for lap_type, file_path in LAP_FILES[race_id].items():
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                lap_cache[race_id][lap_type] = df

        logger.info(f"Loaded lap data for {race_id}")

    return lap_cache[race_id]

@lru_cache(maxsize=8)
def load_best_laps_data(race_id):
    """Load and cache official best lap data for accurate lap metrics"""
    logger.info(f"Loading best laps data for {race_id}")

    if race_id not in best_laps_cache:
        file_path = BEST_LAPS_FILES[race_id]
        if not os.path.exists(file_path):
            logger.warning(f"Best laps file not found: {file_path}")
            best_laps_cache[race_id] = {}
            return best_laps_cache[race_id]

        # Read CSV with semicolon separator
        df = pd.read_csv(file_path, sep=';')

        # Clean up column names (remove extra spaces)
        df.columns = df.columns.str.strip()

        # Group by car number for efficient access
        best_laps_cache[race_id] = {}
        for _, row in df.iterrows():
            car_number = int(row['NUMBER'])
            best_laps_cache[race_id][car_number] = {
                'best_lap_time': row['BESTLAP_1'],
                'best_lap_number': int(row['BESTLAP_1_LAPNUM']),
                'total_laps': int(row['TOTAL_DRIVER_LAPS']),
                'vehicle': row['VEHICLE'],
                'class': row['CLASS'],
                'average_time': row['AVERAGE']
            }

        logger.info(f"Loaded {len(df)} best lap records for {race_id}")

    return best_laps_cache[race_id]

def parse_lap_time(lap_time_str):
    """Parse lap time string like '1:39.387' to milliseconds"""
    if not lap_time_str or pd.isna(lap_time_str):
        return None

    try:
        # Handle format like "1:39.387"
        if ':' in str(lap_time_str):
            parts = str(lap_time_str).split(':')
            minutes = int(parts[0])
            seconds = float(parts[1])
            return int((minutes * 60 + seconds) * 1000)
        else:
            # Handle pure seconds format
            return int(float(lap_time_str) * 1000)
    except (ValueError, IndexError):
        return None

def format_lap_time_from_ms(milliseconds):
    """Format milliseconds back to lap time string like '1:39.387'"""
    if milliseconds is None:
        return None

    total_seconds = milliseconds / 1000.0
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}"


# === API ENDPOINTS ===

@app.route('/api/races', methods=['GET'])
def get_races():
    """Get available races"""
    return jsonify({
        'races': [
            {'id': 'R1', 'name': 'Race 1', 'track': 'Barber Motorsports Park'},
            {'id': 'R2', 'name': 'Race 2', 'track': 'Barber Motorsports Park'}
        ]
    })

@app.route('/api/races/<race_id>/cars', methods=['GET'])
def get_race_cars(race_id):
    """Get available cars for a race"""
    try:
        telemetry_data = load_telemetry_data(race_id)
        cars = []

        for vehicle_id in telemetry_data.keys():
            # Extract car number for display - use last part of hyphen-separated ID
            if '-' in vehicle_id:
                parts = vehicle_id.split('-')
                car_number = parts[-1] if len(parts) >= 3 else parts[1]
            else:
                car_number = vehicle_id

            cars.append({
                'id': vehicle_id,
                'number': car_number,
                'display_name': f"Car #{car_number} ({vehicle_id})"
            })

        # Sort by car number
        cars.sort(key=lambda x: int(x['number']))

        return jsonify({
            'race_id': race_id,
            'cars': cars,
            'total': len(cars)
        })

    except Exception as e:
        logger.error(f"Error loading cars for {race_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/<race_id>/<vehicle_id>/timeline', methods=['GET'])
def get_telemetry_timeline(race_id, vehicle_id):
    """Get complete timeline metadata for a car (for slider setup)"""
    try:
        telemetry_data = load_telemetry_data(race_id)

        if vehicle_id not in telemetry_data:
            return jsonify({'error': 'Vehicle not found'}), 404

        vehicle_data = telemetry_data[vehicle_id]

        # Get GPS data only for timeline
        gps_data = vehicle_data[vehicle_data['telemetry_name'].isin(['VBOX_Lat_Min', 'VBOX_Long_Minutes'])]

        if len(gps_data) == 0:
            return jsonify({'error': 'No GPS data found'}), 404

        # Get unique timestamps with GPS data
        gps_timestamps = gps_data.groupby('timestamp').size()
        valid_timestamps = gps_timestamps[gps_timestamps >= 2].index  # Both lat and lon

        timeline_data = []
        for timestamp in sorted(valid_timestamps):
            timestamp_data = gps_data[gps_data['timestamp'] == timestamp]

            # Extract lap info
            lap = timestamp_data['lap'].iloc[0] if len(timestamp_data) > 0 else 1

            timeline_data.append({
                'timestamp': timestamp.isoformat(),
                'lap': int(lap)
            })

        return jsonify({
            'race_id': race_id,
            'vehicle_id': vehicle_id,
            'timeline': timeline_data,
            'total_points': len(timeline_data),
            'duration_seconds': (valid_timestamps.max() - valid_timestamps.min()).total_seconds()
        })

    except Exception as e:
        logger.error(f"Error getting timeline: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/<race_id>/<vehicle_id>/chunk', methods=['GET'])
def get_telemetry_chunk(race_id, vehicle_id):
    """Get telemetry data for a specific time range (chunked loading)"""
    try:
        # Parse query parameters
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        chunk_size = int(request.args.get('chunk_size', 60))  # seconds

        telemetry_data = load_telemetry_data(race_id)

        if vehicle_id not in telemetry_data:
            return jsonify({'error': 'Vehicle not found'}), 404

        vehicle_data = telemetry_data[vehicle_id]

        # Filter by time range if provided
        logger.info(f"Original data size: {len(vehicle_data)}")
        if start_time:
            # Parse ISO timestamp with proper timezone handling
            start_dt = pd.to_datetime(start_time, utc=True)
            logger.info(f"Filtering from {start_dt} (parsed from {start_time})")
            vehicle_data = vehicle_data[vehicle_data['timestamp'] >= start_dt]
            logger.info(f"After start filter: {len(vehicle_data)}")

        if end_time:
            # Parse ISO timestamp with proper timezone handling
            end_dt = pd.to_datetime(end_time, utc=True)
            logger.info(f"Filtering to {end_dt} (parsed from {end_time})")
            vehicle_data = vehicle_data[vehicle_data['timestamp'] <= end_dt]
            logger.info(f"After end filter: {len(vehicle_data)}")

        # Group by timestamp and build telemetry records
        chunk_data = []
        for timestamp, timestamp_group in vehicle_data.groupby('timestamp'):

            # Build telemetry dictionary for this timestamp
            telemetry_dict = {}
            lap = None

            for _, row in timestamp_group.iterrows():
                telemetry_dict[row['telemetry_name']] = row['telemetry_value']
                if lap is None:
                    lap = row['lap']

            # Only include if we have GPS coordinates
            if 'VBOX_Lat_Min' in telemetry_dict and 'VBOX_Long_Minutes' in telemetry_dict:
                chunk_data.append({
                    'timestamp': timestamp.isoformat(),
                    'lap': int(lap) if lap else 1,
                    'latitude': telemetry_dict['VBOX_Lat_Min'],
                    'longitude': telemetry_dict['VBOX_Long_Minutes'],
                    'speed': telemetry_dict.get('speed'),
                    'gear': telemetry_dict.get('gear'),
                    'throttle': telemetry_dict.get('aps'),
                    'brake_rear': telemetry_dict.get('pbrake_r'),
                    'brake_front': telemetry_dict.get('pbrake_f'),
                    'engine_rpm': telemetry_dict.get('nmot'),
                    'steering_angle': telemetry_dict.get('Steering_Angle'),
                    'g_force_x': telemetry_dict.get('accx_can'),
                    'g_force_y': telemetry_dict.get('accy_can'),
                    'lap_distance': telemetry_dict.get('Laptrigger_lapdist_dls')
                })

        return jsonify({
            'race_id': race_id,
            'vehicle_id': vehicle_id,
            'start_time': start_time,
            'end_time': end_time,
            'chunk_size': chunk_size,
            'data': chunk_data,
            'total_points': len(chunk_data)
        })

    except Exception as e:
        logger.error(f"Error getting telemetry chunk: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/<race_id>/<vehicle_id>/position', methods=['GET'])
def get_position_at_time(race_id, vehicle_id):
    """Get car position and telemetry at specific timestamp"""
    try:
        timestamp_str = request.args.get('timestamp')
        if not timestamp_str:
            return jsonify({'error': 'timestamp parameter required'}), 400

        # Parse ISO timestamp - handle both Z and +00:00 suffixes
        target_timestamp = pd.to_datetime(timestamp_str, utc=True)
        telemetry_data = load_telemetry_data(race_id)

        if vehicle_id not in telemetry_data:
            return jsonify({'error': 'Vehicle not found'}), 404

        vehicle_data = telemetry_data[vehicle_id]

        # Find closest timestamp (within 5 seconds)
        time_diff = abs(vehicle_data['timestamp'] - target_timestamp)
        closest_idx = time_diff.idxmin()

        if time_diff.loc[closest_idx].total_seconds() > 5:
            return jsonify({'error': 'No data found near timestamp'}), 404

        # Get all telemetry for the closest timestamp
        closest_timestamp = vehicle_data.loc[closest_idx, 'timestamp']
        timestamp_data = vehicle_data[vehicle_data['timestamp'] == closest_timestamp]

        # Build response
        telemetry_dict = {}
        lap = None

        for _, row in timestamp_data.iterrows():
            telemetry_dict[row['telemetry_name']] = row['telemetry_value']
            if lap is None:
                lap = row['lap']

        if 'VBOX_Lat_Min' not in telemetry_dict or 'VBOX_Long_Minutes' not in telemetry_dict:
            return jsonify({'error': 'No GPS data at timestamp'}), 404

        return jsonify({
            'timestamp': closest_timestamp.isoformat(),
            'lap': int(lap) if lap else 1,
            'latitude': telemetry_dict['VBOX_Lat_Min'],
            'longitude': telemetry_dict['VBOX_Long_Minutes'],
            'speed': telemetry_dict.get('speed'),
            'gear': telemetry_dict.get('gear'),
            'throttle': telemetry_dict.get('aps'),
            'brake_rear': telemetry_dict.get('pbrake_r'),
            'brake_front': telemetry_dict.get('pbrake_f'),
            'engine_rpm': telemetry_dict.get('nmot'),
            'steering_angle': telemetry_dict.get('Steering_Angle'),
            'g_force_x': telemetry_dict.get('accx_can'),
            'g_force_y': telemetry_dict.get('accy_can'),
            'lap_distance': telemetry_dict.get('Laptrigger_lapdist_dls')
        })

    except Exception as e:
        logger.error(f"Error getting position: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_fallback_lap_data(race_id, vehicle_id, car_number):
    """Calculate basic lap timing data from lap start/end CSV files for cars without analysis data"""
    try:
        logger.info(f"Using fallback lap timing for vehicle {vehicle_id} (car #{car_number})")

        lap_data = load_lap_data(race_id)

        if 'start' not in lap_data or 'end' not in lap_data:
            logger.warning(f"Missing lap start/end data for {race_id}")
            return jsonify({'error': 'No lap timing data available'}), 404

        lap_start_df = lap_data['start']
        lap_end_df = lap_data['end']

        # Filter for this specific vehicle
        vehicle_starts = lap_start_df[lap_start_df['vehicle_id'] == vehicle_id].copy()
        vehicle_ends = lap_end_df[lap_end_df['vehicle_id'] == vehicle_id].copy()

        if len(vehicle_starts) == 0 or len(vehicle_ends) == 0:
            logger.warning(f"No lap timing data found for vehicle {vehicle_id}")
            return jsonify({'error': f'No lap timing data found for vehicle {vehicle_id}'}), 404

        # Convert timestamps to datetime objects for calculations
        vehicle_starts['timestamp'] = pd.to_datetime(vehicle_starts['timestamp'], utc=True)
        vehicle_ends['timestamp'] = pd.to_datetime(vehicle_ends['timestamp'], utc=True)

        # Sort by lap number
        vehicle_starts = vehicle_starts.sort_values('lap')
        vehicle_ends = vehicle_ends.sort_values('lap')

        result = {
            'race_id': race_id,
            'vehicle_id': vehicle_id,
            'car_number': car_number,
            'laps': {},
            'best_lap': None,
            'best_lap_time': None,
            'total_laps': 0
        }

        best_time_ms = None
        best_lap_num = None

        # Calculate lap times by matching start and end timestamps
        for _, start_row in vehicle_starts.iterrows():
            lap_num = int(start_row['lap'])
            start_time = start_row['timestamp']

            # Find matching end time for this lap
            matching_ends = vehicle_ends[vehicle_ends['lap'] == lap_num]

            if len(matching_ends) > 0:
                end_time = matching_ends.iloc[0]['timestamp']
                lap_duration = (end_time - start_time).total_seconds()
                lap_time_ms = int(lap_duration * 1000)

                # Skip invalid lap times (negative or unreasonably short/long)
                if lap_time_ms < 30000 or lap_time_ms > 300000:  # 30 seconds to 5 minutes
                    logger.debug(f"Skipping invalid lap time for lap {lap_num}: {lap_time_ms}ms ({lap_duration}s)")
                    continue

                # Format lap time as MM:SS.mmm
                lap_time_str = format_lap_time_from_ms(lap_time_ms)

                result['laps'][lap_num] = {
                    'lap_number': lap_num,
                    'lap_time': lap_time_str,
                    'lap_time_ms': lap_time_ms,
                    'lap_improvement': 0,  # Not calculated in fallback
                    'elapsed_time': None,   # Not available in fallback
                    'top_speed': None,      # Not available in fallback
                    'pit_time': None,       # Not available in fallback
                    'flag_at_finish': None, # Not available in fallback
                    # Sector times not available in fallback
                    's1_time': None,
                    's2_time': None,
                    's3_time': None,
                    's1_seconds': None,
                    's2_seconds': None,
                    's3_seconds': None
                }

                # Track best lap - only consider valid positive lap times
                if lap_time_ms > 30000 and (best_time_ms is None or lap_time_ms < best_time_ms):  # > 30 seconds minimum
                    best_time_ms = lap_time_ms
                    best_lap_num = lap_num

                result['total_laps'] += 1

        # Set best lap info
        if best_lap_num is not None:
            result['best_lap'] = best_lap_num
            result['best_lap_time'] = result['laps'][best_lap_num]['lap_time']
            result['best_lap_time_ms'] = best_time_ms

        logger.info(f"Fallback lap data calculated: {result['total_laps']} laps, best lap {best_lap_num}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error calculating fallback lap data: {str(e)}")
        return jsonify({'error': f'Error calculating lap data: {str(e)}'}), 500

@app.route('/api/laps/<race_id>/<vehicle_id>', methods=['GET'])
def get_lap_data(race_id, vehicle_id):
    """Get accurate lap timing data for a vehicle using official best lap data"""
    try:
        best_laps_data = load_best_laps_data(race_id)

        # Extract car number from vehicle_id (e.g., "GR86-006-7" -> 7, "GR86-013-80" -> 80)
        car_number = None
        if '-' in vehicle_id:
            parts = vehicle_id.split('-')
            if len(parts) >= 3:
                try:
                    # Use the last part as the car number
                    car_number = int(parts[-1])
                except ValueError:
                    pass

        # Check if this car has official best lap data
        if car_number is None or car_number not in best_laps_data:
            logger.info(f"No official best lap data found for vehicle {vehicle_id} (car number {car_number}) - using fallback lap timing data")
            return get_fallback_lap_data(race_id, vehicle_id, car_number)

        # Get official best lap data for this car
        official_data = best_laps_data[car_number]

        # Parse the official best lap time
        best_lap_time_str = official_data['best_lap_time']
        best_lap_time_ms = parse_lap_time(best_lap_time_str)

        # Get basic lap data using fallback system for individual lap times
        fallback_result = get_fallback_lap_data(race_id, vehicle_id, car_number)

        # Check if fallback returned an error
        if hasattr(fallback_result, 'get_json') and fallback_result.get_json().get('error'):
            # Fallback failed, create minimal response with just official best lap data
            result = {
                'race_id': race_id,
                'vehicle_id': vehicle_id,
                'car_number': car_number,
                'laps': {},
                'best_lap': official_data['best_lap_number'],
                'best_lap_time': best_lap_time_str,
                'best_lap_time_ms': best_lap_time_ms,
                'total_laps': official_data['total_laps']
            }
        else:
            # Use fallback lap data but override with official best lap information
            result = fallback_result.get_json()

            # Override with official best lap data
            result['best_lap'] = official_data['best_lap_number']
            result['best_lap_time'] = best_lap_time_str
            result['best_lap_time_ms'] = best_lap_time_ms
            result['total_laps'] = official_data['total_laps']

            # Update the best lap in the laps dict if it exists
            if official_data['best_lap_number'] in result['laps']:
                result['laps'][official_data['best_lap_number']]['lap_time'] = best_lap_time_str
                result['laps'][official_data['best_lap_number']]['lap_time_ms'] = best_lap_time_ms

        logger.info(f"Using official best lap data for car #{car_number}: best lap {official_data['best_lap_number']} with time {best_lap_time_str}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting lap data: {str(e)}")
        return jsonify({'error': str(e)}), 500


# === AI ASSISTANT ENDPOINTS ===

@app.route('/api/ai/regions', methods=['GET'])
def get_aws_regions():
    """Get list of supported AWS regions for Bedrock"""
    # Common AWS regions that support Bedrock
    regions = [
        {'id': 'us-east-1', 'name': 'US East (N. Virginia)'},
        {'id': 'us-west-2', 'name': 'US West (Oregon)'},
        {'id': 'us-west-1', 'name': 'US West (N. California)'},
        {'id': 'eu-west-1', 'name': 'Europe (Ireland)'},
        {'id': 'eu-central-1', 'name': 'Europe (Frankfurt)'},
        {'id': 'ap-northeast-1', 'name': 'Asia Pacific (Tokyo)'},
        {'id': 'ap-southeast-1', 'name': 'Asia Pacific (Singapore)'},
        {'id': 'ap-southeast-2', 'name': 'Asia Pacific (Sydney)'}
    ]

    return jsonify({
        'regions': regions,
        'default': 'us-west-2'
    })

@app.route('/api/ai/test-connection', methods=['POST'])
def test_ai_connection():
    """Test connection to Amazon Bedrock"""
    try:
        data = request.get_json() or {}
        region = data.get('region', 'us-west-2')

        # Get AI assistant and test connection
        ai_assistant = get_racing_ai(region)
        result = ai_assistant.test_connection(region)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error testing AI connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}',
            'error': str(e)
        }), 500

def aggregate_telemetry_context(race_id, vehicle_id, lap_number=None, time_range=None):
    """
    Aggregate telemetry data for AI context

    Args:
        race_id: Race identifier (R1, R2)
        vehicle_id: Vehicle identifier
        lap_number: Optional specific lap number
        time_range: Optional time range dict with start_time/end_time

    Returns:
        Dictionary with aggregated telemetry context
    """
    try:
        context = {
            'race_id': race_id,
            'vehicle_id': vehicle_id,
            'track_info': {'name': 'Barber Motorsports Park'}
        }

        # Load telemetry data
        telemetry_data = load_telemetry_data(race_id)
        if vehicle_id not in telemetry_data:
            return context

        vehicle_data = telemetry_data[vehicle_id]

        # Get best lap data for comparison
        try:
            best_laps_data = load_best_laps_data(race_id)
            car_number = None
            if '-' in vehicle_id:
                parts = vehicle_id.split('-')
                if len(parts) >= 3:
                    try:
                        car_number = int(parts[-1])
                    except ValueError:
                        pass

            if car_number and car_number in best_laps_data:
                official_data = best_laps_data[car_number]
                context['best_lap'] = {
                    'lap_number': official_data['best_lap_number'],
                    'lap_time': official_data['best_lap_time'],
                    'total_laps': official_data['total_laps']
                }
        except Exception as e:
            logger.warning(f"Could not load best lap data: {e}")

        # Filter by lap number if specified
        if lap_number:
            lap_data = vehicle_data[vehicle_data['lap'] == lap_number]
            context['lap_number'] = lap_number
            logger.info(f"Filtering telemetry for lap {lap_number}: {len(lap_data)} records")
        elif time_range:
            # Filter by time range
            start_dt = pd.to_datetime(time_range['start_time'], utc=True)
            end_dt = pd.to_datetime(time_range['end_time'], utc=True)
            lap_data = vehicle_data[
                (vehicle_data['timestamp'] >= start_dt) &
                (vehicle_data['timestamp'] <= end_dt)
            ]
        else:
            # Use recent data sample (last 1000 points)
            lap_data = vehicle_data.tail(1000)

        if len(lap_data) == 0:
            return context

        # Build telemetry points for AI context
        telemetry_points = []
        for timestamp, timestamp_group in lap_data.groupby('timestamp'):
            # Build telemetry dictionary for this timestamp
            telemetry_dict = {}
            lap_num = None

            for _, row in timestamp_group.iterrows():
                telemetry_dict[row['telemetry_name']] = row['telemetry_value']
                if lap_num is None:
                    lap_num = row['lap']

            # Only include if we have GPS coordinates
            if 'VBOX_Lat_Min' in telemetry_dict and 'VBOX_Long_Minutes' in telemetry_dict:
                point = {
                    'timestamp': timestamp.isoformat(),
                    'lap': int(lap_num) if lap_num else 1,
                    'latitude': telemetry_dict['VBOX_Lat_Min'],
                    'longitude': telemetry_dict['VBOX_Long_Minutes'],
                    'speed': telemetry_dict.get('speed'),
                    'gear': telemetry_dict.get('gear'),
                    'throttle': telemetry_dict.get('aps'),
                    'brake_rear': telemetry_dict.get('pbrake_r'),
                    'brake_front': telemetry_dict.get('pbrake_f'),
                    'engine_rpm': telemetry_dict.get('nmot'),
                    'steering_angle': telemetry_dict.get('Steering_Angle'),
                    'g_force_x': telemetry_dict.get('accx_can'),
                    'g_force_y': telemetry_dict.get('accy_can'),
                    'lap_distance': telemetry_dict.get('Laptrigger_lapdist_dls')
                }
                telemetry_points.append(point)

        # Calculate current lap summary
        if telemetry_points:
            current_lap_num = telemetry_points[0]['lap']
            lap_points = [p for p in telemetry_points if p['lap'] == current_lap_num]

            if lap_points:
                # Calculate lap time from timestamp range
                start_time = pd.to_datetime(lap_points[0]['timestamp'])
                end_time = pd.to_datetime(lap_points[-1]['timestamp'])
                lap_duration = (end_time - start_time).total_seconds()

                # For specific lap requests, include more comprehensive data for professional analysis
                # Professional racing analysis needs high-resolution data for critical events
                if lap_number:
                    # Use up to 8000 points for lap-specific analysis (provides ~99% coverage)
                    # This ensures we capture all braking events, corner entries, and throttle modulation
                    max_points = min(8000, len(lap_points))
                else:
                    # For general queries without specific lap, use smaller sample
                    max_points = 500

                # Sample points evenly across the lap for better representation
                if len(lap_points) > max_points:
                    # Calculate sampling interval to get even distribution
                    interval = len(lap_points) / max_points
                    sampled_points = []
                    for i in range(max_points):
                        index = int(i * interval)
                        if index < len(lap_points):
                            sampled_points.append(lap_points[index])
                    telemetry_points = sampled_points
                else:
                    telemetry_points = lap_points

                context['current_lap'] = {
                    'lap_number': current_lap_num,
                    'lap_time': format_lap_time_from_ms(int(lap_duration * 1000)) if lap_duration > 30 else None,
                    'telemetry_points': telemetry_points,
                    'total_points': len(lap_points),
                    'sampled_points': len(telemetry_points),
                    'complete_lap_requested': lap_number is not None
                }

        return context

    except Exception as e:
        logger.error(f"Error aggregating telemetry context: {str(e)}")
        return {
            'race_id': race_id,
            'vehicle_id': vehicle_id,
            'error': f'Failed to aggregate context: {str(e)}'
        }

@app.route('/api/ai/analyze', methods=['POST'])
def analyze_racing_question():
    """Analyze racing question with telemetry context using AI"""
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # Required fields
        question = data.get('question', '').strip()
        if not question:
            return jsonify({'error': 'Question is required'}), 400

        race_id = data.get('race_id')
        vehicle_id = data.get('vehicle_id')
        if not race_id or not vehicle_id:
            return jsonify({'error': 'race_id and vehicle_id are required'}), 400

        # Optional fields
        region = data.get('region', 'us-west-2')
        lap_number = data.get('lap_number')
        time_range = data.get('time_range')  # {start_time, end_time}

        logger.info(f"AI analysis request: {race_id}/{vehicle_id}, lap={lap_number}, region={region}")

        # Aggregate telemetry context
        telemetry_context = aggregate_telemetry_context(
            race_id=race_id,
            vehicle_id=vehicle_id,
            lap_number=lap_number,
            time_range=time_range
        )

        # Get AI assistant and analyze
        ai_assistant = get_racing_ai(region)

        # Since we're in a Flask route, we need to run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                ai_assistant.analyze_racing_question(question, telemetry_context, region)
            )
        finally:
            loop.close()

        # Add request context to response
        result['request_context'] = {
            'race_id': race_id,
            'vehicle_id': vehicle_id,
            'lap_number': lap_number,
            'question': question,
            'region': region
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in AI analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}',
            'error_type': 'server_error'
        }), 500


# Serve static files for the web app
@app.route('/')
def serve_index():
    return send_from_directory('race_replay', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('race_replay', filename)

if __name__ == '__main__':
    print("🏁 Starting Telemetry API Server...")
    print("📊 Loading telemetry data...")

    # Pre-load data for better performance
    try:
        for race_id in ['R1', 'R2']:
            if os.path.exists(TELEMETRY_FILES[race_id]):
                load_telemetry_data(race_id)
                load_lap_data(race_id)
                load_best_laps_data(race_id)
                print(f"✅ Loaded data for {race_id}")
            else:
                print(f"⚠️  No data found for {race_id}")
    except Exception as e:
        print(f"❌ Error pre-loading data: {e}")

    print("🚀 Server starting on http://localhost:8000")
    print("🌐 API endpoints available:")
    print("   GET /api/races")
    print("   GET /api/races/{race_id}/cars")
    print("   GET /api/telemetry/{race_id}/{vehicle_id}/timeline")
    print("   GET /api/telemetry/{race_id}/{vehicle_id}/chunk")
    print("   GET /api/telemetry/{race_id}/{vehicle_id}/position")
    print("   GET /api/laps/{race_id}/{vehicle_id}")
    print("🤖 AI Assistant endpoints:")
    print("   GET /api/ai/regions")
    print("   POST /api/ai/test-connection")
    print("   POST /api/ai/analyze")

    app.run(host='0.0.0.0', port=8001, debug=True, threaded=True)