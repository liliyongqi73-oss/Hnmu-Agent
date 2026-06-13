"""MySQL 数据库连接与会话管理。"""
from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式模型基类。"""


def get_db() -> Generator[Session, None, None]:
    """提供单次请求使用的数据库会话。

    Yields:
        SQLAlchemy 数据库会话。
    """
    database = SessionLocal()
    try:
        database.execute(text("SELECT 1"))
        yield database
    except SQLAlchemyError as error:
        database.rollback()
        raise HTTPException(status_code=503, detail="MySQL 数据库未连接，请检查 DATABASE_URL") from error
    finally:
        database.close()


def initialize_database() -> None:
    """创建应用数据库表。

    Returns:
        None。
    """
    from ..models import user  # noqa: F401  导入模型以注册表结构
    from ..services.auth_service import ensure_bootstrap_admin

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as error:
        if "Unknown database" not in str(error):
            raise
        database_url = make_url(settings.database_url)
        database_name = database_url.database
        if not database_name or not database_name.replace("_", "").isalnum():
            raise
        server_engine = create_engine(database_url.set(database=None), pool_pre_ping=True)
        with server_engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as database:
        ensure_bootstrap_admin(database)


def database_health() -> tuple[bool, str]:
    """检测 MySQL 连接状态。

    Returns:
        是否可连接与状态说明。
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "connected"
    except Exception:  # noqa: BLE001  健康检查只暴露安全状态，不返回数据库凭据
        return False, "unavailable"
