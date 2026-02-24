from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.shared.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler
)
from app.modules.plantas.router import router as plants_router
from app.modules.maquinas.router import router as machines_router
from app.modules.documentos.router import router as documents_router
from app.modules.mantenimiento.router import router as maintenance_router
from app.modules.users.router import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    prefix = "/api/v1"
    app.include_router(users_router, prefix=f"{prefix}/users", tags=["Users"])
    app.include_router(plants_router, prefix=f"{prefix}/plantas", tags=["Plants"])
    app.include_router(machines_router, prefix=f"{prefix}/maquinas", tags=["Machines"])
    app.include_router(documents_router, prefix=f"{prefix}/documentos", tags=["Documents"])
    app.include_router(maintenance_router, prefix=f"{prefix}/mantenimiento", tags=["Maintenance"])

    @app.get("/health")
    def health_check():
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT
        }

    return app


app = create_app()