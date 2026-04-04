from django.db import migrations, models


def merge_duplicate_carts(apps, schema_editor):
    Cart = apps.get_model('cart', 'Cart')
    CartItem = apps.get_model('cart', 'CartItem')

    for user_id in Cart.objects.values_list('user_id', flat=True).distinct():
        carts = list(Cart.objects.filter(user_id=user_id).order_by('id'))
        if len(carts) <= 1:
            continue

        primary_cart = carts[0]
        for duplicate in carts[1:]:
            for item in CartItem.objects.filter(cart=duplicate):
                existing_item = CartItem.objects.filter(
                    cart=primary_cart,
                    product_id=item.product_id,
                    size=item.size,
                ).first()
                if existing_item:
                    existing_item.quantity += item.quantity
                    existing_item.save(update_fields=['quantity'])
                    item.delete()
                else:
                    item.cart_id = primary_cart.id
                    item.save(update_fields=['cart_id'])
            duplicate.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0002_alter_cartitem_unique_together_cartitem_size_and_more'),
    ]

    operations = [
        migrations.RunPython(merge_duplicate_carts, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='cart',
            constraint=models.UniqueConstraint(fields=['user'], name='unique_cart_user'),
        ),
    ]
