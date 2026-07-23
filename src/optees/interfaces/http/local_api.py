from __future__ import annotations

import hmac
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from optees.application.contracts.batch import (
    BatchItemRequest,
    BatchRequest,
    BatchSnapshot,
)
from optees.application.contracts.errors import ErrorCode, ErrorDetail, StructuredError
from optees.application.contracts.job import JobSnapshot
from optees.application.contracts.json_value import require_json_value
from optees.application.services.local_job_service import LocalJobService
from optees.composition.local_agent import create_local_job_service
from optees.core.version import get_app_version


API_VERSION = "v1"
DEFAULT_MAX_REQUEST_BYTES = 1_048_576
LOOPBACK_HOST = "127.0.0.1"


class ProblemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str = Field(min_length=1)
    problem: dict[str, Any]


class CancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BatchProblemItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_item_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    problem: dict[str, Any]


class BatchProblemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(pattern="^1$")
    items: list[BatchProblemItemRequest] = Field(min_length=1, max_length=32)


class RequestGuardMiddleware:
    """Reject non-JSON and oversized mutation requests before body parsing."""

    def __init__(self, app, *, max_request_bytes: int) -> None:
        self.app = app
        self.max_request_bytes = max_request_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", ())
        }
        request_id = _normalized_request_id(headers.get("x-request-id"))
        media_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            await _send_guard_error(
                scope,
                send,
                status_code=415,
                code=ErrorCode.INVALID_REQUEST,
                message="Mutation endpoints require Content-Type application/json.",
                request_id=request_id,
            )
            return
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_request_bytes:
                    await _send_guard_error(
                        scope,
                        send,
                        status_code=413,
                        code=ErrorCode.INVALID_REQUEST,
                        message="The JSON request body exceeds the configured size limit.",
                        request_id=request_id,
                    )
                    return
            except ValueError:
                await _send_guard_error(
                    scope,
                    send,
                    status_code=400,
                    code=ErrorCode.INVALID_REQUEST,
                    message="Content-Length must be an integer.",
                    request_id=request_id,
                )
                return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_request_bytes:
                await _send_guard_error(
                    scope,
                    send,
                    status_code=413,
                    code=ErrorCode.INVALID_REQUEST,
                    message="The JSON request body exceeds the configured size limit.",
                    request_id=request_id,
                )
                return
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay():
            nonlocal delivered
            if delivered:
                return {"type": "http.request", "body": b"", "more_body": False}
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)


