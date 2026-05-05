from __future__ import annotations

import re
from collections import OrderedDict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from bom_db import SessionLocal, get_db
from bom_models import Client, ManagedProduct, Quotation, QuotationItem
from bom_schemas import (
    ClientCreate,
    ClientRead,
    ClientsListResponse,
    ManagedProductCreate,
    ManagedProductRead,
    ManagedProductUpdate,
    ProductsListResponse,
    ProposalNumberResponse,
    QuotationRead,
    QuotationsListResponse,
    QuotationWrite,
)

router = APIRouter(tags=["bom"])

MONEY_QUANT = Decimal("0.01")
DISCOUNT_TYPES = {"item-wise", "common-percentage", "on-total"}
ROOM_OPTIONS = [
    "Kid's Bathroom",
    "Guest Bathroom",
    "Parent's Bathroom",
    "Master Bathroom",
    "Common / Powder Room",
    "Living Room",
    "Kitchen",
    "Balcony",
    "Utility Room",
]
ROOM_OPTIONS_SET = {value.lower() for value in ROOM_OPTIONS}


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _compact_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", _clean_text(value).lower())


def _normalize_product_key(product_code: str, product_name: str) -> str:
    return _compact_text(product_code) or _compact_text(product_name)


def _money(value: object) -> Decimal:
    try:
        numeric = Decimal(str(value or 0))
    except Exception:
        numeric = Decimal("0")
    if numeric < 0:
        numeric = Decimal("0")
    return numeric.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _sort_products_query(sort: str):
    if sort == "name":
        return ManagedProduct.product_name.asc(), ManagedProduct.product_code.asc()
    if sort == "price_desc":
        return ManagedProduct.price.desc(), ManagedProduct.product_name.asc()
    if sort == "price_asc":
        return ManagedProduct.price.asc(), ManagedProduct.product_name.asc()
    return ManagedProduct.product_code.asc(), ManagedProduct.product_name.asc()


def _serialize_managed_product(product: ManagedProduct) -> dict:
    return {
        "code": product.product_code,
        "name": product.product_name,
        "source": "managed",
        "sourceLabel": product.brand or "Managed",
        "price": float(product.price or 0),
        "category": product.category or "General",
        "brand": product.brand or "Managed",
        "color": None,
        "size": None,
        "details": f"{product.brand} | {product.category}".strip(" |"),
        "image": product.product_image or "",
        "hasImage": bool(product.product_image),
    }


def _score_managed_product(product: ManagedProduct, normalized_query: str, compact_query: str) -> int:
    code = _compact_text(product.product_code)
    name = _clean_text(product.product_name).lower()
    brand = _clean_text(product.brand).lower()
    category = _clean_text(product.category).lower()
    score = 0

    if compact_query and code == compact_query:
        score = max(score, 240)
    if compact_query and code.startswith(compact_query):
        score = max(score, 210)
    if compact_query and compact_query in code:
        score = max(score, 180)
    if normalized_query and name == normalized_query:
        score = max(score, 170)
    if normalized_query and name.startswith(normalized_query):
        score = max(score, 150)
    if normalized_query and normalized_query in name:
        score = max(score, 130)
    if normalized_query and normalized_query in brand:
        score = max(score, 110)
    if normalized_query and normalized_query in category:
        score = max(score, 100)

    return score


def search_managed_product_matches(query: str, catalog: str = "all", limit: int = 20) -> list[dict]:
    selected_catalog = _clean_text(catalog).lower() or "all"
    if selected_catalog not in {"all", "managed"}:
        return []

    normalized_query = _clean_text(query).lower()
    compact_query = _compact_text(query)
    if not normalized_query and not compact_query:
        return []

    with SessionLocal() as db:
        products = db.scalars(select(ManagedProduct).order_by(ManagedProduct.product_name.asc())).all()

    scored = []
    for product in products:
        score = _score_managed_product(product, normalized_query, compact_query)
        if score > 0:
            scored.append((score, product))

    scored.sort(
        key=lambda pair: (
            -pair[0],
            _compact_text(pair[1].product_code),
            _clean_text(pair[1].product_name).lower(),
        )
    )
    return [_serialize_managed_product(product) for _, product in scored[:limit]]


def autocomplete_managed_products(query: str, catalog: str = "all", limit: int = 10) -> list[dict]:
    return search_managed_product_matches(query, catalog=catalog, limit=limit)


