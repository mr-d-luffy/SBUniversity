import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

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

RESULT_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "result"
RESULT_TEMPLATE = RESULT_ASSETS / "SiliconBrains_Result_Template.pdf"
CERTIFICATE_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "certificate"
CERTIFICATE_TEMPLATE = CERTIFICATE_ASSETS / "SiliconBrains_Certificate_Template.pdf"

CERTIFICATE_PAGE_W = 595.2755905511812
CERTIFICATE_LINE_L, CERTIFICATE_LINE_R = 92.0, CERTIFICATE_PAGE_W - 92.0
CERTIFICATE_CODE_BOX = {
    "x": 74.0,
    "y": 42.0,
    "w": 150.0,
    "h": 15.0,
    "prefix": "SB-2026-",
    "baseline": 46.6,
    "prefix_font": "CertificateCinzelBold",
    "prefix_size": 8.2,
    "prefix_char_space": 1.2,
    "prefix_x_pad": 6.0,
    "line_gap": 4.0,
    "right_pad": 6.0,
}


def _register_result_fonts() -> None:
    if "ResultCinzel" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ResultCinzel", str(RESULT_ASSETS / "fonts" / "Cinzel-Bold.ttf")))
    if "ResultPinyon" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ResultPinyon", str(RESULT_ASSETS / "fonts" / "PinyonScript-Regular.ttf")))


def _register_certificate_fonts() -> None:
    fonts = {
        "CertificateCinzelBold": "Cinzel-Bold.ttf",
        "CertificateCinzelMedium": "Cinzel-Medium.ttf",
        "CertificateName": "PinyonScript-Regular.ttf",
    }
    registered = set(pdfmetrics.getRegisteredFontNames())
    for font_name, filename in fonts.items():
        if font_name not in registered:
            pdfmetrics.registerFont(TTFont(font_name, str(CERTIFICATE_ASSETS / "fonts" / filename)))


def _certificate_text_width(text: str, font: str, size: float, char_space: float = 0.0) -> float:
    return pdfmetrics.stringWidth(text, font, size) + char_space * max(len(text) - 1, 0)


def _fit_certificate_text(
    text: str,
    font: str,
    max_size: float,
    max_width: float,
    min_size: float = 6.0,
    char_space: float = 0.0,
) -> float:
    size = max_size
    while size >= min_size:
        if _certificate_text_width(text, font, size, char_space) <= max_width:
            return size
        size -= 0.25
    raise ValueError(f"Certificate value is too long to fit its template field: {text!r}")


def _certificate_cap_height(font: str, size: float) -> float:
    face = pdfmetrics.getFont(font).face
    return (getattr(face, "capHeight", 700) or 700) * size / 1000.0


def _draw_certificate_text(
    c: canvas.Canvas,
    text: str,
    font: str,
    size: float,
    center_x: float,
    baseline: float,
    color: colors.Color,
    char_space: float = 0.0,
) -> None:
    text_object = c.beginText(center_x - _certificate_text_width(text, font, size, char_space) / 2, baseline)
    text_object.setFont(font, size)
    text_object.setCharSpace(char_space)
    text_object.setFillColor(color)
    text_object.textOut(text)
    c.drawText(text_object)


def _exact_number(value: float | Decimal) -> str:
    """Render the stored numeric value without rounding it for the result sheet."""
    number = Decimal(str(value))
    return format(number, "f").rstrip("0").rstrip(".") if "." in format(number, "f") else format(number, "f")


def _fit_text(c: canvas.Canvas, text: str, font: str, max_size: float, max_width: float, min_size: float = 5) -> float:
    size = max_size
    while size > min_size and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 0.25
    if pdfmetrics.stringWidth(text, font, size) > max_width:
        raise ValueError(f"Result value does not fit the supplied template: {text!r}")
    c.setFont(font, size)
    return size


