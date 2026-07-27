"""
Management command to verify normalized product images have consistent
visual weight.

Usage:
    python manage.py verify_image_normalization
    python manage.py verify_image_normalization --json
"""

import json
from collections import defaultdict
from io import BytesIO

from django.core.management.base import BaseCommand

from products.models import Product
from products.utils.image_normalizer import CANVAS_SIZE


class Command(BaseCommand):
    help = 'Verify that normalized product images have consistent visual weight'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', help='Output as JSON')

    def handle(self, *args, **options):
        from PIL import Image

        products = Product.objects.select_related('category').filter(
            image__isnull=False
        ).exclude(image='')

        results = []
        by_category = defaultdict(list)

        self.stdout.write(f'Analyzing {products.count()} product images...\n')

        for product in products:
            try:
                product.image.open('rb')
                image_bytes = product.image.read()
                product.image.close()
            except Exception as e:
                self.stderr.write(f'Cannot read {product.name}: {e}')
                continue

            if not image_bytes:
                continue

            img = Image.open(BytesIO(image_bytes))
            w, h = img.size

            gray = img.convert('L')
            mask = gray.point(lambda p: 255 if p < 250 else 0)
            bbox = mask.getbbox()

            if bbox:
                bx, by, bw, bh = bbox
                fill_h = bh / CANVAS_SIZE
                fill_w = bw / CANVAS_SIZE
                center_y = (by + bh / 2) / CANVAS_SIZE
                center_x = (bx + bw / 2) / CANVAS_SIZE
            else:
                fill_h = fill_w = center_y = center_x = 0

            cat_name = product.category.name if product.category else 'Uncategorized'

            result = {
                'product': product.name,
                'category': cat_name,
                'image_size': f'{w}x{h}',
                'fill_height': round(fill_h * 100, 1),
                'fill_width': round(fill_w * 100, 1),
                'center_x': round(center_x, 3),
                'center_y': round(center_y, 3),
            }
            results.append(result)
            by_category[cat_name].append(result)

        if options['json']:
            self.stdout.write(json.dumps(results, indent=2))
            return

        for cat, items in sorted(by_category.items()):
            self.stdout.write(self.style.WARNING(f'\n{"="*60}'))
            self.stdout.write(self.style.WARNING(f'{cat} ({len(items)} products)'))
            self.stdout.write(self.style.WARNING(f'{"="*60}'))

            for item in items:
                self.stdout.write(f"\n  {item['product']}")
                self.stdout.write(f"    Size: {item['image_size']}")
                self.stdout.write(f"    Fill: {item['fill_height']}%H × {item['fill_width']}%W")
                self.stdout.write(f"    Center: ({item['center_x']:.2f}, {item['center_y']:.2f})")

            fills_h = [i['fill_height'] for i in items]
            fills_w = [i['fill_width'] for i in items]
            centers_y = [i['center_y'] for i in items]

            if fills_h:
                avg_h = sum(fills_h) / len(fills_h)
                std_h = (sum((f - avg_h)**2 for f in fills_h) / len(fills_h)) ** 0.5
                avg_w = sum(fills_w) / len(fills_w)
                std_w = (sum((f - avg_w)**2 for f in fills_w) / len(fills_w)) ** 0.5
                avg_cy = sum(centers_y) / len(centers_y)
                std_cy = (sum((c - avg_cy)**2 for c in centers_y) / len(centers_y)) ** 0.5

                self.stdout.write(f"\n  Consistency:")
                self.stdout.write(f"    Height fill: avg={avg_h:.1f}%  std={std_h:.1f}%  range={min(fills_h):.1f}%-{max(fills_h):.1f}%")
                self.stdout.write(f"    Width fill:  avg={avg_w:.1f}%  std={std_w:.1f}%  range={min(fills_w):.1f}%-{max(fills_w):.1f}%")
                self.stdout.write(f"    Center Y:    avg={avg_cy:.3f}  std={std_cy:.3f}")

        # Overall
        all_h = [r['fill_height'] for r in results]
        all_w = [r['fill_width'] for r in results]
        all_cy = [r['center_y'] for r in results]

        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS('OVERALL'))
        self.stdout.write(f'{"="*60}')
        self.stdout.write(f'Total: {len(results)} products')

        if all_h:
            avg_h = sum(all_h) / len(all_h)
            std_h = (sum((f - avg_h)**2 for f in all_h) / len(all_h)) ** 0.5
            avg_w = sum(all_w) / len(all_w)
            std_w = (sum((f - avg_w)**2 for f in all_w) / len(all_w)) ** 0.5
            avg_cy = sum(all_cy) / len(all_cy)
            std_cy = (sum((c - avg_cy)**2 for c in all_cy) / len(all_cy)) ** 0.5

            self.stdout.write(f'Height fill: avg={avg_h:.1f}%  std={std_h:.1f}%')
            self.stdout.write(f'Width fill:  avg={avg_w:.1f}%  std={std_w:.1f}%')
            self.stdout.write(f'Center Y:    avg={avg_cy:.3f}  std={std_cy:.3f}')

            status_h = 'GOOD' if std_h < 8 else 'NEEDS REVIEW'
            status_cy = 'GOOD' if std_cy < 0.15 else 'NEEDS REVIEW'
            self.stdout.write(self.style.SUCCESS(f'  Height consistency: {status_h} (std={std_h:.1f}%)'))
            self.stdout.write(self.style.SUCCESS(f'  Center consistency: {status_cy} (std={std_cy:.3f})'))
