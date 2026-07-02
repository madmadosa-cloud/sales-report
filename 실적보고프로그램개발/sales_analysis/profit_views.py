from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from sales_analysis.models import ProfitRecord
from sales_analysis.services.profit_aggregation import ProfitReport, build_profit_report
from sales_analysis.services.profit_export import (
    build_profit_download_filename,
    export_profit_excel,
    export_profit_pdf,
)
from sales_analysis.services.profit_import_service import (
    get_stored_profit_summary,
    process_profit_upload,
)


def _session_key(request) -> str:
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key or ""


def _get_profit_report_from_session(request) -> ProfitReport | None:
    params = request.session.get("last_profit_report")
    if not params or not ProfitRecord.objects.exists():
        return None
    return build_profit_report(
        welfare=params.get("welfare", False),
        final=params.get("final", False),
    )


@require_GET
def profit_index(request):
    stored = get_stored_profit_summary()
    last_report = None
    if request.session.get("last_profit_report") and stored:
        params = request.session["last_profit_report"]
        last_report = build_profit_report(
            welfare=params.get("welfare", False),
            final=params.get("final", False),
        )
    return render(
        request,
        "sales_analysis/profit_index.html",
        {
            "stored_summary": stored,
            "last_report": last_report,
        },
    )


@require_POST
def upload_profit(request):
    files = request.FILES.getlist("files")
    period_label = request.POST.get("period_label", "").strip()
    if not files:
        return render(
            request,
            "sales_analysis/partials/profit_upload_status.html",
            {"error": "업로드할 CSV 파일을 선택하세요."},
        )
    if not period_label:
        return render(
            request,
            "sales_analysis/partials/profit_upload_status.html",
            {"error": "조회기간(표시용)을 입력하세요. 예: 2026/01/01~06/30"},
        )

    try:
        result = process_profit_upload(
            _session_key(request),
            files,
            period_label,
            confirmed=False,
        )
    except ValueError as exc:
        return render(
            request,
            "sales_analysis/partials/profit_upload_status.html",
            {"error": str(exc)},
        )

    if result["status"] == "confirm_needed":
        return render(
            request,
            "sales_analysis/partials/profit_confirm_replace.html",
            {
                "warnings": result.get("warnings", []),
                "total_rows": result["total_rows"],
                "period_label": result.get("period_label", period_label),
            },
        )

    messages.success(request, f"{result['count']}건의 이익 데이터를 저장했습니다.")
    request.session.pop("last_profit_report", None)
    return render(
        request,
        "sales_analysis/partials/profit_upload_status.html",
        {
            "success": True,
            "count": result["count"],
            "warnings": result.get("warnings", []),
            "stored_summary": get_stored_profit_summary(),
        },
    )


@require_POST
def confirm_profit_upload(request):
    result = process_profit_upload(_session_key(request), [], "", confirmed=True)
    if result["status"] == "no_pending":
        return render(
            request,
            "sales_analysis/partials/profit_upload_status.html",
            {"error": "대기 중인 업로드 데이터가 없습니다. 파일을 다시 선택해 주세요."},
        )

    messages.success(request, f"{result['count']}건 저장 완료 (기존 이익자료 교체)")
    request.session.pop("last_profit_report", None)
    return render(
        request,
        "sales_analysis/partials/profit_upload_status.html",
        {
            "success": True,
            "count": result["count"],
            "stored_summary": get_stored_profit_summary(),
        },
    )


def _generate_profit_report_response(
    request, *, welfare: bool = False, final: bool = False
):
    if not ProfitRecord.objects.exists():
        return render(
            request,
            "sales_analysis/partials/profit_report_preview.html",
            {"error": "저장된 이익자료가 없습니다. 먼저 CSV를 업로드하세요."},
        )

    report = build_profit_report(welfare=welfare, final=final)
    request.session["last_profit_report"] = {"welfare": welfare, "final": final}
    return render(
        request,
        "sales_analysis/partials/profit_report_preview.html",
        {"report": report},
    )


@require_POST
def generate_profit_report(request):
    return _generate_profit_report_response(request, welfare=False)


@require_POST
def generate_profit_welfare_report(request):
    return _generate_profit_report_response(request, welfare=True)


@require_POST
def generate_profit_final_report(request):
    return _generate_profit_report_response(request, final=True)


@require_GET
def download_profit_excel(request):
    report = _get_profit_report_from_session(request)
    if not report:
        return HttpResponseBadRequest("먼저 이익 보고서를 생성하세요.")
    data = export_profit_excel(report)
    filename = build_profit_download_filename(report, "xlsx")
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_GET
def download_profit_pdf(request):
    report = _get_profit_report_from_session(request)
    if not report:
        return HttpResponseBadRequest("먼저 이익 보고서를 생성하세요.")
    try:
        data = export_profit_pdf(report)
    except Exception as exc:
        return HttpResponseBadRequest(f"PDF 생성 실패: {exc}")
    filename = build_profit_download_filename(report, "pdf")
    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
