"""登录、注册与当前用户接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.user import User
from ...schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserInfo
from ...services.auth_service import create_access_token, create_user, verify_password
from ..dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest, database: Session = Depends(get_db)) -> AuthResponse:
    """注册新用户并直接登录。

    Args:
        request: 注册请求。
        database: 数据库会话。

    Returns:
        登录令牌与用户信息。
    """
    try:
        user = create_user(database, request)
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(status_code=409, detail="用户名已存在") from error
    return AuthResponse(access_token=create_access_token(user), user=user)


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, database: Session = Depends(get_db)) -> AuthResponse:
    """验证账号密码并签发令牌。

    Args:
        request: 登录请求。
        database: 数据库会话。

    Returns:
        登录令牌与用户信息。
    """
    user = database.scalar(select(User).where(User.username == request.username))
    if not user or not user.is_active or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return AuthResponse(access_token=create_access_token(user), user=user)


@router.get("/me", response_model=UserInfo)
def me(user: User = Depends(get_current_user)) -> User:
    """返回当前登录用户。

    Args:
        user: 当前用户。

    Returns:
        当前用户信息。
    """
    return user
