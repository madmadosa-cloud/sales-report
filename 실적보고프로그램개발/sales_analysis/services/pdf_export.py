"""
PDF 보고서 출력 (xhtml2pdf — exe 패키징에 적합한 순수 Python 기반)
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

from sales_analysis.services.aggregation import SalesReport


def resolve_korean_font_path() -> Path | None:
    env_path = getattr(settings, "REPORT_FONT_PATH", "") or ""
    if env_path:
        path = Path(env_path)
        if path.is_file():
            return path

    static_fonts = Path(settings.BASE_DIR) / "static" / "fonts"
    if static_fonts.is_dir():
        for pattern in ("*.ttf", "*.otf"):
            matches = sorted(static_fonts.glob(pattern))
            if matches:
                return matches[0]

    windows_font = Path(r"C:\Windows\Fonts\malgun.ttf")
    if windows_font.is_file():
        return windows_font

    return None


def _register_pdf_font(font_path: Path | None) -> str:
    if not font_path:
        return "Helvetica"
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "ReportFont"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    return font_name


def export_report_pdf(report: SalesReport) -> bytes:
    font_path = resolve_korean_font_path()
    font_name = _register_pdf_font(font_path)
    font_url = font_path.as_uri() if font_path else ""

    html = render_to_string(
        "sales_analysis/report_pdf.html",
        {
            "report": report,
            "font_url": font_url,
            "font_name": font_name,
        },
    )

    from xhtml2pdf import pisa

    result = BytesIO()
    status = pisa.CreatePDF(html, dest=result, encoding="utf-8")
    if status.err:
        raise RuntimeError("PDF 생성 중 오류가 발생했습니다.")
    return result.getvalue()
