import pytest
from pydantic import ValidationError

from canceros.settings import Settings


def test_deployed_configuration_fails_closed_without_private_dependencies():
    with pytest.raises(ValidationError) as result:
        Settings(mode="production", model_api_key="artificial-secret-value", _env_file=None)
    assert "artificial-secret-value" not in str(result.value)


def test_secrets_redacted_and_inference_disabled_by_default():
    settings = Settings(mode="test", database_url="postgresql://artificial-secret", _env_file=None)
    assert "artificial-secret" not in settings.model_dump_json()
    assert settings.external_inference_enabled is False
