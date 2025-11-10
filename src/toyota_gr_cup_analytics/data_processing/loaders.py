"""Data loading utilities for Toyota GR Cup racing data."""

from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger


def load_lap_data(
    track: str,
    race: int,
    data_root: Optional[Path] = None,
) -> pd.DataFrame:
    """Load lap timing data for a specific track and race.

    Args:
        track: Track name (e.g., 'barber', 'cota', 'sebring')
        race: Race number (1 or 2)
        data_root: Root directory for data files

    Returns:
        DataFrame with lap timing data
    """
    if data_root is None:
        # Find the project root by looking for the dataset directory
        current_dir = Path.cwd()
        if (current_dir / "dataset" / "data_files").exists():
            data_root = current_dir / "dataset" / "data_files"
        elif (current_dir.parent / "dataset" / "data_files").exists():
            data_root = current_dir.parent / "dataset" / "data_files"
        else:
            # Fallback to relative path
            data_root = Path("dataset/data_files")

    logger.info(f"Loading lap data for {track} Race {race}")
    # logger.debug(f"Data root: {data_root}")

    # Determine file pattern based on track
    track_lower = track.lower()

    # Try to load the analysis file first (has lap times), fall back to timing file
    analysis_files = []
    timing_files = []

    if track_lower == "barber":
        analysis_files.append(data_root / track_lower / f"23_AnalysisEnduranceWithSections_Race {race}_Anonymized.CSV")
        timing_files.append(data_root / track_lower / f"R{race}_{track_lower}_lap_time.csv")
    elif track_lower in ["cota", "sebring", "sonoma"]:
        analysis_files.append(data_root / track_lower.upper() / f"Race {race}" / f"23_AnalysisEnduranceWithSections_Race {race}_Anonymized.CSV")
        timing_files.append(data_root / track_lower.upper() / f"Race {race}" / f"{track_lower.upper()}_lap_time_R{race}.csv")
    elif track_lower == "vir":
        analysis_files.append(data_root / track_lower.upper() / f"Race {race}" / f"23_AnalysisEnduranceWithSections_Race {race}_Anonymized.CSV")
        timing_files.append(data_root / track_lower.upper() / f"Race {race}" / f"{track_lower}_lap_time_R{race}.csv")
    else:
        raise ValueError(f"Unknown track: {track}")

    # Try analysis file first (preferred - has lap times)
    for lap_file in analysis_files + timing_files:
        # logger.debug(f"Looking for lap file: {lap_file}")
        if lap_file.exists():
            try:
                # Load CSV file with appropriate delimiter
                if "AnalysisEnduranceWithSections" in lap_file.name:
                    # logger.debug(f"Loading analysis file with semicolon delimiter")
                    df = pd.read_csv(lap_file, delimiter=';')
                else:
                    # logger.debug(f"Loading regular CSV file")
                    df = pd.read_csv(lap_file)

                # ALWAYS clean up column names (remove leading/trailing whitespace)
                # logger.debug(f"Columns before cleaning: {list(df.columns[:5])}")
                df.columns = df.columns.str.strip()
                # logger.debug(f"Columns after cleaning: {list(df.columns[:5])}")

                logger.info(f"Loaded {len(df)} lap records for {track} Race {race} from {lap_file.name}")
                # logger.debug(f"Final column check - Has LAP_TIME: {'LAP_TIME' in df.columns}")
                return df
            except Exception as e:
                logger.error(f"Error loading lap data from {lap_file}: {e}")
                continue

    logger.warning(f"No lap data files found for {track} Race {race}")
    return pd.DataFrame()


def load_telemetry_data(
    track: str,
    race: int,
    data_root: Optional[Path] = None,
) -> pd.DataFrame:
    """Load telemetry data for a specific track and race.

    Args:
        track: Track name
        race: Race number
        data_root: Root directory for data files

    Returns:
        DataFrame with telemetry data
    """
    if data_root is None:
        data_root = Path("dataset/data_files")

    logger.info(f"Loading telemetry data for {track} Race {race}")

    # Placeholder implementation
    return pd.DataFrame()


def load_weather_data(
    track: str,
    race: int,
    data_root: Optional[Path] = None,
) -> pd.DataFrame:
    """Load weather data for a specific track and race.

    Args:
        track: Track name
        race: Race number
        data_root: Root directory for data files

    Returns:
        DataFrame with weather data
    """
    if data_root is None:
        # Find the project root by looking for the dataset directory
        current_dir = Path.cwd()
        if (current_dir / "dataset" / "data_files").exists():
            data_root = current_dir / "dataset" / "data_files"
        elif (current_dir.parent / "dataset" / "data_files").exists():
            data_root = current_dir.parent / "dataset" / "data_files"
        else:
            # Fallback to relative path
            data_root = Path("dataset/data_files")

    logger.info(f"Loading weather data for {track} Race {race}")
    # logger.debug(f"Data root: {data_root}")

    track_lower = track.lower()

    # Different tracks have different directory structures
    if track_lower == "barber":
        weather_file = data_root / track_lower / f"26_Weather_Race {race}_Anonymized.CSV"
    elif track_lower in ["cota", "sebring", "sonoma", "vir"]:
        # Handle different race naming patterns
        if track_lower == "cota" and race == 2:
            weather_file = data_root / track_lower.upper() / f"Race {race}" / f"26_Weather_ Race {race}_Anonymized.CSV"
        elif track_lower == "sebring" and race == 2:
            weather_file = data_root / track_lower.title() / f"Race {race}" / f"26_Weather_Race {race}_Anonymized.CSV"
        else:
            # Try the standard pattern first
            weather_file = data_root / track_lower.title() / f"Race {race}" / f"26_Weather_Race {race}_Anonymized.CSV"
            if not weather_file.exists():
                # Try alternative patterns
                weather_file = data_root / track_lower.upper() / f"Race {race}" / f"26_Weather_Race {race}_Anonymized.CSV"
    else:
        raise ValueError(f"Unknown track: {track}")

    # logger.debug(f"Looking for weather file: {weather_file}")

    if not weather_file.exists():
        logger.warning(f"Weather data file not found: {weather_file}")
        return pd.DataFrame()

    try:
        # Weather files use semicolon delimiter
        df = pd.read_csv(weather_file, delimiter=';')

        # ALWAYS clean up column names (remove leading/trailing whitespace)
        # logger.debug(f"Weather columns before cleaning: {list(df.columns[:3])}")
        df.columns = df.columns.str.strip()
        # logger.debug(f"Weather columns after cleaning: {list(df.columns[:3])}")

        logger.info(f"Loaded {len(df)} weather records for {track} Race {race}")
        return df
    except Exception as e:
        logger.error(f"Error loading weather data: {e}")
        return pd.DataFrame()