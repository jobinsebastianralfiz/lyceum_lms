"""
Certificate PDF Generator for LM Academy LMS
Generates professional PDF certificates with QR code verification using ReportLab.
"""

import io
import os
import qrcode
from datetime import datetime
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch, cm, mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


class CertificatePDFGenerator:
    """
    Generates professional PDF certificates for course completion.
    """

    # LM Academy brand colors
    PRIMARY_COLOR = colors.HexColor('#2AB673')  # Green
    SECONDARY_COLOR = colors.HexColor('#1a365d')  # Dark blue/Navy
    GOLD_COLOR = colors.HexColor('#D4AF37')  # Rich Gold
    TEXT_COLOR = colors.HexColor('#1a1a2e')  # Almost black
    LIGHT_TEXT = colors.HexColor('#555555')  # Gray text

    # Page margins - increased to keep content inside border
    MARGIN = 40
    INNER_MARGIN = 55

    def __init__(self, certificate):
        self.certificate = certificate
        self.width, self.height = landscape(A4)
        self.buffer = io.BytesIO()
        self.logo_path = self._find_logo()

    def _find_logo(self):
        """Find the logo file."""
        possible_paths = [
            os.path.join(settings.BASE_DIR, 'static', 'images', 'logos', 'logo.png'),
            os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png'),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def generate(self):
        """Generate the certificate PDF and return the buffer."""
        c = canvas.Canvas(self.buffer, pagesize=landscape(A4))

        # White background
        c.setFillColor(colors.white)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)

        # Draw borders
        self._draw_borders(c)

        # Draw header with logo
        self._draw_header(c)

        # Draw certificate title
        self._draw_title(c)

        # Draw main content
        self._draw_content(c)

        # Draw footer section (dates, signature, QR, cert info)
        self._draw_footer(c)

        c.save()
        self.buffer.seek(0)
        return self.buffer

    def _draw_borders(self, c):
        """Draw decorative borders."""
        # Outer green border
        c.setStrokeColor(self.PRIMARY_COLOR)
        c.setLineWidth(4)
        c.roundRect(self.MARGIN, self.MARGIN,
                   self.width - 2*self.MARGIN,
                   self.height - 2*self.MARGIN, 8)

        # Inner gold border
        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(2)
        c.roundRect(self.MARGIN + 10, self.MARGIN + 10,
                   self.width - 2*(self.MARGIN + 10),
                   self.height - 2*(self.MARGIN + 10), 6)

        # Corner decorations
        self._draw_corners(c)

    def _draw_corners(self, c):
        """Draw corner decorations."""
        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(1.5)
        corner_size = 25
        offset = self.MARGIN + 18

        # Top-left
        c.line(offset, self.height - offset, offset + corner_size, self.height - offset)
        c.line(offset, self.height - offset, offset, self.height - offset - corner_size)

        # Top-right
        c.line(self.width - offset, self.height - offset, self.width - offset - corner_size, self.height - offset)
        c.line(self.width - offset, self.height - offset, self.width - offset, self.height - offset - corner_size)

        # Bottom-left
        c.line(offset, offset, offset + corner_size, offset)
        c.line(offset, offset, offset, offset + corner_size)

        # Bottom-right
        c.line(self.width - offset, offset, self.width - offset - corner_size, offset)
        c.line(self.width - offset, offset, self.width - offset, offset + corner_size)

    def _draw_header(self, c):
        """Draw header with logo and institution name."""
        center_x = self.width / 2
        header_y = self.height - 75

        # Draw logo
        if self.logo_path:
            try:
                logo = ImageReader(self.logo_path)
                logo_size = 50
                c.drawImage(logo, center_x - logo_size/2, header_y - 20,
                           width=logo_size, height=logo_size, mask='auto')
            except:
                self._draw_placeholder_logo(c, center_x, header_y)
        else:
            self._draw_placeholder_logo(c, center_x, header_y)

        # Institution name
        c.setFillColor(self.SECONDARY_COLOR)
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(center_x, header_y - 50, "LM ACADEMY")

    def _draw_placeholder_logo(self, c, center_x, y):
        """Draw placeholder logo."""
        c.setFillColor(self.PRIMARY_COLOR)
        c.circle(center_x, y, 25, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setStrokeColor(colors.white)
        c.setLineWidth(2)

        # Simple graduation cap
        cap_y = y
        path = c.beginPath()
        path.moveTo(center_x - 15, cap_y)
        path.lineTo(center_x, cap_y + 8)
        path.lineTo(center_x + 15, cap_y)
        path.lineTo(center_x, cap_y - 5)
        path.close()
        c.drawPath(path, fill=1)
        c.line(center_x + 10, cap_y + 4, center_x + 10, cap_y - 12)
        c.circle(center_x + 10, cap_y - 14, 2.5, fill=1)

    def _draw_title(self, c):
        """Draw certificate title with tagline and decorations."""
        center_x = self.width / 2

        # Tagline with decorative lines
        tagline_y = self.height - 140
        tagline = "Excellence in Learning"
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica-Oblique", 10)

        tagline_width = c.stringWidth(tagline, "Helvetica-Oblique", 10)
        line_len = 40

        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(1)
        c.line(center_x - tagline_width/2 - line_len - 8, tagline_y + 4,
               center_x - tagline_width/2 - 8, tagline_y + 4)
        c.line(center_x + tagline_width/2 + 8, tagline_y + 4,
               center_x + tagline_width/2 + line_len + 8, tagline_y + 4)

        c.drawCentredString(center_x, tagline_y, tagline)

        # Certificate type title
        title_y = self.height - 170
        cert_type = self.certificate.get_certificate_type_display()
        c.setFillColor(self.SECONDARY_COLOR)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(center_x, title_y, f"CERTIFICATE OF {cert_type.upper()}")

    def _draw_content(self, c):
        """Draw main certificate content."""
        center_x = self.width / 2

        # "This is to certify that"
        y = self.height - 200
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica-Oblique", 12)
        c.drawCentredString(center_x, y, "This is to certify that")

        # Student name
        student_name = (self.certificate.student.get_full_name() or
                       self.certificate.student.name or
                       self.certificate.student.email)

        y -= 30
        c.setFillColor(self.SECONDARY_COLOR)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(center_x, y, student_name)

        # Gold underline
        name_width = c.stringWidth(student_name, "Helvetica-Bold", 30)
        c.setStrokeColor(self.GOLD_COLOR)
        c.setLineWidth(2)
        c.line(center_x - name_width/2 - 15, y - 8,
               center_x + name_width/2 + 15, y - 8)

        # "has successfully completed"
        y -= 28
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica-Oblique", 12)
        c.drawCentredString(center_x, y, "has successfully completed the course")

        # Course title
        y -= 26
        c.setFillColor(self.PRIMARY_COLOR)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(center_x, y, self.certificate.course.title)

        # Description
        if self.certificate.description:
            y -= 18
            c.setFillColor(self.LIGHT_TEXT)
            c.setFont("Helvetica", 9)
            desc = self.certificate.description[:100]
            if len(self.certificate.description) > 100:
                desc += "..."
            c.drawCentredString(center_x, y, desc)

        # Score and Grade boxes
        self._draw_achievements(c, y - 30)

    def _draw_achievements(self, c, y):
        """Draw score and grade boxes."""
        center_x = self.width / 2
        has_score = self.certificate.final_score is not None
        has_grade = bool(self.certificate.grade_display)

        if not has_score and not has_grade:
            return

        box_width = 90
        box_height = 40
        gap = 25

        if has_score and has_grade:
            start_x = center_x - box_width - gap/2
        else:
            start_x = center_x - box_width/2

        if has_score:
            self._draw_achievement_box(c, start_x, y, box_width, box_height,
                                      "SCORE", f"{self.certificate.final_score}%")
            start_x += box_width + gap

        if has_grade:
            self._draw_achievement_box(c, start_x, y, box_width, box_height,
                                      "GRADE", self.certificate.grade_display)

    def _draw_achievement_box(self, c, x, y, width, height, label, value):
        """Draw a styled achievement box."""
        # Background
        c.setFillColor(colors.HexColor('#f0f9f4'))
        c.setStrokeColor(self.PRIMARY_COLOR)
        c.setLineWidth(1)
        c.roundRect(x, y - height, width, height, 4, fill=1, stroke=1)

        # Label
        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + width/2, y - 12, label)

        # Value
        c.setFillColor(self.PRIMARY_COLOR)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(x + width/2, y - 32, value)

    def _draw_footer(self, c):
        """Draw footer with dates, signature, QR code, and certificate info."""
        # Draw a subtle separator line
        center_x = self.width / 2
        sep_y = 135
        c.setStrokeColor(colors.HexColor('#dddddd'))
        c.setLineWidth(0.5)
        c.line(self.INNER_MARGIN + 20, sep_y, self.width - self.INNER_MARGIN - 20, sep_y)

        footer_y = 105

        # Left section - Dates
        date_x = self.INNER_MARGIN + 55

        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 7)
        c.drawCentredString(date_x, footer_y + 20, "DATE OF COMPLETION")

        c.setFillColor(self.TEXT_COLOR)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(date_x, footer_y + 6,
                           self.certificate.completion_date.strftime("%B %d, %Y"))

        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 7)
        c.drawCentredString(date_x, footer_y - 12, "DATE OF ISSUE")

        c.setFillColor(self.TEXT_COLOR)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(date_x, footer_y - 26,
                           self.certificate.issue_date.strftime("%B %d, %Y"))

        # Center section - Certificate info
        c.setFillColor(self.SECONDARY_COLOR)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(center_x, footer_y + 10,
                           f"Certificate No: {self.certificate.certificate_number}")

        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 7)
        c.drawCentredString(center_x, footer_y - 5,
                           f"Verification: {self.certificate.verification_code[:24]}...")

        c.setFont("Helvetica", 8)
        c.setFillColor(self.PRIMARY_COLOR)
        c.drawCentredString(center_x, footer_y - 22,
                           "www.lmacademy.info")

        # Right section - Signature (if exists)
        if self.certificate.signed_by:
            sig_x = self.width - self.INNER_MARGIN - 130

            c.setFillColor(self.LIGHT_TEXT)
            c.setFont("Helvetica", 7)
            c.drawCentredString(sig_x, footer_y + 20, "AUTHORIZED SIGNATURE")

            c.setStrokeColor(self.TEXT_COLOR)
            c.setLineWidth(0.8)
            c.line(sig_x - 50, footer_y + 5, sig_x + 50, footer_y + 5)

            c.setFillColor(self.TEXT_COLOR)
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(sig_x, footer_y - 10, self.certificate.signed_by)

            if self.certificate.signed_by_title:
                c.setFillColor(self.LIGHT_TEXT)
                c.setFont("Helvetica", 8)
                c.drawCentredString(sig_x, footer_y - 24, self.certificate.signed_by_title)

        # QR Code - far right
        qr_x = self.width - self.INNER_MARGIN - 35
        self._draw_qr_code(c, qr_x, footer_y)

    def _draw_qr_code(self, c, x, y):
        """Draw QR code for verification."""
        verification_url = f"{settings.FRONTEND_URL}/admin/certificates/verify/{self.certificate.verification_code}/"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=1,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#1a1a2e", back_color="white")

        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        qr_size = 45
        qr_image = ImageReader(qr_buffer)
        c.drawImage(qr_image, x - qr_size/2, y - qr_size/2 + 5,
                   width=qr_size, height=qr_size)

        c.setFillColor(self.LIGHT_TEXT)
        c.setFont("Helvetica", 6)
        c.drawCentredString(x, y - qr_size/2 - 5, "Scan to Verify")


def generate_certificate_pdf(certificate):
    """
    Generate a PDF certificate for the given certificate object.

    Args:
        certificate: Certificate model instance

    Returns:
        BytesIO buffer containing the PDF
    """
    generator = CertificatePDFGenerator(certificate)
    return generator.generate()
