from __future__ import annotations

import re
from datetime import date, datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ClientBase(BaseModel):
    client_name: str = Field(min_length=1, max_length=160)
    company: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=60)
    email: str = Field(default="", max_length=160)
    address: str = Field(default="", max_length=2000)

    @field_validator("client_name", "company", "phone", "email", "address", mode="before")
    @classmethod
    def _normalize_text(cls, value: object) -> str:
        return _clean_text(value)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    client_name: str = Field(min_length=1, max_length=160)
    company: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=60)
    email: str = Field(default="", max_length=160)
    address: str = Field(default="", max_length=2000)

    @field_validator("client_name", "company", "phone", "email", "address", mode="before")
    @classmethod
    def _normalize_text(cls, value: object) -> str:
        return _clean_text(value)


class ClientRead(ORMModel):
    id: int
    client_name: str
    company: str
    phone: str
    email: str
    address: str
    created_at: datetime
    updated_at: datetime


class ClientsListResponse(BaseModel):
    results: list[ClientRead]
    total: int


class ManagedProductBase(BaseModel):
    product_code: str = Field(min_length=1, max_length=80)
    product_name: str = Field(min_length=1, max_length=240)
    brand: str = Field(default="Custom", max_length=120)
    category: str = Field(default="General", max_length=120)
    product_image: str = Field(default="", max_length=4000)
    price: float = Field(default=0, ge=0)

    @field_validator("product_code", "product_name", "brand", "category", "product_image", mode="before")
    @classmethod
    def _normalize_text(cls, value: object) -> str:
        return _clean_text(value)


class ManagedProductCreate(ManagedProductBase):
    pass


class ManagedProductUpdate(ManagedProductBase):
    pass


class ManagedProductRead(ORMModel):
    id: int
    product_code: str
    product_name: str
    brand: str
    category: str
    product_image: str
    price: float
    created_at: datetime
    updated_at: datetime


class ProductsListResponse(BaseModel):
    results: list[ManagedProductRead]
    total: int


class QuotationItemInput(BaseModel):
    product_code: str = Field(default="", max_length=80)
    product_name: str = Field(min_length=1, max_length=240)
    brand: str = Field(default="", max_length=120)
    category: str = Field(default="", max_length=120)
    product_image: str = Field(
        default="",
        max_length=4000,
        validation_alias=AliasChoices("product_image", "image"),
    )
    details: str = Field(default="", max_length=4000)
    size: str = Field(default="", max_length=120)
    color: str = Field(default="", max_length=120)
    room_name: str = Field(
        default="",
        max_length=120,
        validation_alias=AliasChoices("room_name", "room"),
    )
    qty: int = Field(default=1, ge=1)
    price: float = Field(default=0, ge=0)
    discount_percent: float = Field(
        default=0,
        ge=0,
        le=100,
        validation_alias=AliasChoices("discount_percent", "discount"),
    )

    @field_validator(
        "product_code",
        "product_name",
        "brand",
        "category",
        "product_image",
        "details",
        "size",
        "color",
        "room_name",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: object) -> str:
        return _clean_text(value)


class QuotationItemRead(ORMModel):
    id: int
    position: int
    product_key: str
    product_code: str
    product_name: str
    brand: str
    category: str
    product_image: str
    details: str
    size: str
    color: str
    room_name: str
    qty: int
    price: float
    discount_percent: float
    total: float


class QuotationWrite(BaseModel):
    proposal_no: str | None = Field(default=None, max_length=80)
    client_id: int | None = None
    client_name: str = Field(min_length=1, max_length=160)
    company: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=60)
    email: str = Field(default="", max_length=160)
    address: str = Field(default="", max_length=2000)
    prepared_by: str = Field(default="", max_length=160)
    prepared_phone: str = Field(default="", max_length=60)
    date: date
    discount_type: Literal["item-wise", "common-percentage", "on-total"] = "item-wise"
    discount_value: float = Field(default=0, ge=0)
    gst_rate: float = Field(default=18, ge=0, le=100)
    status: Literal["draft", "final"] = "draft"
    watermark: bool = True
    items: list[QuotationItemInput] = Field(min_length=1)

    @field_validator(
        "proposal_no",
        "client_name",
        "company",
        "phone",
        "email",
        "address",
        "prepared_by",
        "prepared_phone",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: object) -> str:
        return _clean_text(value)


class QuotationSummary(ORMModel):
    id: int
    proposal_no: str
    client_id: int | None
    client_name: str
    company: str
    phone: str
    email: str
    address: str
    prepared_by: str
    prepared_phone: str
    date: date
    subtotal: float
    discount_type: str
    discount_value: float
    gst_rate: float
    gst_amount: float
    total: float
    status: str
    watermark: bool
    created_at: datetime
    updated_at: datetime


class QuotationRead(QuotationSummary):
    items: list[QuotationItemRead]


class QuotationsListResponse(BaseModel):
    results: list[QuotationSummary]
    total: int


class ProposalNumberResponse(BaseModel):
    proposal_no: str
