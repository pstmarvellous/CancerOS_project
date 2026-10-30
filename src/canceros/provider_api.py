"""Project-scoped capability discovery; no generic model invocation endpoint."""

from uuid import UUID

from fastapi import APIRouter, Header

from canceros.identity import authenticate, authorize_project
from canceros.provider_contracts import ProviderCapabilities


def provider_routes(config, memberships):
    router = APIRouter(prefix="/api/v1/projects/{project_id}/ai")

    @router.get("/capabilities", response_model=ProviderCapabilities)
    def capabilities(project_id: UUID, authorization: str | None = Header(default=None)):
        identity = authenticate(authorization, config, memberships)
        authorize_project(identity, project_id)
        return ProviderCapabilities()

    return router
