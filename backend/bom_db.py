from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from runtime_paths import get_backend_base_dir


def _default_sqlite_url() -> str:
    database_path = (get_backend_base_dir() / "bom_system.db").resolve()
    return f"sqlite:///{database_path.as_posix()}"


def normalize_database_url(raw_url: str | None) -> str:
    value = str(raw_url or "").strip()
    if not value:
        return _default_sqlite_url()

    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)

    if value.startswith("postgresql://") and not value.startswith("postgresql+"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)

    return value


DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL"))
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=not IS_SQLITE,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)


if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_tables() -> None:
    # Import models lazily so metadata is fully registered before create_all.
    import bom_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_existing_schema()


def _migrate_existing_schema() -> None:
    migrations = {
        "products": {
            "product_image": "TEXT NOT NULL DEFAULT ''",
        },
        "quotations": {
            "discount_type": "VARCHAR(32) NOT NULL DEFAULT 'item-wise'",
            "discount_value": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "prepared_by": "VARCHAR(160) NOT NULL DEFAULT ''",
            "prepared_phone": "VARCHAR(60) NOT NULL DEFAULT ''",
        },
        "quotation_items": {
            "discount_percent": "NUMERIC(5, 2) NOT NULL DEFAULT 0",
            "room_name": "VARCHAR(120) NOT NULL DEFAULT ''",
            "product_image": "TEXT NOT NULL DEFAULT ''",
        },
    }

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name, columns in migrations.items():
            if not inspector.has_table(table_name):
                continue

            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))

        if inspector.has_table("quotation_items"):
            existing_columns = {column["name"] for column in inspector.get_columns("quotation_items")}
            if {"room", "room_name"}.issubset(existing_columns):
                connection.execute(
                    text(
                        "UPDATE quotation_items "
                        "SET room_name = COALESCE(NULLIF(room_name, ''), room, '')"
                    )
                )
            if {"image", "product_image"}.issubset(existing_columns):
                connection.execute(
                    text(
                        "UPDATE quotation_items "
                        "SET product_image = COALESCE(NULLIF(product_image, ''), image, '')"
                    )
                )
            if {"discount", "discount_percent"}.issubset(existing_columns):
                connection.execute(
                    text(
                        "UPDATE quotation_items "
                        "SET discount_percent = COALESCE(discount_percent, discount, 0)"
                    )
                )
