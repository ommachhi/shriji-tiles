from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse
from urllib.request import urlopen
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from runtime_paths import get_backend_base_dir, get_images_dir

PAGE_WIDTH, PAGE_HEIGHT = A4
TABLE_WIDTH = 175 * mm


def _clean_text(value: object, fallback: str = "-") -> str:
    text = " ".join(str(value or "").split()).strip()
    return text or fallback


def _money(value: object) -> float:
    try:
        return max(0.0, float(value or 0))
    except Exception:
        return 0.0


def _is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _format_currency(value: object) -> str:
    return f"Rs. {_money(value):,.2f}"


def _format_display_date(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "-"
    try:
        parsed = datetime.fromisoformat(raw).date() if "T" in raw else date.fromisoformat(raw)
        return parsed.strftime("%d %b %Y")
    except Exception:
        return raw


def _discount_label(discount_type: str, discount_value: object) -> str:
    normalized = _clean_text(discount_type, "item-wise").lower()
    if normalized == "common-percentage":
        return f"Common Discount ({_money(discount_value):g}%)"
    if normalized == "on-total":
        return "On-total Discount"
    return "Item-wise Discount"


def _find_existing_path(candidates: Iterable[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _frontend_public_dir() -> Path:
    return get_backend_base_dir().parent / "frontend" / "public"


def _logo_path(filename: str) -> Path | None:
    public_dir = _frontend_public_dir()
    return _find_existing_path(
        [
            public_dir / "assets" / "logos" / filename,
            public_dir / "assets" / filename,
        ]
    )


def _read_image_bytes(source: object) -> BytesIO | None:
    raw_source = str(source or "").strip()
    if not raw_source:
        return None

    if raw_source.startswith("data:image") and "," in raw_source:
        try:
            header, encoded = raw_source.split(",", 1)
            if ";base64" in header:
                return BytesIO(base64.b64decode(encoded))
        except Exception:
            return None

    parsed = urlparse(raw_source)
    if parsed.scheme in {"http", "https"}:
        try:
            with urlopen(raw_source, timeout=8) as response:
                return BytesIO(response.read())
        except Exception:
            return None

    if parsed.scheme == "file":
        local_path = Path(unquote(parsed.path))
        if local_path.exists():
            try:
                return BytesIO(local_path.read_bytes())
            except Exception:
                return None

    local_candidates = []
    decoded_path = unquote(parsed.path or raw_source)
    if decoded_path:
        decoded = decoded_path.lstrip("/")
        local_candidates.extend(
            [
                Path(decoded_path),
                get_backend_base_dir() / decoded,
                _frontend_public_dir() / decoded,
                get_images_dir() / Path(decoded).name,
            ]
        )
        if "images/" in decoded.lower():
            _, _, suffix = decoded.lower().partition("images/")
            local_candidates.append(get_images_dir() / suffix)

    existing = _find_existing_path(local_candidates)
    if not existing:
        return None

    try:
        return BytesIO(existing.read_bytes())
    except Exception:
        return None


def _placeholder_box(label: str, width: float = 16 * mm, height: float = 16 * mm) -> Table:
    styles = getSampleStyleSheet()
    return Table(
        [[Paragraph(_clean_text(label, "Image"), ParagraphStyle("thumb-fallback", parent=styles["BodyText"], fontSize=6.2, alignment=1, textColor=colors.HexColor("#64748b")))]],
        colWidths=[width],
        rowHeights=[height],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        ),
    )


def _build_thumb(source: object, label: str) -> Image | Table:
    image_bytes = _read_image_bytes(source)
    if not image_bytes:
        return _placeholder_box(label)
    try:
        return Image(image_bytes, width=16 * mm, height=16 * mm)
    except Exception:
        return _placeholder_box(label)


def _build_logo() -> Image | None:
    logo = _logo_path("shreeji-logo.png")
    if not logo:
        return None
    try:
        return Image(str(logo), width=28 * mm, height=28 * mm)
    except Exception:
        return None


def _watermark_path() -> Path | None:
    return _logo_path("shreeji-watermark.png")


def generate_professional_pdf(data: dict) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    story = []

    body_style = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    muted_style = ParagraphStyle(
        "muted",
        parent=body_style,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b"),
    )
    title_style = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f3d5e"),
        spaceAfter=2,
    )
    section_style = ParagraphStyle(
        "section",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#0f3d5e"),
        spaceAfter=3,
    )
    table_product_style = ParagraphStyle(
        "product",
        parent=body_style,
        fontSize=8.4,
        leading=10.4,
    )
    table_meta_style = ParagraphStyle(
        "product-meta",
        parent=muted_style,
        fontSize=7.2,
        leading=9,
    )

    client_info = data.get("client_info", {})
    quote_date = _format_display_date(data.get("quote_date"))
    proposal_no = _clean_text(data.get("proposal_no"))
    watermark_enabled = _is_truthy(data.get("watermark"))
    discount_type = _clean_text(data.get("discount_type"), "item-wise").lower()
    discount_value = data.get("discount_value", 0)
    subtotal = _money(data.get("subtotal"))
    discount_amount = _money(data.get("discount_amount"))
    taxable_total = _money(data.get("taxable_total"))
    gst_rate = _money(data.get("gst_rate"))
    total_gst = _money(data.get("total_gst"))
    grand_total = _money(data.get("grand_total"))

    logo = _build_logo()
    company_block = [
        Paragraph("SHREEJI CERAMICA", title_style),
        Paragraph("Professional Quotation", section_style),
        Paragraph("Premium bathware, fittings, and project-ready BOM quotations", muted_style),
        Paragraph("Phone: +91 98765 43210 | Email: info@shreejiceramica.com", muted_style),
    ]
    header_left = logo if logo else Paragraph("SC", ParagraphStyle("logo-fallback", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=24, textColor=colors.HexColor("#0f3d5e")))
    header_right = Table([[cell] for cell in company_block], colWidths=[110 * mm], style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    header_table = Table(
        [[header_left, header_right]],
        colWidths=[32 * mm, 143 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    story.append(header_table)
    story.append(Spacer(1, 5 * mm))

    meta_table = Table(
        [
            [
                Paragraph("<b>Proposal No</b><br/>" + proposal_no, body_style),
                Paragraph("<b>Date</b><br/>" + quote_date, body_style),
                Paragraph("<b>Status</b><br/>" + ("Final" if str(data.get("status", "")).lower() == "final" else "Draft"), body_style),
            ]
        ],
        colWidths=[58 * mm, 50 * mm, 42 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d7dee7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#d7dee7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        ),
    )
    story.append(meta_table)
    story.append(Spacer(1, 5 * mm))

    bill_to = Paragraph(
        "<b>Client Details</b><br/>"
        f"{_clean_text(client_info.get('clientName'))}<br/>"
        f"{_clean_text(client_info.get('company'), '-') if client_info.get('company') else '-'}<br/>"
        f"Phone: {_clean_text(client_info.get('phone'))}<br/>"
        f"Email: {_clean_text(client_info.get('email'))}<br/>"
        f"Address: {_clean_text(client_info.get('address'))}",
        body_style,
    )
    story.append(
        Table(
            [[bill_to]],
            colWidths=[TABLE_WIDTH],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d7dee7")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            ),
        )
    )
    story.append(Spacer(1, 5 * mm))

    table_rows = [[
        Paragraph("<b>#</b>", body_style),
        Paragraph("<b>Image</b>", body_style),
        Paragraph("<b>Product</b>", body_style),
        Paragraph("<b>Room</b>", body_style),
        Paragraph("<b>Qty</b>", body_style),
        Paragraph("<b>Price</b>", body_style),
        Paragraph("<b>Disc %</b>", body_style),
        Paragraph("<b>Total</b>", body_style),
    ]]

    for index, item in enumerate(data.get("bom", []), start=1):
        product_bits = [
            f"<b>{_clean_text(item.get('name'))}</b>",
            f"Code: {_clean_text(item.get('code'))}",
        ]
        meta_bits = []
        if item.get("brand"):
            meta_bits.append(f"Brand: {_clean_text(item.get('brand'))}")
        if item.get("size") and str(item.get("size")).strip() != "-":
            meta_bits.append(f"Size: {_clean_text(item.get('size'))}")
        if item.get("color") and str(item.get("color")).strip() != "-":
            meta_bits.append(f"Color: {_clean_text(item.get('color'))}")
        if item.get("details"):
            meta_bits.append(_clean_text(item.get("details")))

        product_html = "<br/>".join(product_bits)
        if meta_bits:
            product_html += "<br/><font color='#64748b'>" + "<br/>".join(meta_bits[:3]) + "</font>"

        table_rows.append(
            [
                Paragraph(str(index), body_style),
                _build_thumb(item.get("product_image"), item.get("name") or "Product"),
                Paragraph(product_html, table_product_style),
                Paragraph(_clean_text(item.get("room_name")), table_meta_style),
                Paragraph(str(int(_money(item.get("qty")) or 0)), body_style),
                Paragraph(_format_currency(item.get("rate")), body_style),
                Paragraph(f"{_money(item.get('discount_percent')):g}%", body_style),
                Paragraph(_format_currency(item.get("amount")), body_style),
            ]
        )

    items_table = Table(
        table_rows,
        colWidths=[8 * mm, 16 * mm, 60 * mm, 24 * mm, 12 * mm, 18 * mm, 14 * mm, 22 * mm],
        repeatRows=1,
    )
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3d5e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (4, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#d7dee7")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbfdff")]),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 5 * mm))

    summary_rows = [
        ["Subtotal", _format_currency(subtotal)],
        [_discount_label(discount_type, discount_value), f"- {_format_currency(discount_amount)}"],
        ["Net Taxable", _format_currency(taxable_total)],
        [f"GST ({gst_rate:g}%)", _format_currency(total_gst)],
        ["Grand Total", _format_currency(grand_total)],
    ]
    summary_table = Table(
        summary_rows,
        colWidths=[46 * mm, 34 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d7dee7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#d7dee7")),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#0f3d5e")),
            ]
        ),
    )
    summary_wrap = Table(
        [["", summary_table]],
        colWidths=[95 * mm, 80 * mm],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]),
    )
    story.append(summary_wrap)
    story.append(Spacer(1, 5 * mm))

    terms = Paragraph(
        "<b>Terms & Conditions</b><br/>"
        "1. This quotation is valid for 15 days from the issue date.<br/>"
        "2. Product availability and dispatch timelines remain subject to stock confirmation.<br/>"
        "3. Installation, transport, and site handling are excluded unless stated otherwise.<br/>"
        "4. Taxes are applied as shown above and final billing will follow the approved quotation.",
        muted_style,
    )
    story.append(terms)

    watermark_image = _watermark_path()

    def decorate_page(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d7dee7"))
        canvas.setLineWidth(0.8)
        canvas.rect(12 * mm, 12 * mm, PAGE_WIDTH - (24 * mm), PAGE_HEIGHT - (24 * mm))
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(PAGE_WIDTH - (14 * mm), 10 * mm, f"Page {canvas.getPageNumber()}")

        if watermark_enabled:
            if watermark_image and watermark_image.exists():
                try:
                    canvas.saveState()
                    if hasattr(canvas, "setFillAlpha"):
                        canvas.setFillAlpha(0.08)
                    canvas.drawImage(
                        str(watermark_image),
                        40 * mm,
                        82 * mm,
                        width=130 * mm,
                        height=75 * mm,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                    canvas.restoreState()
                except Exception:
                    pass
            else:
                canvas.saveState()
                canvas.translate(PAGE_WIDTH / 2, PAGE_HEIGHT / 2)
                canvas.rotate(35)
                canvas.setFillColor(colors.HexColor("#94a3b8"))
                if hasattr(canvas, "setFillAlpha"):
                    canvas.setFillAlpha(0.08)
                canvas.setFont("Helvetica-Bold", 42)
                canvas.drawCentredString(0, 0, "SHREEJI CERAMICA")
                canvas.restoreState()

        canvas.restoreState()

    doc.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)
    buffer.seek(0)
    return buffer
