"""Private settings; validation errors must never serialize supplied secrets."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    mode: Literal["development", "test", "staging", "production"] = "development"
    database_url: SecretStr | None = None
    queue_url: SecretStr | None = None
    storage_endpoint: str | None = None
    storage_access_key: SecretStr | None = None
    storage_secret_key: SecretStr | None = None
    storage_bucket: str = "canceros-private"
    monitor_token: SecretStr | None = None
    cors_origins: list[str] = ["http://127.0.0.1:3000"]
    identity_issuer: str = "canceros-local"
    identity_audience: str = "canceros-api"
    identity_public_key: str | None = None
    identity_public_key_file: str | None = None
    linkage_keys: dict[str, SecretStr] = {}
    linkage_active_key: str | None = None
    external_inference_enabled: bool = False
    model_api_key: SecretStr | None = None
    model_provider: str = "meta"
    model_identifier: str = "muse-spark-1.3"
    export_policy_path: str | None = None
    request_limit_bytes: int = 1048576
    artifact_limit_bytes: int = 1048576
    job_max_attempts: int = 3
    dependency_timeout_seconds: int = 3

    @model_validator(mode="after")
    def enforce_modes(self):
        import base64
        import re

        if bool(self.linkage_keys) != bool(self.linkage_active_key):
            raise ValueError("Linkage requires a key ring and active key version")
        if self.linkage_active_key and self.linkage_active_key not in self.linkage_keys:
            raise ValueError("Active linkage key is not installed")
        for version, secret in self.linkage_keys.items():
            try:
                decoded = base64.b64decode(secret.get_secret_value(), validate=True)
            except (ValueError, TypeError):
                raise ValueError("Invalid private linkage key encoding") from None
            if len(decoded) != 32 or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", version):
                raise ValueError("Linkage requires named 256-bit keys")
        for value, schemes in (
            (self.database_url, ("postgresql+psycopg", "postgresql")),
            (self.queue_url, ("redis", "rediss")),
        ):
            if value:
                parsed = urlparse(value.get_secret_value())
                if parsed.scheme not in schemes or not parsed.hostname:
                    raise ValueError("Invalid private service URL")
        if self.storage_endpoint:
            parsed = urlparse(self.storage_endpoint)
            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError("Invalid private storage endpoint")
        if (
            not 1 <= self.job_max_attempts <= 3
            or not 1 <= self.request_limit_bytes <= 1048576
            or not 1 <= self.artifact_limit_bytes <= 10485760
        ):
            raise ValueError("Invalid bounded engineering limits")
        if not 1 <= self.dependency_timeout_seconds <= 30:
            raise ValueError("Invalid dependency timeout")
        if self.mode in ("staging", "production"):
            if not all(
                (
                    self.database_url,
                    self.queue_url,
                    self.storage_endpoint,
                    self.storage_access_key,
                    self.storage_secret_key,
                    self.monitor_token,
                    self.identity_public_key
                    or (
                        self.identity_public_key_file
                        and Path(self.identity_public_key_file).is_file()
                    ),
                )
            ):
                raise ValueError(
                    "Deployment requires private dependencies and trusted identity configuration"
                )
            if any(
                "*" in origin or not origin.startswith("https://") for origin in self.cors_origins
            ) or not self.identity_issuer.startswith("https://"):
                raise ValueError("Deployment requires explicit origins and trusted HTTPS issuer")
        if self.external_inference_enabled:
            from canceros.export import verified_policy

            try:
                verified_policy(self)
            except PermissionError:
                raise ValueError(
                    "External inference requires verified versioned permission policy and private credentials"
                ) from None
        return self
