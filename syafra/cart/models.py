from django.db import models, transaction
from django.contrib.auth import get_user_model
from products.models import Product

User = get_user_model()


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Cart {self.id} - {self.user.username}"

    @classmethod
    def get_for_user(cls, user):
        """Return a single cart for the user, merging duplicates if they exist."""
        with transaction.atomic():
            carts = list(cls.objects.select_for_update().filter(user=user).order_by('id'))
            if not carts:
                return cls.objects.create(user=user)

            primary_cart = carts[0]
            for duplicate in carts[1:]:
                for item in duplicate.items.all():
                    existing_item = primary_cart.items.filter(
                        product=item.product,
                        size=item.size,
                    ).first()
                    if existing_item:
                        existing_item.quantity += item.quantity
                        existing_item.save(update_fields=['quantity'])
                    else:
                        item.cart = primary_cart
                        item.save(update_fields=['cart'])
                duplicate.delete()
            return primary_cart

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_cart_user'),
        ]

    @property
    def total(self):
        # Use select_related to avoid N+1 queries when calculating cart totals.
        return sum(
            item.product.price * item.quantity
            for item in self.items.select_related('product').all()
        )


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, blank=True, default='')

    class Meta:
        unique_together = ('cart', 'product', 'size')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='cart_items_quantity_gt_0',
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.name}" + (f" ({self.size})" if self.size else "")

    @property
    def subtotal(self):
        return self.product.price * self.quantity
