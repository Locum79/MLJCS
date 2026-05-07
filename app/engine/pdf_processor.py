from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import qrcode
import io


def _make_qr_bytes(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def generate_personalized_pdf(
    master_pdf_path: str,
    overlay_coords: dict,
    full_name: str,
    certificate_id: str,
    issuance_date: str,
    include_qr: bool = False,
    cert_name: str = '',
    master_file_type: str = 'pdf'
) -> bytes:
    """
    Overlay participant details onto master certificate (PDF or PNG).
    Only name + cert_id + date are overlaid — all other master content untouched.
    QR is optional per participant.
    """

    # --- Load master as PDF page ---
    if master_file_type == 'png':
        # Convert PNG master to a single-page PDF in memory
        img = Image.open(master_pdf_path)
        img_w, img_h = img.size
        # A4-ish at 72dpi scaling
        scale = min(841 / img_h, 595 / img_w)
        page_w = img_w * scale
        page_h = img_h * scale

        master_buf = io.BytesIO()
        c_master = canvas.Canvas(master_buf, pagesize=(page_w, page_h))
        c_master.drawImage(ImageReader(master_pdf_path), 0, 0, width=page_w, height=page_h)
        c_master.save()
        master_buf.seek(0)
        reader = PdfReader(master_buf)
    else:
        reader = PdfReader(master_pdf_path)

    writer = PdfWriter()
    master_page = reader.pages[0]
    page_w = float(master_page.mediabox.width)
    page_h = float(master_page.mediabox.height)

    # --- Build overlay layer ---
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_w, page_h))

    # Name
    font_size = overlay_coords.get('name_font_size', 28)
    c.setFont("Helvetica-Bold", font_size)
    c.drawCentredString(
        overlay_coords.get('name_x', page_w / 2),
        overlay_coords.get('name_y', page_h * 0.45),
        full_name
    )

    # Certificate ID
    c.setFont("Helvetica", overlay_coords.get('cert_id_font_size', 10))
    c.drawString(
        overlay_coords.get('cert_id_x', 50),
        overlay_coords.get('cert_id_y', 52),
        f"ID: {certificate_id}"
    )

    # Issued date
    c.setFont("Helvetica", overlay_coords.get('date_font_size', 10))
    c.drawString(
        overlay_coords.get('date_x', 50),
        overlay_coords.get('date_y', 38),
        f"Issued: {issuance_date}"
    )

    # QR code — only if admin ticked for this participant
    if include_qr:
        qr_data = f"CERT:{certificate_id}|{full_name}|{cert_name}|PASSED|{issuance_date}"
        qr_buf = _make_qr_bytes(qr_data)
        qr_size = overlay_coords.get('qr_size', 90)
        c.drawImage(
            ImageReader(qr_buf),
            overlay_coords.get('qr_x', page_w - 110),
            overlay_coords.get('qr_y', 30),
            width=qr_size,
            height=qr_size
        )

    c.save()
    packet.seek(0)

    # --- Merge overlay onto master ---
    overlay_page = PdfReader(packet).pages[0]
    master_page.merge_page(overlay_page)
    writer.add_page(master_page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
