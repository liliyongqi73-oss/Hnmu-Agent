"""管理员用户与角色管理接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.user import User
from ...schemas.auth import UserInfo, UserRoleRequest
from ..dependencies import require_admin

router = APIRouter()


@router.get("", response_model=list[UserInfo])
def users(
    database: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[User]:
    """返回全部用户。

    Args:
        database: 数据库会话。

    Returns:
        用户列表。
    """
    return list(database.scalars(select(User).order_by(User.created_at.desc())))


@router.put("/{user_id}", response_model=UserInfo)
def update_user(
    user_id: int,
    request: UserRoleRequest,
    database: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    """更新用户角色与启用状态。

    Args:
        user_id: 用户编号。
        request: 角色与状态。
        database: 数据库会话。

    Returns:
        更新后的用户。
    """
    user = database.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id and (request.role != "admin" or not request.is_active):
        raise HTTPException(status_code=400, detail="不能停用或降级当前管理员账号")
    user.role = request.role
    user.is_active = request.is_active
    database.commit()
    database.refresh(user)
    return user
