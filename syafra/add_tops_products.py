import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')
django.setup()
from products.models import ProductCollection, Product

wc = ProductCollection.objects.get(name="Women's Tops")
products = Product.objects.filter(id__in=[4, 7, 3, 10, 5, 1])
wc.products.add(*products)
print(f'Added {products.count()} products to "{wc.name}"')
print(f'Total: {wc.products.count()} products')
for p in wc.products.all():
    print(f'  - {p.name}')