def _get_client_or_404(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found.")
    return client


def _get_product_or_404(db: Session, product_id: int) -> ManagedProduct:
    product = db.get(ManagedProduct, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


def _get_quotation_or_404(db: Session, quotation_id: int) -> Quotation:
    quotation = db.scalar(
        select(Quotation)
        .options(selectinload(Quotation.items))
        .where(Quotation.id == quotation_id)
    )
    if quotation is None:
        raise HTTPException(status_code=404, detail="Quotation not found.")
    return quotation


def _proposal_prefix(target_date: date | None = None) -> str:
    effective_date = target_date or date.today()
    return f"PROP-{effective_date:%Y%m%d}-"


def generate_next_proposal_no(db: Session, target_date: date | None = None) -> str:
    prefix = _proposal_prefix(target_date)
    rows = db.scalars(
        select(Quotation.proposal_no).where(Quotation.proposal_no.like(f"{prefix}%"))
    ).all()
    current_max = 0
    for proposal_no in rows:
        suffix = str(proposal_no).replace(prefix, "", 1)
        if suffix.isdigit():
            current_max = max(current_max, int(suffix))
    return f"{prefix}{current_max + 1:03d}"


def _normalize_discount_type(value: str) -> str:
    normalized = _clean_text(value).lower() or "item-wise"
    if normalized not in DISCOUNT_TYPES:
        raise HTTPException(status_code=422, detail="Invalid discount type.")
    return normalized


def _normalize_room_name(value: str, product_name: str) -> str:
    room_name = _clean_text(value)
    if not room_name:
        raise HTTPException(
            status_code=422,
            detail=f"Select a room for '{product_name}' before saving the quotation.",
        )
    if room_name.lower() not in ROOM_OPTIONS_SET:
        raise HTTPException(status_code=422, detail=f"Invalid room selected for '{product_name}'.")
    return next(option for option in ROOM_OPTIONS if option.lower() == room_name.lower())


def _merge_items(items) -> list[dict]:
    merged: OrderedDict[str, dict] = OrderedDict()

    for item in items:
        product_name = _clean_text(item.product_name) or "Product"
        product_key = _normalize_product_key(item.product_code, product_name)
        if not product_key:
            raise HTTPException(status_code=422, detail="Each quotation item needs a product code or product name.")

        qty = max(1, int(item.qty))
        price = _money(item.price)
        base_total = (Decimal(qty) * price).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        room_name = _normalize_room_name(item.room_name, product_name)
        discount_percent = min(Decimal("100.00"), _money(item.discount_percent))

        if product_key not in merged:
            merged[product_key] = {
                "position": len(merged),
                "product_key": product_key,
                "product_code": _clean_text(item.product_code),
                "product_name": product_name,
                "brand": _clean_text(item.brand),
                "category": _clean_text(item.category) or "General",
                "product_image": _clean_text(item.product_image),
                "details": _clean_text(item.details),
                "size": _clean_text(item.size),
                "color": _clean_text(item.color),
                "room_name": room_name,
                "qty": qty,
                "price": price,
                "discount_percent": discount_percent,
                "base_total": base_total,
                "total": base_total,
            }
            continue

        existing = merged[product_key]
        existing["qty"] += qty
        existing["price"] = price
        existing["discount_percent"] = discount_percent
        existing["base_total"] = (Decimal(existing["qty"]) * price).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        existing["total"] = existing["base_total"]
        if item.brand:
            existing["brand"] = _clean_text(item.brand)
        if item.category:
            existing["category"] = _clean_text(item.category)
        if item.product_image:
            existing["product_image"] = _clean_text(item.product_image)
        if item.details:
            existing["details"] = _clean_text(item.details)
        if item.size:
            existing["size"] = _clean_text(item.size)
        if item.color:
            existing["color"] = _clean_text(item.color)
        existing["room_name"] = room_name

    return list(merged.values())


def _calculate_quote_totals(merged_items: list[dict], discount_type: str, discount_value: Decimal, gst_rate: Decimal) -> dict:
    gross_subtotal = sum((row["base_total"] for row in merged_items), start=Decimal("0.00")).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    discount_amount = Decimal("0.00")
    subtotal = gross_subtotal

    if discount_type == "item-wise":
        for row in merged_items:
            row_discount = (row["base_total"] * (row["discount_percent"] / Decimal("100"))).quantize(
                MONEY_QUANT,
                rounding=ROUND_HALF_UP,
            )
            row["total"] = (row["base_total"] - row_discount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            discount_amount += row_discount
        discount_amount = discount_amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        subtotal = (gross_subtotal - discount_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    elif discount_type == "common-percentage":
        common_percent = min(Decimal("100.00"), discount_value)
        for row in merged_items:
            row["total"] = (
                row["base_total"] * (Decimal("1.00") - (common_percent / Decimal("100")))
            ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        discount_amount = sum((row["base_total"] - row["total"] for row in merged_items), start=Decimal("0.00")).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )
        subtotal = sum((row["total"] for row in merged_items), start=Decimal("0.00")).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )
    else:
        for row in merged_items:
            row["total"] = row["base_total"]
        discount_amount = Decimal("0.00")

    if discount_type == "on-total":
        taxable_total = gross_subtotal
    else:
        taxable_total = max(Decimal("0.00"), subtotal).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    gst_amount = (taxable_total * (gst_rate / Decimal("100"))).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    grand_total = (taxable_total + gst_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    if discount_type == "on-total":
        discount_amount = min(discount_value, grand_total).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        grand_total = max(Decimal("0.00"), grand_total - discount_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    return {
        "subtotal": subtotal,
        "gross_subtotal": gross_subtotal,
        "discount_amount": discount_amount,
        "taxable_total": taxable_total,
        "gst_amount": gst_amount,
        "grand_total": grand_total,
    }


def _quotation_discount_amount(quotation: Quotation) -> Decimal:
    discount_type = _normalize_discount_type(quotation.discount_type)
    discount_value = _money(quotation.discount_value)
    gross_subtotal = sum((_money(item.price) * Decimal(item.qty) for item in quotation.items), start=Decimal("0.00")).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )

    if discount_type == "item-wise":
        amount = sum(
            (
                (_money(item.price) * Decimal(item.qty) * (_money(item.discount_percent) / Decimal("100"))).quantize(
                    MONEY_QUANT,
                    rounding=ROUND_HALF_UP,
                )
                for item in quotation.items
            ),
            start=Decimal("0.00"),
        )
        return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    if discount_type == "common-percentage":
        return (gross_subtotal * (min(discount_value, Decimal("100.00")) / Decimal("100"))).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )

    return min(discount_value, subtotal + _money(quotation.gst_amount)).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )


def _build_pdf_payload(quotation: Quotation) -> dict:
    discount_amount = _quotation_discount_amount(quotation)
    discount_type = _normalize_discount_type(quotation.discount_type)
    subtotal = _money(quotation.subtotal)
    taxable_total = subtotal
    if discount_type != "on-total":
        taxable_total = max(Decimal("0.00"), subtotal - discount_amount).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )

    return {
        "proposal_no": quotation.proposal_no,
        "quote_date": quotation.date.isoformat(),
        "preparedBy": quotation.prepared_by,
        "preparedPhone": quotation.prepared_phone,
        "client_info": {
            "clientName": quotation.client_name,
            "company": quotation.company,
            "phone": quotation.phone,
            "email": quotation.email,
            "address": quotation.address,
            "preparedBy": quotation.prepared_by,
            "preparedPhone": quotation.prepared_phone,
        },
        "discount_type": discount_type,
        "discount_value": float(_money(quotation.discount_value)),
        "subtotal": float(subtotal),
        "discount_amount": float(discount_amount),
        "taxable_total": float(taxable_total),
        "gst_rate": float(_money(quotation.gst_rate)),
        "total_gst": float(_money(quotation.gst_amount)),
        "grand_total": float(_money(quotation.total)),
        "status": quotation.status,
        "watermark": quotation.watermark,
        "bom": [
            {
                "name": item.product_name,
                "code": item.product_code,
                "brand": item.brand,
                "category": item.category,
                "details": item.details,
                "size": item.size or "-",
                "color": item.color or "-",
                "room_name": item.room_name,
                "qty": item.qty,
                "rate": float(_money(item.price)),
                "discount_percent": float(_money(item.discount_percent)),
                "amount": float(_money(item.total)),
                "product_image": item.product_image,
            }
            for item in quotation.items
        ],
    }


def _apply_quotation_payload(db: Session, quotation: Quotation, payload: QuotationWrite, proposal_no: str) -> Quotation:
    if not payload.client_id:
        raise HTTPException(status_code=422, detail="Select a client before saving the quotation.")

    linked_client = _get_client_or_404(db, payload.client_id)
    discount_type = _normalize_discount_type(payload.discount_type)
    discount_value = _money(payload.discount_value)
    gst_rate = min(Decimal("100.00"), _money(payload.gst_rate))
    merged_items = _merge_items(payload.items)
    if not merged_items:
        raise HTTPException(status_code=422, detail="Add at least one item before saving the quotation.")

    totals = _calculate_quote_totals(merged_items, discount_type, discount_value, gst_rate)

    quotation.proposal_no = proposal_no
    quotation.client_id = linked_client.id
    quotation.client_name = payload.client_name or linked_client.client_name
    quotation.company = payload.company or linked_client.company
    quotation.phone = payload.phone or linked_client.phone
    quotation.email = payload.email or linked_client.email
    quotation.address = payload.address or linked_client.address
    quotation.prepared_by = payload.prepared_by
    quotation.prepared_phone = payload.prepared_phone
    quotation.date = payload.date
    quotation.discount_type = discount_type
    quotation.discount_value = discount_value
    quotation.gst_rate = gst_rate
    quotation.gst_amount = totals["gst_amount"]
    quotation.subtotal = totals["subtotal"]
    quotation.total = totals["grand_total"]
    quotation.status = payload.status
    quotation.watermark = bool(payload.watermark)

    quotation.items = [
        QuotationItem(
            position=row["position"],
            product_key=row["product_key"],
            product_code=row["product_code"],
            product_name=row["product_name"],
            brand=row["brand"],
            category=row["category"],
            product_image=row["product_image"],
            details=row["details"],
            size=row["size"],
            color=row["color"],
            room_name=row["room_name"],
            qty=row["qty"],
            price=row["price"],
            discount_percent=row["discount_percent"],
            total=row["total"],
        )
        for row in merged_items
    ]

    return quotation


def _commit_or_conflict(db: Session, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=conflict_message) from exc


@router.get("/clients", response_model=ClientsListResponse)
def list_clients(
    q: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = _clean_text(q)
    statement = select(Client)
    if query:
        pattern = f"%{query}%"
        statement = statement.where(
            or_(
                Client.client_name.ilike(pattern),
                Client.company.ilike(pattern),
                Client.phone.ilike(pattern),
                Client.email.ilike(pattern),
            )
        )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    results = db.scalars(statement.order_by(Client.client_name.asc()).limit(limit)).all()
    return {"results": results, "total": total}


@router.post("/clients", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    client = Client(**payload.model_dump())
    db.add(client)
    _commit_or_conflict(db, "Unable to create client with the provided details.")
    db.refresh(client)
    return client


@router.get("/clients/{client_id}", response_model=ClientRead)
def get_client(client_id: int, db: Session = Depends(get_db)):
    return _get_client_or_404(db, client_id)


@router.put("/clients/{client_id}", response_model=ClientRead)
def update_client(client_id: int, payload: ClientCreate, db: Session = Depends(get_db)):
    client = _get_client_or_404(db, client_id)
    for field, value in payload.model_dump().items():
        setattr(client, field, value)
    _commit_or_conflict(db, "Unable to update client with the provided details.")
    db.refresh(client)
    return client


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = _get_client_or_404(db, client_id)
    quote_count = db.scalar(select(func.count()).select_from(Quotation).where(Quotation.client_id == client_id)) or 0
    if quote_count > 0:
        raise HTTPException(
            status_code=409,
            detail="This client is linked to saved quotations and cannot be deleted.",
        )
    db.delete(client)
    db.commit()


@router.get("/products", response_model=ProductsListResponse)
def list_managed_products(
    q: str = Query(default=""),
    brand: str = Query(default="all"),
    category: str = Query(default="all"),
    sort: str = Query(default="code"),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = _clean_text(q)
    statement = select(ManagedProduct)
    if query:
        pattern = f"%{query}%"
        statement = statement.where(
            or_(
                ManagedProduct.product_code.ilike(pattern),
                ManagedProduct.product_name.ilike(pattern),
                ManagedProduct.brand.ilike(pattern),
                ManagedProduct.category.ilike(pattern),
            )
        )
    if _clean_text(brand).lower() != "all":
        statement = statement.where(ManagedProduct.brand.ilike(brand))
    if _clean_text(category).lower() != "all":
        statement = statement.where(ManagedProduct.category.ilike(category))

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    results = db.scalars(statement.order_by(*_sort_products_query(sort)).limit(limit)).all()
    return {"results": results, "total": total}


@router.post("/products", response_model=ManagedProductRead, status_code=status.HTTP_201_CREATED)
def create_managed_product(payload: ManagedProductCreate, db: Session = Depends(get_db)):
    existing = db.scalar(
        select(ManagedProduct).where(func.lower(ManagedProduct.product_code) == payload.product_code.lower())
    )
    if existing:
        raise HTTPException(status_code=409, detail="A product with this code already exists.")

    product = ManagedProduct(**payload.model_dump())
    db.add(product)
    _commit_or_conflict(db, "Unable to create product. Check that the product code is unique.")
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ManagedProductRead)
def update_managed_product(product_id: int, payload: ManagedProductUpdate, db: Session = Depends(get_db)):
    product = _get_product_or_404(db, product_id)
    duplicate = db.scalar(
        select(ManagedProduct).where(
            func.lower(ManagedProduct.product_code) == payload.product_code.lower(),
            ManagedProduct.id != product_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="A product with this code already exists.")

    for field, value in payload.model_dump().items():
        setattr(product, field, value)
    _commit_or_conflict(db, "Unable to update product. Check that the product code is unique.")
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_managed_product(product_id: int, db: Session = Depends(get_db)):
    product = _get_product_or_404(db, product_id)
    db.delete(product)
    db.commit()


@router.get("/quotations/next-proposal", response_model=ProposalNumberResponse)
def next_proposal_number(db: Session = Depends(get_db)):
    return {"proposal_no": generate_next_proposal_no(db)}


@router.get("/quotations", response_model=QuotationsListResponse)
def list_quotations(
    q: str = Query(default=""),
    status_filter: str = Query(default="all", alias="status"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = _clean_text(q)
    selected_status = _clean_text(status_filter).lower() or "all"

    statement = select(Quotation)
    if query:
        pattern = f"%{query}%"
        statement = statement.where(
            or_(
                Quotation.proposal_no.ilike(pattern),
                Quotation.client_name.ilike(pattern),
                Quotation.company.ilike(pattern),
                Quotation.phone.ilike(pattern),
            )
        )
    if selected_status != "all":
        statement = statement.where(func.lower(Quotation.status) == selected_status)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    results = db.scalars(
        statement.order_by(Quotation.date.desc(), Quotation.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return {"results": results, "total": total}


@router.get("/quotations/{quotation_id}/pdf")
def get_quotation_pdf(quotation_id: int, db: Session = Depends(get_db)):
    quotation = _get_quotation_or_404(db, quotation_id)
    from pdf_service import generate_professional_pdf

    pdf_buffer = generate_professional_pdf(_build_pdf_payload(quotation))
    safe_filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", quotation.proposal_no).strip("_") or "quotation"
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_filename}.pdf"'},
    )


@router.get("/quotations/{quotation_id}", response_model=QuotationRead)
def get_quotation(quotation_id: int, db: Session = Depends(get_db)):
    return _get_quotation_or_404(db, quotation_id)


@router.post("/quotations", response_model=QuotationRead, status_code=status.HTTP_201_CREATED)
def create_quotation(payload: QuotationWrite, db: Session = Depends(get_db)):
    requested_proposal_no = _clean_text(payload.proposal_no)
    if requested_proposal_no:
        existing = db.scalar(select(Quotation.id).where(Quotation.proposal_no == requested_proposal_no))
        if existing:
            raise HTTPException(status_code=409, detail="Proposal already exists.")

    attempts = 0
    while attempts < 3:
        attempts += 1
        proposal_no = requested_proposal_no or generate_next_proposal_no(db, payload.date)
        quotation = _apply_quotation_payload(db, Quotation(), payload, proposal_no)
        db.add(quotation)
        try:
            db.commit()
            db.refresh(quotation)
            return _get_quotation_or_404(db, quotation.id)
        except IntegrityError as exc:
            db.rollback()
            if requested_proposal_no:
                raise HTTPException(status_code=409, detail="Proposal already exists.") from exc
            if attempts >= 3:
                raise HTTPException(status_code=409, detail="Unable to generate a unique proposal number.") from exc

    raise HTTPException(status_code=409, detail="Unable to generate a unique proposal number.")


@router.put("/quotations/{quotation_id}", response_model=QuotationRead)
def update_quotation(quotation_id: int, payload: QuotationWrite, db: Session = Depends(get_db)):
    quotation = _get_quotation_or_404(db, quotation_id)
    requested_proposal_no = _clean_text(payload.proposal_no) or quotation.proposal_no
    existing = db.scalar(
        select(Quotation.id).where(
            Quotation.proposal_no == requested_proposal_no,
            Quotation.id != quotation_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Proposal already exists.")

    _apply_quotation_payload(db, quotation, payload, requested_proposal_no)
    _commit_or_conflict(db, "Unable to update quotation. Please try again.")
    db.refresh(quotation)
    return _get_quotation_or_404(db, quotation_id)


@router.delete("/quotations/{quotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quotation(quotation_id: int, db: Session = Depends(get_db)):
    quotation = _get_quotation_or_404(db, quotation_id)
    db.delete(quotation)
    db.commit()
