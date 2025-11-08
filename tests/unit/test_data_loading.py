"""Unit tests for data loading functionality."""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path

from toyota_gr_cup_analytics.data_processing.loaders import (
    load_lap_data,
    load_telemetry_data,
    load_weather_data,
)


class TestDataLoaders:
    """Test suite for data loading functions."""

    def test_load_lap_data_parameters(self):
        """Test that load_lap_data accepts correct parameters."""
        # This is a placeholder test - will be implemented with real data
        result = load_lap_data("barber", 1)
        assert isinstance(result, pd.DataFrame)

    def test_load_telemetry_data_parameters(self):
        """Test that load_telemetry_data accepts correct parameters."""
        result = load_telemetry_data("cota", 2)
        assert isinstance(result, pd.DataFrame)

    def test_load_weather_data_parameters(self):
        """Test that load_weather_data accepts correct parameters."""
        result = load_weather_data("sebring", 1)
        assert isinstance(result, pd.DataFrame)

    def test_custom_data_root(self):
        """Test using custom data root directory."""
        custom_root = Path("./test_data")
        result = load_lap_data("barber", 1, data_root=custom_root)
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.parametrize("track", ["barber", "cota", "sebring", "sonoma", "vir"])
    def test_supported_tracks(self, track):
        """Test that all supported tracks can be loaded."""
        result = load_lap_data(track, 1)
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.parametrize("race", [1, 2])
    def test_supported_races(self, race):
        """Test that both race numbers are supported."""
        result = load_lap_data("barber", race)
        assert isinstance(result, pd.DataFrame)