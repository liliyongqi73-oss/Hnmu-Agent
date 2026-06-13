"""用户认证、密码安全与 JWT 服务。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os

import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config import settings

from ..models.user import User
from ..schemas.auth import RegisterRequest


def hash_password(password: str) -> str:
    """使用 PBKDF2-SHA256 哈希用户密码。

    Args:
        password: 用户明文密码。

    Returns:
        包含算法、迭代次数、盐和摘要的密码哈希。
    """
    iterations = 600_000
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """验证用户密码。

    Args:
        password: 待验证明文密码。
        password_hash: 数据库密码哈希。

    Returns:
        密码是否匹配。
    """
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            bytes.fromhex(salt),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> str:
    """创建用户 JWT 访问令牌。

    Args:
        user: 当前用户。

    Returns:
        JWT 字符串。
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.auth_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user.id), "role": user.role, "exp": expires_at},
        settings.auth_secret_key,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> int | None:
    """解析 JWT 并返回用户编号。

    Args:
        token: JWT 字符串。

    Returns:
        用户编号；令牌无效时返回 None。
    """
    try:
        payload = jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def create_user(database: Session, request: RegisterRequest) -> User:
    """创建用户，首个注册用户自动成为管理员。

    Args:
        database: 数据库会话。
        request: 注册请求。

    Returns:
        新用户。
    """
    user_count = database.scalar(select(func.count(User.id))) or 0
    user = User(
        username=request.username,
        display_name=request.display_name,
        password_hash=hash_password(request.password),
        role="admin" if user_count == 0 else "user",
    )
    database.add(user)
    database.commit()
    database.refresh(user)
    return user
