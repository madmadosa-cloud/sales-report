from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from sales_analysis.constants import MASTER_UPLOAD_MODE_REPLACE
from sales_analysis.forms import CategoryMasterForm, CategoryMasterUploadForm
from sales_analysis.services.classification import parse_master_csv
from sales_analysis.services.master_service import (
    apply_master_upload,
    create_customer_category,
    create_item_category,
    delete_customer_category,
    delete_item_category,
    list_customer_categories_with_usage,
    list_item_categories_with_usage,
    preview_master_upload,
    update_customer_category,
    update_item_category,
)


def _pending_session_key(kind: str) -> str:
    return f"pending_master_upload_{kind}"


def _panel_context() -> dict:
    return {
        "item_categories": list_item_categories_with_usage(),
        "customer_categories": list_customer_categories_with_usage(),
        "item_form": CategoryMasterForm(),
        "customer_form": CategoryMasterForm(),
        "item_upload_form": CategoryMasterUploadForm(),
        "customer_upload_form": CategoryMasterUploadForm(),
    }


def _refresh_item_response(request, message: str, *, via_status: bool = False):
    context = _panel_context()
    context["message"] = message
    template = (
        "sales_analysis/partials/master_refresh_item_status.html"
        if via_status
        else "sales_analysis/partials/master_refresh_item.html"
    )
    return render(request, template, context)


def _refresh_customer_response(request, message: str, *, via_status: bool = False):
    context = _panel_context()
    context["message"] = message
    template = (
        "sales_analysis/partials/master_refresh_customer_status.html"
        if via_status
        else "sales_analysis/partials/master_refresh_customer.html"
    )
    return render(request, template, context)


@require_GET
def category_master(request):
    return render(request, "sales_analysis/master.html", _panel_context())


@require_GET
def item_category_list(request):
    context = _panel_context()
    return render(request, "sales_analysis/partials/item_category_panel.html", context)


@require_GET
def customer_category_list(request):
    context = _panel_context()
    return render(request, "sales_analysis/partials/customer_category_panel.html", context)


@require_POST
def item_category_create(request):
    form = CategoryMasterForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "; ".join(e for errs in form.errors.values() for e in errs)},
        )
    try:
        create_item_category(
            form.cleaned_data["code"],
            form.cleaned_data["name"],
            form.cleaned_data.get("is_active", True),
        )
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})
    return _refresh_item_response(request, f"품목분류 '{form.cleaned_data['code']}'를 추가했습니다.")


@require_POST
def customer_category_create(request):
    form = CategoryMasterForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "; ".join(e for errs in form.errors.values() for e in errs)},
        )
    try:
        create_customer_category(
            form.cleaned_data["code"],
            form.cleaned_data["name"],
            form.cleaned_data.get("is_active", True),
        )
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})
    return _refresh_customer_response(request, f"거래처분류 '{form.cleaned_data['code']}'를 추가했습니다.")


@require_POST
def item_category_update(request, code: str):
    form = CategoryMasterForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "; ".join(e for errs in form.errors.values() for e in errs)},
        )
    try:
        update_item_category(
            code,
            form.cleaned_data["name"],
            form.cleaned_data.get("is_active", True),
        )
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})
    return _refresh_item_response(request, f"품목분류 '{code}'를 수정했습니다.")


@require_POST
def customer_category_update(request, code: str):
    form = CategoryMasterForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "; ".join(e for errs in form.errors.values() for e in errs)},
        )
    try:
        update_customer_category(
            code,
            form.cleaned_data["name"],
            form.cleaned_data.get("is_active", True),
        )
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})
    return _refresh_customer_response(request, f"거래처분류 '{code}'를 수정했습니다.")


@require_POST
def item_category_delete(request, code: str):
    force = request.POST.get("force") == "1"
    try:
        delete_item_category(code, force=force)
    except ValueError as exc:
        usage = list_item_categories_with_usage()
        row = next((r for r in usage if r["code"] == code), None)
        return render(
            request,
            "sales_analysis/partials/master_delete_confirm.html",
            {
                "kind": "item",
                "code": code,
                "usage_count": row["usage_count"] if row else 0,
                "error": str(exc),
            },
        )
    return _refresh_item_response(request, f"품목분류 '{code}'를 삭제했습니다.", via_status=True)


@require_POST
def customer_category_delete(request, code: str):
    force = request.POST.get("force") == "1"
    try:
        delete_customer_category(code, force=force)
    except ValueError as exc:
        usage = list_customer_categories_with_usage()
        row = next((r for r in usage if r["code"] == code), None)
        return render(
            request,
            "sales_analysis/partials/master_delete_confirm.html",
            {
                "kind": "customer",
                "code": code,
                "usage_count": row["usage_count"] if row else 0,
                "error": str(exc),
            },
        )
    return _refresh_customer_response(request, f"거래처분류 '{code}'를 삭제했습니다.", via_status=True)


def _handle_master_upload(request, kind: str):
    form = CategoryMasterUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "CSV 파일과 업로드 방식을 확인하세요."},
        )

    uploaded = form.cleaned_data["file"]
    mode = form.cleaned_data["mode"]
    try:
        rows = parse_master_csv(uploaded.read(), kind)
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})

    if not rows:
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "업로드할 분류코드가 없습니다."},
        )

    try:
        preview = preview_master_upload(kind, rows, mode)
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})

    if mode == MASTER_UPLOAD_MODE_REPLACE:
        request.session[_pending_session_key(kind)] = {
            "kind": kind,
            "mode": mode,
            "rows": preview.rows,
        }
        return render(
            request,
            "sales_analysis/partials/master_upload_confirm.html",
            {"preview": preview, "kind": kind},
        )

    result = apply_master_upload(kind, preview.rows, mode)
    label = "품목" if kind == "item" else "거래처"
    message = f"{label}분류 업로드 완료: 추가 {result['created']}건, 수정 {result['updated']}건"
    if kind == "item":
        return _refresh_item_response(request, message, via_status=True)
    return _refresh_customer_response(request, message, via_status=True)


@require_POST
def item_category_upload(request):
    return _handle_master_upload(request, "item")


@require_POST
def customer_category_upload(request):
    return _handle_master_upload(request, "customer")


@require_POST
def item_category_upload_confirm(request):
    return _confirm_master_upload(request, "item")


@require_POST
def customer_category_upload_confirm(request):
    return _confirm_master_upload(request, "customer")


def _confirm_master_upload(request, kind: str):
    pending = request.session.pop(_pending_session_key(kind), None)
    if not pending:
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "대기 중인 업로드가 없습니다. 파일을 다시 선택하세요."},
        )
    if request.POST.get("confirm") != "1":
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "전체 교체가 취소되었습니다."},
        )
    try:
        result = apply_master_upload(kind, pending["rows"], pending["mode"])
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})

    label = "품목" if kind == "item" else "거래처"
    message = (
        f"{label}분류 전체 교체 완료: 추가 {result['created']}건, 수정 {result['updated']}건, "
        f"삭제 {result['removed']}건"
    )
    if kind == "item":
        return _refresh_item_response(request, message, via_status=True)
    return _refresh_customer_response(request, message, via_status=True)