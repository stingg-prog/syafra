from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import (
    Count, DecimalField, Exists, ExpressionWrapper, F,
    IntegerField, OuterRef, Q, Sum, Value,
)
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from orders.models import Order, OrderItem, PaymentSettings
from products.models import Product
from wishlist.models import Wishlist
from cart.models import Cart, CartItem
from accounts.models import EmailLog

User = get_user_model()

SUPPORTED_RANGES = {"today", "7", "30", "90", "365"}

STATUS_ORDER = ["pending", "failed", "paid", "packed", "shipped", "delivered", "cancelled"]


def _decimal_zero():
    return Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))


def _int_zero():
    return Value(0, output_field=IntegerField())


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
        "values": [float(date_map.get(day, 0) or 0) for day in labels],
    }


def _coerce_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def resolve_analytics_range(params):
    today = timezone.localdate()
    selected_range = (params.get("range") or "30").strip()
    filter_error = ""

    if selected_range == "custom":
        start_date = _coerce_date(params.get("start_date"))
        end_date = _coerce_date(params.get("end_date"))
        if not start_date or not end_date:
            selected_range = "30"
            start_date = today - timedelta(days=29)
            end_date = today
            filter_error = "Custom range was incomplete, so the last 30 days are shown."
        elif start_date > end_date:
            selected_range = "30"
            start_date = today - timedelta(days=29)
            end_date = today
            filter_error = "Custom start date must be before the end date, so the last 30 days are shown."
    elif selected_range == "today":
        start_date = today
        end_date = today
    else:
        try:
            days = int(selected_range)
        except ValueError:
            days = 30
        if str(days) not in SUPPORTED_RANGES and selected_range != "today":
            days = 30
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
            "Today"
            if selected_range == "today"
            else (
                f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
                if selected_range == "custom"
                else f"Last {selected_range} days"
            )
        ),
    }


