"""
PDF 보고서 출력 (WeasyPrint)
"""

from __future__ import annotations

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


def export_report_pdf(report: SalesReport) -> bytes:
    font_path = resolve_korean_font_path()
    font_url = font_path.as_uri() if font_path else ""

    html = render_to_string(
        "sales_analysis/report_pdf.html",
        {
            "report": report,
            "font_url": font_url,
        },
    )

    from weasyprint import HTML

    return HTML(string=html).write_pdf()
