import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'syafra.settings'
sys.path.insert(0, os.path.dirname(__file__))
import django
django.setup()
from django.db.models import Count
from products.models import Product

qs = Product.objects.filter(stock__gt=0)
print('Total products with stock > 0:', qs.count())
cats = qs.values('category__name').annotate(c=Count('id')).order_by('-c')
for c in cats:
    print(f'  {c["category__name"]}: {c["c"]}')
print()

# Check a product with related products
# Check ALL products
for product in Product.objects.filter(stock__gt=0).order_by('id'):
    print(f'Product: {product.id} - {product.name}')
    print(f'  Category: {product.category.name if product.category else "None"}')
    if product.category:
        same_cat = Product.objects.filter(category=product.category, stock__gt=0).exclude(pk=product.pk)
        print(f'  Same category count: {same_cat.count()}')
        extra = Product.objects.filter(stock__gt=0).exclude(pk=product.pk).exclude(pk__in=list(same_cat.values_list("pk", flat=True)))
        related = list(same_cat) + list(extra[:6 - same_cat.count()])
        print(f'  Related count: {len(related)}')
        print(f'  Related IDs: {[p.id for p in related]}')
    else:
        print(f'  No category - skip')
    print()
if product:
    print(f'Product: {product.id} - {product.name}')
    print(f'Category: {product.category.name if product.category else "None"}')
    same_cat = Product.objects.filter(category=product.category, stock__gt=0).exclude(pk=product.pk)
    print(f'Same category count: {same_cat.count()}')
    extra = Product.objects.filter(stock__gt=0).exclude(pk=product.pk).exclude(pk__in=list(same_cat.values_list("pk", flat=True)))
    print(f'Extra count: {extra.count()}')
    related = list(same_cat) + list(extra[:6 - same_cat.count()])
    print(f'Related count: {len(related)}')
    print(f'Related IDs: {[p.id for p in related]}')
