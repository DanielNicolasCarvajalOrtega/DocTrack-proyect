import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan
from app.modules.compañias.services.company_service import CompanyService
from app.modules.compañias.schemas import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyUserResponse,
    SubsidiaryCreate,
    UserInvite,
    RoleUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/compania", tags=["Compañias"])

# crud

@router.post(
    "/",
    response_model=CompanyResponse,
    status_code= status.HTTP_201_CREATED,
    summary="Crear compañia raiz",
)
def crear_compañia_raiz(company_data:CompanyCreate, 
        db:Session = Depends(get_db),
        current_user: User= Depends(get_current_user)) -> Company:

    # la estructura y limites se aplican automaticamente segun el plan seleccionado
    try:
        company = CompanyService.crear_compañia(db, company_data.model_dump())
        logger.info(f"[Router] compañia creada id={company.id} by= {current_user.id}")
        return company
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[Router.crear_compañia_raiz] error inesperado - {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")