import logging

from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html

from .models import Order, OrderItem, PAID_FULFILLMENT_STATUSES, Payment, PaymentSettings, WhatsAppSettings
from .services.email_service import send_order_email
from .services.order_service import confirm_order_payment, ensure_paid_order_stock_reduced

logger = logging.getLogger(__name__)


@admin.register(WhatsAppSettings)
class WhatsAppSettingsAdmin(admin.ModelAdmin):
    list_display = ('is_active', 'whatsapp_number', 'enquiry_whatsapp', 'updated_at')
    fieldsets = (
        ('WhatsApp Number', {
            'fields': ('whatsapp_number', 'enquiry_whatsapp', 'default_message')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )

    def has_add_permission(self, request):
        if WhatsAppSettings.objects.exists():
            return False
        return True


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ('is_active', 'currency', 'currency_symbol', 'updated_at')
    fieldsets = (
        ('Razorpay API Keys', {
            'fields': ('razorpay_key_id', 'razorpay_key_secret')
        }),
        ('UPI Payment Settings', {
            'fields': ('upi_enabled', 'upi_id', 'upi_merchant_name', 'upi_qr_code')
        }),
        ('Payment Settings', {
            'fields': ('is_active', 'currency', 'currency_symbol', 'payment_disabled_message')
        }),
    )

    def has_add_permission(self, request):
        if PaymentSettings.objects.exists():
            return False
        return True


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ('subtotal_display',)
    
    def subtotal_display(self, obj):
        value = obj.subtotal if obj and obj.subtotal else 0
        settings = PaymentSettings.get_settings()
        currency = settings.currency_symbol if settings else '₹'
        return f"{currency}{value:.2f}"
    subtotal_display.short_description = 'Subtotal'


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = (
        'provider',
        'status',
        'amount',
        'currency',
        'receipt',
        'razorpay_order_id',
        'razorpay_payment_id',
        'verified_at',
        'created_at',
        'updated_at',
        'failure_reason',
    )
    fields = readonly_fields


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer_name',
        'user',
        'total_price',
        'status_colored',
        'payment_status',
        'stock_reduced',
        'email',
        'phone_number',
        'created_at',
    )
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = (
        'user__username', 
        'customer_name',
        'email',
        'phone_number', 
        'shipping_address',
        'tracking_id',
        'razorpay_order_id',
        'razorpay_payment_id'
    )
    list_editable = ('payment_status',)
    list_per_page = 25
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'razorpay_order_id', 'razorpay_payment_id', 'stock_reduced', 'payment_confirmed_at')
    raw_id_fields = ('user',)
    actions = ('mark_as_paid', 'mark_as_packed', 'mark_as_shipped', 'mark_as_delivered')
    list_select_related = ('user',)
    
    inlines = [OrderItemInline, PaymentInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'total_price', 'status', 'payment_status', 'stock_reduced', 'created_at')
        }),
        ('Payment Information', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'payment_confirmed_at')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'email', 'phone_number')
        }),
        ('Fulfillment', {
            'fields': ('tracking_id',)
        }),
        ('Shipping Address', {
            'fields': ('shipping_address',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Track previous status for stock/email triggers and send admin-created order emails."""
        is_new = obj.pk is None
        obj._created_via_admin = is_new
        if change:
            try:
                old_obj = Order.objects.get(pk=obj.pk)
                obj._admin_old_status = old_obj.status
                obj._admin_old_payment_status = old_obj.payment_status
            except Order.DoesNotExist:
                obj._admin_old_status = None
                obj._admin_old_payment_status = None
        else:
            obj._admin_old_status = None
            obj._admin_old_payment_status = None
        
        super().save_model(request, obj, form, change)
        if is_new:
            print("ADMIN ORDER CREATED - EMAIL")
            if not send_order_email(obj, "created"):
                logger.warning("Admin-created order email was not sent | order_id=%s", obj.pk)
    
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        order = form.instance
        order.refresh_from_db()

        if (
            order.status in PAID_FULFILLMENT_STATUSES
            and order.payment_status == 'paid'
            and order.items.exists()
            and not order.stock_reduced
        ):
            try:
                if ensure_paid_order_stock_reduced(order):
                    self.message_user(request, f"Stock reduced for order #{order.id}", level=messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Warning: {str(e)}", level=messages.WARNING)

    @admin.display(description='Status', ordering='status')
    def status_colored(self, obj):
        """Safe HTML via format_html."""
        status_colors = {
            'pending': '#FFC107',
            'failed': '#DC2626',
            'paid': '#16A34A',
            'packed': '#2563EB',
            'shipped': '#9C27B0',
            'delivered': '#4CAF50',
            'cancelled': '#F44336',
        }
        color = status_colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display().upper(),
        )

    def mark_as_paid(self, request, queryset):
        updated = 0
        skipped = 0
        for order in queryset:
            if order.payment_status == 'paid' and order.status == 'paid':
                skipped += 1
                continue
            try:
                if order.payment_status == 'paid':
                    order._admin_old_status = order.status
                    order.status = 'paid'
                    order.save(update_fields=['status'])
                else:
                    order._admin_old_status = order.status
                    order._admin_old_payment_status = order.payment_status
                    confirm_order_payment(order, payment_reference=order.razorpay_payment_id or '', save=True)
                updated += 1
            except Exception as exc:
                self.message_user(request, f"Warning for order {order.id}: {exc}", level=messages.WARNING)
        if updated:
            self.message_user(request, f"{updated} order(s) marked as Paid.", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"{skipped} order(s) were already Paid.", level=messages.INFO)
    mark_as_paid.short_description = 'Mark selected orders as Paid'

    def mark_as_packed(self, request, queryset):
        updated = 0
        skipped = 0
        for order in queryset:
            if order.payment_status != 'paid':
                skipped += 1
                continue
            if order.status != 'packed':
                order._admin_old_status = order.status
                order.status = 'packed'
                order.save(update_fields=['status'])
                updated += 1
        if updated:
            self.message_user(request, f"{updated} order(s) marked as Packed. Notifications will be sent.", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"{skipped} unpaid order(s) were skipped.", level=messages.WARNING)
    mark_as_packed.short_description = 'Mark selected orders as Packed'

    def mark_as_shipped(self, request, queryset):
        updated = 0
        skipped = 0
        for order in queryset:
            if order.payment_status != 'paid':
                skipped += 1
                continue
            if order.status != 'shipped':
                order._admin_old_status = order.status
                order.status = 'shipped'
                order.save(update_fields=['status'])
                updated += 1
        if updated:
            self.message_user(request, f"{updated} order(s) marked as Shipped. Notifications will be sent.", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"{skipped} unpaid order(s) were skipped.", level=messages.WARNING)
    mark_as_shipped.short_description = 'Mark selected orders as Shipped'

    def mark_as_delivered(self, request, queryset):
        updated = 0
        skipped = 0
        for order in queryset:
            if order.payment_status != 'paid':
                skipped += 1
                continue
            if order.status != 'delivered':
                order._admin_old_status = order.status
                order.status = 'delivered'
                order.save(update_fields=['status'])
                updated += 1
        if updated:
            self.message_user(request, f"{updated} order(s) marked as Delivered. Notifications will be sent.", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"{skipped} unpaid order(s) were skipped.", level=messages.WARNING)
    mark_as_delivered.short_description = 'Mark selected orders as Delivered'

    def get_ordering(self, request):
        return ['-created_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price', 'size', 'subtotal_display')
    list_filter = ('order__status',)
    search_fields = ('order__customer_name', 'product__name')
    list_per_page = 50
    list_select_related = ('order', 'product',)
    
    def subtotal_display(self, obj):
        value = obj.subtotal if obj and obj.subtotal else 0
        settings = PaymentSettings.get_settings()
        currency = settings.currency_symbol if settings else '₹'
        return f"{currency}{value:.2f}"
    subtotal_display.short_description = 'Subtotal'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'provider',
        'status',
        'amount',
        'currency',
        'razorpay_order_id',
        'razorpay_payment_id',
        'verified_at',
        'created_at',
    )
    list_filter = ('provider', 'status', 'currency', 'created_at')
    search_fields = (
        'order__customer_name',
        'order__email',
        'receipt',
        'razorpay_order_id',
        'razorpay_payment_id',
    )
    list_select_related = ('order',)
    readonly_fields = ('verified_at', 'created_at', 'updated_at')
