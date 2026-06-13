"""认证与角色权限依赖。"""
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.user import User
from ..services.auth_service import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_authenticated_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """校验 Bearer 令牌并返回用户编号。

    Args:
        credentials: Bearer 令牌。

    Returns:
        令牌中的用户编号。
    """
    user_id = decode_access_token(credentials.credentials) if credentials else None
    if not user_id:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    return user_id


def get_current_user(
    user_id: int = Depends(get_authenticated_user_id),
    database: Session = Depends(get_db),
) -> User:
    """读取并校验当前登录用户。

    Args:
        user_id: 已通过令牌校验的用户编号。
        database: 数据库会话。

    Returns:
        当前用户。
    """
    user = database.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """要求当前用户拥有管理员角色。

    Args:
        user: 当前用户。

    Returns:
        管理员用户。
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="当前账号没有管理员权限")
    return user
