from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "customer_phone",
        "status",
        "total_price",
        "last_notified_status",
        "last_notified_at",
    )
    list_editable = ("status",)
    readonly_fields = ("last_notified_status", "last_notified_at")
    search_fields = ("customer_name", "customer_phone", "id")
    list_filter = ("status",)
