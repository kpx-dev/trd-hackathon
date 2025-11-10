"""Feature engineering for lap time prediction models."""

from typing import Optional, Tuple

import pandas as pd
import numpy as np
from loguru import logger


def detect_stints(lap_data: pd.DataFrame, pit_time_threshold: float = 30.0, track: str = None) -> pd.DataFrame:
    """Detect tire stints by identifying pit stops.

    Args:
        lap_data: DataFrame with lap data including LAP_TIME and LAP_NUMBER
        pit_time_threshold: Lap time threshold to consider as pit stop (seconds)
        track: Track name for track-specific adjustments

    Returns:
        DataFrame with added 'stint_number' and 'tire_age' columns
    """
    # Use higher threshold for COTA due to data characteristics
    if track and track.lower() == 'cota':
        pit_time_threshold = 200.0
        logger.info(f"Detecting tire stints from lap data (COTA-specific threshold: {pit_time_threshold}s)")
    else:
        logger.info("Detecting tire stints from lap data")

    df = lap_data.copy()

    # Convert lap times to seconds if not already
    if 'LAP_TIME' in df.columns:
        df['lap_time_seconds'] = df['LAP_TIME'].apply(_convert_laptime_to_seconds)

    # Group by car/driver
    id_column = 'NUMBER' if 'NUMBER' in df.columns else 'DRIVER_NUMBER'

    stint_info = []

    for car_id in df[id_column].unique():
        car_data = df[df[id_column] == car_id].copy()
        car_data = car_data.sort_values('LAP_NUMBER')

        stint_number = 1
        tire_age = 1

        for idx, row in car_data.iterrows():
            lap_time = row.get('lap_time_seconds', 0)

            # Check if this is a pit lap (unusually slow)
            if lap_time > pit_time_threshold:
                stint_number += 1
                tire_age = 1

            stint_info.append({
                'index': idx,
                'stint_number': stint_number,
                'tire_age': tire_age
            })

            tire_age += 1

    # Add stint information back to dataframe
    stint_df = pd.DataFrame(stint_info).set_index('index')
    df = df.join(stint_df)

    logger.info(f"Detected {df['stint_number'].max()} stints across all cars")

    return df


def calculate_degradation_rate(lap_data: pd.DataFrame, track: str = None) -> pd.DataFrame:
    """Calculate tire degradation rate per stint.

    Args:
        lap_data: DataFrame with stint information
        track: Track name for track-specific adjustments

    Returns:
        DataFrame with degradation_rate column
    """
    logger.info("Calculating tire degradation rates")

    df = lap_data.copy()

    if 'stint_number' not in df.columns:
        df = detect_stints(df, track=track)

    id_column = 'NUMBER' if 'NUMBER' in df.columns else 'DRIVER_NUMBER'

    degradation_rates = []

    # Relax minimum stint length for COTA due to data limitations
    min_stint_laps = 2 if (track and track.lower() == 'cota') else 3

    for car_id in df[id_column].unique():
        car_data = df[df[id_column] == car_id]

        for stint in car_data['stint_number'].unique():
            stint_data = car_data[car_data['stint_number'] == stint].copy()

            # Skip stints with too few laps
            if len(stint_data) < min_stint_laps:
                degradation_rate = 0.0
            else:
                # Calculate linear regression slope (degradation per lap)
                if 'lap_time_seconds' in stint_data.columns:
                    tire_ages = stint_data['tire_age'].values
                    lap_times = stint_data['lap_time_seconds'].values

                    # Simple linear fit
                    if len(tire_ages) > 1:
                        coeffs = np.polyfit(tire_ages, lap_times, 1)
                        degradation_rate = coeffs[0]  # Slope
                    else:
                        degradation_rate = 0.0
                else:
                    degradation_rate = 0.0

            for idx in stint_data.index:
                degradation_rates.append({
                    'index': idx,
                    'degradation_rate': degradation_rate
                })

    deg_df = pd.DataFrame(degradation_rates).set_index('index')
    df = df.join(deg_df)

    return df


