import os, django, sys
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')
django.setup()

from products.models import HomepageSection, Testimonial, InstagramPost

sections = HomepageSection.objects.filter(is_active=True).order_by('display_order')
print('=== ACTIVE HOMEPAGE SECTIONS ===')
for s in sections:
    col = s.collection
    col_name = col.name if col else 'NONE'
    if s.section_type in ('product_collection', 'womens_tops', 'trending_now', 'best_sellers'):
        prod_count = col.products.count() if col else 0
    else:
        prod_count = 'N/A'
    print(f'{s.display_order:>2}. {s.section_type:25s} title="{s.title}" subtitle="{s.subtitle}" overline="{s.overline}" active={s.is_active} collection={col_name} products={prod_count}')

print()
print('=== HOMEPAGE SECTION COUNTS ===')
print(f'Total sections: {HomepageSection.objects.count()}')
print(f'Active sections: {HomepageSection.objects.filter(is_active=True).count()}')

print()
print('=== ALL SECTIONS (including inactive) ===')
all_sections = HomepageSection.objects.all().order_by('section_type')
for s in all_sections:
    print(f'{s.section_type:25s} active={s.is_active} order={s.display_order}')

print()
print('=== TESTIMONIALS ===')
for t in Testimonial.objects.all():
    print(f'"{t.name}" active={t.is_active}')

print()
print('=== INSTAGRAM POSTS ===')
for p in InstagramPost.objects.all():
    print(f'id={p.id} active={p.is_active}')
