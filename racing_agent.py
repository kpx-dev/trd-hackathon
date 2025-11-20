#!/usr/bin/env python3
"""
Racing Analysis Agent with Multiple Data Source Tools
Uses Strands Agents SDK to provide comprehensive racing analysis
"""

import os
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from functools import lru_cache
from datetime import datetime

from strands import Agent, tool

# Configure logging
logger = logging.getLogger(__name__)

class RacingDataTools:
    """Class containing all racing data access tools for the Strands agent"""

    def __init__(self, project_root: str):
        self.data_dir = os.path.join(project_root, "dataset/data_files/barber")
        # Cache loaded CSV data for performance
        self._csv_cache = {}
        logger.info(f"Initialized RacingDataTools with data directory: {self.data_dir}")

    def _load_csv(self, filename: str) -> pd.DataFrame:
        """Lazy load and cache CSV files with appropriate separators"""
        if filename not in self._csv_cache:
            file_path = os.path.join(self.data_dir, filename)
            if not os.path.exists(file_path):
                logger.error(f"CSV file not found: {file_path}")
                raise FileNotFoundError(f"CSV file not found: {file_path}")

            # Check if the file uses semicolon separator
            with open(file_path, 'r') as f:
                first_line = f.readline()

            if ';' in first_line and ',' not in first_line:
                self._csv_cache[filename] = pd.read_csv(file_path, sep=';')
            else:
                self._csv_cache[filename] = pd.read_csv(file_path)

            # Clean up column names (remove extra spaces)
            self._csv_cache[filename].columns = self._csv_cache[filename].columns.str.strip()
            logger.info(f"Loaded CSV: {filename} with {len(self._csv_cache[filename])} rows")

        return self._csv_cache[filename]

    def _parse_lap_time_to_seconds(self, lap_time_str: str) -> float:
        """Parse lap time string like '1:39.387' to seconds as float"""
        if not lap_time_str or pd.isna(lap_time_str):
            return float('inf')

        try:
            if ':' in str(lap_time_str):
                parts = str(lap_time_str).split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(lap_time_str)
        except (ValueError, IndexError):
            return float('inf')

    @tool
    def get_telemetry_analysis(self, race_id: str, vehicle_id: str, lap_number: int = None) -> str:
        """Get detailed telemetry data for driver coaching analysis.

        Use this for questions about:
        - Throttle, brake, and steering technique analysis
        - Speed analysis and racing line optimization
        - G-force analysis and vehicle dynamics
        - Comparing driving technique between laps

        Args:
            race_id: Race identifier (R1, R2)
            vehicle_id: Vehicle identifier (e.g., 'GR86-006-7')
            lap_number: Specific lap to analyze (optional, uses recent data if None)
        """
        try:
            # Import here to avoid circular imports
            from api_server import aggregate_telemetry_context

            # Use the existing telemetry aggregation logic
            context = aggregate_telemetry_context(
                race_id=race_id,
                vehicle_id=vehicle_id,
                lap_number=lap_number
            )

            if 'error' in context:
                return f"Error loading telemetry data: {context['error']}"

            # Format the telemetry analysis
            if 'current_lap' in context:
                lap_data = context['current_lap']
                result_parts = [
                    f"Telemetry Analysis for {vehicle_id} - {race_id}",
                    f"Lap {lap_data.get('lap_number', 'Unknown')}: {lap_data.get('lap_time', 'Unknown')} lap time"
                ]

                if 'telemetry_points' in lap_data:
                    points = lap_data['telemetry_points']
                    result_parts.append(f"Analyzed {len(points)} telemetry data points")

                    # Calculate key performance metrics
                    if points:
                        speeds = [p.get('speed', 0) for p in points if p.get('speed')]
                        throttles = [p.get('throttle', 0) for p in points if p.get('throttle') is not None]
                        brake_rear = [p.get('brake_rear', 0) for p in points if p.get('brake_rear') is not None]

                        if speeds:
                            result_parts.append(f"Speed: {min(speeds):.1f} - {max(speeds):.1f} mph (avg: {sum(speeds)/len(speeds):.1f})")
                        if throttles:
                            avg_throttle = sum(throttles)/len(throttles)
                            result_parts.append(f"Throttle: {min(throttles):.1f}% - {max(throttles):.1f}% (avg: {avg_throttle:.1f}%)")
                        if brake_rear:
                            max_brake = max(brake_rear)
                            result_parts.append(f"Peak Brake Pressure: {max_brake:.1f} psi")

                return "\n".join(result_parts)
            else:
                return f"No telemetry data available for {vehicle_id} in {race_id}"

        except Exception as e:
            logger.error(f"Error in get_telemetry_analysis: {str(e)}")
            return f"Error analyzing telemetry: {str(e)}"

    @tool
    def get_best_laps_data(self, race_id: str, car_number: int = None) -> str:
        """Get best lap times and rankings for competitive analysis.

        Use this for questions about:
        - "Who had the fastest lap time?"
        - "What was my best lap compared to others?"
        - "How do the top 10 best laps compare?"
        - "What's my average lap time vs the field?"

        Args:
            race_id: Race identifier (R1, R2)
            car_number: Specific car to focus on (optional, returns field overview if None)
        """
        try:
            filename = f"99_Best 10 Laps By Driver_Race {race_id[-1]}_Anonymized.CSV"
            df = self._load_csv(filename)

            if car_number is not None:
                car_data = df[df['NUMBER'] == car_number]
                if len(car_data) == 0:
                    # Provide helpful context about what cars are available and field leaders
                    available_cars = sorted(df['NUMBER'].tolist())
                    fastest_overall = df.iloc[0] if len(df) > 0 else None

                    result_parts = [
                        f"Car #{car_number} is not included in the official best laps data for {race_id}.",
                        f"This car may not have completed enough laps for official timing analysis.",
                        "",
                        f"Available cars in official data: {', '.join(['#' + str(c) for c in available_cars[:10]])}{'...' if len(available_cars) > 10 else ''}",
                    ]

                    if fastest_overall is not None:
                        result_parts.extend([
                            "",
                            f"Field Leader Performance:",
                            f"• Fastest Lap: Car #{fastest_overall['NUMBER']} - {fastest_overall['BESTLAP_1']} (Lap {fastest_overall['BESTLAP_1_LAPNUM']})",
                            f"• Field Average: {df['AVERAGE'].mean():.3f}" if 'AVERAGE' in df.columns else "",
                            "",
                            f"Recommendation: Compare your telemetry and lap times to Car #{fastest_overall['NUMBER']}'s performance."
                        ])

                    return "\n".join([p for p in result_parts if p is not None])

                row = car_data.iloc[0]
                result_parts = [
                    f"Car #{car_number} Best Lap Performance ({race_id}):",
                    f"• Best Lap Time: {row['BESTLAP_1']} (Lap {row['BESTLAP_1_LAPNUM']})",
                    f"• Total Laps Completed: {row['TOTAL_DRIVER_LAPS']}",
                    f"• Average Lap Time: {row['AVERAGE']}",
                    f"• Vehicle: {row['VEHICLE']} ({row['CLASS']} class)"
                ]

                # Show top 5 best laps for this driver
                best_laps = []
                for i in range(1, 6):  # Top 5
                    lap_time_col = f'BESTLAP_{i}'
                    lap_num_col = f'BESTLAP_{i}_LAPNUM'
                    if lap_time_col in row and pd.notna(row[lap_time_col]):
                        best_laps.append(f"  {i}. {row[lap_time_col]} (Lap {row[lap_num_col]})")

                if best_laps:
                    result_parts.append("• Top 5 Best Laps:")
                    result_parts.extend(best_laps)

                return "\n".join(result_parts)
            else:
                # Return field overview with top performers
                # Find fastest overall lap
                fastest_times = []
                for _, row in df.iterrows():
                    lap_time = row['BESTLAP_1']
                    if pd.notna(lap_time):
                        seconds = self._parse_lap_time_to_seconds(lap_time)
                        fastest_times.append((seconds, row['NUMBER'], lap_time))

                fastest_times.sort()

                result_parts = [
                    f"Race {race_id} Best Lap Overview:",
                    f"• Total Cars: {len(df)} with lap time data"
                ]

                if fastest_times:
                    result_parts.append("• Top 5 Fastest Laps Overall:")
                    for i, (_, car_num, lap_time) in enumerate(fastest_times[:5], 1):
                        result_parts.append(f"  {i}. Car #{car_num}: {lap_time}")

                    # Field statistics
                    valid_averages = [self._parse_lap_time_to_seconds(row['AVERAGE'])
                                    for _, row in df.iterrows()
                                    if pd.notna(row['AVERAGE'])]
                    if valid_averages:
                        avg_of_averages = sum(valid_averages) / len(valid_averages)
                        result_parts.append(f"• Field Average Lap Time: {avg_of_averages/60:.0f}:{avg_of_averages%60:06.3f}")

                return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error in get_best_laps_data: {str(e)}")
            return f"Error loading best laps data: {str(e)}"

    @tool
    def get_race_results_analysis(self, race_id: str, car_number: int = None) -> str:
        """Get race finishing positions, gaps, and competitive standings.

        Use this for questions about:
        - "How far behind the race leader am I?"
        - "What was my finishing position?"
        - "Who won the race and by what margin?"
        - "What were the gaps between positions?"

        Args:
            race_id: Race identifier (R1, R2)
            car_number: Specific car to focus on (optional, returns race overview if None)
        """
        try:
            # Try official results first, then fall back to provisional results
            race_num = race_id[-1]
            official_filename = f"03_Results GR Cup Race {race_num} Official_Anonymized.CSV"
            provisional_filename = f"03_Provisional Results_Race {race_num}_Anonymized.CSV"

            # Check which file exists
            official_path = os.path.join(self.data_dir, official_filename)
            provisional_path = os.path.join(self.data_dir, provisional_filename)

            if os.path.exists(official_path):
                filename = official_filename
            elif os.path.exists(provisional_path):
                filename = provisional_filename
            else:
                return f"No race results file found for {race_id}"

            df = self._load_csv(filename)

            if car_number is not None:
                car_result = df[df['NUMBER'] == car_number]
                if len(car_result) == 0:
                    return f"Car #{car_number} not found in race results for {race_id}"

                result = car_result.iloc[0]
                winner = df.iloc[0]  # First row is winner

                result_parts = [
                    f"Car #{car_number} Race Result ({race_id}):",
                    f"• Finishing Position: {result['POSITION']}",
                    f"• Status: {result['STATUS']}",
                    f"• Total Race Time: {result['TOTAL_TIME']}",
                    f"• Laps Completed: {result['LAPS']}"
                ]

                # Gap information
                if result['GAP_FIRST'] != '-':
                    result_parts.append(f"• Gap to Winner: {result['GAP_FIRST']}")
                else:
                    result_parts.append("• Race Winner! 🏆")

                if result['GAP_PREVIOUS'] != '-':
                    result_parts.append(f"• Gap to Car Ahead: {result['GAP_PREVIOUS']}")

                # Fastest lap info
                if pd.notna(result['FL_TIME']) and result['FL_TIME'] != '':
                    result_parts.append(f"• Fastest Lap: {result['FL_TIME']} (Lap {result['FL_LAPNUM']}) - {result['FL_KPH']} kph")

                # Winner context
                result_parts.append(f"• Race Winner: Car #{winner['NUMBER']} ({winner['TOTAL_TIME']})")

                return "\n".join(result_parts)
            else:
                # Return race overview
                winner = df.iloc[0]
                classified_finishers = df[df['STATUS'] == 'Classified']

                result_parts = [
                    f"Race {race_id} Final Results:",
                    f"• Winner: Car #{winner['NUMBER']}",
                    f"• Winning Time: {winner['TOTAL_TIME']}",
                    f"• Total Finishers: {len(classified_finishers)} classified",
                    f"• Race Distance: {winner['LAPS']} laps"
                ]

                if pd.notna(winner['FL_TIME']) and winner['FL_TIME'] != '':
                    result_parts.append(f"• Race Fastest Lap: {winner['FL_TIME']} by Car #{winner['NUMBER']}")

                # Show top 5 finishers
                result_parts.append("• Top 5 Finishers:")
                for i in range(min(5, len(classified_finishers))):
                    car = classified_finishers.iloc[i]
                    gap = f" (+{car['GAP_FIRST']})" if car['GAP_FIRST'] != '-' else ""
                    result_parts.append(f"  {car['POSITION']}. Car #{car['NUMBER']}: {car['TOTAL_TIME']}{gap}")

                return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error in get_race_results_analysis: {str(e)}")
            return f"Error loading race results: {str(e)}"

    @tool
    def get_lap_sector_analysis(self, race_id: str, car_number: int, lap_number: int = None) -> str:
        """Get detailed lap and sector time analysis with improvements.

        Use this for questions about:
        - "How were my sector times on lap X?"
        - "Where did I improve/lose time during the race?"
        - "What were my pit stop times?"
        - "How did flags affect my lap times?"

        Args:
            race_id: Race identifier (R1, R2)
            car_number: Car number to analyze
            lap_number: Specific lap (optional, returns summary if None)
        """
        try:
            filename = f"23_AnalysisEnduranceWithSections_Race {race_id[-1]}_Anonymized.CSV"
            df = self._load_csv(filename)

            car_data = df[df['NUMBER'] == car_number]
            if len(car_data) == 0:
                # Provide helpful context about what data is available
                available_cars = sorted(df['NUMBER'].unique().tolist())

                result_parts = [
                    f"Car #{car_number} is not included in the detailed sector analysis data for {race_id}.",
                    f"This car may not have been part of the official timing analysis.",
                    "",
                    f"Cars with detailed sector data: {', '.join(['#' + str(c) for c in available_cars[:8]])}{'...' if len(available_cars) > 8 else ''}",
                    "",
                    f"Alternative: I can still analyze your telemetry data for driving technique insights."
                ]
                return "\n".join(result_parts)

            if lap_number is not None:
                lap_data = car_data[car_data['LAP_NUMBER'] == lap_number]
                if len(lap_data) == 0:
                    return f"Lap {lap_number} not found for car #{car_number} in {race_id}"

                lap = lap_data.iloc[0]
                result_parts = [
                    f"Car #{car_number} Lap {lap_number} Analysis ({race_id}):",
                    f"• Lap Time: {lap['LAP_TIME']} (Improvement: {lap['LAP_IMPROVEMENT']}s)",
                    f"• Sector 1: {lap['S1']} (Δ {lap['S1_IMPROVEMENT']}s)",
                    f"• Sector 2: {lap['S2']} (Δ {lap['S2_IMPROVEMENT']}s)",
                    f"• Sector 3: {lap['S3']} (Δ {lap['S3_IMPROVEMENT']}s)",
                    f"• Top Speed: {lap['TOP_SPEED']} kph",
                    f"• Average Speed: {lap['KPH']} kph"
                ]

                # Flag and track conditions
                if pd.notna(lap['FLAG_AT_FL']) and lap['FLAG_AT_FL'] != '':
                    result_parts.append(f"• Flag Conditions: {lap['FLAG_AT_FL']}")

                # Pit information
                if pd.notna(lap['PIT_TIME']) and lap['PIT_TIME'] != '' and lap['PIT_TIME'] != 0:
                    result_parts.append(f"• Pit Stop Time: {lap['PIT_TIME']}s")

                # Elapsed time context
                if pd.notna(lap['ELAPSED']):
                    result_parts.append(f"• Race Elapsed Time: {lap['ELAPSED']}")

                return "\n".join(result_parts)
            else:
                # Return summary for the car
                sorted_laps = car_data.sort_values('LAP_NUMBER')

                # Find best lap
                best_lap_idx = car_data['LAP_TIME'].apply(self._parse_lap_time_to_seconds).idxmin()
                best_lap_data = car_data.loc[best_lap_idx]

                # Find best sectors
                best_s1 = car_data['S1'].apply(self._parse_lap_time_to_seconds).min()
                best_s2 = car_data['S2'].apply(self._parse_lap_time_to_seconds).min()
                best_s3 = car_data['S3'].apply(self._parse_lap_time_to_seconds).min()

                result_parts = [
                    f"Car #{car_number} Lap Analysis Summary ({race_id}):",
                    f"• Total Laps: {len(car_data)}",
                    f"• Best Lap: {best_lap_data['LAP_TIME']} (Lap {best_lap_data['LAP_NUMBER']})",
                    f"• Best Sectors: S1={best_s1/60:.0f}:{best_s1%60:06.3f}, S2={best_s2/60:.0f}:{best_s2%60:06.3f}, S3={best_s3/60:.0f}:{best_s3%60:06.3f}",
                    f"• Average Speed: {car_data['KPH'].mean():.1f} kph",
                    f"• Peak Speed: {car_data['TOP_SPEED'].max():.1f} kph"
                ]

                # Pit stops
                pit_stops = car_data[pd.notna(car_data['PIT_TIME']) & (car_data['PIT_TIME'] != '') & (car_data['PIT_TIME'] != 0)]
                if len(pit_stops) > 0:
                    result_parts.append(f"• Pit Stops: {len(pit_stops)} stops")
                    for _, pit in pit_stops.iterrows():
                        result_parts.append(f"  Lap {pit['LAP_NUMBER']}: {pit['PIT_TIME']}s")

                return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error in get_lap_sector_analysis: {str(e)}")
            return f"Error loading lap sector analysis: {str(e)}"

    @tool
    def get_track_position_analysis(self, race_id: str, vehicle_id: str, lap_distance: float = None, lap_number: int = None) -> str:
        """Get track position analysis with corner numbers and track layout awareness.

        Use this for questions about:
        - "What corner am I approaching next?"
        - "How should I approach corner 3?"
        - "What's my speed through the hairpin?"
        - "Which sector am I in?"
        - "How far am I from the start/finish line?"

        Args:
            race_id: Race identifier (R1, R2)
            vehicle_id: Vehicle identifier
            lap_distance: Current lap distance in meters (optional)
            lap_number: Specific lap to analyze (optional)
        """
        try:
            # Barber Motorsports Park track layout and corner mapping
            track_layout = {
                'name': 'Barber Motorsports Park',
                'length_meters': 3621,  # Total track length
                'total_corners': 15,
                'sectors': {
                    'S1': {'name': 'Sector 1', 'color': 'blue', 'corners': [1, 2, 3, 4]},
                    'S2': {'name': 'Sector 2', 'color': 'yellow', 'corners': [5, 6, 7, 8, 9, 10]},
                    'S3': {'name': 'Sector 3', 'color': 'pink', 'corners': [11, 12, 13, 14, 15]}
                },
                'corners': {
                    1: {'name': 'Turn 1', 'type': 'right', 'sector': 'S1', 'approx_distance': 200, 'description': 'First right turn after start/finish'},
                    2: {'name': 'Turn 2', 'type': 'left', 'sector': 'S1', 'approx_distance': 400, 'description': 'Uphill left turn'},
                    3: {'name': 'Turn 3', 'type': 'right', 'sector': 'S1', 'approx_distance': 600, 'description': 'Right turn at top of hill'},
                    4: {'name': 'Turn 4', 'type': 'left', 'sector': 'S1', 'approx_distance': 900, 'description': 'Left turn entering back section'},
                    5: {'name': 'Turn 5', 'type': 'right', 'sector': 'S2', 'approx_distance': 1200, 'description': 'Right turn in back section'},
                    6: {'name': 'Turn 6', 'type': 'left', 'sector': 'S2', 'approx_distance': 1500, 'description': 'Left turn continuing back section'},
                    7: {'name': 'Turn 7', 'type': 'right', 'sector': 'S2', 'approx_distance': 1700, 'description': 'Right turn'},
                    8: {'name': 'Turn 8', 'type': 'left', 'sector': 'S2', 'approx_distance': 1900, 'description': 'Left turn'},
                    9: {'name': 'Turn 9', 'type': 'right', 'sector': 'S2', 'approx_distance': 2100, 'description': 'Right turn'},
                    10: {'name': 'Turn 10', 'type': 'left', 'sector': 'S2', 'approx_distance': 2300, 'description': 'Left turn ending back section'},
                    11: {'name': 'Turn 11', 'type': 'right', 'sector': 'S3', 'approx_distance': 2600, 'description': 'Right turn starting final sector'},
                    12: {'name': 'Turn 12', 'type': 'left', 'sector': 'S3', 'approx_distance': 2900, 'description': 'Left hairpin - tightest corner'},
                    13: {'name': 'Turn 13', 'type': 'right', 'sector': 'S3', 'approx_distance': 3100, 'description': 'Right turn after hairpin'},
                    14: {'name': 'Turn 14', 'type': 'left', 'sector': 'S3', 'approx_distance': 3300, 'description': 'Left turn approaching final corner'},
                    15: {'name': 'Turn 15', 'type': 'right', 'sector': 'S3', 'approx_distance': 3500, 'description': 'Final right turn before start/finish straight'}
                },
                'key_features': {
                    'start_finish': {'distance': 0, 'description': 'Start/finish line - main straight'},
                    'hairpin': {'corner': 12, 'description': 'Turn 12 - tightest corner, heavy braking zone'},
                    'elevation_change': {'corners': [1, 2, 3], 'description': 'Uphill section through turns 1-3'}
                }
            }

            # Get current position data if available
            current_position = None
            current_sector = None
            next_corner = None

            if lap_distance is not None:
                # Calculate current position based on lap distance
                current_position = lap_distance

                # Determine current sector
                for sector_id, sector_info in track_layout['sectors'].items():
                    corner_distances = [track_layout['corners'][c]['approx_distance'] for c in sector_info['corners']]
                    if min(corner_distances) <= current_position <= max(corner_distances):
                        current_sector = sector_id
                        break

                # Find next upcoming corner
                for corner_num in range(1, 16):
                    corner_distance = track_layout['corners'][corner_num]['approx_distance']
                    if corner_distance > current_position:
                        next_corner = corner_num
                        break

                # Handle wrap-around (if past turn 15, next is turn 1)
                if next_corner is None:
                    next_corner = 1
            else:
                # Try to get lap distance from telemetry if not provided
                try:
                    from api_server import aggregate_telemetry_context
                    context = aggregate_telemetry_context(
                        race_id=race_id,
                        vehicle_id=vehicle_id,
                        lap_number=lap_number
                    )

                    if 'current_lap' in context and 'telemetry_points' in context['current_lap']:
                        telemetry_points = context['current_lap']['telemetry_points']
                        if telemetry_points:
                            # Use latest telemetry point
                            latest_point = telemetry_points[-1]
                            current_position = latest_point.get('lap_distance')

                            if current_position:
                                # Determine sector and next corner
                                for sector_id, sector_info in track_layout['sectors'].items():
                                    corner_distances = [track_layout['corners'][c]['approx_distance'] for c in sector_info['corners']]
                                    if min(corner_distances) <= current_position <= max(corner_distances):
                                        current_sector = sector_id
                                        break

                                for corner_num in range(1, 16):
                                    corner_distance = track_layout['corners'][corner_num]['approx_distance']
                                    if corner_distance > current_position:
                                        next_corner = corner_num
                                        break

                                if next_corner is None:
                                    next_corner = 1

                except Exception as e:
                    logger.debug(f"Could not get telemetry position data: {e}")

            # Build response
            result_parts = [
                f"Barber Motorsports Park Track Position Analysis ({race_id}):",
                f"• Track Length: {track_layout['length_meters']}m with {track_layout['total_corners']} numbered corners"
            ]

            if current_position is not None:
                result_parts.extend([
                    f"• Current Position: {current_position:.0f}m into lap",
                    f"• Current Sector: {current_sector} ({track_layout['sectors'][current_sector]['name']})" if current_sector else "• Current Sector: Unable to determine",
                    f"• Next Corner: Turn {next_corner} ({track_layout['corners'][next_corner]['type']} turn)" if next_corner else "• Next Corner: Unable to determine"
                ])

                if next_corner:
                    corner_info = track_layout['corners'][next_corner]
                    distance_to_corner = corner_info['approx_distance'] - current_position
                    if distance_to_corner < 0:  # Handle wrap-around
                        distance_to_corner = track_layout['length_meters'] - current_position + corner_info['approx_distance']

                    result_parts.extend([
                        f"• Distance to Next Corner: ~{distance_to_corner:.0f}m",
                        f"• Corner Description: {corner_info['description']}"
                    ])

            # Add track layout overview
            result_parts.append("\\n• Track Layout Overview:")
            for sector_id, sector_info in track_layout['sectors'].items():
                corner_list = ", ".join([f"T{c}" for c in sector_info['corners']])
                result_parts.append(f"  {sector_id} ({sector_info['color']}): Corners {corner_list}")

            # Add key corner information
            result_parts.append("\\n• Key Corners:")
            result_parts.append("  Turn 1: First right after start/finish - sets up lap")
            result_parts.append("  Turn 12: Hairpin (tightest corner) - major braking zone")
            result_parts.append("  Turn 15: Final corner - critical for lap time and overtaking")

            return "\\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error in get_track_position_analysis: {str(e)}")
            return f"Error analyzing track position: {str(e)}"

    @tool
    def get_weather_conditions(self, race_id: str, time_period: str = None) -> str:
        """Get weather and track conditions during the race.

        Use this for questions about:
        - "How did weather affect lap times?"
        - "Was it raining during my slow lap?"
        - "How did track temperature change during the race?"
        - "Did wind conditions impact performance?"

        Args:
            race_id: Race identifier (R1, R2)
            time_period: Specific time period to focus on (optional)
        """
        try:
            filename = f"26_Weather_Race {race_id[-1]}_Anonymized.CSV"
            df = self._load_csv(filename)

            # Convert timestamp to datetime for better analysis
            df['datetime'] = pd.to_datetime(df['TIME_UTC_STR'], format='mixed', utc=True)

            result_parts = [
                f"Race {race_id} Weather Conditions:",
                f"• Data Points: {len(df)} weather measurements",
                f"• Time Range: {df['datetime'].min().strftime('%H:%M')} - {df['datetime'].max().strftime('%H:%M')}"
            ]

            # Temperature analysis
            air_temp_range = f"{df['AIR_TEMP'].min():.1f}°C to {df['AIR_TEMP'].max():.1f}°C"
            track_temp_range = f"{df['TRACK_TEMP'].min():.1f}°C to {df['TRACK_TEMP'].max():.1f}°C"
            result_parts.extend([
                f"• Air Temperature: {air_temp_range} (avg: {df['AIR_TEMP'].mean():.1f}°C)",
                f"• Track Temperature: {track_temp_range} (avg: {df['TRACK_TEMP'].mean():.1f}°C)"
            ])

            # Humidity and pressure
            result_parts.extend([
                f"• Humidity: {df['HUMIDITY'].min():.1f}% to {df['HUMIDITY'].max():.1f}% (avg: {df['HUMIDITY'].mean():.1f}%)",
                f"• Pressure: {df['PRESSURE'].min():.1f} to {df['PRESSURE'].max():.1f} hPa"
            ])

            # Wind conditions
            wind_speed_avg = df['WIND_SPEED'].mean()
            wind_speed_max = df['WIND_SPEED'].max()
            result_parts.append(f"• Wind: {wind_speed_avg:.1f} m/s average (peak: {wind_speed_max:.1f} m/s)")

            # Dominant wind direction
            wind_directions = df['WIND_DIRECTION'].value_counts()
            if len(wind_directions) > 0:
                dominant_dir = wind_directions.index[0]
                result_parts.append(f"• Dominant Wind Direction: {dominant_dir}°")

            # Rain analysis
            rain_periods = df[df['RAIN'] > 0]
            if len(rain_periods) > 0:
                result_parts.append(f"• Rain: Yes - {len(rain_periods)} periods with precipitation")
                result_parts.append(f"  Rain intensity: {rain_periods['RAIN'].min()} to {rain_periods['RAIN'].max()}")
            else:
                result_parts.append("• Rain: No precipitation detected")

            # Temperature trends
            if len(df) > 1:
                temp_change = df['AIR_TEMP'].iloc[-1] - df['AIR_TEMP'].iloc[0]
                if abs(temp_change) > 0.5:
                    trend = "increased" if temp_change > 0 else "decreased"
                    result_parts.append(f"• Temperature Trend: {trend} by {abs(temp_change):.1f}°C during race")

            return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error in get_weather_conditions: {str(e)}")
            return f"Error loading weather data: {str(e)}"

    def _extract_lap_number_from_question(self, question_text: str) -> int:
        """Extract lap number from question text using multiple patterns"""
        import re

        # Multiple patterns to catch lap number references
        patterns = [
            r'Current Lap Number:\s*(\d+)',
            r'Lap Number:\s*(\d+)',
            r'current lap:\s*(\d+)',
            r'lap:\s*(\d+)',
            r'on lap\s*(\d+)',
            r'during lap\s*(\d+)',
            r'lap\s+(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, question_text, re.IGNORECASE)
            if match:
                lap_num = int(match.group(1))
                logger.info(f"Extracted lap number {lap_num} from context using pattern: {pattern}")
                return lap_num

        logger.warning("Could not extract lap number from question context")
        return None

    @tool
    def get_individual_lap_times(self, race_id: str, car_number: int) -> str:
        """Get individual lap times for a specific car in chronological order.

        Use this for questions about:
        - "List my lap times for this race"
        - "Which lap was my fastest/slowest?"
        - "What were my lap times throughout the race?"
        - "How did my lap times compare from start to finish?"
        - "Show me all my lap times"

        Args:
            race_id: Race identifier (R1, R2)
            car_number: Car number to analyze
        """
        try:
            filename = f"23_AnalysisEnduranceWithSections_Race {race_id[-1]}_Anonymized.CSV"
            df = self._load_csv(filename)

            car_data = df[df['NUMBER'] == car_number]
            if len(car_data) == 0:
                # Provide helpful context about what data is available
                available_cars = sorted(df['NUMBER'].unique().tolist())

                result_parts = [
                    f"Car #{car_number} is not included in the detailed lap timing data for {race_id}.",
                    f"This car may not have been part of the official timing analysis.",
                    "",
                    f"Cars with detailed lap timing data: {', '.join(['#' + str(c) for c in available_cars[:10]])}{'...' if len(available_cars) > 10 else ''}",
                ]
                return "\n".join(result_parts)

            # Sort by lap number to show chronological progression
            sorted_laps = car_data.sort_values('LAP_NUMBER')

            # Parse lap times to find fastest and slowest
            lap_times_seconds = []
            for _, lap in sorted_laps.iterrows():
                lap_time_str = lap['LAP_TIME']
                if pd.notna(lap_time_str):
                    seconds = self._parse_lap_time_to_seconds(lap_time_str)
                    if seconds != float('inf'):
                        lap_times_seconds.append((lap['LAP_NUMBER'], seconds, lap_time_str))

            if not lap_times_seconds:
                return f"No valid lap times found for car #{car_number} in {race_id}"

            # Find fastest and slowest laps
            fastest_lap = min(lap_times_seconds, key=lambda x: x[1])
            slowest_lap = max(lap_times_seconds, key=lambda x: x[1])

            result_parts = [
                f"Car #{car_number} Lap Times for {race_id}:",
                f"• Total Laps Completed: {len(lap_times_seconds)}",
                f"• Fastest Lap: Lap {fastest_lap[0]} - {fastest_lap[2]}",
                f"• Slowest Lap: Lap {slowest_lap[0]} - {slowest_lap[2]}",
                "",
                "• Individual Lap Times:"
            ]

            # List all lap times chronologically
            for _, lap in sorted_laps.iterrows():
                lap_num = lap['LAP_NUMBER']
                lap_time = lap['LAP_TIME']

                # Mark fastest and slowest laps
                marker = ""
                if pd.notna(lap_time):
                    lap_seconds = self._parse_lap_time_to_seconds(lap_time)
                    if lap_seconds != float('inf'):
                        if lap_num == fastest_lap[0]:
                            marker = " 🏆 (Fastest)"
                        elif lap_num == slowest_lap[0]:
                            marker = " 🐌 (Slowest)"

                if pd.notna(lap_time):
                    result_parts.append(f"  Lap {lap_num:2d}: {lap_time}{marker}")
                else:
                    result_parts.append(f"  Lap {lap_num:2d}: --:--:--- (Invalid)")

            # Calculate some statistics
            if len(lap_times_seconds) > 1:
                valid_times = [x[1] for x in lap_times_seconds]
                avg_time = sum(valid_times) / len(valid_times)
                avg_minutes = int(avg_time // 60)
                avg_seconds = avg_time % 60

                result_parts.extend([
                    "",
                    f"• Average Lap Time: {avg_minutes}:{avg_seconds:06.3f}",
                    f"• Time Range: {fastest_lap[2]} to {slowest_lap[2]}",
                    f"• Difference: {slowest_lap[1] - fastest_lap[1]:.3f} seconds"
                ])

            return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error in get_individual_lap_times: {str(e)}")
            return f"Error loading lap times: {str(e)}"

    @tool
    def get_live_race_positions(self, race_id: str, timestamp: str = None, vehicle_id: str = None, lap_number: int = None) -> str:
        """Get real-time race positions for all cars at a specific time during the race.

        *** CRITICAL: Always extract lap_number from user context and pass it here! ***
        If user says "Current Lap Number: 4", pass lap_number=4 to get accurate timing!

        Use this for questions about:
        - "What position am I in right now?"
        - "Who is leading the race at this point?"
        - "How far behind the leader am I?"
        - "What are the current race positions?"
        - "Where do I stand compared to other drivers?"

        Args:
            race_id: Race identifier (R1, R2)
            timestamp: ISO timestamp for position snapshot (if None, uses current context timestamp)
            vehicle_id: Focus on specific vehicle (optional, highlights this car in results)
            lap_number: REQUIRED when available - Current lap number from UI context (used to find correct timestamp if timestamp is None)
        """
        try:
            import requests
            import json
            from datetime import datetime

            # Log the parameters received
            logger.info(f"get_live_race_positions called with: race_id={race_id}, vehicle_id={vehicle_id}, lap_number={lap_number}, timestamp={timestamp}")

            # CRITICAL FIX: If lap_number is not provided, try to extract it from the agent's context
            # This is a fallback mechanism since Strands agents may not properly pass parameters
            if lap_number is None:
                # Access the agent's current question/context (this is a workaround)
                # Try to get the question from the execution context
                try:
                    # This is a hack to get the current question being processed
                    import inspect
                    frame = inspect.currentframe()
                    while frame:
                        if 'question' in frame.f_locals or 'enhanced_question' in frame.f_locals:
                            question_text = frame.f_locals.get('enhanced_question', frame.f_locals.get('question', ''))
                            extracted_lap = self._extract_lap_number_from_question(question_text)
                            if extracted_lap:
                                lap_number = extracted_lap
                                logger.info(f"Extracted lap number {lap_number} from execution context")
                                break
                        frame = frame.f_back
                except Exception as e:
                    logger.debug(f"Could not extract lap from execution context: {e}")

                # If still no lap number, log this as a critical issue
                if lap_number is None:
                    logger.error("CRITICAL: No lap_number provided and could not extract from context!")
                    logger.error("This will result in incorrect position calculation using wrong timestamp!")

            # If no timestamp provided, try to get from current context or estimate from lap data
            if timestamp is None:
                try:
                    from api_server import aggregate_telemetry_context, load_telemetry_data

                    # CRITICAL FIX: If lap_number is provided, ALWAYS prioritize our lap-based calculation
                    # over generic telemetry context to avoid using wrong timestamps
                    if lap_number is not None and vehicle_id:
                        logger.info(f"LAP_NUMBER PROVIDED ({lap_number}): Skipping generic telemetry context, using lap-based calculation")
                        # Go directly to lap-based calculation below
                        pass
                    else:
                        # Only use telemetry context if no lap_number is provided
                        logger.info(f"No lap_number provided: Trying generic telemetry context")

                        # Try to get timestamp from current telemetry context if available
                        context = aggregate_telemetry_context(race_id=race_id, vehicle_id=vehicle_id)

                        if 'current_lap' in context and 'telemetry_points' in context['current_lap']:
                            telemetry_points = context['current_lap']['telemetry_points']
                            if telemetry_points:
                                # Use timestamp from most recent telemetry point
                                latest_point = telemetry_points[-1]
                                timestamp = latest_point.get('timestamp')
                                logger.info(f"Using timestamp from telemetry context: {timestamp}")

                    # Lap-based timestamp calculation (when lap_number is provided OR no timestamp from context)
                    if not timestamp and vehicle_id:
                        # Load telemetry and find a timestamp that corresponds to the current lap
                        telemetry_data = load_telemetry_data(race_id)
                        if vehicle_id in telemetry_data:
                            vehicle_data = telemetry_data[vehicle_id]

                            # If we have a specific lap number, find telemetry data from that lap
                            if lap_number is not None:
                                logger.info(f"CRITICAL: Attempting to find timestamp for lap {lap_number}")

                                # CRITICAL FIX: For early laps (1-6), use intelligent lap timing calculation
                                if lap_number <= 6:
                                    logger.info(f"EARLY LAP DETECTED (lap {lap_number}): Using lap timing calculation approach")

                                    # Calculate expected timestamp for this lap based on race start + lap times
                                    race_start = pd.to_datetime('2025-09-04T18:20:00+00:00')  # Approximate race start
                                    avg_lap_time_seconds = 95  # Approximately 1:35 lap time at Barber

                                    # Calculate expected elapsed time: (lap_number - 1) * avg_lap_time + some progress into current lap
                                    laps_completed = lap_number - 1
                                    progress_into_current_lap = 0.5  # Assume halfway through the current lap
                                    total_elapsed_seconds = (laps_completed + progress_into_current_lap) * avg_lap_time_seconds

                                    # Calculate target timestamp
                                    target_timestamp = race_start + pd.Timedelta(seconds=total_elapsed_seconds)
                                    timestamp = target_timestamp.isoformat()

                                    logger.info(f"LAP TIMING CALCULATION: Lap {lap_number}")
                                    logger.info(f"  Race start: {race_start}")
                                    logger.info(f"  Estimated elapsed time: {total_elapsed_seconds:.1f} seconds")
                                    logger.info(f"  Target timestamp: {timestamp}")

                                    # Verify this timestamp makes sense by checking if it's within the data range
                                    vehicle_data_sorted = vehicle_data.sort_values('timestamp')
                                    earliest_time = vehicle_data_sorted.iloc[0]['timestamp']
                                    latest_time = vehicle_data_sorted.iloc[-1]['timestamp']

                                    if target_timestamp < earliest_time:
                                        logger.warning(f"Calculated timestamp {timestamp} is before data starts ({earliest_time})")
                                        timestamp = earliest_time.isoformat()
                                        logger.info(f"Using earliest available timestamp: {timestamp}")
                                    elif target_timestamp > latest_time:
                                        logger.warning(f"Calculated timestamp {timestamp} is after data ends ({latest_time})")
                                        # Use chronological position instead
                                        race_progress = min(lap_number / 25.0, 0.95)  # Assume 25-lap race, don't go past 95%
                                        position_idx = int(len(vehicle_data_sorted) * race_progress)
                                        sample_timestamp = vehicle_data_sorted.iloc[position_idx]['timestamp']
                                        timestamp = sample_timestamp.isoformat()
                                        logger.info(f"Using chronological position {race_progress:.1%}: {timestamp}")
                                    else:
                                        logger.info(f"Calculated timestamp is within data range - using lap timing calculation")
                                else:
                                    # For later laps (7+), try exact lap matching first
                                    logger.info(f"LATER LAP (lap {lap_number}): Trying exact lap matching")

                                    # Debug: Check available lap range
                                    available_laps = sorted(vehicle_data['lap'].unique())
                                    logger.info(f"Available laps in telemetry data: {available_laps[:10]}...{available_laps[-10:]} (showing first and last 10)")

                                    # Try exact match first
                                    lap_specific_data = vehicle_data[vehicle_data['lap'] == lap_number]
                                    logger.info(f"Exact match for lap {lap_number}: {len(lap_specific_data)} records")

                                    if len(lap_specific_data) > 0:
                                        # Use EARLY part of the lap data to represent lap conditions
                                        early_idx = len(lap_specific_data) // 4  # Use first quarter of lap
                                        sample_timestamp = lap_specific_data.iloc[early_idx]['timestamp']
                                        timestamp = sample_timestamp.isoformat()
                                        logger.info(f"SUCCESS: Using timestamp from specific lap {lap_number}: {timestamp}")
                                    else:
                                        logger.warning(f"No exact match for lap {lap_number}, trying nearby laps")

                                        # Try nearby laps (lap 3, 4, 5)
                                        for nearby_lap in [lap_number-1, lap_number+1, lap_number-2, lap_number+2]:
                                            if nearby_lap > 0:
                                                nearby_data = vehicle_data[vehicle_data['lap'] == nearby_lap]
                                                if len(nearby_data) > 0:
                                                    early_idx = len(nearby_data) // 4  # Use first quarter
                                                    sample_timestamp = nearby_data.iloc[early_idx]['timestamp']
                                                    timestamp = sample_timestamp.isoformat()
                                                    logger.info(f"Using nearby lap {nearby_lap} timestamp: {timestamp}")
                                                    break

                                        # If still no luck, use chronological approach based on lap position
                                        if not timestamp:
                                            # Use chronological position based on lap number
                                            vehicle_data_sorted = vehicle_data.sort_values('timestamp')
                                            # Estimate position: lap_number / max_laps * total_data
                                            max_lap = vehicle_data['lap'].max()
                                            estimated_position = int((lap_number / max_lap) * len(vehicle_data_sorted))
                                            estimated_position = min(estimated_position, len(vehicle_data_sorted) - 1)

                                            sample_timestamp = vehicle_data_sorted.iloc[estimated_position]['timestamp']
                                            timestamp = sample_timestamp.isoformat()
                                            logger.info(f"CHRONOLOGICAL ESTIMATE: Using timestamp at position {estimated_position} for lap {lap_number}: {timestamp}")

                            # If still no timestamp, use intelligent estimation based on available lap data
                            if not timestamp:
                                lap_data = vehicle_data[vehicle_data['telemetry_name'] == 'Laptrigger_lapdist_dls']

                                if len(lap_data) > 0:
                                    # Use middle of available lap distance data for better representation
                                    middle_idx = len(lap_data) // 2
                                    sample_timestamp = lap_data.iloc[middle_idx]['timestamp']
                                    timestamp = sample_timestamp.isoformat()
                                    logger.info(f"Using lap-based timestamp estimation: {timestamp}")
                                else:
                                    # Fallback to general middle of telemetry data
                                    sample_timestamp = vehicle_data['timestamp'].iloc[len(vehicle_data) // 2]
                                    timestamp = sample_timestamp.isoformat()
                                    logger.info(f"Using general timestamp estimation: {timestamp}")

                except Exception as e:
                    logger.debug(f"Could not get timestamp from context: {e}")

                # If still no timestamp, return error
                if timestamp is None:
                    return "Error: timestamp parameter required. Please provide a race timestamp to get positions at that point in time."

            # Call the API endpoint for race positions
            base_url = 'http://localhost:8001'
            url = f"{base_url}/api/race/{race_id}/positions"
            params = {'timestamp': timestamp}

            # CRITICAL: Add expected lap parameter when lap_number is available for proper synchronization
            if lap_number is not None:
                params['expected_lap'] = lap_number
                logger.info(f"SYNCHRONIZATION: Passing expected_lap={lap_number} to API for proper lap synchronization")

            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                return f"Error getting race positions: {response.text}"

            data = response.json()

            if 'error' in data:
                return f"Error: {data['error']}"

            positions = data.get('positions', [])
            total_cars = data.get('total_cars', 0)

            if not positions:
                return f"No race position data available for {race_id} at timestamp {timestamp}"

            # Build response
            result_parts = [
                f"Race Positions for {race_id} at {timestamp[:19]}:",
                f"• Total Cars with Position Data: {total_cars}"
            ]

            # Find the specific vehicle if requested
            focus_car_info = None
            if vehicle_id:
                for pos in positions:
                    if pos['vehicle_id'] == vehicle_id:
                        focus_car_info = pos
                        break

            # Show focus car first if found
            if focus_car_info:
                result_parts.extend([
                    "",
                    f"🎯 YOUR POSITION ({focus_car_info['vehicle_id']}):",
                    f"• Race Position: P{focus_car_info['race_position']} of {total_cars}",
                    f"• Current Lap: {focus_car_info['lap']}",
                    f"• Lap Distance: {focus_car_info['lap_distance']:.0f}m",
                    f"• Car Number: #{focus_car_info['car_number']}"
                ])

                # Calculate gaps to leader and cars around
                leader = positions[0]
                if focus_car_info['race_position'] > 1:
                    gap_to_leader = leader['total_distance'] - focus_car_info['total_distance']
                    result_parts.append(f"• Gap to Leader: {gap_to_leader:.0f}m behind")
                else:
                    result_parts.append("• Gap to Leader: LEADING THE RACE! 🏆")

                # Gap to car ahead
                if focus_car_info['race_position'] > 1:
                    car_ahead = positions[focus_car_info['race_position'] - 2]  # -2 because positions are 1-indexed
                    gap_ahead = car_ahead['total_distance'] - focus_car_info['total_distance']
                    result_parts.append(f"• Gap to Car Ahead (P{car_ahead['race_position']}): {gap_ahead:.0f}m")

                # Gap to car behind
                if focus_car_info['race_position'] < len(positions):
                    car_behind = positions[focus_car_info['race_position']]  # positions are 1-indexed
                    gap_behind = focus_car_info['total_distance'] - car_behind['total_distance']
                    result_parts.append(f"• Gap to Car Behind (P{car_behind['race_position']}): {gap_behind:.0f}m ahead")

            # Show top 5 positions
            result_parts.extend([
                "",
                "🏁 TOP 5 RACE POSITIONS:"
            ])

            for i, pos in enumerate(positions[:5]):
                pos_indicator = "🎯 " if vehicle_id and pos['vehicle_id'] == vehicle_id else "   "
                result_parts.append(
                    f"{pos_indicator}P{pos['race_position']}: Car #{pos['car_number']} ({pos['vehicle_id']}) - Lap {pos['lap']}"
                )

            # Show cars around focus vehicle if it's not in top 5
            if focus_car_info and focus_car_info['race_position'] > 5:
                result_parts.extend([
                    "",
                    f"POSITIONS AROUND P{focus_car_info['race_position']}:"
                ])

                start_pos = max(0, focus_car_info['race_position'] - 3)  # Show 2 cars before
                end_pos = min(len(positions), focus_car_info['race_position'] + 2)  # Show 1 car after

                for pos in positions[start_pos:end_pos]:
                    pos_indicator = "🎯 " if pos['vehicle_id'] == vehicle_id else "   "
                    result_parts.append(
                        f"{pos_indicator}P{pos['race_position']}: Car #{pos['car_number']} ({pos['vehicle_id']}) - Lap {pos['lap']}"
                    )

            return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error in get_live_race_positions: {str(e)}")
            return f"Error getting live race positions: {str(e)}"


def create_racing_agent(project_root: str = None) -> Agent:
    """Create and configure the racing analysis agent with all data tools"""

    if project_root is None:
        project_root = os.path.dirname(os.path.abspath(__file__))

    # Initialize the data tools
    racing_tools = RacingDataTools(project_root)

    # Create the racing analysis agent with comprehensive system prompt
    system_prompt = """You are an expert racing coach and data analyst with deep knowledge of motorsports, vehicle dynamics, and racing techniques.

You have access to comprehensive racing data through specialized tools:
- High-resolution telemetry data (throttle, brake, steering, GPS, G-forces)
- Detailed lap and sector timing analysis with improvements
- Best lap rankings and competitive performance data
- Race results, positions, and time gaps
- Real-time race positions for all cars at any point during the race
- Track position analysis with corner numbers and spatial awareness
- Weather and track conditions throughout the race

CRITICAL TOOL USAGE REQUIREMENTS:
- ALWAYS use your tools to get data - never claim you don't have access to data
- When users ask about performance comparisons, best laps, or sector analysis, IMMEDIATELY use the appropriate tools
- For best lap questions: Use get_best_laps_data() with the provided race_id and car_number
- For sector analysis: Use get_lap_sector_analysis() with race_id and car_number
- For telemetry questions: Use get_telemetry_analysis() with the provided parameters
- If context provides a car number, always use it in your tool calls

IMPORTANT: When users provide current situation context (race, vehicle, lap distance, position), use this information directly with your tools.

**LAP NUMBER EXTRACTION CRITICAL:**
- When context includes "Current Lap Number: X" or similar lap information, ALWAYS extract that number
- Pass the lap number as the lap_number parameter to get_live_race_positions
- This ensures you get position data from the correct point in the race, not wrong timestamps
- Example: If context shows "Current Lap Number: 4", use get_live_race_positions(race_id="R1", vehicle_id="GR86-013-80", lap_number=4)

For track position questions, use the get_track_position_analysis tool with the provided lap_distance parameter when available.

When answering questions, intelligently select the appropriate tools to gather relevant data, then provide specific, actionable insights based on the actual data. Always reference concrete values, times, and measurements when making recommendations.

Your coaching style should be:
- Data-driven with specific references to telemetry values
- Focused on actionable improvements (braking points, throttle technique, racing line)
- Comparative when possible (vs best lap, vs competitors, vs optimal)
- Professional but encouraging
- Context-aware: Use provided race, vehicle, and position information to give precise responses

Example tool usage patterns:
- For technique questions: Use get_telemetry_analysis for detailed driving data
- For competitive questions: Use get_best_laps_data or get_race_results_analysis
- For race position questions: Use get_live_race_positions to get current standings and gaps between cars
  * CRITICAL: When lap number is provided in context (like "Current Lap Number: 4"), ALWAYS extract that number and pass it as lap_number parameter
  * EXAMPLE: get_live_race_positions(race_id="R1", vehicle_id="GR86-013-80", lap_number=4)
  * NEVER ignore the lap number from context - this is essential for accurate timing
- For specific lap analysis: Use get_lap_sector_analysis for sector splits and timing
- For track position questions: Use get_track_position_analysis with race_id, vehicle_id, and lap_distance from context
- For track conditions: Use get_weather_conditions for environmental factors

Always provide concrete, data-driven insights rather than generic advice. When context is provided about current position, immediately use the relevant tools to analyze the situation."""

    agent = Agent(
        name="racing_analyst",
        system_prompt=system_prompt,
        model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",  # Use Claude Sonnet 4.5 inference profile
        tools=[
            racing_tools.get_telemetry_analysis,
            racing_tools.get_best_laps_data,
            racing_tools.get_race_results_analysis,
            racing_tools.get_lap_sector_analysis,
            racing_tools.get_track_position_analysis,
            racing_tools.get_weather_conditions,
            racing_tools.get_live_race_positions,
            racing_tools.get_individual_lap_times
        ]
    )

    logger.info("Racing analysis agent created successfully with 8 data tools")
    return agent


# Global agent instance (will be initialized by the API server)
racing_agent_instance = None

def get_racing_agent(project_root: str = None) -> Agent:
    """Get or create the global racing analysis agent instance"""
    global racing_agent_instance

    if racing_agent_instance is None:
        racing_agent_instance = create_racing_agent(project_root)

    return racing_agent_instance


if __name__ == "__main__":
    # Test the agent
    agent = create_racing_agent()
    print("🏁 Racing Analysis Agent created successfully!")

    # Example usage
    result = agent("Who had the fastest lap in R1?")
    print("\nTest question: 'Who had the fastest lap in R1?'")
    print(f"Response: {result}")