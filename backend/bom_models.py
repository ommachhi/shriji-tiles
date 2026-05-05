from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bom_db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Client(TimestampMixin, Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(60), nullable=False, default="", index=True)
    email: Mapped[str] = mapped_column(String(160), nullable=False, default="", index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False, default="")

    quotations: Mapped[list["Quotation"]] = relationship(back_populates="client")


class ManagedProduct(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(120), nullable=False, default="Custom")
    category: Mapped[str] = mapped_column(String(120), nullable=False, default="General")
    product_image: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)


class Quotation(TimestampMixin, Base):
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    proposal_no: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    client_name: Mapped[str] = mapped_column(String(160), nullable=False)
    company: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    prepared_by: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    prepared_phone: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_type: Mapped[str] = mapped_column(String(32), nullable=False, default="item-wise")
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", index=True)
    watermark: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    client: Mapped[Client | None] = relationship(back_populates="quotations")
    items: Mapped[list["QuotationItem"]] = relationship(
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="QuotationItem.position",
    )


class QuotationItem(Base):
    __tablename__ = "quotation_items"
    __table_args__ = (
        UniqueConstraint("quotation_id", "product_key", name="uq_quotation_item_product_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    product_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    product_name: Mapped[str] = mapped_column(String(240), nullable=False)
    brand: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    product_image: Mapped[str] = mapped_column(Text, nullable=False, default="")
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")
    size: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    color: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    room_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    quotation: Mapped[Quotation] = relationship(back_populates="items")
