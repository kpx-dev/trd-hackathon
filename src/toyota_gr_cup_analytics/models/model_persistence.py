"""Model persistence utilities for saving and loading trained models."""

from pathlib import Path
from typing import Optional, Union
import joblib
from loguru import logger


def save_model(
    model,
    model_name: str,
    models_dir: Optional[Path] = None
) -> Path:
    """Save a trained model to disk.

    Args:
        model: Trained model instance
        model_name: Name for the saved model file
        models_dir: Directory to save models (defaults to models/ in project root)

    Returns:
        Path to saved model file
    """
    if models_dir is None:
        # Default to models directory in project root
        models_dir = Path.cwd() / "models"

    models_dir.mkdir(parents=True, exist_ok=True)

    # Ensure .pkl extension
    if not model_name.endswith('.pkl'):
        model_name = f"{model_name}.pkl"

    model_path = models_dir / model_name

    logger.info(f"Saving model to {model_path}")
    joblib.dump(model, model_path)
    logger.info(f"Model saved successfully ({model_path.stat().st_size / 1024:.1f} KB)")

    return model_path


def load_model(
    model_name: str,
    models_dir: Optional[Path] = None
):
    """Load a trained model from disk.

    Args:
        model_name: Name of the saved model file
        models_dir: Directory where models are saved

    Returns:
        Loaded model instance

    Raises:
        FileNotFoundError: If model file doesn't exist
    """
    if models_dir is None:
        models_dir = Path.cwd() / "models"

    # Ensure .pkl extension
    if not model_name.endswith('.pkl'):
        model_name = f"{model_name}.pkl"

    model_path = models_dir / model_name

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    logger.info(f"Loading model from {model_path}")
    model = joblib.load(model_path)
    logger.info(f"Model loaded successfully")

    return model


def list_saved_models(models_dir: Optional[Path] = None) -> list[Path]:
    """List all saved model files.

    Args:
        models_dir: Directory where models are saved

    Returns:
        List of paths to saved model files
    """
    if models_dir is None:
        models_dir = Path.cwd() / "models"

    if not models_dir.exists():
        logger.warning(f"Models directory does not exist: {models_dir}")
        return []

    model_files = list(models_dir.glob("*.pkl"))
    logger.info(f"Found {len(model_files)} saved models in {models_dir}")

    return model_files


def save_model_bundle(
    models: dict,
    bundle_name: str,
    models_dir: Optional[Path] = None
) -> Path:
    """Save multiple models as a bundle.

    Args:
        models: Dictionary of model_name -> model_instance
        bundle_name: Name for the bundle
        models_dir: Directory to save models

    Returns:
        Path to saved bundle file
    """
    if models_dir is None:
        models_dir = Path.cwd() / "models"

    models_dir.mkdir(parents=True, exist_ok=True)

    if not bundle_name.endswith('.pkl'):
        bundle_name = f"{bundle_name}.pkl"

    bundle_path = models_dir / bundle_name

    logger.info(f"Saving model bundle with {len(models)} models to {bundle_path}")
    joblib.dump(models, bundle_path)
    logger.info(f"Bundle saved successfully ({bundle_path.stat().st_size / 1024:.1f} KB)")

    return bundle_path


def load_model_bundle(
    bundle_name: str,
    models_dir: Optional[Path] = None
) -> dict:
    """Load a bundle of models.

    Args:
        bundle_name: Name of the saved bundle file
        models_dir: Directory where models are saved

    Returns:
        Dictionary of model_name -> model_instance

    Raises:
        FileNotFoundError: If bundle file doesn't exist
    """
    if models_dir is None:
        models_dir = Path.cwd() / "models"

    if not bundle_name.endswith('.pkl'):
        bundle_name = f"{bundle_name}.pkl"

    bundle_path = models_dir / bundle_name

    if not bundle_path.exists():
        raise FileNotFoundError(f"Model bundle not found: {bundle_path}")

    logger.info(f"Loading model bundle from {bundle_path}")
    models = joblib.load(bundle_path)
    logger.info(f"Loaded bundle with {len(models)} models")

    return models
