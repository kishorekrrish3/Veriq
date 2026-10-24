"""Unit tests for VERIQ configuration settings.
"""

from app.core.config import Settings


def test_default_settings():
    s = Settings()
    assert s.APP_NAME == "VERIQ"
    assert s.TAGLINE == "Code is generated. Proof is earned."
    assert s.MAX_REPAIR_ATTEMPTS >= 1
    assert s.MAX_EXECUTION_SECONDS > 0
    assert s.MAX_PATCH_BYTES == 50000
    assert s.MAX_PATCH_FILES == 10


def test_live_inference_detection():
    s = Settings(NEBIUS_API_KEY="", ENABLE_LIVE_INFERENCE=False)
    assert not s.is_live_inference_configured

    s2 = Settings(NEBIUS_API_KEY="test_key", ENABLE_LIVE_INFERENCE=True)
    assert s2.is_live_inference_configured

    s3 = Settings(NEBIUS_API_KEY="test_key", ENABLE_LIVE_INFERENCE=False)
    assert not s3.is_live_inference_configured
