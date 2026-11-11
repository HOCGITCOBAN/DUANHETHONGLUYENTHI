import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from app.admin import admin_router
from app.database import get_database_url, make_engine
from app.routes import router, subjects_router

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "SmartExam_Frontend" / "dist"


def create_app(database_url: str | None = None) -> FastAPI:
    engine = make_engine(database_url or get_database_url())

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="SmartExam — Đăng ký sinh viên",
        version="1.0.0",
        description="US-01: đăng ký tài khoản với quyền student.",
        lifespan=lifespan,
    )
    application.state.engine = engine
    application.state.session_factory = sessionmaker(bind=engine)
    application.include_router(router)
    application.include_router(subjects_router)
    application.include_router(admin_router)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500"
            ).split(",")
            if origin.strip()
        ],
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's default validation error includes raw inputs, possibly passwords.
        errors = [
            {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @application.middleware("http")
    async def prevent_auth_caching(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/auth/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.get("/config.js", include_in_schema=False)
    def frontend_api_config() -> Response:
        return Response(
            "window.SMARTEXAM_CONFIG = { mode: 'api', baseUrl: '' };\n",
            media_type="application/javascript",
            headers={"Cache-Control": "no-store"},
        )

    application.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

    return application


app = create_app()