def engineer_features(
    lap_data: pd.DataFrame,
    weather_data: Optional[pd.DataFrame] = None,
    track: str = None
) -> Tuple[pd.DataFrame, pd.Series]:
    """Engineer features for lap time prediction.

    Args:
        lap_data: Raw lap data
        weather_data: Optional weather data
        track: Track name for track-specific adjustments

    Returns:
        Tuple of (features_df, target_series)
    """
    logger.info("Engineering features for lap time prediction")

    df = lap_data.copy()

    # Detect stints and calculate degradation (with track-specific settings)
    df = detect_stints(df, track=track)
    df = calculate_degradation_rate(df, track=track)

    # Convert lap times to seconds for target
    if 'lap_time_seconds' not in df.columns and 'LAP_TIME' in df.columns:
        df['lap_time_seconds'] = df['LAP_TIME'].apply(_convert_laptime_to_seconds)

    # Basic features
    features = pd.DataFrame()
    id_column = 'NUMBER' if 'NUMBER' in df.columns else 'DRIVER_NUMBER'

    features['car_id'] = df[id_column]
    features['lap_number'] = df['LAP_NUMBER']
    features['tire_age'] = df['tire_age']
    features['stint_number'] = df['stint_number']
    features['degradation_rate'] = df['degradation_rate']

    # Fuel load proxy (car gets lighter as race progresses)
    max_lap = df['LAP_NUMBER'].max()
    features['fuel_load_proxy'] = 1 - (df['LAP_NUMBER'] / max_lap)

    # Rolling statistics (look back at last 3 laps per car)
    for car_id in df[id_column].unique():
        car_mask = df[id_column] == car_id
        car_data = df[car_mask].sort_values('LAP_NUMBER')

        if 'lap_time_seconds' in car_data.columns:
            rolling_mean = car_data['lap_time_seconds'].rolling(window=3, min_periods=1).mean()
            rolling_std = car_data['lap_time_seconds'].rolling(window=3, min_periods=1).std().fillna(0)

            features.loc[car_mask, 'rolling_mean_3'] = rolling_mean.values
            features.loc[car_mask, 'rolling_std_3'] = rolling_std.values
        else:
            features.loc[car_mask, 'rolling_mean_3'] = 0
            features.loc[car_mask, 'rolling_std_3'] = 0

    # Add weather features if available
    if weather_data is not None and not weather_data.empty:
        # Use average weather for now (can be enhanced with time matching)
        if 'AIR_TEMP' in weather_data.columns:
            features['air_temp'] = weather_data['AIR_TEMP'].mean()
        if 'TRACK_TEMP' in weather_data.columns:
            features['track_temp'] = weather_data['TRACK_TEMP'].mean()
        if 'HUMIDITY' in weather_data.columns:
            features['humidity'] = weather_data['HUMIDITY'].mean()
    else:
        features['air_temp'] = 25.0  # Default values
        features['track_temp'] = 30.0
        features['humidity'] = 50.0

    # Target variable
    target = df['lap_time_seconds'] if 'lap_time_seconds' in df.columns else pd.Series()

    # Remove any rows with NaN in target
    valid_mask = target.notna() & (target > 0)
    features = features[valid_mask]
    target = target[valid_mask]

    logger.info(f"Engineered {len(features.columns)} features for {len(features)} samples")

    return features, target


def _convert_laptime_to_seconds(lap_time_str) -> float:
    """Convert lap time string (M:SS.mmm) to seconds.

    Args:
        lap_time_str: Lap time in format "1:23.456" or already as numeric seconds

    Returns:
        Lap time in seconds
    """
    # If already numeric (like COTA data), return as-is
    if isinstance(lap_time_str, (int, float)) and not np.isnan(lap_time_str):
        return float(lap_time_str)

    try:
        clean_time = str(lap_time_str).strip()
        if ':' in clean_time and clean_time != 'nan':
            parts = clean_time.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
    except (ValueError, AttributeError):
        pass

    return np.nan
