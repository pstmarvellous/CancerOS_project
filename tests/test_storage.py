from dataclasses import replace
from urllib.error import HTTPError
from urllib.request import urlopen
from uuid import uuid4

import pytest

from canceros.settings import Settings
from canceros.storage import PrivateStorage

pytestmark = pytest.mark.integration


def test_real_private_service_roundtrip_version_hash_and_denial():
    settings = Settings()
    storage = PrivateStorage(settings)
    storage.initialize_development_bucket()
    project = uuid4()
    artifact = storage.write_verified(
        project, b"CancerOS engineering-only byte fixture; no clinical data"
    )
    assert storage.read(artifact, project).startswith(b"CancerOS engineering-only")
    assert artifact.version and artifact.version != "null"
    with pytest.raises(PermissionError):
        storage.read(artifact, uuid4())
    with pytest.raises(ValueError):
        storage.read(replace(artifact, sha256="0" * 64), project)
    with pytest.raises(ValueError):
        storage.read_grant(artifact, project, 301)
    with pytest.raises(HTTPError) as error:
        urlopen(f"{settings.storage_endpoint}/{settings.storage_bucket}/{artifact.key}", timeout=3)
    assert error.value.code in (401, 403)
    # A valid short-lived authorized grant resolves; do not print or persist the URL.
    with urlopen(storage.read_grant(artifact, project), timeout=3) as response:
        assert response.read() == storage.read(artifact, project)
