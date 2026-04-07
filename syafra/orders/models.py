from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q
from products.models import Product

User = get_user_model()
_PAYMENT_SETTINGS_WARNING_LOGGED = False
_RAZORPAY_PLACEHOLDER_VALUES = {
    'your_razorpay_key_id',
    'your_razorpay_key_secret',
}
PAID_FULFILLMENT_STATUSES = ('paid', 'packed', 'shipped', 'delivered')


class PaymentSettings(models.Model):
    razorpay_key_id = models.CharField(max_length=255, blank=True, default='')
    razorpay_key_secret = models.CharField(max_length=255, blank=True, default='')
    currency = models.CharField(max_length=10, default='INR')
    currency_symbol = models.CharField(max_length=5, default='₹')
    is_active = models.BooleanField(default=False)
    payment_disabled_message = models.CharField(
        max_length=255,
        default='Online payment is temporarily unavailable. Please try again later.',
    )
    
    # UPI Payment Settings
    upi_enabled = models.BooleanField(default=False)
    upi_id = models.CharField(max_length=100, blank=True, default='')
    upi_merchant_name = models.CharField(max_length=100, blank=True, default='SYAFRA')
    upi_qr_code = models.ImageField(upload_to='upi/qr/', blank=True, null=True)
    
    # Payment method options
    payment_methods = models.JSONField(default=list, help_text='List of enabled payment methods: ["razorpay", "upi"]')
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Setting'
        verbose_name_plural = 'Payment Settings'

    def __str__(self):
        return f"Payment Settings (Active: {self.is_active})"

    def save(self, *args, **kwargs):
        if not self.pk and PaymentSettings.objects.exists():
            raise ValueError("Only one PaymentSettings instance allowed")
        return super().save(*args, **kwargs)

    @staticmethod
    def sanitize_razorpay_credential(value):
        if not value:
            return ''
        cleaned = value.strip()
        if cleaned.lower() in _RAZORPAY_PLACEHOLDER_VALUES:
            return ''
        return cleaned

    @classmethod
    def get_env_razorpay_credentials(cls):
        return (
            cls.sanitize_razorpay_credential(getattr(settings, 'RAZORPAY_KEY_ID', '')),
            cls.sanitize_razorpay_credential(getattr(settings, 'RAZORPAY_KEY_SECRET', '')),
        )

    @classmethod
    def get_settings(cls):
        """
        Get PaymentSettings singleton.
        
        🔧 FIX: Better error handling with logging.
        """
        global _PAYMENT_SETTINGS_WARNING_LOGGED
        try:
            settings = cls.objects.first()
            if not settings and not _PAYMENT_SETTINGS_WARNING_LOGGED:
                import logging
                logger = logging.getLogger('orders')
                logger.warning('PaymentSettings not configured in database. Admin must set up Razorpay keys.')
                _PAYMENT_SETTINGS_WARNING_LOGGED = True
            elif settings:
                _PAYMENT_SETTINGS_WARNING_LOGGED = False
            return settings
        except Exception as e:
            import logging
            logger = logging.getLogger('orders')
            logger.error(f'Error retrieving PaymentSettings: {e}')
            return None
    
    def get_currency_display_symbol(self):
        return self.currency_symbol

    @property
    def resolved_razorpay_key_id(self):
        db_value = self.sanitize_razorpay_credential(self.razorpay_key_id)
        if db_value:
            return db_value
        env_key_id, _ = self.get_env_razorpay_credentials()
        return env_key_id

    @property
    def resolved_razorpay_key_secret(self):
        db_value = self.sanitize_razorpay_credential(self.razorpay_key_secret)
        if db_value:
            return db_value
        _, env_key_secret = self.get_env_razorpay_credentials()
        return env_key_secret

    @property
    def has_payment_credentials(self):
        return bool(
            self.resolved_razorpay_key_id
        ) and bool(
            self.resolved_razorpay_key_secret
        )

    @property
    def is_ready(self):
        return bool(self.is_active and self.has_payment_credentials)


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', db_index=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, default='')
    shipping_address = models.TextField(default='')
    phone_number = models.CharField(max_length=20, default='')
    email = models.EmailField(default='', db_index=True)
    customer_name = models.CharField(max_length=200, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    stock_reduced = models.BooleanField(default=False, help_text='Whether stock has been reduced for this order')
    payment_confirmed_at = models.DateTimeField(null=True, blank=True, help_text='When payment was confirmed')
    confirmation_email_sent = models.BooleanField(default=False, help_text='Whether confirmation email has been sent')
    confirmation_email_claimed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the confirmation email send was claimed by a worker',
    )
    payment_email_sent = models.BooleanField(default=False, help_text='Whether payment confirmation email has been sent')
    payment_email_claimed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the payment email send was claimed by a worker',
    )
    admin_notification_sent = models.BooleanField(
        default=False,
        help_text='Whether the admin new-order notification email has been sent',
    )
    admin_notification_claimed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the admin notification send was claimed by a worker',
    )
    payment_retry_reserved_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='When the current payment retry reservation or retry session was created',
    )

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at'], name='orders_user_created_idx'),
            models.Index(fields=['payment_status', '-created_at'], name='orders_pay_created_idx'),
            models.Index(fields=['status', 'payment_status', '-created_at'], name='orders_status_pay_idx'),
            models.Index(fields=['payment_status', 'payment_retry_reserved_at'], name='orders_retry_state_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_price__gte=0),
                name='orders_total_price_gte_0',
            ),
            models.CheckConstraint(
                condition=Q(stock_reduced=False) | Q(payment_status='paid'),
                name='orders_stock_reduced_requires_paid',
            ),
            models.CheckConstraint(
                condition=Q(payment_confirmed_at__isnull=True) | Q(payment_status='paid'),
                name='orders_confirmed_at_requires_paid',
            ),
            models.UniqueConstraint(
                fields=['razorpay_order_id'],
                condition=~Q(razorpay_order_id=''),
                name='orders_unique_razorpay_order_id',
            ),
            models.UniqueConstraint(
                fields=['razorpay_payment_id'],
                condition=~Q(razorpay_payment_id=''),
                name='orders_unique_razorpay_payment_id',
            ),
            models.CheckConstraint(
                condition=Q(confirmation_email_sent=False) | Q(confirmation_email_claimed_at__isnull=True),
                name='orders_conf_email_claim_cleared',
            ),
            models.CheckConstraint(
                condition=Q(payment_email_sent=False) | Q(payment_email_claimed_at__isnull=True),
                name='orders_payment_email_claim_cleared',
            ),
            models.CheckConstraint(
                condition=Q(admin_notification_sent=False) | Q(admin_notification_claimed_at__isnull=True),
                name='orders_admin_email_claim_cleared',
            ),
            models.CheckConstraint(
                condition=Q(payment_retry_reserved_at__isnull=True) | Q(payment_status='pending'),
                name='orders_retry_reservation_pending_only',
            ),
        ]

    def __str__(self):
        return f"Order {self.id} - {self.user.username}"

    @property
    def latest_payment(self):
        return self.payments.order_by('-created_at').first()


