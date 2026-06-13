"""认证、用户与权限接口数据结构。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """用户注册请求。"""

    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """用户登录请求。"""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserInfo(BaseModel):
    """前端可见的用户信息。"""

    id: int
    username: str
    display_name: str
    role: Literal["admin", "user"]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """登录或注册成功响应。"""

    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class UserRoleRequest(BaseModel):
    """管理员修改用户角色请求。"""

    role: Literal["admin", "user"]
    is_active: bool
