"""Bounded evidence metadata and exact paragraph locators; never fetches URLs.

Manifest declarations do not authorize text use. Services must check current
source rights, scope, review and retraction before indexing or returning content.
"""

import hashlib
import ipaddress
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import AwareDatetime, ConfigDict, Field, SecretStr, field_validator, model_validator

from canceros.contracts import Contract, Hash

Code = Annotated[str, Field(strict=True, pattern=r"^[a-zA-Z0-9_.-]{1,64}$")]
Label = Annotated[str, Field(strict=True, min_length=1, max_length=500)]
NORMALIZATION_VERSION: Literal["unicode-nfc/1"] = "unicode-nfc/1"
MAX_TEXT_BYTES = 65536
MAX_PASSAGE_CODEPOINTS = 1000


def safe_evidence_url(value: str) -> str:
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or any(ord(char) <= 32 for char in value)
    ):
        raise ValueError("Public HTTPS citation URL without credentials or query required")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP addresses are not citation hosts")
    if (
        not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", host)
        or "." not in host
        or ".." in host
        or host.lower().endswith((".localhost", ".local", ".internal"))
        or any(
            label.startswith("-") or label.endswith("-") or len(label) > 63
            for label in host.split(".")
        )
    ):
        raise ValueError("Public citation hostname required")
    return value


def normalize_doi(value: str) -> str:
    value = value.strip()
    lowered = value.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if lowered.startswith(prefix):
            value = value[len(prefix) :].strip()
            break
    if not re.fullmatch(r"10\.[0-9]{4,9}/[-._;()/A-Za-z0-9:]+", value):
        raise ValueError("DOI metadata format required; resolution is not verified")
    return value.lower()


class EvidenceManifest(Contract):
    schema_version: Literal["evidence-source/1"] = "evidence-source/1"
    source_version_id: UUID
    title: Label
    publisher: Label
    authors: tuple[Label, ...] | None = Field(default=None, max_length=50)
    canonical_url: str = Field(strict=True, min_length=1, max_length=2000)
    doi: str | None = Field(default=None, max_length=250)
    publication_date: date | None = None
    publication_date_unknown_reason: Literal["not_available", "not_applicable"] | None = None
    update_date: date | None = None
    update_date_unknown_reason: Literal["not_available", "not_applicable"] | None = None
    retrieved_at: AwareDatetime
    document_version: Code
    topics: tuple[Code, ...] = Field(min_length=1, max_length=30)
    subtypes: tuple[Code, ...] = Field(default=(), max_length=30)
    settings: tuple[Code, ...] = Field(default=(), max_length=30)
    component_license_reference: Label
    permission_review_reference: Label
    attribution: Label
    content_mode: Literal["metadata_only", "approved_excerpt"]
    review_basis: Literal["synthetic_fixture", "documented_review"]
    retraction_status: Literal["clear", "unknown", "retracted"]

    @field_validator("canonical_url")
    @classmethod
    def citation_url(cls, value):
        return safe_evidence_url(value)

    @field_validator("doi")
    @classmethod
    def doi_metadata(cls, value):
        return normalize_doi(value) if value is not None else None

    @field_validator("publication_date", "update_date", mode="before")
    @classmethod
    def date_without_fabricated_timestamp(cls, value):
        if value is not None and (
            isinstance(value, datetime)
            or not isinstance(value, (str, date))
            or (isinstance(value, str) and len(value) != 10)
        ):
            raise ValueError("Source calendar date or explicit unknown required")
        return value

    @model_validator(mode="after")
    def consistent_metadata(self):
        if self.retrieved_at > datetime.now(timezone.utc):
            raise ValueError("Retrieval cannot be future dated")
        for value, reason in (
            (self.publication_date, self.publication_date_unknown_reason),
            (self.update_date, self.update_date_unknown_reason),
        ):
            if (value is None) != (reason is not None):
                raise ValueError("Missing dates require an explicit unknown reason")
            if value is not None and value > self.retrieved_at.date():
                raise ValueError("Source date cannot follow retrieval")
        if self.publication_date and self.update_date and self.update_date < self.publication_date:
            raise ValueError("Source update precedes publication")
        for codes in (self.topics, self.subtypes, self.settings):
            if len(codes) != len(set(codes)):
                raise ValueError("Duplicate topic or context tags")
        for label in (
            self.title,
            self.publisher,
            self.component_license_reference,
            self.permission_review_reference,
            self.attribution,
            *(self.authors or ()),
        ):
            if not label.strip():
                raise ValueError("Nonblank metadata required")
        return self


