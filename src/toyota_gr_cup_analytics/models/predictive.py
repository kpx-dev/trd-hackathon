"""Predictive models for racing analytics."""

from typing import Dict, Optional, Tuple, List

import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from loguru import logger


class LapTimePredictorModel(BaseEstimator, RegressorMixin):
    """Machine learning model for lap time prediction."""

    def __init__(
        self,
        n_estimators: int = 100,
        random_state: int = 42,
        model_type: str = "random_forest"
    ):
        """Initialize the lap time predictor.

        Args:
            n_estimators: Number of trees/estimators
            random_state: Random seed for reproducibility
            model_type: Type of model ('random_forest' or 'gradient_boosting')
        """
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model_type = model_type

        if model_type == "gradient_boosting":
            self.model = GradientBoostingRegressor(
                n_estimators=n_estimators,
                random_state=random_state,
                max_depth=5,
                learning_rate=0.1
            )
        else:
            self.model = RandomForestRegressor(
                n_estimators=n_estimators,
                random_state=random_state,
                max_depth=10,
                min_samples_split=5
            )

        self.is_fitted = False
        self.feature_names = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'LapTimePredictorModel':
        """Train the lap time prediction model.

        Args:
            X: Feature DataFrame (weather, track conditions, tire age, etc.)
            y: Target lap times in seconds

        Returns:
            Fitted model instance
        """
        logger.info(f"Training lap time predictor model ({self.model_type})")

        if X.empty or y.empty:
            logger.warning("Empty training data provided")
            return self

        # Store feature names
        self.feature_names = X.columns.tolist()

        # Fit the model
        self.model.fit(X, y)
        self.is_fitted = True

        # Log feature importances
        if hasattr(self.model, 'feature_importances_'):
            importances = self.feature_importance()
            top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info(f"Top 5 features: {top_features}")

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict lap times for given conditions.

        Args:
            X: Feature DataFrame

        Returns:
            Predicted lap times in seconds
        """
        if not self.is_fitted:
            logger.warning("Model not fitted yet")
            return np.array([90.0] * len(X))

        return self.model.predict(X)

    def predict_next_lap(
        self,
        current_state: Dict,
        weather_conditions: Optional[Dict] = None
    ) -> Tuple[float, Dict]:
        """Predict the next lap time given current race state.

        Args:
            current_state: Dictionary with current race state
                - car_id, lap_number, tire_age, stint_number, etc.
            weather_conditions: Optional weather data

        Returns:
            Tuple of (predicted_lap_time, prediction_metadata)
        """
        if not self.is_fitted:
            logger.warning("Model not fitted")
            return 90.0, {}

        # Build feature vector
        features = pd.DataFrame([current_state])

        # Add weather if provided
        if weather_conditions:
            for key, value in weather_conditions.items():
                features[key] = value

        # Ensure all training features are present
        for col in self.feature_names:
            if col not in features.columns:
                features[col] = 0.0

        features = features[self.feature_names]

        # Predict
        prediction = self.predict(features)[0]

        metadata = {
            'prediction': float(prediction),
            'tire_age': current_state.get('tire_age', 0),
            'lap_number': current_state.get('lap_number', 0)
        }

        return float(prediction), metadata

    def feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores.

        Returns:
            Dictionary of feature names and their importance scores
        """
        if not self.is_fitted or not hasattr(self.model, 'feature_importances_'):
            return {}

        importances = dict(zip(self.feature_names, self.model.feature_importances_))
        return importances

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Evaluate model performance.

        Args:
            X: Test features
            y: True lap times

        Returns:
            Dictionary of evaluation metrics
        """
        if not self.is_fitted:
            logger.warning("Model not fitted")
            return {}

        predictions = self.predict(X)

        metrics = {
            'mae': mean_absolute_error(y, predictions),
            'rmse': np.sqrt(mean_squared_error(y, predictions)),
            'r2': r2_score(y, predictions),
            'mean_error': np.mean(predictions - y),
            'max_error': np.max(np.abs(predictions - y))
        }

        logger.info(f"Lap time model - MAE: {metrics['mae']:.3f}s, RMSE: {metrics['rmse']:.3f}s, R²: {metrics['r2']:.3f}")

        return metrics


class TireDegradationModel(BaseEstimator, RegressorMixin):
    """Model for predicting tire degradation effects."""

    def __init__(self, degradation_type: str = "linear"):
        """Initialize tire degradation model.

        Args:
            degradation_type: Type of degradation model ('linear', 'exponential')
        """
        self.degradation_type = degradation_type
        self.model = LinearRegression() if degradation_type == "linear" else GradientBoostingRegressor(n_estimators=50)
        self.coefficients = {}
        self.is_fitted = False
        self.feature_names = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'TireDegradationModel':
        """Train the tire degradation model.

        Args:
            X: Features including tire_age, temperature, etc.
            y: Observed lap times

        Returns:
            Fitted model instance
        """
        logger.info(f"Training tire degradation model ({self.degradation_type})")

        if X.empty or y.empty:
            logger.warning("Empty training data provided")
            return self

        # Store feature names
        self.feature_names = X.columns.tolist()

        # Fit the model
        self.model.fit(X, y)
        self.is_fitted = True

        # Extract coefficients for interpretability
        if self.degradation_type == "linear" and hasattr(self.model, 'coef_'):
            self.coefficients = dict(zip(self.feature_names, self.model.coef_))
            self.coefficients['intercept'] = self.model.intercept_

            logger.info(f"Linear degradation model coefficients: {self.coefficients}")

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict lap times with tire degradation.

        Args:
            X: Feature DataFrame

        Returns:
            Predicted lap times
        """
        if not self.is_fitted:
            logger.warning("Tire degradation model not fitted")
            return np.zeros(len(X))

        return self.model.predict(X)

    def predict_stint_performance(
        self,
        base_lap_time: float,
        stint_length: int,
        car_id: int,
        start_lap: int = 1,
        temperature: float = 30.0,
    ) -> Tuple[np.ndarray, Dict]:
        """Predict performance over a tire stint.

        Args:
            base_lap_time: Baseline lap time for the car
            stint_length: Number of laps in stint
            car_id: Car identifier
            start_lap: Starting lap number
            temperature: Track temperature

        Returns:
            Tuple of (lap_times_array, stint_stats_dict)
        """
        logger.info(f"Predicting {stint_length}-lap stint performance for car #{car_id}")

        if not self.is_fitted:
            logger.warning("Model not fitted, returning baseline predictions")
            return np.array([base_lap_time] * stint_length), {}

        # Create feature dataframe for the stint
        stint_features = []
        for lap_in_stint in range(1, stint_length + 1):
            features = {
                'car_id': car_id,
                'lap_number': start_lap + lap_in_stint - 1,
                'tire_age': lap_in_stint,
                'stint_number': 1,
                'degradation_rate': 0.0,  # Will be estimated
                'fuel_load_proxy': 1.0 - ((start_lap + lap_in_stint - 1) / (start_lap + stint_length)),
                'rolling_mean_3': base_lap_time,
                'rolling_std_3': 0.0,
                'air_temp': temperature - 5,
                'track_temp': temperature,
                'humidity': 50.0
            }
            stint_features.append(features)

        stint_df = pd.DataFrame(stint_features)

        # Ensure features match training
        for col in self.feature_names:
            if col not in stint_df.columns:
                stint_df[col] = 0.0

        stint_df = stint_df[self.feature_names]

        # Predict lap times
        predicted_times = self.predict(stint_df)

        # Calculate statistics
        degradation = predicted_times[-1] - predicted_times[0] if len(predicted_times) > 1 else 0.0
        stats = {
            'total_degradation': float(degradation),
            'degradation_per_lap': float(degradation / stint_length) if stint_length > 0 else 0.0,
            'fastest_lap': float(predicted_times.min()),
            'slowest_lap': float(predicted_times.max()),
            'average_lap': float(predicted_times.mean())
        }

        return predicted_times, stats

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Evaluate model performance.

        Args:
            X: Test features
            y: True lap times

        Returns:
            Dictionary of evaluation metrics
        """
        if not self.is_fitted:
            logger.warning("Model not fitted")
            return {}

        predictions = self.predict(X)

        metrics = {
            'mae': mean_absolute_error(y, predictions),
            'rmse': np.sqrt(mean_squared_error(y, predictions)),
            'r2': r2_score(y, predictions)
        }

        logger.info(f"Model evaluation - MAE: {metrics['mae']:.3f}s, RMSE: {metrics['rmse']:.3f}s, R²: {metrics['r2']:.3f}")

        return metrics