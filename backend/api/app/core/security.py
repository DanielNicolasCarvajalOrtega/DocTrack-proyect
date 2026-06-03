import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.core.config import settings
from app.core.database import get_db
from app.modules.users.models import User
from sqlalchemy.orm import Session
from app.core.config import settings
import logging
from uuid import UUID

"""
dependecias (FastAPI) para validacion de JWT y obtencion del usuario autenticado
uso en cualquier endpoint con el metodo -> get_current_user
variables de entorno requeridas:
- SECRET_KEY
- ALGORITHM
"""

logger = logging.getLogger(__name__)

# Beader token, extrae el JWT del header: Authorization: Beader <token>
_bearer_schema = HTTPBearer(auto_error=True)

def create_access_token(user_id:UUID, expires_minutes: int = 60) -> str:
    """
    Genera un JWT de acceso.
    Payload:
      sub  → user_id (sujeto del token)
      exp  → fecha de expiración
      iat  → fecha de emisión
      type → "access" (diferencia de refresh tokens)
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "exp": now + timedelta(minutes=expires_minutes),
        "iat": now,
        "type": "access"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm = settings.ALGORITHM)


def create_refresh_token(user_id:UUID,expires_days: int = 30) -> str:
    """
    genera un JWT de refresco (larga duración)
    se usa para obtener un nuevo access token sin re-login.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "exp": now + timedelta(minutes=expires_days),
        "iat": now,
        "type": "refresh"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm = settings.ALGORITHM)


def hash_password(password: str) -> str:
    # Bcrypt requiere bytes, así que codificamos el string
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    # Devolvemos un string para guardarlo en la base de datos
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)





def _decode_token(token: str) -> dict:
    """
    decodifica y valida un JWT.
 
    raises:
      HTTPException 401 -> token expirado
      HTTPException 401 -> token inválido o malformado
    """
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "la session expiro.",
            headers= {"WWW-Authenticate": "Bearer"}
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "token invalido",
            headers = {"WWW-Authenticate": "Bearer"}
        )


def _extract_user_id(payload:dict) -> UUID:
    # extrae el user_id del payload desde el token
    # HTTPException si el payload no contiene el "sub" o no es un UUID valido

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail = "no autorizado"
        ) 
    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "token invalido"
        )

# dependencias FastAPI
def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer_schema), 
        db:Session = Depends(get_db)) -> User:

    """
    dependencias principal de autenticacion
    -- flujo --
    extrae el Bearer token del header
    decodifica y valida el JWT
    extrae el user_id del payload
    verifica que el token es de tipo "access" 
    busca el usuaroi en la DB
    finalmente verifica que el usuario esta activo
    RETORNA el objeto User autenticado

    HTTP 401 -> token invalido, expirado o usuario no encontrado
    HTTP 303 -> usuario inactivo
    """
    payload = _decode_token(credentials.credentials)
    
    # guard -> verificar que es el access token, no un refresh token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "token invalido u expirado",
            headers = {"WWW-Authenticate": "Beader"}
        )
    
    user_id = _extract_user_id(payload)

    # Buscar usuario en DB
    user = db.query(User).filter(
        User.id == user_id,
    ).first()

    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail= "usuario no encontrado",
            headers = {"WWW-Authenticate": "Bearer"}
        )
    
    # guard -> usuario inactivo 
    if not user.is_active:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail= "cuenta desactivada, usuario inactivo",
        )
    return user


def get_current_user_admin(current_user:User = Depends(get_current_user)) -> User:
    """
    dependencias para endpoint exclusivos de super admin
    usada en endpoints de administracion del sistema 
    Ejemplo:
      @router.get("/admin/companies")
    """
    
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail = "ne eres usuario autorizado para esta view"
        )
    return current_user