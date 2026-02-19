from contextvars import ContextVar
from uuid import UUID
from typing import Optional

current_company_id = ContextVar[Optional[UUID]] = ContextVar(
    "current_company_id", default=None
)

# ESTABLECE LA EMPRESA ACTUAL DENTRO DEL REQUEST
def set_current_company(company_id: UUID):
    current_company_id.set(company_id)


def get_current_company() -> Optional[UUID]:
    return current_company_id.get()

def clear_current_company():
    current_company_id.set(None)

    
