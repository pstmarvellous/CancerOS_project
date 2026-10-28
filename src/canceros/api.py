"""Minimal truthful HTTP surface; domain capabilities are not scaffold successes."""

import hmac
import json
import logging
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from canceros.clinical_api import clinical_routes
from canceros.contracts import FoundationStatus, Health, Me, Problem, ProjectRole
from canceros.evaluation_api import evaluation_routes
from canceros.identity import SQLMemberships, authenticate, authorize_project
from canceros.imaging_api import imaging_routes
from canceros.patient_api import patient_routes
from canceros.readiness import dependencies_ready
from canceros.settings import Settings
from canceros.source_api import source_routes
from canceros.state_api import state_routes

LOG = logging.getLogger("canceros.requests")


def create_app(settings: Settings | None = None, membership_repository=None) -> FastAPI:
    config = settings or Settings()
    if membership_repository is not None and config.mode != "test":
        raise ValueError("Injected identity repositories are test-only")
    app = FastAPI(title="CancerOS foundation", version="0.1.0", docs_url=None, redoc_url=None)
    app.openapi_version = "3.1.1"
    app.state.settings = config
    memberships = (
        membership_repository if membership_repository is not None else SQLMemberships(config)
    )
    app.state.readiness_check = lambda: dependencies_ready(config)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def safe_request(request: Request, call_next):
        request.state.request_id = str(uuid4())
        try:
            if int(request.headers.get("content-length", "0")) > config.request_limit_bytes:
                response = problem(request, 413, "PAYLOAD_TOO_LARGE")
            else:
                response = await call_next(request)
        except Exception:
            # Never serialize arbitrary exception messages or input into logs/responses.
            response = problem(request, 500, "INTERNAL_ERROR")
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        LOG.info(
            json.dumps(
                {
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "status": response.status_code,
                }
            )
        )
        return response

    def problem(request: Request, status: int, code: str, errors=None):
        return JSONResponse(
            status_code=status,
            media_type="application/problem+json",
            content=Problem(
                title=code.replace("_", " ").title(),
                status=status,
                code=code,
                request_id=request.state.request_id,
                errors=errors or [],
            ).model_dump(mode="json"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        safe_codes = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            422: "FAILED_SCHEMA",
            503: "DEPENDENCY_UNAVAILABLE",
        }
        return problem(
            request, exc.status_code, safe_codes.get(exc.status_code, "REQUEST_REJECTED")
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        schema = app.openapi()
        known = {"body", "path", "query", "header", "cookie"}
        for model in schema.get("components", {}).get("schemas", {}).values():
            known.update(model.get("properties", {}))
        for path in schema["paths"].values():
            for operation in path.values():
                if isinstance(operation, dict):
                    known.update(p["name"] for p in operation.get("parameters", []))
        errors = [
            "/"
            + "/".join(
                str(v) if isinstance(v, int) or v in known else "field" for v in error["loc"]
            )
            for error in exc.errors()
        ]
        return problem(
            request,
            422,
            "FAILED_SCHEMA",
            errors,
        )

    @app.get("/health/live", response_model=Health)
    def live():
        return Health()

    @app.get("/api/v1/me", response_model=Me)
    def me(authorization: str | None = Header(default=None)):
        identity = authenticate(authorization, config, memberships)
        return Me(
            user_id=identity.user_id,
            project_roles=[
                ProjectRole.model_validate({"project_id": p, "role": r})
                for p, r in identity.memberships.items()
            ],
        )

    @app.get("/api/v1/projects/{project_id}/foundation/status", response_model=FoundationStatus)
    def foundation(project_id: UUID, authorization: str | None = Header(default=None)):
        identity = authenticate(authorization, config, memberships)
        authorize_project(identity, project_id)
        return FoundationStatus()

    @app.get("/health/ready", response_model=Health)
    def ready(authorization: str | None = Header(default=None)):
        if not config.monitor_token or not hmac.compare_digest(
            authorization or "", "Bearer " + config.monitor_token.get_secret_value()
        ):
            raise HTTPException(401)
        # Real checks are wired by COS-012/013; missing integration fails closed.
        checker = getattr(app.state, "readiness_check", None)
        if checker is None or not checker():
            raise HTTPException(503)
        return Health()

    app.include_router(source_routes(config, memberships))
    app.include_router(patient_routes(config, memberships))
    app.include_router(clinical_routes(config, memberships))
    app.include_router(evaluation_routes(config, memberships))
    app.include_router(imaging_routes(config, memberships))
    app.include_router(state_routes(config, memberships))
    return app
