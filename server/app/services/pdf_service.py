import io
import uuid
from datetime import datetime
import qrcode
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, inch
from reportlab.pdfgen import canvas
from app.core.config import settings
from app.core.logging import logger

# SiliconBrains University brand colors (Docs/design.md & Docs/rules.md §19)
# Bordo: #6C151E | Green: #0F3D3A | Cream: #F5DABF | Ink: #092A28
COLOR_BORDO = colors.HexColor("#6C151E")
COLOR_GREEN = colors.HexColor("#0F3D3A")
COLOR_GREEN_DARK = colors.HexColor("#08211F")
COLOR_CREAM = colors.HexColor("#F5DABF")
COLOR_CREAM_LIGHT = colors.HexColor("#FDF7F0")
COLOR_INK = colors.HexColor("#092A28")
COLOR_INK_MUTED = colors.HexColor("#4A6B68")
COLOR_WHITE = colors.HexColor("#FFFFFF")
COLOR_SUCCESS = colors.HexColor("#1A7F48")
COLOR_DANGER = colors.HexColor("#BA1A1A")


def generate_qr_image(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F3D3A", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


class PDFService:
    @staticmethod
    def render_certificate_pdf(
        student_name: str,
        student_code: str,
        course_title: str,
        certificate_code: str,
        final_percentage: float,
        issued_at: datetime,
    ) -> bytes:
        """
        Generates an official A4 landscape SiliconBrains University certificate.
        Design: Cream background, double green border, Bordo highlights,
        central seal, verify QR code bottom-right.
        """
        buffer = io.BytesIO()
        width, height = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))

        # 1. Background
        c.setFillColor(COLOR_CREAM_LIGHT)
        c.rect(0, 0, width, height, fill=1, stroke=0)

        # 2. Double Border (Outer 3pt, Inner 1pt)
        c.setStrokeColor(COLOR_GREEN)
        c.setLineWidth(3.0)
        c.rect(1.2 * cm, 1.2 * cm, width - 2.4 * cm, height - 2.4 * cm)

        c.setLineWidth(1.0)
        c.rect(1.5 * cm, 1.5 * cm, width - 3.0 * cm, height - 3.0 * cm)

        # 3. Header
        c.setFillColor(COLOR_GREEN)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2.0, height - 3.2 * cm, "SBUNIVERSITY")

        c.setFont("Helvetica", 10)
        c.setFillColor(COLOR_INK_MUTED)
        c.drawCentredString(width / 2.0, height - 3.8 * cm, "OFFICIAL CERTIFICATE OF COURSE COMPLETION")

        # 4. Title
        c.setFillColor(COLOR_GREEN_DARK)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(width / 2.0, height - 5.5 * cm, "CERTIFICATE OF EXCELLENCE")

        # 5. Body Presentation
        c.setFont("Helvetica", 12)
        c.setFillColor(COLOR_INK)
        c.drawCentredString(width / 2.0, height - 6.8 * cm, "This is proudly presented to")

        # Student Name (Large Bordo)
        c.setFillColor(COLOR_BORDO)
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(width / 2.0, height - 8.2 * cm, student_name.upper())

        # Subtext
        c.setFont("Helvetica", 11)
        c.setFillColor(COLOR_INK_MUTED)
        c.drawCentredString(width / 2.0, height - 9.1 * cm, f"Student ID: {student_code}")

        c.setFont("Helvetica", 13)
        c.setFillColor(COLOR_INK)
        c.drawCentredString(
            width / 2.0,
            height - 10.6 * cm,
            f"for successfully completing all academic requirements and exams for the course",
        )

        # Course Title (Green)
        c.setFillColor(COLOR_GREEN)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width / 2.0, height - 11.8 * cm, f'"{course_title}"')

        c.setFont("Helvetica", 12)
        c.setFillColor(COLOR_INK)
        c.drawCentredString(
            width / 2.0,
            height - 12.9 * cm,
            f"with an overall grade performance of {final_percentage:.1f}%",
        )

        # 6. Center Seal (Circular Bordo)
        seal_x = width / 2.0
        seal_y = 4.2 * cm
        c.setFillColor(COLOR_BORDO)
        c.circle(seal_x, seal_y, 1.2 * cm, fill=1, stroke=0)
        c.setStrokeColor(COLOR_CREAM)
        c.setLineWidth(1.5)
        c.circle(seal_x, seal_y, 1.05 * cm, fill=0, stroke=1)
        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(seal_x, seal_y + 0.3 * cm, "SEAL OF")
        c.drawCentredString(seal_x, seal_y - 0.1 * cm, "ACADEMIC")
        c.drawCentredString(seal_x, seal_y - 0.5 * cm, "EXCELLENCE")

        # 7. Signature Line (Left)
        sig_x = 4.0 * cm
        c.setStrokeColor(COLOR_GREEN)
        c.setLineWidth(1.0)
        c.line(sig_x, 3.8 * cm, sig_x + 5.0 * cm, 3.8 * cm)
        c.setFillColor(COLOR_INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(sig_x + 0.5 * cm, 3.3 * cm, "Office of Academic Affairs")
        c.setFont("Helvetica", 8)
        c.setFillColor(COLOR_INK_MUTED)
        c.drawString(sig_x + 0.5 * cm, 2.9 * cm, f"Issued: {issued_at.strftime('%B %d, %Y')}")

        # 8. QR Code and Verification (Right)
        verify_url = f"{settings.FRONTEND_ORIGIN}/verify/{certificate_code}"
        qr_buf = generate_qr_image(verify_url)
        qr_img = Image.open(qr_buf)
        qr_x = width - 6.5 * cm
        qr_y = 2.4 * cm
        c.drawInlineImage(qr_img, qr_x, qr_y, width=2.4 * cm, height=2.4 * cm)

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(COLOR_INK)
        c.drawString(qr_x - 0.2 * cm, 2.0 * cm, f"Code: {certificate_code}")
        c.setFont("Helvetica", 7)
        c.setFillColor(COLOR_INK_MUTED)
        c.drawString(qr_x - 0.2 * cm, 1.6 * cm, "Scan or visit site to verify")

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def render_result_pdf(
        student_name: str,
        student_code: str,
        exam_title: str,
        course_title: str,
        score: float,
        total_marks: float,
        percentage: float,
        grade: str,
        passed: bool,
        time_taken_sec: int,
        rank_in_exam: int,
        submitted_at: datetime,
    ) -> bytes:
        """
        Generates an official A4 portrait SiliconBrains University exam result statement.
        Design: White page, green top band, cream accents, pass pill,
        score in Bordo, verification footer.
        """
        buffer = io.BytesIO()
        width, height = A4
        c = canvas.Canvas(buffer, pagesize=A4)

        # 1. Top Green Banner
        c.setFillColor(COLOR_GREEN)
        c.rect(0, height - 3.5 * cm, width, 3.5 * cm, fill=1, stroke=0)

        # Header Title
        c.setFillColor(COLOR_CREAM)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(2.0 * cm, height - 1.8 * cm, "SBUNIVERSITY")

        c.setFont("Helvetica", 11)
        c.setFillColor(COLOR_WHITE)
        c.drawString(2.0 * cm, height - 2.6 * cm, "Official Academic Examination Report")

        # 2. Student & Exam Details Box
        c.setFillColor(COLOR_CREAM_LIGHT)
        c.rect(1.8 * cm, height - 8.2 * cm, width - 3.6 * cm, 4.0 * cm, fill=1, stroke=0)
        c.setStrokeColor(COLOR_CREAM)
        c.setLineWidth(1.0)
        c.rect(1.8 * cm, height - 8.2 * cm, width - 3.6 * cm, 4.0 * cm, fill=0, stroke=1)

        c.setFillColor(COLOR_INK)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2.4 * cm, height - 5.0 * cm, "Student Name:")
        c.drawString(2.4 * cm, height - 5.8 * cm, "Student Code:")
        c.drawString(2.4 * cm, height - 6.6 * cm, "Course:")
        c.drawString(2.4 * cm, height - 7.4 * cm, "Examination:")

        c.setFont("Helvetica", 11)
        c.drawString(5.8 * cm, height - 5.0 * cm, student_name)
        c.drawString(5.8 * cm, height - 5.8 * cm, student_code)
        c.drawString(5.8 * cm, height - 6.6 * cm, course_title)
        c.drawString(5.8 * cm, height - 7.4 * cm, exam_title)

        # 3. Score Highlight Card
        card_y = height - 13.8 * cm
        c.setFillColor(COLOR_WHITE)
        c.rect(1.8 * cm, card_y, width - 3.6 * cm, 4.8 * cm, fill=1, stroke=0)
        c.setStrokeColor(COLOR_GREEN)
        c.setLineWidth(1.5)
        c.rect(1.8 * cm, card_y, width - 3.6 * cm, 4.8 * cm, fill=0, stroke=1)

        # Pass / Fail Pill
        pill_color = COLOR_SUCCESS if passed else COLOR_DANGER
        c.setFillColor(pill_color)
        c.roundRect(width - 5.8 * cm, card_y + 3.8 * cm, 3.2 * cm, 0.7 * cm, 4, fill=1, stroke=0)
        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", 9)
        status_text = "PASSED" if passed else "FAILED"
        c.drawCentredString(width - 4.2 * cm, card_y + 4.0 * cm, status_text)

        # Main Score
        c.setFillColor(COLOR_BORDO)
        c.setFont("Helvetica-Bold", 34)
        c.drawString(2.4 * cm, card_y + 2.8 * cm, f"{score:g} / {total_marks:g}")

        c.setFillColor(COLOR_INK_MUTED)
        c.setFont("Helvetica", 11)
        c.drawString(2.4 * cm, card_y + 2.0 * cm, f"Percentage: {percentage:.1f}%   |   Grade Awarded: {grade}")

        # Metrics Breakdown
        mins = time_taken_sec // 60
        secs = time_taken_sec % 60
        time_str = f"{mins}m {secs}s"
        c.setFont("Helvetica", 10)
        c.setFillColor(COLOR_INK)
        c.drawString(2.4 * cm, card_y + 0.8 * cm, f"Time Taken: {time_str}      Rank in Exam: #{rank_in_exam}      Date: {submitted_at.strftime('%Y-%m-%d %H:%M')}")

        # 4. Summary & Verification Footer
        c.setFillColor(COLOR_INK_MUTED)
        c.setFont("Helvetica", 9)
        c.drawString(2.0 * cm, 2.5 * cm, "This document is computer-generated by the SiliconBrains University examination system.")
        c.drawString(2.0 * cm, 2.0 * cm, "Results and certifications are governed under the institutional academic policy.")

        c.setStrokeColor(COLOR_GREEN)
        c.setLineWidth(0.5)
        c.line(2.0 * cm, 1.5 * cm, width - 2.0 * cm, 1.5 * cm)

        c.setFont("Helvetica", 8)
        c.drawString(2.0 * cm, 1.0 * cm, "SiliconBrains University Academic Portal")

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
