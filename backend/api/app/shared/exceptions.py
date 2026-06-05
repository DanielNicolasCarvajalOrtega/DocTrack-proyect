from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

class AppException(Exception):
    def __init__(self, status_code: int, detail:str):
        self.status_code = status_code
        self.detail = detail

class NotFoundException(AppException):
    def __init__(self, resource:str):
        super().__init__(404,f"{resource} no encontrado")

class ConflictException(AppException):
    def __init__(self, detail:str):
        super().__init__(409, detail)
    
class ForbiddenException(AppException):
    def __init__(self):
        super().__init__(403, "Acceso denegado")

async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status":"error"}
    )

async def validation_exception_handler(request:Request, exc: RequestValidationError):
    errors = [ ]

    for error in exc.errors():
        errors.append({
            "field": "-> ".join(str(e) for e in error["loc"]),
            "message": error["msg"]
        })
    return JSONResponse(
        status_code=422,
        content={"detail":errors, "status":"validation_error"}
    )

