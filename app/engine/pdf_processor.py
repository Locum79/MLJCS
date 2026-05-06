from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
import qrcode
import io

def generate_personalized_pdf(master_pdf_path, overlay_coords, full_name, certificate_id, issuance_date):
    reader = PdfReader(master_pdf_path)
    writer = PdfWriter()
    master_page = reader.pages[0]
    
    page_w = float(master_page.mediabox.width)
    page_h = float(master_page.mediabox.height)
    
    qr = qrcode.make(f"CERT:{certificate_id}|{full_name}|{issuance_date}")
    qr_bytes = io.BytesIO()
    qr.save(qr_bytes, format='PNG')
    qr_bytes.seek(0)
    
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_w, page_h))
    
    c.setFont("Helvetica-Bold", 36)
    c.drawString(overlay_coords.get('name_x', 300), overlay_coords.get('name_y', 400), full_name)
    
    c.setFont("Helvetica", 12)
    c.drawString(overlay_coords.get('cert_id_x', 50), overlay_coords.get('cert_id_y', 50), f"ID: {certificate_id}")
    
    c.drawImage(qr_bytes, overlay_coords.get('qr_x', 450), overlay_coords.get('qr_y', 50), width=100, height=100)
    
    c.setFont("Helvetica", 10)
    c.drawString(overlay_coords.get('date_x', 50), overlay_coords.get('date_y', 30), f"Issued: {issuance_date}")
    
    c.save()
    packet.seek(0)
    
    overlay_page = PdfReader(packet).pages[0]
    master_page.merge_page(overlay_page)
    writer.add_page(master_page)
    
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
