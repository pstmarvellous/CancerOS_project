"""RS256 bearer validation and database-backed project memberships; no auth bypass."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import jwt
from fastapi import HTTPException
from sqlalchemy import text

from canceros.persistence import engine_for
from canceros.settings import Settings


@dataclass(frozen=True)
class Identity:
    user_id: UUID
    memberships: dict[UUID, str]


class SQLMemberships:
    def __init__(self, config: Settings):
        self.config = config

    def resolve(self, issuer, subject):
        engine = engine_for(self.config)
        try:
            with engine.connect() as connection:
                user = connection.execute(
                    text("SELECT id FROM access.users WHERE issuer=:issuer AND subject=:subject"),
                    {"issuer": issuer, "subject": subject},
                ).one_or_none()
                if user is None:
                    raise HTTPException(401)
                memberships = connection.execute(
                    text("SELECT project_id,role FROM access.memberships WHERE user_id=:id"),
                    {"id": user.id},
                ).all()
                return Identity(user.id, {r.project_id: r.role for r in memberships})
        finally:
            engine.dispose()


def authenticate(header, config: Settings, repository) -> Identity:
    if not header or not header.startswith("Bearer "):
        raise HTTPException(401)
    key = config.identity_public_key
    if key is None and config.identity_public_key_file:
        try:
            key = Path(config.identity_public_key_file).read_text(encoding="utf-8")
        except OSError:
            raise HTTPException(401) from None
    if not key:
        raise HTTPException(401)
    try:
        claims = jwt.decode(
            header[7:],
            key,
            algorithms=["RS256"],
            issuer=config.identity_issuer,
            audience=config.identity_audience,
            options={"require": ["sub", "iss", "aud", "exp", "iat", "nbf"]},
            leeway=0,
        )
    except jwt.PyJWTError:
        raise HTTPException(401) from None
    # Role/project claims in the token cannot override database memberships.
    return repository.resolve(claims["iss"], claims["sub"])


def authorize_project(identity: Identity, project_id: UUID, minimum="viewer"):
    levels = {"viewer": 0, "editor": 1, "admin": 2}
    role = identity.memberships.get(project_id)
    if role is None:
        raise HTTPException(404)
    if levels.get(role, -1) < levels[minimum]:
        raise HTTPException(403)
