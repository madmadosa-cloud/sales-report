from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def comma(value):
    """정수에 천 단위 콤마 표시"""
    if value is None or value == "":
        return "0"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value


@register.filter
def comma_qty(value):
    """수량 등 소수 가능 숫자 콤마 표시"""
    if value is None or value == "":
        return "0"
    try:
        d = Decimal(str(value))
        if d == d.to_integral_value():
            return f"{int(d):,}"
        text = f"{d:,.2f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text
    except (TypeError, ValueError):
        return value


@register.filter
def get_item(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key, "")
    return ""


@register.filter
def month_count(row, month):
    cell = row.months.get(int(month))
    return cell.count if cell else 0


@register.filter
def month_quantity(row, month):
    cell = row.months.get(int(month))
    return cell.quantity if cell else Decimal("0")


@register.filter
def month_amount(row, month):
    cell = row.months.get(int(month))
    return cell.amount_thousand if cell else 0


@register.filter
def block_count(row, block_id):
    cell = row.blocks.get(block_id)
    return cell.count if cell else 0


@register.filter
def block_quantity(row, block_id):
    cell = row.blocks.get(block_id)
    return cell.quantity if cell else Decimal("0")


@register.filter
def block_amount(row, block_id):
    cell = row.blocks.get(block_id)
    return cell.amount_thousand if cell else 0
