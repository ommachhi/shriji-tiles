from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, unquote
import base64
import requests
from datetime import datetime
from runtime_paths import get_images_dir


def _is_truthy_watermark(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on", "enabled"}


def generate_professional_pdf(data: dict):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []
    is_branding_on = _is_truthy_watermark(data.get('discount_config', {}).get('watermark'))
    primary_color = colors.HexColor("#0f3d5e") if is_branding_on else colors.HexColor("#173b63")
    accent_color = colors.HexColor("#0b7c6d") if is_branding_on else colors.HexColor("#c6932d")

    images_dir = get_images_dir()

    placeholder_style = ParagraphStyle(
        'MissingImageStyle',
        parent=styles['Normal'],
        alignment=1,
        fontSize=7,
        leading=8,
        textColor=colors.HexColor('#64748b'),
    )

    def missing_image_placeholder():
        return Table(
            [[Paragraph('IMAGE NOT FOUND', placeholder_style)]],
            colWidths=[40],
            rowHeights=[40],
            style=TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ])
        )

    # Helper to fetch image into buffer
    def get_image(url):
        if not url:
            return None

        raw_url = str(url).strip()
        if not raw_url:
            return None

        if raw_url.startswith("data:image") and "," in raw_url:
            try:
                header, encoded = raw_url.split(",", 1)
                if ";base64" in header:
                    return BytesIO(base64.b64decode(encoded))
            except Exception:
                return None

        parsed = urlparse(raw_url)
        path_value = unquote(parsed.path or "")
        filename = Path(path_value).name if path_value else ""

        # Local first: resolves /images/<file> without extra HTTP calls.
        if filename:
            local_path = images_dir / filename
            if local_path.exists() and local_path.is_file():
                try:
                    return BytesIO(local_path.read_bytes())
                except Exception:
                    pass

        try:
            resp = requests.get(raw_url, timeout=8)
            if resp.status_code == 200:
                return BytesIO(resp.content)
        except Exception:
            pass
        return None

    # --- HEADER ---
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], alignment=2, fontSize=18, fontName='Helvetica-Bold', textColor=primary_color)
    tagline_style = ParagraphStyle('TaglineStyle', parent=styles['Normal'], alignment=2, fontSize=9, textColor=colors.gray)
    contact_style = ParagraphStyle('ContactStyle', parent=styles['Normal'], alignment=2, fontSize=9, textColor=colors.HexColor("#475569"))

    t_header = None
    if is_branding_on:
        brand_left = Paragraph(
            "<b>SHREEJI CERAMICA - BRANDED QUOTATION</b>",
            ParagraphStyle('BrandLeft', parent=styles['Normal'], alignment=0, fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor("#334155")),
        )
        brand_right = Paragraph(
            "<font size='19' color='#0f3d5e'><b>SHREEJI CERAMICA</b></font><br/>"
            "<font size='8'>Premium Tiles &amp; Bathware Showroom</font><br/>"
            "<font size='8'>123 Business Road | City, State - 123456</font><br/>"
            "<font size='8'>+91 9876543210 | info@shreejiceramica.com</font><br/>"
            "<font size='9' color='#0b7c6d'><b>BRANDED QUOTATION COPY</b></font>",
            ParagraphStyle('BrandRightBlock', parent=styles['Normal'], alignment=2, textColor=colors.HexColor("#475569"), leading=10),
        )

        t_header = Table(
            [[brand_left, brand_right]],
            colWidths=[280, 250],
            rowHeights=[74],
        )
        t_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9edf2')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
    if t_header is not None:
        elements.append(t_header)
        elements.append(Spacer(1, 8))
        elements.append(Table([[""]], colWidths=[530], rowHeights=[1], style=[('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor("#cbd5e1"))]))
        elements.append(Spacer(1, 15))

    # --- QUOTATION DETAILS ---
    lbl_style = ParagraphStyle('LabelStyle', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=accent_color)
    txt_style = ParagraphStyle('TxtStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#334155"))
    
    client_info = data.get('client_info', {})

    prepared_by = client_info.get('preparedBy', 'N/A')
    prepared_phone = client_info.get('phone', '').strip()
    prepared_line = ""
    if is_branding_on:
        prepared_line = f"Prepared By: {prepared_by}"
        if prepared_phone:
            prepared_line += f"  |  +91 {prepared_phone}"

    quote_top = [
        [Paragraph("BUSINESS QUOTATION", lbl_style), Paragraph(prepared_line, ParagraphStyle('PreparedStyle', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=primary_color, alignment=2))],
        [Paragraph(f"Ref: SC-2  |  Date: {datetime.now().strftime('%d %b %Y')}", txt_style), ""]
    ]
    t_top = Table(quote_top, colWidths=[300, 230])
    t_top.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'RIGHT')]))
    elements.append(t_top)
    elements.append(Spacer(1, 12 if not is_branding_on else 20))

    # --- BILL TO ---
    elements.append(Paragraph("<b>BILL TO:</b>", ParagraphStyle('BillTitle', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold', textColor=primary_color)))
    cl = client_info
    bill_info = f"{cl.get('clientName', 'N/A')}<br/>{cl.get('address', 'N/A')}<br/>Phone: {cl.get('phone', 'N/A')}<br/>Email: {cl.get('email', 'N/A')}"
    elements.append(Paragraph(bill_info, ParagraphStyle('BillStyle', parent=styles['Normal'], leading=15, fontSize=10, textColor=colors.HexColor("#1f2937"))))
    elements.append(Spacer(1, 20 if not is_branding_on else 30))

    # --- PRODUCTS TABLE ---
    col_widths = [20, 60, 150, 60, 50, 25, 60, 40, 65]
    table_data = [["#", "IMG", "Item Details", "SKU", "Size", "Qty", "Rate", "Disc%", "Amount"]]
    
    for idx, item in enumerate(data.get('bom', []), 1):
        img_elem = missing_image_placeholder()
        img_url = item.get('image')
        if img_url:
            img_data = get_image(img_url)
            if img_data:
                try:
                    img_elem = Image(img_data, width=40, height=40)
                except:
                    img_elem = missing_image_placeholder()

        details = f"<b>{item.get('name', 'N/A')}</b><br/><font size='8' color='gray'>Color: {item.get('color', '-')}</font>"
        
        table_data.append([
            str(idx), img_elem, Paragraph(details, styles['Normal']),
            item.get('code', '-'), item.get('size', '-'), str(item.get('qty', 0)),
            f"Rs. {float(item.get('rate', 0) or 0):,.2f}", f"{float(item.get('discount', 0) or 0):g}%", f"Rs. {float(item.get('amount', 0) or 0):,.2f}"
        ])

    items_table = Table(table_data, colWidths=col_widths)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#d6deea")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,1), (0,-1), 'CENTER'),
        ('ALIGN', (5,1), (-1,-1), 'CENTER'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 14 if not is_branding_on else 20))

    # --- SUMMARY ---
    def get_val(item, key):
        try:
            return float(item.get(key, 0) or 0)
        except:
            return 0.0

    total_disc = sum((get_val(i, 'qty') * get_val(i, 'rate') * (get_val(i, 'discount')/100)) for i in data.get('bom', []))
    summary_data = [
        ["", "Gross Subtotal:", f"Rs. {data.get('subtotal', 0):,.2f}"],
        ["", f"Discount:", f"- Rs. {total_disc:,.2f}"],
    ]
    
    net_taxable = data.get('subtotal', 0) - total_disc
    summary_data.append(["", "Net Taxable Amount:", f"Rs. {net_taxable:,.2f}"])
    
    cl_info = data.get('client_info', {})
    gst_percentage = float(cl_info.get('gstPercentage', 0) or 0)
    
    if cl_info.get('gstCompliance'):
        gst_val = gst_percentage / 2
        gst_amt = data.get('total_gst', 0) / 2
        summary_data.extend([
            ["", f"CGST ({gst_val}%):", f"Rs. {gst_amt:,.2f}"],
            ["", f"SGST ({gst_val}%):", f"Rs. {gst_amt:,.2f}"],
        ])
        
    summary_data.append(["", "GRAND TOTAL:", f"Rs. {data.get('grand_total', 0):,.2f}"])
    
    summary_table = Table(summary_data, colWidths=[300, 130, 100])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'), ('FONTNAME', (1,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (1,-1), (-1,-1), 11), ('TEXTCOLOR', (1,-1), (-1,-1), accent_color),
    ]))
    elements.append(summary_table)
    
    elements.append(Spacer(1, 24 if not is_branding_on else 40))
    terms = "<b>Terms & Conditions:</b><br/>1. Quotation valid for 15 days.<br/>2. 100% advance payment required.<br/>3. Subject to local jurisdiction only."
    if not is_branding_on:
        terms += "<br/><font color='#94a3b8'><i>Tip: You can return to edit mode anytime to update product details or quantities.</i></font>"
    elements.append(Paragraph(terms, ParagraphStyle('TermsStyle', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.gray)))

    # --- WATERMARK ---
    def add_page_decorations(canvas, doc):
        if not is_branding_on:
            return

        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
        canvas.setLineWidth(0.8)
        canvas.rect(18, 18, A4[0] - 36, A4[1] - 36)

        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(A4[0] - 28, 28, f"Generated on {datetime.now().strftime('%d %b %Y %I:%M %p')} | Page {canvas.getPageNumber()}")

        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(45)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFillAlpha(0.06)
        canvas.setFont('Helvetica-Bold', 52)
        canvas.drawCentredString(0, 32, "SHREEJI CERAMICA")
        canvas.setFont('Helvetica-Bold', 24)
        canvas.drawCentredString(0, -16, "CONFIDENTIAL")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
    buffer.seek(0)
    return buffer
