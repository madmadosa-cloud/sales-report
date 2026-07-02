from __future__ import annotations

from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from sales_analysis.forms import WelfareOutputItemForm
from sales_analysis.services.welfare_service import (
    create_welfare_output_item,
    delete_welfare_output_item,
    list_welfare_items_with_mappings,
    update_welfare_output_item,
)


def _panel_context() -> dict:
    return {
        "welfare_items": list_welfare_items_with_mappings(),
        "welfare_form": WelfareOutputItemForm(),
    }


def _refresh_response(request, message: str, *, via_status: bool = False):
    context = _panel_context()
    context["message"] = message
    template = (
        "sales_analysis/partials/welfare_refresh_status.html"
        if via_status
        else "sales_analysis/partials/welfare_refresh.html"
    )
    return render(request, template, context)


@require_GET
def welfare_category_master(request):
    return render(request, "sales_analysis/welfare_master.html", _panel_context())


@require_GET
def welfare_output_list(request):
    return render(request, "sales_analysis/partials/welfare_output_panel.html", _panel_context())


@require_POST
def welfare_output_create(request):
    form = WelfareOutputItemForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "; ".join(e for errs in form.errors.values() for e in errs)},
        )
    try:
        create_welfare_output_item(
            form.cleaned_data["code"],
            form.cleaned_data["name"],
            form.cleaned_data.get("item_codes", ""),
            is_active=form.cleaned_data.get("is_active", True),
            sort_order=form.cleaned_data.get("sort_order"),
        )
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})
    return _refresh_response(request, f"출력항목 '{form.cleaned_data['name']}'를 추가했습니다.")


@require_POST
def welfare_output_update(request, code: str):
    form = WelfareOutputItemForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "sales_analysis/partials/master_status.html",
            {"error": "; ".join(e for errs in form.errors.values() for e in errs)},
        )
    try:
        update_welfare_output_item(
            code,
            form.cleaned_data["name"],
            form.cleaned_data.get("item_codes", ""),
            is_active=form.cleaned_data.get("is_active", True),
            sort_order=form.cleaned_data.get("sort_order"),
        )
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})
    return _refresh_response(request, f"출력항목 '{form.cleaned_data['name']}'를 수정했습니다.")


@require_POST
def welfare_output_delete(request, code: str):
    try:
        delete_welfare_output_item(code)
    except ValueError as exc:
        return render(request, "sales_analysis/partials/master_status.html", {"error": str(exc)})
    return _refresh_response(request, "출력항목을 삭제했습니다.", via_status=True)
