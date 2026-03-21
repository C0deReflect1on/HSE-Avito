import pytest

from app import settings


pytestmark = pytest.mark.unit


def test_retry_settings_exist():
    """Test that retry configuration settings are defined."""
    assert hasattr(settings, "MAX_RETRIES")
    assert hasattr(settings, "RETRY_DELAY_SECONDS")
    assert isinstance(settings.MAX_RETRIES, int)
    assert isinstance(settings.RETRY_DELAY_SECONDS, int)
    assert settings.MAX_RETRIES > 0
    assert settings.RETRY_DELAY_SECONDS > 0


def test_max_retries_default_value():
    """Test that MAX_RETRIES has sensible default value."""
    assert settings.MAX_RETRIES == 3


def test_retry_delay_default_value():
    """Test that RETRY_DELAY_SECONDS has sensible default value."""
    assert settings.RETRY_DELAY_SECONDS == 5


def test_moderation_worker_imports_retry_settings():
    """Test that moderation worker imports retry settings."""
    from app.workers import moderation_worker
    
    assert hasattr(moderation_worker, "MAX_RETRIES")
    assert hasattr(moderation_worker, "RETRY_DELAY_SECONDS")
    assert hasattr(moderation_worker, "ModelUnavailableError")
    assert hasattr(moderation_worker, "ModelPredictionError")


def test_dlq_worker_uses_max_retries_from_settings():
    """Test that DLQ worker uses MAX_RETRIES from settings."""
    from app.workers import dlq_worker
    
    assert hasattr(dlq_worker, "MAX_RETRIES")
    assert dlq_worker.MAX_RETRIES == settings.MAX_RETRIES