class PDFService:
    @staticmethod
    def render_certificate_pdf(
        student_name: str,
        student_code: str,
        course_title: str,
        certificate_code: str,
        final_percentage: float | Decimal,
        issued_at: datetime,
    ) -> bytes:
        """Fill the supplied certificate template with saved certificate values."""
        if not CERTIFICATE_TEMPLATE.is_file():
            raise FileNotFoundError(f"Certificate PDF template is missing: {CERTIFICATE_TEMPLATE}")
        _register_certificate_fonts()

        template_reader = PdfReader(str(CERTIFICATE_TEMPLATE))
        page = template_reader.pages[0]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        center_x = page_width / 2
        overlay = io.BytesIO()
        c = canvas.Canvas(overlay, pagesize=(page_width, page_height))

        name = " ".join(str(student_name).split())
        name_size = _fit_certificate_text(
            name, "CertificateName", 32, (CERTIFICATE_LINE_R - CERTIFICATE_LINE_L) - 24, min_size=16
        )
        _draw_certificate_text(c, name, "CertificateName", name_size, center_x, 490.5, colors.HexColor("#051F20"))

        subject = " ".join(str(course_title).split())
        subject_size = _fit_certificate_text(
            subject, "CertificateCinzelMedium", 17, (CERTIFICATE_LINE_R - CERTIFICATE_LINE_L) - 24,
            min_size=9, char_space=1.0,
        )
        _draw_certificate_text(
            c, subject, "CertificateCinzelMedium", subject_size, center_x, 409.0,
            colors.HexColor("#0B2B26"), char_space=1.0,
        )

        percentage_text = f"{format(Decimal(str(final_percentage)), 'f')}%"
        score_box = {"x": page_width / 2 - 75, "y": 306.0, "w": 150.0, "h": 38.0}
        score_size = _fit_certificate_text(
            percentage_text, "CertificateCinzelBold", 20, score_box["w"] - 24, min_size=9, char_space=1.0
        )
        score_baseline = score_box["y"] + score_box["h"] / 2 - _certificate_cap_height(
            "CertificateCinzelBold", score_size
        ) / 2
        _draw_certificate_text(
            c, percentage_text, "CertificateCinzelBold", score_size,
            score_box["x"] + score_box["w"] / 2, score_baseline, colors.HexColor("#051F20"), char_space=1.0,
        )

        date_text = f"{issued_at.day} {issued_at.strftime('%B %Y')}"
        date_box = {"x": page_width - 74 - 110, "y": 42.0, "w": 110.0, "h": 15.0}
        date_size = _fit_certificate_text(
            date_text, "CertificateCinzelBold", 8.2, date_box["w"] - 12, min_size=5.5, char_space=0.6
        )
        date_baseline = date_box["y"] + date_box["h"] / 2 - _certificate_cap_height(
            "CertificateCinzelBold", date_size
        ) / 2
        _draw_certificate_text(
            c, date_text, "CertificateCinzelBold", date_size,
            date_box["x"] + date_box["w"] / 2, date_baseline, colors.HexColor("#163832"), char_space=0.6,
        )

        code = str(certificate_code).strip().upper()
        code_box = CERTIFICATE_CODE_BOX
        code_center_x = code_box["x"] + code_box["w"] / 2
        if code.startswith(code_box["prefix"]):
            code_suffix = code.removeprefix(code_box["prefix"])
            prefix_width = _certificate_text_width(
                code_box["prefix"], code_box["prefix_font"], code_box["prefix_size"],
            ) + code_box["prefix_char_space"]
            span_left = code_box["x"] + code_box["prefix_x_pad"] + prefix_width + code_box["line_gap"]
            span_right = code_box["x"] + code_box["w"] - code_box["right_pad"]
            code_size = _fit_certificate_text(
                code_suffix, code_box["prefix_font"], code_box["prefix_size"],
                span_right - span_left - 2, min_size=5.5, char_space=code_box["prefix_char_space"],
            )
            code_center_x = (span_left + span_right) / 2
        else:
            # Older records use SBU-CERT-...; replace only the template's printed
            # prefix so the visible code stays exactly verifiable against the DB.
            c.setFillColor(colors.white)
            c.rect(code_box["x"], code_box["y"], code_box["w"], code_box["h"], fill=1, stroke=0)
            code_suffix = code
            code_size = _fit_certificate_text(
                code_suffix, code_box["prefix_font"], code_box["prefix_size"],
                code_box["w"] - 12, min_size=5.5, char_space=0.6,
            )
        _draw_certificate_text(
            c, code_suffix, code_box["prefix_font"], code_size, code_center_x,
            code_box["baseline"], colors.HexColor("#163832"),
            char_space=code_box["prefix_char_space"] if code.startswith(code_box["prefix"]) else 0.6,
        )

        c.save()
        overlay.seek(0)
        page.merge_page(PdfReader(overlay).pages[0])
        writer = PdfWriter()
        writer.add_page(page)
        writer.add_metadata({
            "/Title": f"Certificate of Completion - {name}",
            "/Author": "SiliconBrains University",
            "/Subject": subject,
        })
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

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
        """Fill the supplied result sheet using the result row's persisted values."""
        if not RESULT_TEMPLATE.is_file():
            raise FileNotFoundError(f"Result PDF template is missing: {RESULT_TEMPLATE}")
        _register_result_fonts()

        overlay = io.BytesIO()
        page_width, page_height = 595.2756, 841.8898
        c = canvas.Canvas(overlay, pagesize=(page_width, page_height))
        c.setFillColor(colors.HexColor("#172321"))

        # Student name and student code positions from the supplied generator.
        name_font = "ResultPinyon"
        _fit_text(c, student_name, name_font, 24, 250)
        c.drawCentredString(221, 488.5, student_name)
        code = student_code
        code = code.removeprefix("SBU-2026-").removeprefix("SB-2026-")
        _fit_text(c, code, "ResultCinzel", 11, 121)
        c.drawCentredString((372 + 503.2756) / 2, 486.5, code)

        # The source layout supports six subjects. This result download represents
        # one exam, so it uses one row and preserves its exact stored score/maximum.
        subject = f"{course_title} - {exam_title}" if course_title else exam_title
        columns = [62, 100, 340, 432, 533.2756]
        _fit_text(c, "1", "ResultCinzel", 9, columns[1] - columns[0] - 8)
        c.drawCentredString((columns[0] + columns[1]) / 2, 419, "1")
        _fit_text(c, subject, "ResultCinzel", 8, columns[2] - columns[1] - 8, min_size=4)
        c.drawCentredString((columns[1] + columns[2]) / 2, 419, subject)
        score_text = f"{_exact_number(score)} / {_exact_number(total_marks)}"
        _fit_text(c, score_text, "ResultCinzel", 8, columns[3] - columns[2] - 8)
        c.drawCentredString((columns[2] + columns[3]) / 2, 419, score_text)
        status_text = "PASS" if passed else "FAIL"
        _fit_text(c, status_text, "ResultCinzel", 8, columns[4] - columns[3] - 8)
        c.drawCentredString((columns[3] + columns[4]) / 2, 419, status_text)

        # Summary boxes retain the stored percentage and grade; never recompute them.
        summary_y = 252
        summary_values = [
            score_text,
            f"{_exact_number(percentage)}%  |  {grade}",
            status_text,
        ]
        box_left, box_right = 62, 533.2756
        box_width = (box_right - box_left - 30) / 3
        for index, text in enumerate(summary_values):
            center_x = box_left + index * (box_width + 15) + box_width / 2
            _fit_text(c, text, "ResultCinzel", 10, box_width - 16)
            c.drawCentredString(center_x, summary_y, text)

        # The template has a fixed ten-character result code and date field.
        date_text = submitted_at.strftime("%d %b %Y")
        c.setFillColor(colors.HexColor("#172321"))
        _fit_text(c, date_text, "ResultCinzel", 10, 106)
        c.drawCentredString((413.2756 + 519.2756) / 2, 163, date_text)
        c.save()
        overlay.seek(0)

        writer = PdfWriter(clone_from=str(RESULT_TEMPLATE))
        page = writer.pages[0]
        if "/Annots" in page:
            del page["/Annots"]
        if "/AcroForm" in writer._root_object:
            del writer._root_object["/AcroForm"]
        page.merge_page(PdfReader(overlay).pages[0])
        writer.add_metadata({"/Title": f"Result - {student_name}", "/Author": "SiliconBrains University"})
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