def create_local_api(
    *,
    token: str,
    job_service: LocalJobService | None = None,
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES,
    shutdown_job_service: bool = True,
) -> FastAPI:
    """Create the authenticated loopback API without starting a server."""

    normalized_token = str(token or "")
    if len(normalized_token) < 32:
        raise ValueError("local API bearer token must contain at least 32 characters")
    if (
        isinstance(max_request_bytes, bool)
        or not isinstance(max_request_bytes, int)
        or max_request_bytes < 1
    ):
        raise ValueError("max_request_bytes must be a positive integer")
    service = job_service or create_local_job_service()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if shutdown_job_service:
            service.shutdown(wait=True, cancel_pending=True)

    app = FastAPI(
        title="Optees Local Solver API",
        version=get_app_version(),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        RequestGuardMiddleware,
        max_request_bytes=max_request_bytes,
    )
    bearer = HTTPBearer(auto_error=False)

    async def require_token(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> None:
        supplied = credentials.credentials if credentials is not None else ""
        scheme = credentials.scheme if credentials is not None else ""
        if scheme.lower() != "bearer" or not hmac.compare_digest(
            supplied,
            normalized_token,
        ):
            raise _ApiError(
                status_code=401,
                error=StructuredError(
                    code=ErrorCode.AUTHENTICATION_FAILED,
                    message="A valid bearer token is required.",
                    request_id=_request_id(request),
                ),
                headers={"WWW-Authenticate": "Bearer"},
            )

    protected = [Depends(require_token)]

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = (
            _normalized_request_id(request.headers.get("X-Request-ID"))
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(_ApiError)
    async def api_error_handler(request: Request, exc: _ApiError):
        error = exc.error
        if error.request_id is None:
            error = replace(error, request_id=_request_id(request))
        return JSONResponse(
            status_code=exc.status_code,
            content=error.to_dict(),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        details = tuple(
            ErrorDetail(
                path=_validation_path(error.get("loc", ())),
                message=str(error.get("msg", "Invalid request value.")),
                code=str(error.get("type", "invalid_value")),
            )
            for error in exc.errors()
        )
        error = StructuredError(
            code=ErrorCode.INVALID_REQUEST,
            message="The HTTP request does not match the API contract.",
            request_id=_request_id(request),
            details=details,
        )
        return JSONResponse(status_code=422, content=error.to_dict())

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, _exc: Exception):
        error = StructuredError(
            code=ErrorCode.INTERNAL_ERROR,
            message="The local API failed to process the request.",
            request_id=_request_id(request),
        )
        return JSONResponse(status_code=500, content=error.to_dict())

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {"status": "ok", "api_version": API_VERSION}

    @app.get("/api/v1/info", dependencies=protected)
    async def info() -> dict[str, object]:
        return {
            "name": "Optees Local Solver API",
            "optees_version": get_app_version(),
            "api_version": API_VERSION,
            "bind_scope": "loopback_only",
            "persistent_jobs": False,
        }

    @app.get("/api/v1/capabilities", dependencies=protected)
    async def capabilities() -> dict[str, object]:
        return {"capabilities": list(service.list_capabilities())}

    @app.get("/api/v1/capabilities/{capability_id}", dependencies=protected)
    async def capability(capability_id: str, request: Request):
        descriptor = next(
            (
                item
                for item in service.list_capabilities()
                if item["id"] == capability_id
            ),
            None,
        )
        if descriptor is None:
            _raise_structured(
                StructuredError(
                    code=ErrorCode.CAPABILITY_NOT_FOUND,
                    message=f"Capability '{capability_id}' is not registered.",
                    request_id=_request_id(request),
                    context={"capability_id": capability_id},
                )
            )
        return descriptor

    @app.post("/api/v1/problems/validate", dependencies=protected)
    async def validate_problem(
        body: ProblemRequest,
        request: Request,
    ):
        outcome = service.validate(
            body.capability_id,
            body.problem,
            request_id=_request_id(request),
        )
        if isinstance(outcome, StructuredError):
            _raise_structured(outcome)
        return outcome.to_dict()

    @app.post("/api/v1/jobs", status_code=202, dependencies=protected)
    async def submit_job(
        body: ProblemRequest,
        request: Request,
    ):
        outcome = service.submit(
            body.capability_id,
            body.problem,
            request_id=_request_id(request),
        )
        return _job_or_raise(outcome)

    @app.get("/api/v1/jobs", dependencies=protected)
    async def jobs() -> dict[str, object]:
        return {"jobs": [job.to_dict() for job in service.list_jobs()]}

    @app.get("/api/v1/jobs/{job_id}", dependencies=protected)
    async def job(job_id: str):
        return _job_or_raise(service.get(job_id))

    @app.get("/api/v1/jobs/{job_id}/result", dependencies=protected)
    async def job_result(job_id: str):
        outcome = service.result(job_id)
        if isinstance(outcome, StructuredError):
            _raise_structured(outcome)
        return outcome.to_dict()

    @app.post("/api/v1/jobs/{job_id}/cancel", dependencies=protected)
    async def cancel_job(job_id: str, _body: CancelRequest):
        return _job_or_raise(service.cancel(job_id))

    @app.post("/api/v1/batches/validate", dependencies=protected)
    async def validate_batch(
        body: BatchProblemRequest,
        request: Request,
    ):
        batch = _batch_request(body, request_id=_request_id(request))
        return service.validate_batch(
            batch,
            request_id=_request_id(request),
        ).to_dict()

    @app.post("/api/v1/batches", status_code=202, dependencies=protected)
    async def submit_batch(
        body: BatchProblemRequest,
        request: Request,
    ):
        outcome = service.submit_batch(
            _batch_request(body, request_id=_request_id(request)),
            request_id=_request_id(request),
        )
        return _batch_or_raise(outcome)

    @app.get("/api/v1/batches/{batch_id}", dependencies=protected)
    async def batch(batch_id: str):
        return _batch_or_raise(service.get_batch(batch_id))

    @app.get("/api/v1/batches/{batch_id}/result", dependencies=protected)
    async def batch_result(batch_id: str):
        outcome = service.batch_result(batch_id)
        if isinstance(outcome, StructuredError):
            _raise_structured(outcome)
        return outcome.to_dict()

    @app.post("/api/v1/batches/{batch_id}/cancel", dependencies=protected)
    async def cancel_batch(batch_id: str, _body: CancelRequest):
        return _batch_or_raise(service.cancel_batch(batch_id))

    @app.get("/api/v1/openapi.json", dependencies=protected)
    async def openapi_document():
        return app.openapi()

    return app


def run_local_api(
    *,
    token: str,
    host: str = LOOPBACK_HOST,
    port: int = 8765,
    log_level: str = "warning",
) -> None:
    if host != LOOPBACK_HOST:
        raise ValueError("the local API may bind only to 127.0.0.1")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("port must be an integer in [1, 65535]")
    import uvicorn

    uvicorn.run(
        create_local_api(token=token),
        host=host,
        port=port,
        log_level=log_level,
    )


class _ApiError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        error: StructuredError,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(error.message)
        self.status_code = status_code
        self.error = error
        self.headers = headers or {}


def _job_or_raise(outcome: JobSnapshot | StructuredError) -> dict[str, object]:
    if isinstance(outcome, StructuredError):
        _raise_structured(outcome)
    return outcome.to_dict()


def _batch_or_raise(
    outcome: BatchSnapshot | StructuredError,
) -> dict[str, object]:
    if isinstance(outcome, StructuredError):
        _raise_structured(outcome)
    return outcome.to_dict()


def _batch_request(
    body: BatchProblemRequest,
    *,
    request_id: str,
) -> BatchRequest:
    try:
        items = []
        for item in body.items:
            problem = require_json_value(item.problem, path="$.batch.items[].problem")
            assert isinstance(problem, dict)
            items.append(
                BatchItemRequest(
                    client_item_id=item.client_item_id,
                    capability_id=item.capability_id,
                    problem=problem,
                )
            )
        return BatchRequest(tuple(items), version=body.version)
    except ValueError as exc:
        _raise_structured(
            StructuredError(
                code=ErrorCode.INVALID_REQUEST,
                message=str(exc),
                request_id=request_id,
            )
        )
        raise AssertionError("unreachable")


def _raise_structured(error: StructuredError) -> None:
    raise _ApiError(status_code=_status_code(error.code), error=error)


def _status_code(code: ErrorCode) -> int:
    return {
        ErrorCode.INVALID_REQUEST: 400,
        ErrorCode.AUTHENTICATION_FAILED: 401,
        ErrorCode.VALIDATION_FAILED: 422,
        ErrorCode.CAPABILITY_NOT_FOUND: 404,
        ErrorCode.DEPENDENCY_UNAVAILABLE: 503,
        ErrorCode.EXECUTION_FAILED: 500,
        ErrorCode.CANCELLATION_NOT_SUPPORTED: 409,
        ErrorCode.JOB_NOT_FOUND: 404,
        ErrorCode.JOB_RESULT_NOT_READY: 409,
        ErrorCode.JOB_RESULT_NOT_AVAILABLE: 409,
        ErrorCode.JOB_CAPACITY_EXCEEDED: 429,
        ErrorCode.BATCH_NOT_FOUND: 404,
        ErrorCode.BATCH_RESULT_NOT_READY: 409,
        ErrorCode.BATCH_CAPACITY_EXCEEDED: 429,
        ErrorCode.SERVICE_UNAVAILABLE: 503,
        ErrorCode.INTERNAL_ERROR: 500,
    }[code]


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or _normalized_request_id(
        request.headers.get("X-Request-ID")
    )


def _normalized_request_id(value: str | None) -> str:
    candidate = str(value or "").strip()
    if candidate and len(candidate) <= 128 and re.fullmatch(r"[A-Za-z0-9._:-]+", candidate):
        return candidate
    return f"request-{uuid4().hex}"


def _validation_path(location: tuple[object, ...]) -> str:
    return "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in location)


async def _send_guard_error(
    scope,
    send,
    *,
    status_code: int,
    code: ErrorCode,
    message: str,
    request_id: str,
) -> None:
    response = JSONResponse(
        status_code=status_code,
        content=StructuredError(
            code=code,
            message=message,
            request_id=request_id,
        ).to_dict(),
        headers={"X-Request-ID": request_id},
    )
    await response(scope, _empty_receive, send)


async def _empty_receive():
    return {"type": "http.request", "body": b"", "more_body": False}
