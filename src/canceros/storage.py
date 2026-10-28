"""Private version-aware S3 adapter. Keys are server-selected, never viewer input."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from canceros.settings import Settings


@dataclass(frozen=True)
class StoredObject:
    project_id: UUID
    key: str
    version: str
    sha256: str
    byte_size: int


class PrivateStorage:
    def __init__(self, config: Settings):
        if (
            not config.storage_endpoint
            or not config.storage_access_key
            or not config.storage_secret_key
        ):
            raise ValueError("Private storage configuration required")
        self.bucket = config.storage_bucket
        self.cap = config.artifact_limit_bytes
        self.client = boto3.client(
            "s3",
            endpoint_url=config.storage_endpoint,
            aws_access_key_id=config.storage_access_key.get_secret_value(),
            aws_secret_access_key=config.storage_secret_key.get_secret_value(),
            region_name="us-east-1",
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 1},
                connect_timeout=3,
                read_timeout=5,
            ),
        )

    def initialize_development_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as error:
            if error.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
                raise
            self.client.create_bucket(Bucket=self.bucket)
        self.client.put_bucket_versioning(
            Bucket=self.bucket, VersioningConfiguration={"Status": "Enabled"}
        )

    def write_verified(
        self, project_id: UUID, content: bytes, *, cleanup_scope=None
    ) -> StoredObject:
        if cleanup_scope not in (None, "engineering_fixture"):
            raise ValueError("INVALID_CLEANUP_SCOPE")
        if len(content) > self.cap:
            raise ValueError("ARTIFACT_TOO_LARGE")
        digest = hashlib.sha256(content).hexdigest()
        metadata = {"sha256": digest}
        if cleanup_scope:
            metadata.update(
                {
                    "cleanup-scope": cleanup_scope,
                    "owner-project": str(project_id),
                    "cleanup-created-at": datetime.now(timezone.utc).isoformat(),
                }
            )
        key = f"quarantined/{project_id}/{uuid4()}"
        response = self.client.put_object(
            Bucket=self.bucket, Key=key, Body=content, Metadata=metadata
        )
        version = response.get("VersionId")
        if not version or version == "null":
            raise ValueError("IMMUTABLE_STORAGE_VERSION_REQUIRED")
        read = self.client.get_object(Bucket=self.bucket, Key=key, VersionId=version)["Body"].read()
        if hashlib.sha256(read).hexdigest() != digest:
            raise ValueError("ARTIFACT_INTEGRITY_FAILURE")
        verified_key = f"verified/{project_id}/{uuid4()}"
        copied = self.client.copy_object(
            Bucket=self.bucket,
            Key=verified_key,
            CopySource={"Bucket": self.bucket, "Key": key, "VersionId": version},
        )
        verified_version = copied.get("VersionId")
        if not verified_version or verified_version == "null":
            raise ValueError("IMMUTABLE_STORAGE_VERSION_REQUIRED")
        result = StoredObject(project_id, verified_key, verified_version, digest, len(content))
        assert self.read(result, project_id) == content
        return result

    def read(self, artifact: StoredObject, authorized_project_id: UUID) -> bytes:
        if artifact.project_id != authorized_project_id or not artifact.key.startswith(
            f"verified/{authorized_project_id}/"
        ):
            raise PermissionError("CROSS_CONTEXT_REFERENCE")
        response = self.client.get_object(
            Bucket=self.bucket, Key=artifact.key, VersionId=artifact.version
        )
        value = response["Body"].read(self.cap + 1)
        if len(value) != artifact.byte_size or hashlib.sha256(value).hexdigest() != artifact.sha256:
            raise ValueError("ARTIFACT_INTEGRITY_FAILURE")
        return value

    def read_grant(self, artifact: StoredObject, authorized_project_id: UUID, expires_seconds=60):
        if not 1 <= expires_seconds <= 300:
            raise ValueError("INVALID_GRANT_EXPIRY")
        self.read(artifact, authorized_project_id)
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": artifact.key, "VersionId": artifact.version},
            ExpiresIn=expires_seconds,
        )
