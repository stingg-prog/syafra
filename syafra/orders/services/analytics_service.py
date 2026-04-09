from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from orders.models import Order, OrderItem, PaymentSettings

User = get_user_model()

DEFAULT_RANGE_DAYS = 30
SUPPORTED_RANGE_DAYS = {7, 30}
STATUS_ORDER = ["pending", "failed", "paid", "packed", "shipped", "delivered", "cancelled"]


def _decimal_zero():
    return Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))


def _to_aware_start(value):
    return timezone.make_aware(datetime.combine(value, time.min))


def _to_aware_end_exclusive(value):
    return timezone.make_aware(datetime.combine(value + timedelta(days=1), time.min))


def _build_date_labels(start_date, end_date):
    labels = []
    current = start_date
    while current <= end_date:
        labels.append(current)
        current += timedelta(days=1)
    return labels


def _fill_daily_series(rows, *, start_date, end_date, value_key):
    date_map = {row["day"]: row[value_key] for row in rows}
    labels = _build_date_labels(start_date, end_date)
    return {
        "labels": [day.strftime("%b %d") for day in labels],
        "values": [date_map.get(day, 0) or 0 for day in labels],
    }


def _coerce_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def resolve_analytics_range(params):
    today = timezone.localdate()
    selected_range = (params.get("range") or str(DEFAULT_RANGE_DAYS)).strip()
    filter_error = ""

    if selected_range == "custom":
        start_date = _coerce_date(params.get("start_date"))
        end_date = _coerce_date(params.get("end_date"))
        if not start_date or not end_date:
            selected_range = str(DEFAULT_RANGE_DAYS)
            start_date = today - timedelta(days=DEFAULT_RANGE_DAYS - 1)
            end_date = today
            filter_error = "Custom range was incomplete, so the last 30 days are shown."
        elif start_date > end_date:
            selected_range = str(DEFAULT_RANGE_DAYS)
            start_date = today - timedelta(days=DEFAULT_RANGE_DAYS - 1)
            end_date = today
            filter_error = "Custom start date must be before the end date, so the last 30 days are shown."
    else:
        try:
            days = int(selected_range)
        except ValueError:
            days = DEFAULT_RANGE_DAYS
        if days not in SUPPORTED_RANGE_DAYS:
            days = DEFAULT_RANGE_DAYS
        selected_range = str(days)
        start_date = today - timedelta(days=days - 1)
        end_date = today

    return {
        "selected_range": selected_range,
        "start_date": start_date,
        "end_date": end_date,
        "filter_error": filter_error,
        "start_date_value": start_date.isoformat(),
        "end_date_value": end_date.isoformat(),
        "range_label": (
            f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
            if selected_range == "custom"
            else f"Last {selected_range} days"
        ),
    }


def get_analytics_dashboard_data(params):
    filters = resolve_analytics_range(params)
    start_date = filters["start_date"]
    end_date = filters["end_date"]
    start_dt = _to_aware_start(start_date)
    end_dt = _to_aware_end_exclusive(end_date)

    payment_settings = PaymentSettings.get_settings()
    currency_symbol = payment_settings.currency_symbol if payment_settings else "₹"

    customer_users_qs = User.objects.filter(is_staff=False, is_superuser=False)
    orders_qs = Order.objects.all()
    paid_orders_qs = orders_qs.filter(payment_status="paid")
    range_orders_qs = orders_qs.filter(created_at__gte=start_dt, created_at__lt=end_dt)
    range_paid_orders_qs = paid_orders_qs.filter(created_at__gte=start_dt, created_at__lt=end_dt)

    order_totals = orders_qs.aggregate(
        total_orders=Count("id"),
        total_revenue=Coalesce(Sum("total_price", filter=Q(payment_status="paid")), _decimal_zero()),
        average_order_value=Coalesce(Avg("total_price", filter=Q(payment_status="paid")), _decimal_zero()),
    )

    total_users = customer_users_qs.count()
    new_users_total = customer_users_qs.filter(date_joined__gte=start_dt, date_joined__lt=end_dt).count()
    active_users = (
        customer_users_qs.filter(
            Q(last_login__gte=start_dt, last_login__lt=end_dt)
            | Q(orders__created_at__gte=start_dt, orders__created_at__lt=end_dt)
        )
        .distinct()
        .count()
    )

    orders_by_status_rows = (
        range_orders_qs.values("status")
        .annotate(total=Count("id"))
        .order_by()
    )
    orders_by_status = {status: 0 for status in STATUS_ORDER}
    for row in orders_by_status_rows:
        orders_by_status[row["status"]] = row["total"]

    orders_per_day_rows = list(
        range_orders_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    revenue_per_day_rows = list(
        range_paid_orders_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Coalesce(Sum("total_price"), _decimal_zero()))
        .order_by("day")
    )
    new_users_per_day_rows = list(
        customer_users_qs.filter(date_joined__gte=start_dt, date_joined__lt=end_dt)
        .annotate(day=TruncDate("date_joined"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    order_series = _fill_daily_series(
        orders_per_day_rows,
        start_date=start_date,
        end_date=end_date,
        value_key="total",
    )
    revenue_series_raw = _fill_daily_series(
        revenue_per_day_rows,
        start_date=start_date,
        end_date=end_date,
        value_key="total",
    )
    revenue_series = {
        "labels": revenue_series_raw["labels"],
        "values": [float(value or 0) for value in revenue_series_raw["values"]],
    }
    user_series = _fill_daily_series(
        new_users_per_day_rows,
        start_date=start_date,
        end_date=end_date,
        value_key="total",
    )

    line_total = ExpressionWrapper(
        F("quantity") * F("price"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    top_products = list(
        OrderItem.objects.filter(order__payment_status="paid", order__created_at__gte=start_dt, order__created_at__lt=end_dt)
        .annotate(line_total=line_total)
        .values("product_id", "product__name", "product__brand")
        .annotate(
            quantity_sold=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(Sum("line_total"), _decimal_zero()),
            order_count=Count("order_id", distinct=True),
        )
        .order_by("-quantity_sold", "-revenue", "product__name")[:5]
    )

    recent_orders = list(
        Order.objects.select_related("user")
        .order_by("-created_at")[:10]
    )

    return {
        "filters": filters,
        "summary": {
            "total_orders": order_totals["total_orders"] or 0,
            "total_revenue": order_totals["total_revenue"] or Decimal("0.00"),
            "average_order_value": order_totals["average_order_value"] or Decimal("0.00"),
            "currency_symbol": currency_symbol,
            "total_users": total_users,
            "active_users": active_users,
            "new_users_in_range": new_users_total,
            "orders_in_range": range_orders_qs.count(),
            "paid_orders_in_range": range_paid_orders_qs.count(),
        },
        "orders_by_status": orders_by_status,
        "order_chart": order_series,
        "revenue_chart": revenue_series,
        "user_chart": user_series,
        "status_chart": {
            "labels": [status.replace("_", " ").title() for status in STATUS_ORDER],
            "values": [orders_by_status[status] for status in STATUS_ORDER],
        },
        "top_products": top_products,
        "recent_orders": recent_orders,
    }
