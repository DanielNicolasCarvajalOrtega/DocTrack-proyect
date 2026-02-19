from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.security import decode_token
from app.modules.users.repository.repository import UserRepository
from app.modules.users.models import User
from app.modules.compañias.models import CompanyUser, CompanyRole
from typing import Optional
from app.core.tenat import set_current_company, get_current_company

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
        token:str = Depends(oauth2_scheme),
        db:Session = Depends(get_db)
        )-> User:
    
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Credenciales invalidas",
        headers= {"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception
    except ValueError:
        raise credentials_exception
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if user is None or not user.is_active:
        raise credentials_exception
    return user

def require_roles(*roles:str):
    def role_cheker(current_user: User= Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta accion"
            )
        return current_user
    return role_cheker


async def get_company_context(
        company_id: Optional[str] = Header(None),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
) -> UUID:
    
    """
    EXTRAE Y VALIDA EL ID DEL HEADER
    ESTABLECE UN CONTEXTO PARA USO EN QUERIEs
    """

    if current_user.is_super_admin and company_id:
        get_company_id = UUID(company_id)
        set_current_company(get_company_id)
        return get_company_id
    
    if not company_id:
        company_user = (
            db.query(CompanyUser)
            .filter(
                CompanyUser.user_id == current_user.id,
                CompanyUser.is_active == True
            ).first()
        )
        if not company_user:
            raise HTTPException(403, "Usuario sin empresa asignada")
        company_id = company_user.company_id
    else:
        company_id = UUID(get_company_id)

        # VERIFICA QUE EL USUARIO PERTENECE A LA EMPRESA

        company_user = (
            db.query(CompanyUser)
            .filter(
                CompanyUser.user_id == current_user.id,
                CompanyUser.company_id == company_id,
                CompanyUser.is_active == True
            ).first()
        )

        if not company_user:
            raise HTTPException(403, "Sin acceso a esta empresa")
        
    set_current_company(company_id)
    return company_id


    

            