def get_analytics_dashboard_data(params):
    filters = resolve_analytics_range(params)
    start_date = filters["start_date"]
    end_date = filters["end_date"]
    start_dt = _to_aware_start(start_date)
    end_dt = _to_aware_end_exclusive(end_date)

    today = timezone.localdate()
    today_start_dt = _to_aware_start(today)
    month_start = today.replace(day=1)
    month_start_dt = _to_aware_start(month_start)
    week_start_dt = _to_aware_start(today - timedelta(days=today.weekday()))

    payment_settings = PaymentSettings.get_settings()
    currency_symbol = payment_settings.currency_symbol if payment_settings else "\u20b9"

    customer_users_qs = User.objects.filter(is_staff=False, is_superuser=False)

    order_aggs = Order.objects.aggregate(
        total_revenue=Coalesce(Sum("total_price", filter=Q(payment_status="paid")), _decimal_zero()),
        total_orders=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        paid=Count("id", filter=Q(status="paid")),
        delivered=Count("id", filter=Q(status="delivered")),
        cancelled=Count("id", filter=Q(status="cancelled")),
        today_revenue=Coalesce(
            Sum("total_price", filter=Q(payment_status="paid", created_at__gte=today_start_dt)),
            _decimal_zero(),
        ),
        month_revenue=Coalesce(
            Sum("total_price", filter=Q(payment_status="paid", created_at__gte=month_start_dt)),
            _decimal_zero(),
        ),
        orders_today=Count("id", filter=Q(created_at__gte=today_start_dt)),
    )

    product_aggs = Product.objects.aggregate(
        total=Count("id"),
        low_stock=Count("id", filter=Q(stock__gt=0, stock__lte=5)),
        out_of_stock=Count("id", filter=Q(stock=0)),
    )

    total_customers = customer_users_qs.count()

    wishlist_aggs = Wishlist.objects.aggregate(
        total_items=Count("id"),
        unique_users=Count("user", distinct=True),
        growth_today=Count("id", filter=Q(created_at__gte=today_start_dt)),
        growth_week=Count("id", filter=Q(created_at__gte=week_start_dt)),
        growth_month=Count("id", filter=Q(created_at__gte=month_start_dt)),
    )

    most_wishlisted = (
        Wishlist.objects.values("product__name", "product_id")
        .annotate(count=Count("id"))
        .order_by("-count")
        .first()
    )

    users_with_wishlist = (
        Wishlist.objects.values("user").distinct().count()
    )
    users_with_wishlist_and_order = (
        Wishlist.objects.filter(user__orders__payment_status="paid")
        .values("user")
        .distinct()
        .count()
    )
    wishlist_purchase_conversion = (
        round((users_with_wishlist_and_order / users_with_wishlist) * 100, 1)
        if users_with_wishlist
        else 0
    )

    carts_with_items = Cart.objects.filter(items__isnull=False)
    total_carts_with_items = carts_with_items.count()
    cutoff_24h_ago = timezone.now() - timedelta(hours=24)

    cart_aggs = carts_with_items.aggregate(
        active_carts=Count("id", filter=Q(created_at__gte=cutoff_24h_ago)),
        abandoned_carts=Count("id", filter=Q(created_at__lt=cutoff_24h_ago)),
    )

    cart_item_aggs = CartItem.objects.aggregate(
        total_items=Coalesce(Sum("quantity"), _int_zero()),
    )

    cart_total_data = CartItem.objects.annotate(
        line_total=ExpressionWrapper(
            F("quantity") * F("product__price"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    ).aggregate(
        total_value=Coalesce(Sum("line_total"), _decimal_zero()),
    )
    avg_cart_value = (
        float(cart_total_data["total_value"] or 0) / total_carts_with_items
        if total_carts_with_items
        else 0
    )

    total_paid_orders = Order.objects.filter(payment_status="paid").count()
    cart_conversion_rate = (
        round((total_paid_orders / total_carts_with_items) * 100, 1)
        if total_carts_with_items
        else 0
    )

    recovered_carts = 0
    if total_carts_with_items:
        user_order_exists = Order.objects.filter(
            user=OuterRef("user"),
            payment_status="paid",
            created_at__gte=OuterRef("created_at"),
        )
        recovered_carts = (
            carts_with_items.filter(Exists(user_order_exists)).count()
        )

    total_orders_count = order_aggs["total_orders"] or 0
    conversion_rate = (
        round((total_paid_orders / total_orders_count) * 100, 1)
        if total_orders_count
        else 0
    )

    range_orders_qs = Order.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)

    daily_data = list(
        range_orders_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            orders=Count("id"),
            revenue=Coalesce(Sum("total_price", filter=Q(payment_status="paid")), _decimal_zero()),
            paid_orders=Count("id", filter=Q(payment_status="paid")),
        )
        .order_by("day")
    )

    charts = {
        "revenue": _fill_daily_series(daily_data, start_date=start_date, end_date=end_date, value_key="revenue"),
        "orders": _fill_daily_series(daily_data, start_date=start_date, end_date=end_date, value_key="orders"),
    }
    aov_data = []
    for entry in daily_data:
        aov_data.append({
            "day": entry["day"],
            "aov": float(entry["revenue"] or 0) / float(entry["paid_orders"] or 1) if entry["paid_orders"] else 0,
        })
    aov_series = _fill_daily_series(aov_data, start_date=start_date, end_date=end_date, value_key="aov")
    charts["aov"] = {
        "labels": aov_series["labels"],
        "values": [round(v, 2) for v in aov_series["values"]],
    }

    line_total = ExpressionWrapper(
        F("quantity") * F("price"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    top_selling = list(
        OrderItem.objects.filter(order__payment_status="paid")
        .annotate(line_total=line_total)
        .values("product_id", "product__name", "product__brand")
        .annotate(
            quantity_sold=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(Sum("line_total"), _decimal_zero()),
            order_count=Count("order_id", distinct=True),
        )
        .order_by("-quantity_sold", "-revenue")[:10]
    )

    top_wishlisted = list(
        Wishlist.objects.values("product_id", "product__name", "product__brand")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    low_stock_products = list(
        Product.objects.filter(stock__gt=0, stock__lte=5)
        .order_by("stock")[:10]
        .values("id", "name", "brand", "stock", "price")
    )

    out_of_stock_products = list(
        Product.objects.filter(stock=0)
        .order_by("-updated_at")[:10]
        .values("id", "name", "brand", "stock", "price")
    )

    most_viewed_products = list(
        Product.objects.filter(views__gt=0)
        .order_by("-views")[:10]
        .values("id", "name", "brand", "price", "views")
    )

    top_customers = list(
        User.objects.filter(
            is_staff=False, is_superuser=False,
            orders__payment_status="paid",
        )
        .annotate(
            total_spent=Coalesce(Sum("orders__total_price"), _decimal_zero()),
            order_count=Count("orders", filter=Q(orders__payment_status="paid")),
        )
        .order_by("-total_spent")[:10]
        .values("id", "username", "email", "total_spent", "order_count")
    )

    new_customers_in_range = customer_users_qs.filter(
        date_joined__gte=start_dt, date_joined__lt=end_dt,
    ).count()

    returning_customers = customer_users_qs.annotate(
        paid_order_count=Count("orders", filter=Q(orders__payment_status="paid")),
    ).filter(paid_order_count__gt=1).count()

    customers_with_orders = (
        customer_users_qs.filter(orders__payment_status="paid")
        .distinct()
        .count()
    )
    total_revenue = order_aggs["total_revenue"] or Decimal("0.00")
    customer_lifetime_value = (
        float(total_revenue) / customers_with_orders
        if customers_with_orders
        else 0
    )

    recently_added_products = list(
        Product.objects.order_by("-created_at")[:10]
        .values("id", "name", "brand", "price", "stock", "created_at")
    )

    top_categories = list(
        OrderItem.objects.filter(order__payment_status="paid")
        .values("product__category__name", "product__category_id")
        .annotate(
            total_revenue=Coalesce(Sum(ExpressionWrapper(F("quantity") * F("price"), output_field=DecimalField(max_digits=12, decimal_places=2))), _decimal_zero()),
            total_orders=Count("order_id", distinct=True),
            total_sold=Coalesce(Sum("quantity"), 0),
        )
        .order_by("-total_revenue")[:10]
    )

    highest_revenue_products = list(
        OrderItem.objects.filter(order__payment_status="paid")
        .annotate(line_total=line_total)
        .values("product_id", "product__name", "product__brand")
        .annotate(
            revenue=Coalesce(Sum("line_total"), _decimal_zero()),
            quantity_sold=Coalesce(Sum("quantity"), 0),
        )
        .order_by("-revenue")[:10]
    )

    most_active_customers = list(
        User.objects.filter(
            is_staff=False, is_superuser=False,
            orders__payment_status="paid",
        )
        .annotate(
            order_count=Count("orders", filter=Q(orders__payment_status="paid")),
            total_spent=Coalesce(Sum("orders__total_price", filter=Q(orders__payment_status="paid")), _decimal_zero()),
        )
        .order_by("-order_count")[:10]
        .values("id", "username", "email", "order_count", "total_spent")
    )

    customer_growth_data = list(
        customer_users_qs
        .filter(date_joined__gte=start_dt, date_joined__lt=end_dt)
        .annotate(day=TruncDate("date_joined"))
        .values("day")
        .annotate(count=Count("id"))  # Use Count instead of summing pre-counted
        .order_by("day")
    )
    customer_growth = _fill_daily_series(
        customer_growth_data, start_date=start_date, end_date=end_date, value_key="count"
    )

    wishlist_growth_data = list(
        Wishlist.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    wishlist_growth_chart = _fill_daily_series(
        wishlist_growth_data, start_date=start_date, end_date=end_date, value_key="count"
    )

    cart_growth_data = list(
        Cart.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    cart_growth_chart = _fill_daily_series(
        cart_growth_data, start_date=start_date, end_date=end_date, value_key="count"
    )

    recent_emails = list(
        EmailLog.objects.order_by("-created_at")[:10]
        .values("id", "recipient", "email_type", "status", "created_at", "subject")
    )

    wishlist_weekly = wishlist_aggs["growth_week"] or 0

    order_status = {}
    for s in STATUS_ORDER:
        order_status[s] = 0
    status_rows = range_orders_qs.values("status").annotate(total=Count("id"))
    for row in status_rows:
        order_status[row["status"]] = row["total"]

    email_aggs = EmailLog.objects.aggregate(
        total=Count("id"),
        failed=Count("id", filter=Q(status="failed")),
        delivered=Count("id", filter=Q(status="delivered")),
        accepted=Count("id", filter=Q(status__in=["accepted", "delivered"])),
    )
    email_success_rate = (
        round((email_aggs["delivered"] / email_aggs["total"]) * 100, 1)
        if email_aggs["total"]
        else 0
    )

    email_logs_with_times = EmailLog.objects.filter(
        delivered_at__isnull=False, created_at__isnull=False,
    ).values_list("delivered_at", "created_at")[:1000]
    total_diff_seconds = 0
    count = 0
    for delivered_at, created_at in email_logs_with_times:
        if delivered_at and created_at:
            diff = (delivered_at - created_at).total_seconds()
            if diff >= 0:
                total_diff_seconds += diff
                count += 1
    avg_send_seconds = round(total_diff_seconds / count, 1) if count else 0

    recent_orders = list(
        Order.objects.select_related("user")
        .order_by("-created_at")[:10]
    )
    recent_customers = list(
        customer_users_qs.order_by("-date_joined")[:10]
        .values("id", "username", "email", "date_joined")
    )
    recent_wishlist = list(
        Wishlist.objects.select_related("user", "product")
        .order_by("-created_at")[:10]
    )
    recent_cart_items = list(
        CartItem.objects.select_related("cart__user", "product")
        .order_by("-cart__created_at")[:10]
    )
    recent_payments = list(
        Order.objects.filter(payment_status="paid")
        .select_related("user")
        .order_by("-created_at")[:10]
        .values("id", "user__username", "total_price", "created_at", "status")
    )

    top_cart_products = list(
        CartItem.objects.values("product_id", "product__name", "product__brand")
        .annotate(total_qty=Coalesce(Sum("quantity"), 0))
        .order_by("-total_qty")[:10]
    )

    return {
        "filters": filters,
        "overview": {
            "total_revenue": float(order_aggs["total_revenue"] or 0),
            "today_revenue": float(order_aggs["today_revenue"] or 0),
            "monthly_revenue": float(order_aggs["month_revenue"] or 0),
            "total_orders": order_aggs["total_orders"] or 0,
            "orders_today": order_aggs["orders_today"] or 0,
            "pending_orders": order_aggs["pending"] or 0,
            "paid_orders": order_aggs["paid"] or 0,
            "delivered_orders": order_aggs["delivered"] or 0,
            "cancelled_orders": order_aggs["cancelled"] or 0,
            "total_products": product_aggs["total"] or 0,
            "low_stock_products": product_aggs["low_stock"] or 0,
            "out_of_stock_products": product_aggs["out_of_stock"] or 0,
            "total_customers": total_customers,
            "new_customers": new_customers_in_range,
            "returning_customers": returning_customers,
            "total_wishlist_items": wishlist_aggs["total_items"] or 0,
            "unique_wishlist_users": wishlist_aggs["unique_users"] or 0,
            "most_wishlisted_product": most_wishlisted["product__name"] if most_wishlisted else None,
            "wishlist_growth_today": wishlist_aggs["growth_today"] or 0,
            "wishlist_growth_week": wishlist_aggs["growth_week"] or 0,
            "wishlist_growth_month": wishlist_aggs["growth_month"] or 0,
            "active_carts": cart_aggs["active_carts"] or 0,
            "total_cart_items": cart_item_aggs["total_items"] or 0,
            "average_cart_value": avg_cart_value,
            "abandoned_carts": cart_aggs["abandoned_carts"] or 0,
            "cart_conversion_rate": cart_conversion_rate,
            "conversion_rate": conversion_rate,
            "currency_symbol": currency_symbol,
        },
        "sales_charts": charts,
        "product_analytics": {
            "top_selling": top_selling,
            "most_viewed": most_viewed_products,
            "most_wishlisted": top_wishlisted,
            "low_stock": low_stock_products,
            "out_of_stock": out_of_stock_products,
        },
        "customer_analytics": {
            "new_customers": new_customers_in_range,
            "returning_customers": returning_customers,
            "top_customers": top_customers,
            "most_active": most_active_customers,
            "customer_lifetime_value": round(customer_lifetime_value, 2),
            "growth_chart": customer_growth,
        },
        "wishlist_analytics": {
            "total_items": wishlist_aggs["total_items"] or 0,
            "unique_users": wishlist_aggs["unique_users"] or 0,
            "top_products": top_wishlisted,
            "added_today": wishlist_aggs["growth_today"] or 0,
            "added_week": wishlist_weekly,
            "added_month": wishlist_aggs["growth_month"] or 0,
            "purchase_conversion_rate": wishlist_purchase_conversion,
            "growth_chart": wishlist_growth_chart,
        },
        "cart_analytics": {
            "active_carts": cart_aggs["active_carts"] or 0,
            "total_items": cart_item_aggs["total_items"] or 0,
            "average_value": float(cart_total_data["total_value"] or 0) / total_carts_with_items if total_carts_with_items else 0,
            "abandoned": cart_aggs["abandoned_carts"] or 0,
            "recovered": recovered_carts,
            "conversion_rate": cart_conversion_rate,
            "top_products": top_cart_products,
            "growth_chart": cart_growth_chart,
        },
        "product_analytics_extended": {
            "top_categories": top_categories,
            "recently_added": recently_added_products,
            "highest_revenue": highest_revenue_products,
        },
        "order_status": order_status,
        "email_analytics": {
            "total_sent": email_aggs["total"] or 0,
            "failed": email_aggs["failed"] or 0,
            "delivered": email_aggs["delivered"] or 0,
            "success_rate": email_success_rate,
            "average_send_time": avg_send_seconds,
        },
        "recent_activity": {
            "orders": recent_orders,
            "customers": recent_customers,
            "wishlist": recent_wishlist,
            "cart": recent_cart_items,
            "payments": recent_payments,
            "emails": recent_emails,
        },
    }