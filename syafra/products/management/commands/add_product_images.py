from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from urllib.request import urlopen
from urllib.error import URLError
from products.models import Product


class Command(BaseCommand):
    help = 'Downloads and assigns images to products'

    def handle(self, *args, **options):
        # Use Picsum for reliable placeholder images
        image_urls = [
            'https://picsum.photos/seed/jacket1/600/800',
            'https://picsum.photos/seed/jacket2/600/800',
            'https://picsum.photos/seed/jacket3/600/800',
            'https://picsum.photos/seed/jacket4/600/800',
            'https://picsum.photos/seed/jacket5/600/800',
            'https://picsum.photos/seed/jacket6/600/800',
            'https://picsum.photos/seed/jacket7/600/800',
            'https://picsum.photos/seed/jacket8/600/800',
            'https://picsum.photos/seed/jacket9/600/800',
            'https://picsum.photos/seed/jacket10/600/800',
            'https://picsum.photos/seed/jacket11/600/800',
            'https://picsum.photos/seed/jacket12/600/800',
            'https://picsum.photos/seed/jacket13/600/800',
            'https://picsum.photos/seed/jacket14/600/800',
            'https://picsum.photos/seed/jacket15/600/800',
            'https://picsum.photos/seed/jacket16/600/800',
            'https://picsum.photos/seed/jacket17/600/800',
            'https://picsum.photos/seed/jacket18/600/800',
            'https://picsum.photos/seed/jacket19/600/800',
            'https://picsum.photos/seed/jacket20/600/800',
            'https://picsum.photos/seed/jacket21/600/800',
            'https://picsum.photos/seed/jacket22/600/800',
            'https://picsum.photos/seed/jacket23/600/800',
            'https://picsum.photos/seed/jacket24/600/800',
            'https://picsum.photos/seed/jacket25/600/800',
            'https://picsum.photos/seed/jacket26/600/800',
            'https://picsum.photos/seed/jacket27/600/800',
            'https://picsum.photos/seed/jacket28/600/800',
            'https://picsum.photos/seed/jacket29/600/800',
            'https://picsum.photos/seed/jacket30/600/800',
            'https://picsum.photos/seed/jacket31/600/800',
            'https://picsum.photos/seed/jacket32/600/800',
        ]
        
        self.stdout.write('Downloading images for all products...')
        
        count = 0
        products = Product.objects.all()
        
        for i, product in enumerate(products):
            url = image_urls[i % len(image_urls)]
            
            try:
                response = urlopen(url, timeout=15)
                content = response.read()
                filename = f"jacket_{product.id}.jpg"
                product.image.save(
                    filename,
                    ContentFile(content),
                    save=True
                )
                count += 1
                self.stdout.write(f'  Added: {product.name}')
            except URLError as e:
                self.stdout.write(f'  Error for {product.name}: {e}')
        
        self.stdout.write(self.style.SUCCESS(f'Images added! ({count}/{products.count()} products)'))