class EvidenceTextInput(Contract):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    manifest: EvidenceManifest
    media_type: Literal["text/plain"] = "text/plain"
    text: SecretStr = Field(
        repr=False, exclude=True, json_schema_extra={"writeOnly": True, "maxLength": 65536}
    )

    @model_validator(mode="after")
    def only_requested_text(self):
        if self.manifest.content_mode != "approved_excerpt":
            raise ValueError("Metadata-only imports cannot contain source text")
        value = self.text.get_secret_value()
        if not value.strip() or len(value.encode("utf-8", errors="strict")) > MAX_TEXT_BYTES:
            raise ValueError("Nonblank bounded UTF-8 text required")
        if "\x00" in value or value.lstrip().startswith(("%PDF-", "PK\x03\x04")):
            raise ValueError("Binary/PDF/archive extraction is unsupported")
        return self


class PreparedText(Contract):
    original_sha256: Hash
    normalized_sha256: Hash
    normalization_version: Literal["unicode-nfc/1"] = NORMALIZATION_VERSION
    unicode_version: str
    text: SecretStr = Field(repr=False, exclude=True, json_schema_extra={"writeOnly": True})


def prepare_text(value: EvidenceTextInput) -> PreparedText:
    # Recheck private input in case internal callers used an unvalidated model_copy.
    value = EvidenceTextInput.model_validate({**value.model_dump(), "text": value.text})
    raw = value.text.get_secret_value()
    normalized = unicodedata.normalize("NFC", raw)
    return PreparedText(
        original_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        normalized_sha256=hashlib.sha256(normalized.encode()).hexdigest(),
        unicode_version=unicodedata.unidata_version,
        text=SecretStr(normalized),
    )


class EvidenceSpan(Contract):
    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, ge=1)

    @model_validator(mode="after")
    def ordered(self):
        if not 0 < self.end - self.start <= MAX_PASSAGE_CODEPOINTS:
            raise ValueError("A complete passage must fit the code-point budget")
        return self


class PassageDescriptor(Contract):
    id: UUID
    document_fingerprint: Hash
    span: EvidenceSpan
    text_sha256: Hash
    normalization_version: Literal["unicode-nfc/1"] = NORMALIZATION_VERSION
    index_configuration: Literal["english"] = "english"
    locator_kind: Literal["normalized_text_codepoints"] = "normalized_text_codepoints"


def build_passages(
    project_id: UUID, document_fingerprint: str, normalized_text: str
) -> tuple[PassageDescriptor, ...]:
    if (
        unicodedata.normalize("NFC", normalized_text) != normalized_text
        or len(normalized_text.encode("utf-8", errors="strict")) > MAX_TEXT_BYTES
    ):
        raise ValueError("Bounded normalized text required")
    passages = []
    start = 0
    separators = [(m.start(), m.end()) for m in re.finditer(r"\r?\n[ \t]*\r?\n", normalized_text)]
    for end, following in [*separators, (len(normalized_text), len(normalized_text))]:
        raw = normalized_text[start:end]
        paragraph = raw.strip()
        if paragraph:
            offset = start + len(raw) - len(raw.lstrip())
            span = EvidenceSpan(start=offset, end=offset + len(paragraph))
            digest = hashlib.sha256(paragraph.encode()).hexdigest()
            identifier = uuid5(
                NAMESPACE_URL,
                f"canceros:evidence-passage/1:{project_id}:{document_fingerprint}:{span.start}:{span.end}:{digest}",
            )
            passages.append(
                PassageDescriptor(
                    id=identifier,
                    document_fingerprint=document_fingerprint,
                    span=span,
                    text_sha256=digest,
                )
            )
        start = following
    if not passages or len(passages) > 50:
        raise ValueError("One to fifty complete paragraphs required")
    return tuple(passages)


def resolve_passage_text(normalized_text: str, passage: PassageDescriptor) -> str:
    if unicodedata.normalize("NFC", normalized_text) != normalized_text or passage.span.end > len(
        normalized_text
    ):
        raise ValueError("Exact normalized passage source required")
    value = normalized_text[passage.span.start : passage.span.end]
    if hashlib.sha256(value.encode()).hexdigest() != passage.text_sha256:
        raise ValueError("Passage text hash mismatch")
    return value


def evidence_document_fingerprint(
    manifest: EvidenceManifest, original_sha256: str | None = None
) -> str:
    if original_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", original_sha256):
        raise ValueError("Server-computed content SHA256 required")
    if (manifest.content_mode == "approved_excerpt") != (original_sha256 is not None):
        raise ValueError("Content hash must match the requested import mode")
    value = {"manifest": manifest.model_dump(mode="json"), "original_sha256": original_sha256}
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class CorpusBuildInput(Contract):
    document_ids: tuple[UUID, ...] = Field(min_length=1, max_length=50)
    expected_activation_id: UUID | None = None
    index_configuration: Literal["english"] = "english"

    @model_validator(mode="after")
    def unique_documents(self):
        if len(self.document_ids) != len(set(self.document_ids)):
            raise ValueError("Duplicate corpus document IDs")
        return self
