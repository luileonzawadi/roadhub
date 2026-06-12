import io
from datetime import datetime

# Fallback block to prevent the app from failing to start if ReportLab is missing
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

def generate_certificate_pdf(student_name, course_title, cert_code, issue_date=None):
    """
    Generates a professional engineering certificate of completion in PDF format.
    Returns: BytesIO buffer containing the PDF bytes.
    """
    buffer = io.BytesIO()
    
    if not REPORTLAB_AVAILABLE:
        # Fallback to a simple text file styled as a certificate if ReportLab isn't installed
        buffer.write(f"==================================================\n".encode())
        buffer.write(f"               ROADSHUB ACADEMY                   \n".encode())
        buffer.write(f"          CERTIFICATE OF COMPLETION               \n".encode())
        buffer.write(f"==================================================\n\n".encode())
        buffer.write(f"This certifies that {student_name} has successfully\n".encode())
        buffer.write(f"completed the program:\n".encode())
        buffer.write(f"  --> {course_title}\n\n".encode())
        buffer.write(f"Verification Code: {cert_code}\n".encode())
        buffer.write(f"Issued On: {issue_date or datetime.now().strftime('%Y-%m-%d')}\n".encode())
        buffer.write(f"==================================================\n".encode())
        buffer.seek(0)
        return buffer

    # Date formatting
    if not issue_date:
        issue_date_str = datetime.now().strftime('%B %d, %Y')
    elif isinstance(issue_date, str):
        issue_date_str = issue_date
    else:
        issue_date_str = issue_date.strftime('%B %d, %Y')

    # Dimensions for landscape Letter
    width, height = landscape(letter)  # 792 x 612
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    
    # 1. Dark Navy Base Background (#0A1628)
    c.setFillColor(colors.HexColor('#0A1628'))
    c.rect(0, 0, width, height, fill=True, stroke=False)
    
    # 2. Outer Border: Orange (#F57C00)
    c.setStrokeColor(colors.HexColor('#F57C00'))
    c.setLineWidth(5)
    c.rect(20, 20, width - 40, height - 40, fill=False, stroke=True)
    
    # 3. Inner Border: White Accent
    c.setStrokeColor(colors.HexColor('#FFFFFF'))
    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60, fill=False, stroke=True)
    
    # 4. Corner Geometric Decoration (Teal #00BCD4 & Orange #F57C00)
    c.setFillColor(colors.HexColor('#00BCD4'))
    c.rect(30, height - 50, 20, 20, fill=True, stroke=False)  # Top-left Teal
    c.rect(width - 50, 30, 20, 20, fill=True, stroke=False)   # Bottom-right Teal
    
    c.setFillColor(colors.HexColor('#F57C00'))
    c.rect(width - 50, height - 50, 20, 20, fill=True, stroke=False)  # Top-right Orange
    c.rect(30, 30, 20, 20, fill=True, stroke=False)                   # Bottom-left Orange

    # 5. Header Title
    c.setFillColor(colors.HexColor('#FFFFFF'))
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width / 2.0, height - 120, "ROADSHUB ACADEMY")
    
    c.setFillColor(colors.HexColor('#00BCD4'))
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2.0, height - 160, "PROFESSIONAL TRAINING CERTIFICATE")
    
    # 6. Presentation text
    c.setFillColor(colors.HexColor('#94A3B8'))
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2.0, height - 220, "This is to certify that infrastructure professional")
    
    # 7. Student Name (Large Orange Headliner)
    c.setFillColor(colors.HexColor('#F57C00'))
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2.0, height - 270, student_name)
    
    # 8. Achievement Details
    c.setFillColor(colors.HexColor('#E2E8F0'))
    c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2.0, height - 320, "has completed all milestone assessments, laboratory workflows, and quizzes for")
    
    # 9. Course Title
    c.setFillColor(colors.HexColor('#FFFFFF'))
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2.0, height - 365, course_title)
    
    # 10. Autodesk Certified Professional Ready stamp if course is ACP
    c.setFillColor(colors.HexColor('#00BCD4'))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2.0, height - 400, "AUTODESK ACP PREPARATION CURRICULUM APPROVED")
    
    # 11. Signatures
    # Left Line
    c.setStrokeColor(colors.HexColor('#475569'))
    c.setLineWidth(1)
    c.line(80, 130, 250, 130)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor('#FFFFFF'))
    c.drawString(110, 110, "Director of Academics")
    
    # Right Line
    c.line(width - 250, 130, width - 80, 130)
    c.drawRightString(width - 110, 110, "Examining Engineer")
    
    # 12. Verification & Dates Footer
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor('#94A3B8'))
    c.drawString(80, 65, f"Date of Issue: {issue_date_str}")
    c.drawRightString(width - 80, 65, f"Verification Code: {cert_code}")
    c.drawCentredString(width / 2.0, 65, "Verify this credential status at: roadshub.com/verify")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer
