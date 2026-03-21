import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from app.services.model_provider import ModerationModelProvider
from app.services.moderation import ModelUnavailableError


pytestmark = pytest.mark.unit


def test_model_provider_loads_local_by_default():
    """Test that model provider loads from local file by default."""
    with patch.dict(os.environ, {}, clear=True):
        provider = ModerationModelProvider()
        with patch("app.services.model_provider.get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_get_model.return_value = mock_model
            
            provider.load()
            
            mock_get_model.assert_called_once()
            assert provider._model == mock_model


def test_model_provider_loads_from_mlflow_when_enabled():
    """Test that model provider loads from MLflow when USE_MLFLOW=true."""
    with patch.dict(os.environ, {"USE_MLFLOW": "true"}):
        provider = ModerationModelProvider()
        
        mock_mlflow = MagicMock()
        mock_model = MagicMock()
        mock_mlflow.sklearn.load_model.return_value = mock_model
        
        with patch.dict("sys.modules", {"mlflow": mock_mlflow, "mlflow.sklearn": mock_mlflow.sklearn}):
            provider.load()
            
            mock_mlflow.set_tracking_uri.assert_called_once()
            mock_mlflow.sklearn.load_model.assert_called_once()
            assert provider._model == mock_model


def test_model_provider_mlflow_uses_environment_config():
    """Test that MLflow loading respects environment configuration."""
    env_vars = {
        "USE_MLFLOW": "true",
        "MLFLOW_TRACKING_URI": "http://mlflow:5000",
        "MLFLOW_MODEL_NAME": "test-model",
        "MLFLOW_MODEL_STAGE": "Staging",
    }
    
    with patch.dict(os.environ, env_vars):
        provider = ModerationModelProvider()
        
        mock_mlflow = MagicMock()
        mock_model = MagicMock()
        mock_mlflow.sklearn.load_model.return_value = mock_model
        
        with patch.dict("sys.modules", {"mlflow": mock_mlflow, "mlflow.sklearn": mock_mlflow.sklearn}):
            provider.load()
            
            mock_mlflow.set_tracking_uri.assert_called_with("http://mlflow:5000")
            expected_uri = "models:/test-model/Staging"
            mock_mlflow.sklearn.load_model.assert_called_with(expected_uri)


def test_model_provider_mlflow_raises_on_import_error():
    """Test that ModelUnavailableError is raised if mlflow is not installed."""
    with patch.dict(os.environ, {"USE_MLFLOW": "true"}):
        provider = ModerationModelProvider()
        
        with patch.dict("sys.modules", {"mlflow": None, "mlflow.sklearn": None}):
            with pytest.raises(ModelUnavailableError, match="MLflow is not installed"):
                provider.load()


def test_model_provider_mlflow_raises_on_load_failure():
    """Test that ModelUnavailableError is raised if MLflow model loading fails."""
    with patch.dict(os.environ, {"USE_MLFLOW": "true", "MLFLOW_MODEL_NAME": "missing-model"}):
        provider = ModerationModelProvider()
        
        mock_mlflow = MagicMock()
        mock_mlflow.sklearn.load_model.side_effect = Exception("Model not found")
        
        with patch.dict("sys.modules", {"mlflow": mock_mlflow, "mlflow.sklearn": mock_mlflow.sklearn}):
            with pytest.raises(ModelUnavailableError, match="Failed to load model from MLflow"):
                provider.load()


def test_model_provider_predict_proba_works_with_mlflow_model():
    """Test that predict_proba works correctly with MLflow-loaded model."""
    with patch.dict(os.environ, {"USE_MLFLOW": "true"}):
        provider = ModerationModelProvider()
        
        mock_mlflow = MagicMock()
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.3, 0.7]]
        mock_mlflow.sklearn.load_model.return_value = mock_model
        
        with patch.dict("sys.modules", {"mlflow": mock_mlflow, "mlflow.sklearn": mock_mlflow.sklearn}):
            provider.load()
            result = provider.predict_proba([0.1, 0.2, 0.3, 0.4])
            
            assert result == 0.7
            mock_model.predict_proba.assert_called_once()


def test_model_provider_use_mlflow_case_insensitive():
    """Test that USE_MLFLOW environment variable is case-insensitive."""
    test_cases = ["TRUE", "True", "true", "TrUe"]
    
    for value in test_cases:
        with patch.dict(os.environ, {"USE_MLFLOW": value}):
            provider = ModerationModelProvider()
            
            mock_mlflow = MagicMock()
            mock_model = MagicMock()
            mock_mlflow.sklearn.load_model.return_value = mock_model
            
            with patch.dict("sys.modules", {"mlflow": mock_mlflow, "mlflow.sklearn": mock_mlflow.sklearn}):
                provider.load()
                
                mock_mlflow.sklearn.load_model.assert_called_once()
                mock_mlflow.reset_mock()


def test_model_provider_use_mlflow_false_values():
    """Test that USE_MLFLOW=false uses local loading."""
    test_cases = ["false", "False", "FALSE", "no", "0", ""]
    
    for value in test_cases:
        with patch.dict(os.environ, {"USE_MLFLOW": value}):
            provider = ModerationModelProvider()
            
            with patch("app.services.model_provider.get_model") as mock_get_model:
                mock_model = MagicMock()
                mock_get_model.return_value = mock_model
                
                provider.load()
                
                mock_get_model.assert_called_once()
                mock_get_model.reset_mock()
