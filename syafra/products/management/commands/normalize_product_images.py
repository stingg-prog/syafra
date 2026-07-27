"""
Management command to reprocess all existing product images.

Usage:
    python manage.py normalize_product_images
    python manage.py normalize_product_images --category jackets
    python manage.py normalize_product_images --dry-run
    python manage.py normalize_product_images --force
"""

import logging
import sys
from io import BytesIO

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import models

from products.models import Product, ProductImage
from products.utils.image_normalizer import (
    normalize_product_image,
    compute_image_hash,
    NORMALIZATION_VERSION,
)
from products.utils.hooks import _set_normalizing

logger = logging.getLogger('products.utils.image_normalizer')


class Command(BaseCommand):
    help = 'Reprocess product images through the normalization pipeline'

    def add_arguments(self, parser):
        parser.add_argument('--category', type=str, help='Filter by category slug or name')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be processed')
        parser.add_argument('--force', action='store_true', help='Force re-normalization')
        parser.add_argument('--skip-primary', action='store_true', help='Skip primary images')
        parser.add_argument('--skip-gallery', action='store_true', help='Skip gallery images')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        category_filter = options['category']

        if options.get('verbosity', 1) >= 2:
            logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
        else:
            logging.basicConfig(level=logging.INFO, stream=sys.stdout)

        products = Product.objects.select_related('category').all()
        if category_filter:
            products = products.filter(
                models.Q(category__slug__icontains=category_filter) |
                models.Q(category__name__icontains=category_filter)
            )

        total = products.count()
        self.stdout.write(self.style.WARNING(f'Found {total} products (norm v{NORMALIZATION_VERSION})'))
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN'))

        processed = skipped = errors = 0

        for product in products:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'Product: {product.name}')
            self.stdout.write(f'Category: {product.category.name if product.category else "None"}')

            stored_hash = product.image_hash or ''
            stored_version = product.image_norm_version or 0
            if stored_hash:
                self.stdout.write(f'Hash: {stored_hash[:12]}... | Version: {stored_version}')
            else:
                self.stdout.write('Status: Not normalized')

            if not options['skip_primary'] and product.image:
                self.stdout.write(f'\n  Primary: {product.image.name}')
                try:
                    success = self._process(product.image, product, dry_run, force)
                    if success:
                        processed += 1
                        if not dry_run:
                            _set_normalizing(product, True)
                            try:
                                product.save(update_fields=['image_hash', 'image_norm_version'])
                            finally:
                                _set_normalizing(product, False)
                    else:
                        skipped += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'  ERROR: {e}'))
                    errors += 1

            if not options['skip_gallery']:
                for img in product.images.all():
                    if img.image:
                        self.stdout.write(f'\n  Gallery: {img.image.name}')
                        try:
                            success = self._process(img.image, img, dry_run, force)
                            if success:
                                processed += 1
                                if not dry_run:
                                    _set_normalizing(img, True)
                                    try:
                                        img.save(update_fields=['image_hash', 'image_norm_version'])
                                    finally:
                                        _set_normalizing(img, False)
                            else:
                                skipped += 1
                        except Exception as e:
                            self.stderr.write(self.style.ERROR(f'  ERROR: {e}'))
                            errors += 1

        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS(
            f'Processed: {processed} | Skipped: {skipped} | Errors: {errors}'
        ))

    def _process(self, image_field, instance, dry_run, force):
        try:
            image_field.open('rb')
            image_bytes = image_field.read()
            image_field.close()
        except Exception as e:
            self.stderr.write(self.style.WARNING(f'  Could not read: {e}'))
            return False

        if not image_bytes:
            self.stderr.write(self.style.WARNING('  Empty file'))
            return False

        image_file = BytesIO(image_bytes)
        image_file.name = image_field.name.split('/')[-1]

        stored_hash = getattr(instance, 'image_hash', '') or ''
        stored_version = getattr(instance, 'image_norm_version', 0) or 0
        current_hash = compute_image_hash(image_file)

        if not force:
            if stored_hash and stored_version >= NORMALIZATION_VERSION and current_hash == stored_hash:
                self.stdout.write(self.style.SUCCESS(f'  Already normalized (v{stored_version}) — skipping'))
                return False

        if dry_run:
            self.stdout.write(self.style.WARNING('  [DRY RUN] Would normalize'))
            return True

        image_file.seek(0)
        normalized = normalize_product_image(image_file)

        if normalized is image_file:
            self.stdout.write(self.style.WARNING('  Skipped (SVG/animated)'))
            return False

        content_file = ContentFile(normalized.read())
        image_field.save(image_field.name.split('/')[-1], content_file, save=False)

        instance.image_hash = current_hash
        instance.image_norm_version = NORMALIZATION_VERSION

        self.stdout.write(self.style.SUCCESS(f'  Normalized (v{NORMALIZATION_VERSION})'))
        return True
