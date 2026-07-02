from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from sales_analysis.forms import ReportPeriodForm
from sales_analysis.models import SalesRecord
from sales_analysis.services.aggregation import build_sales_report, get_unclassified_records
from sales_analysis.services.excel_export import build_download_filename, export_report_excel
from sales_analysis.services.import_service import get_stored_periods, process_upload
from sales_analysis.services.pdf_export import export_report_pdf
from sales_analysis.services.report_verification import verify_report


def _session_key(request) -> str:
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key or ""


def _get_report_from_session(request) -> tuple | None:
    params = request.session.get("last_report_params")
    if not params:
        return None
    year = params["year"]
    start_month = params["start_month"]
    end_month = params["end_month"]
    period_label = params.get("period_label", "")
    simple = params.get("simple", False)
    welfare = params.get("welfare", False)
    final = params.get("final", False)
    qs = SalesRecord.objects.filter(
        year=year,
        month__gte=start_month,
        month__lte=end_month,
    )
    report = build_sales_report(
        qs,
        year,
        start_month,
        end_month,
        period_label,
        simple=(simple or welfare) and not final,
        welfare=welfare and not final,
        final=final,
    )
    verification = verify_report(qs, report, year, start_month, end_month)
    return report, qs, verification


def _period_label_from_form(year: int, start_month: int, end_month: int, preset: str) -> str:
    if preset == "first_half":
        return f"{year}년 상반기"
    if preset == "second_half":
        return f"{year}년 하반기"
    if preset == "full_year":
        return f"{year}년 연간"
    return f"{year}년 {start_month}월~{end_month}월"


def _generate_report_response(request, simple: bool = False, welfare: bool = False, final: bool = False):
    form = ReportPeriodForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "sales_analysis/partials/report_preview.html",
            {"error": "기간 입력이 올바르지 않습니다.", "form_errors": form.errors},
        )

    year = form.cleaned_data["year"]
    start_month = form.cleaned_data["start_month"]
    end_month = form.cleaned_data["end_month"]
    preset = form.cleaned_data["preset"]
    period_label = _period_label_from_form(year, start_month, end_month, preset)

    qs = SalesRecord.objects.filter(year=year, month__gte=start_month, month__lte=end_month)
    if not qs.exists():
        return render(
            request,
            "sales_analysis/partials/report_preview.html",
            {"error": f"{period_label}에 해당하는 저장 데이터가 없습니다."},
        )

    report = build_sales_report(
        qs,
        year,
        start_month,
        end_month,
        period_label,
        simple=(simple or welfare) and not final,
        welfare=welfare and not final,
        final=final,
    )
    verification = verify_report(qs, report, year, start_month, end_month)
    request.session["last_report_params"] = {
        "year": year,
        "start_month": start_month,
        "end_month": end_month,
        "period_label": report.period_label,
        "simple": simple,
        "welfare": welfare,
        "final": final,
    }
    request.session["last_report_verification_passed"] = verification.passed

    return render(
        request,
        "sales_analysis/partials/report_preview.html",
        {"report": report, "verification": verification},
    )


@require_GET
def index(request):
    stored = get_stored_periods()
    report_form = ReportPeriodForm()
    last_report = None
    last_verification = None
    if request.session.get("last_report_params"):
        result = _get_report_from_session(request)
        if result:
            last_report, _, last_verification = result
    return render(
        request,
        "sales_analysis/index.html",
        {
            "stored_periods": stored,
            "report_form": report_form,
            "last_report": last_report,
            "verification": last_verification,
        },
    )


@require_POST
def upload_sales(request):
    files = request.FILES.getlist("files")
    if not files:
        return render(
            request,
            "sales_analysis/partials/upload_status.html",
            {"error": "업로드할 CSV 파일을 선택하세요."},
        )

    try:
        result = process_upload(_session_key(request), files, confirmed=False)
    except ValueError as exc:
        return render(
            request,
            "sales_analysis/partials/upload_status.html",
            {"error": str(exc)},
        )

    if result["status"] == "confirm_needed":
        return render(
            request,
            "sales_analysis/partials/confirm_replace.html",
            {
                "existing_periods": result["existing"],
                "warnings": result.get("warnings", []),
                "total_rows": result["total_rows"],
            },
        )

    messages.success(request, f"{result['count']}건의 매출 데이터를 저장했습니다.")
    return render(
        request,
        "sales_analysis/partials/upload_status.html",
        {
            "success": True,
            "count": result["count"],
            "warnings": result.get("warnings", []),
            "stored_periods": get_stored_periods(),
        },
    )


@require_POST
def confirm_upload(request):
    result = process_upload(_session_key(request), [], confirmed=True)

    if result["status"] == "no_pending":
        return render(
            request,
            "sales_analysis/partials/upload_status.html",
            {"error": "대기 중인 업로드 데이터가 없습니다. 파일을 다시 선택해 주세요."},
        )

    replaced = result.get("replaced", [])
    msg = f"{result['count']}건 저장 완료"
    if replaced:
        periods = ", ".join(f"{y}년 {m}월" for y, m in replaced)
        msg += f" (교체: {periods})"
    messages.success(request, msg)
    return render(
        request,
        "sales_analysis/partials/upload_status.html",
        {
            "success": True,
            "count": result["count"],
            "warnings": result.get("warnings", []),
            "stored_periods": get_stored_periods(),
        },
    )


@require_POST
def generate_report(request):
    return _generate_report_response(request, simple=False)


@require_POST
def generate_simple_report(request):
    return _generate_report_response(request, simple=True)


@require_POST
def generate_welfare_report(request):
    return _generate_report_response(request, welfare=True)


@require_POST
def generate_final_report(request):
    return _generate_report_response(request, final=True)


@require_GET
def download_excel(request):
    result = _get_report_from_session(request)
    if not result:
        return HttpResponseBadRequest("먼저 보고서를 생성하세요.")
    report, qs, verification = result
    if not verification.passed:
        return HttpResponseBadRequest(
            "집계 검증에 실패하여 Excel을 다운로드할 수 없습니다. 검증 결과를 확인하세요."
        )
    data = export_report_excel(report, qs)
    filename = build_download_filename(report, "xlsx")
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_GET
def download_pdf(request):
    result = _get_report_from_session(request)
    if not result:
        return HttpResponseBadRequest("먼저 보고서를 생성하세요.")
    report, _qs, verification = result
    if not verification.passed:
        return HttpResponseBadRequest(
            "집계 검증에 실패하여 PDF를 다운로드할 수 없습니다. 검증 결과를 확인하세요."
        )
    try:
        data = export_report_pdf(report)
    except Exception as exc:
        return HttpResponseBadRequest(f"PDF 생성 실패: {exc}")
    filename = build_download_filename(report, "pdf")
    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_GET
def unclassified_list(request):
    year = request.GET.get("year")
    qs = SalesRecord.objects.filter(
        models_q_filter_unclassified()
    ).order_by("year", "month", "voucher_no")
    if year:
        qs = qs.filter(year=int(year))
    return render(
        request,
        "sales_analysis/partials/unclassified_list.html",
        {"records": get_unclassified_records(qs), "year": year},
    )


def models_q_filter_unclassified():
    from django.db.models import Q

    return Q(is_unclassified_item=True) | Q(is_unclassified_customer=True)
