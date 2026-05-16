from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import qrcode
import io
import os
import logging
logger = logging.getLogger(__name__)
_FONT_DIR = os.path.join(os.path.dirname(__file__), '../../static/fonts')
_DEFAULT_FONT = 'Helvetica-Bold'
_DEFAULT_FONT_REGULAR = 'Helvetica'


def _register_fonts():
    if not os.path.isdir(_FONT_DIR):
        return
    for fname in os.listdir(_FONT_DIR):
        if fname.endswith('.ttf'):
            name = fname[:-4]
            try:
                pdfmetrics.registerFont(TTFont(name, os.path.join(_FONT_DIR, fname)))
            except Exception:
                pass


_register_fonts()


def _make_qr(data: str, size: int = 90) -> io.BytesIO:
    qr = qrcode.QRCode(version=1, box_size=6, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return buf


def _auto_font_size(text: str, max_width: float, max_height: float, font_name: str, start_size: int = 32) -> int:
    from reportlab.pdfbase.pdfmetrics import stringWidth
    size = start_size
    while size > 7:
        w = stringWidth(text, font_name, size)
        if w <= max_width and size <= max_height * 1.3:
            return size
        size -= 1
    return size


def _master_to_reader(file_path: str, file_type: str) -> PdfReader:
    if file_type == 'png':
        img = Image.open(file_path)
        iw, ih = img.size
        scale = min(841.89 / ih, 595.28 / iw)
        pw, ph = (iw * scale, ih * scale)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(pw, ph))
        c.drawImage(ImageReader(file_path), 0, 0, width=pw, height=ph, preserveAspectRatio=True)
        c.save()
        buf.seek(0)
        return PdfReader(buf)
    else:
        return PdfReader(file_path)


def generate_personalized_pdf(master_pdf_path: str, overlay_coords: dict, full_name: str, certificate_id: str, issuance_date: str, include_qr: bool = True, cert_name: str = '', master_file_type: str = 'pdf', verify_url: str = '', font_name: str = None) -> bytes:
    if not os.path.isfile(master_pdf_path):
        raise FileNotFoundError(f'Master template missing: {master_pdf_path}')
    reader = _master_to_reader(master_pdf_path, master_file_type)
    writer = PdfWriter()
    master_page = reader.pages[0]
    page_w = float(master_page.mediabox.width)
    page_h = float(master_page.mediabox.height)
    name_font = font_name or _DEFAULT_FONT
    body_font = _DEFAULT_FONT_REGULAR
    try:
        from reportlab.pdfbase.pdfmetrics import stringWidth
        stringWidth('test', name_font, 12)
    except Exception:
        name_font = _DEFAULT_FONT
        body_font = _DEFAULT_FONT_REGULAR
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_w, page_h))
    name_x = overlay_coords.get('name_x', page_w / 2)
    name_y = overlay_coords.get('name_y', page_h * 0.46)
    name_w = overlay_coords.get('name_w', page_w * 0.7)
    name_h = overlay_coords.get('name_h', 50)
    name_align = overlay_coords.get('name_align', 'center')
    start_size = overlay_coords.get('name_font_size', 32)
    font_size = _auto_font_size(full_name, name_w, name_h, name_font, start_size)
    c.setFont(name_font, font_size)
    if name_align == 'center':
        c.drawCentredString(name_x, name_y, full_name)
    elif name_align == 'right':
        c.drawRightString(name_x, name_y, full_name)
    else:
        c.drawString(name_x, name_y, full_name)
    cid_x = overlay_coords.get('cert_id_x', 60)
    cid_y = overlay_coords.get('cert_id_y', 55)
    cid_size = overlay_coords.get('cert_id_font_size', 9)
    c.setFont(body_font, cid_size)
    c.drawString(cid_x, cid_y, certificate_id)
    date_x = overlay_coords.get('date_x', 60)
    date_y = overlay_coords.get('date_y', 42)
    date_size = overlay_coords.get('date_font_size', 9)
    c.setFont(body_font, date_size)
    c.drawString(date_x, date_y, issuance_date)
    qr_x = overlay_coords.get('qr_x')
    qr_y = overlay_coords.get('qr_y', 20)
    qr_size = overlay_coords.get('qr_size', 72)
    if qr_x is None:
        qr_x = page_w - qr_size - 20
    if include_qr and isinstance(qr_x, (int, float)) and (qr_x >= 0):
        qr_url = verify_url or f'CERT:{certificate_id}'
        qr_data = f'{qr_url}|{full_name}|{cert_name}|PASSED|{issuance_date}'
        qr_buf = _make_qr(qr_data)
        c.drawImage(ImageReader(qr_buf), qr_x, qr_y, width=qr_size, height=qr_size, mask='auto')
    c.save()
    packet.seek(0)
    overlay_reader = PdfReader(packet)
    master_page.merge_page(overlay_reader.pages[0])
    writer.add_page(master_page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