class Payment(models.Model):
    PROVIDER_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('upi', 'UPI'),
    ]

    STATUS_CHOICES = [
        ('created', 'Created'),
        ('authorized', 'Authorized'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='razorpay', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    receipt = models.CharField(max_length=100, blank=True, default='', db_index=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, default='')
    failure_reason = models.CharField(max_length=255, blank=True, default='')
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name='payments_amount_gte_0',
            ),
            models.UniqueConstraint(
                fields=['razorpay_order_id'],
                condition=~Q(razorpay_order_id=''),
                name='payments_unique_razorpay_order_id',
            ),
            models.UniqueConstraint(
                fields=['razorpay_payment_id'],
                condition=~Q(razorpay_payment_id=''),
                name='payments_unique_razorpay_payment_id',
            ),
        ]
        indexes = [
            models.Index(fields=['order', '-created_at'], name='payments_order_created_idx'),
            models.Index(fields=['provider', 'status', '-created_at'], name='payments_provider_status_idx'),
        ]

    def __str__(self):
        return f"{self.get_provider_display()} payment for Order {self.order_id} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.CharField(max_length=10, blank=True, default='')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}" + (f" ({self.size})" if self.size else "")

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name='order_items_quantity_gt_0',
            ),
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name='order_items_price_gte_0',
            ),
            models.UniqueConstraint(
                fields=['order', 'product', 'size'],
                name='order_items_unique_order_product_size',
            ),
        ]
        indexes = [
            models.Index(fields=['order', 'product'], name='order_items_order_product_idx'),
        ]

    @property
    def subtotal(self):
        if self.price is None or self.quantity is None:
            return 0
        return self.price * self.quantity


class WhatsAppSettings(models.Model):
    whatsapp_number = models.CharField(max_length=20, blank=True, default='')
    enquiry_whatsapp = models.CharField(max_length=20, blank=True, default='')
    default_message = models.TextField(
        blank=True,
        default='Hi, I am interested in your products. Please share more details.'
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'WhatsApp Setting'
        verbose_name_plural = 'WhatsApp Settings'

    def __str__(self):
        return "WhatsApp Settings"

    def save(self, *args, **kwargs):
        if not self.pk and WhatsAppSettings.objects.exists():
            raise ValueError("Only one WhatsAppSettings instance allowed")
        return super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        try:
            return cls.objects.first()
        except Exception:
            return None
