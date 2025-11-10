"""Lap time analysis utilities."""

from typing import Dict, List, Optional

import pandas as pd
from loguru import logger


def analyze_lap_progression(df: pd.DataFrame) -> Dict:
    """Analyze lap time progression throughout a race.

    Args:
        df: Lap timing DataFrame

    Returns:
        Analysis results dictionary
    """
    logger.info("Analyzing lap progression")

    if df.empty:
        return {
            "total_laps": 0,
            "average_lap_time": 0.0,
            "fastest_lap": 0.0,
            "degradation_rate": 0.0,
        }

    # Check if we have the analysis format with LAP_TIME or the timing format
    if 'LAP_TIME' in df.columns:
        # Convert LAP_TIME from M:SS.mmm format to seconds
        lap_times = []
        # logger.debug(f"Processing {len(df['LAP_TIME'].dropna())} lap times")

        for i, lap_time_str in enumerate(df['LAP_TIME'].dropna()):
            try:
                # Clean the string - remove whitespace and handle potential formatting issues
                clean_time = str(lap_time_str).strip()
                # logger.debug(f"Processing lap time {i}: '{clean_time}'")

                if ':' in clean_time and clean_time != '':
                    parts = clean_time.split(':')
                    if len(parts) == 2:
                        minutes = int(parts[0])
                        seconds = float(parts[1])
                        total_seconds = minutes * 60 + seconds
                        lap_times.append(total_seconds)
                        # logger.debug(f"Converted '{clean_time}' to {total_seconds} seconds")
                    else:
                        # logger.debug(f"Skipped malformed time: '{clean_time}' (wrong number of parts)")
                        pass
                else:
                    # logger.debug(f"Skipped time without colon: '{clean_time}'")
                    pass
            except (ValueError, IndexError) as e:
                # logger.debug(f"Error parsing lap time '{lap_time_str}': {e}")
                continue

        # logger.debug(f"Successfully parsed {len(lap_times)} lap times")

        if lap_times:
            average_lap_time = sum(lap_times) / len(lap_times)
            fastest_lap = min(lap_times)

            # Calculate degradation rate (slope of lap times over laps)
            if len(lap_times) > 1:
                # Simple linear regression slope
                n = len(lap_times)
                x_mean = (n - 1) / 2  # lap numbers from 0 to n-1
                y_mean = average_lap_time

                numerator = sum((i - x_mean) * (lap_times[i] - y_mean) for i in range(n))
                denominator = sum((i - x_mean) ** 2 for i in range(n))

                degradation_rate = numerator / denominator if denominator != 0 else 0.0
            else:
                degradation_rate = 0.0
        else:
            average_lap_time = 0.0
            fastest_lap = 0.0
            degradation_rate = 0.0
    else:
        # For timing format, calculate lap times from timestamps
        if 'timestamp' in df.columns:
            # Handle different column naming conventions
            vehicle_col = 'vehicle_id' if 'vehicle_id' in df.columns else 'DRIVER_NUMBER'
            lap_col = 'lap' if 'lap' in df.columns else 'LAP_NUMBER'

            df_sorted = df.sort_values([vehicle_col, lap_col])
            lap_times = []
            for vehicle in df_sorted[vehicle_col].unique():
                vehicle_data = df_sorted[df_sorted[vehicle_col] == vehicle]
                if len(vehicle_data) > 1:
                    timestamps = pd.to_datetime(vehicle_data['timestamp'])
                    lap_durations = timestamps.diff().dt.total_seconds().dropna()
                    # Filter out unrealistic lap times (< 60s or > 300s)
                    valid_laps = lap_durations[(lap_durations >= 60) & (lap_durations <= 300)]
                    lap_times.extend(valid_laps.tolist())

            if lap_times:
                average_lap_time = sum(lap_times) / len(lap_times)
                fastest_lap = min(lap_times)
                degradation_rate = 0.0  # Would need more complex calculation
            else:
                average_lap_time = 0.0
                fastest_lap = 0.0
                degradation_rate = 0.0
        else:
            average_lap_time = 0.0
            fastest_lap = 0.0
            degradation_rate = 0.0

    return {
        "total_laps": len(df),
        "average_lap_time": round(average_lap_time, 3),
        "fastest_lap": round(fastest_lap, 3),
        "degradation_rate": round(degradation_rate, 6),
    }


def calculate_tire_degradation(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate tire degradation from lap times.

    Args:
        df: Lap timing DataFrame

    Returns:
        DataFrame with degradation metrics
    """
    logger.info("Calculating tire degradation")

    # Placeholder implementation
    return df.copy() if not df.empty else pd.DataFrame()


def identify_optimal_racing_line(df: pd.DataFrame) -> Dict:
    """Identify optimal racing line from sector times.

    Args:
        df: Sector timing DataFrame

    Returns:
        Optimal racing line analysis
    """
    logger.info("Identifying optimal racing line")

    # Placeholder implementation
    return {
        "sector_1_optimal": 0.0,
        "sector_2_optimal": 0.0,
        "sector_3_optimal": 0.0,
        "total_theoretical_best": 0.0,
    }