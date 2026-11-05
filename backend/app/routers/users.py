"""User management endpoints. Admins only: every route below needs the admin role."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserAdminOut, UserAdminUpdate
from app.services import user_service

require_admin = require_roles(UserRole.ADMIN)

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserAdminOut])
def list_users(db: Session = Depends(get_db)) -> list[UserAdminOut]:
    return user_service.list_users(db)


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: int,
    data: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserAdminOut:
    """Change a user's role and/or active status. Admins may not do either to themselves."""
    target = user_service.get_user_or_404(db, user_id)
    user_service.update_user(db, target, data, admin=admin)
    return user_service.get_user_out(db, target.id)
