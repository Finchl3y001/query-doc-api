from enum import Enum
from fastapi import Depends, HTTPException, status
from sqlmodel import SQLModel

class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"

class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

        def __call__(self, current_user: User = Depends(get_current_user)):
            if current_user.role not in self.allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail= "You do not have permission to access this resource"
                )
            return current_user