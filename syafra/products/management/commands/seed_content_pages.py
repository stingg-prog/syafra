from django.core.management.base import BaseCommand
from products.models import ContentPage, FooterLink, HomepageSection


CONTENT_PAGES = [
    {
        'slug': 'shipping-returns',
        'title': 'Shipping & Returns',
        'overline': 'Policies',
        'display_order': 1,
    },
    {
        'slug': 'size-guide',
        'title': 'Size Guide',
        'overline': 'Fit Guide',
        'display_order': 2,
    },
    {
        'slug': 'about-us',
        'title': 'About Us',
        'overline': 'Our Story',
        'display_order': 3,
    },
    {
        'slug': 'sustainability',
        'title': 'Sustainability',
        'overline': 'Our Impact',
        'display_order': 4,
    },
    {
        'slug': 'privacy-policy',
        'title': 'Privacy Policy',
        'overline': 'Legal',
        'display_order': 5,
    },
    {
        'slug': 'terms-of-service',
        'title': 'Terms of Service',
        'overline': 'Legal',
        'display_order': 6,
    },
    {
        'slug': 'contact-us',
        'title': 'Contact Us',
        'overline': 'Get in Touch',
        'display_order': 7,
    },
]

FOOTER_LINK_UPDATES = [
    {
        'label': 'Contact Us',
        'url': '/contact/',
        'column_heading': 'HELP',
        'display_order': 5,
    },
    {
        'label': 'Shipping Info',
        'url': '/pages/shipping-returns/',
        'column_heading': 'HELP',
        'display_order': 6,
    },
    {
        'label': 'Returns',
        'url': '/pages/shipping-returns/',
        'column_heading': 'HELP',
        'display_order': 7,
    },
    {
        'label': 'FAQ',
        'url': '/pages/faq/',
        'column_heading': 'HELP',
        'display_order': 8,
    },
]

NEW_FOOTER_LINKS = [
    {
        'column_heading': 'HELP',
        'label': 'Size Guide',
        'url': '/pages/size-guide/',
        'display_order': 9,
    },
    {
        'column_heading': 'HELP',
        'label': 'Track Order',
        'url': '/track-order/',
        'display_order': 10,
    },
    {
        'column_heading': 'COMPANY',
        'label': 'About Us',
        'url': '/pages/about-us/',
        'display_order': 11,
    },
    {
        'column_heading': 'COMPANY',
        'label': 'Sustainability',
        'url': '/pages/sustainability/',
        'display_order': 12,
    },
    {
        'column_heading': 'COMPANY',
        'label': 'Privacy Policy',
        'url': '/pages/privacy-policy/',
        'display_order': 13,
    },
    {
        'column_heading': 'COMPANY',
        'label': 'Terms of Service',
        'url': '/pages/terms-of-service/',
        'display_order': 14,
    },
]


class Command(BaseCommand):
    help = 'Seed CMS ContentPage records and update FooterLink URLs'

    def handle(self, *args, **options):
        self._seed_content_pages()
        self._update_footer_links()
        self.stdout.write(self.style.SUCCESS('\nContent pages seeded successfully!'))
        self.stdout.write(f'ContentPages: {ContentPage.objects.count()}')
        self.stdout.write(f'FooterLinks: {FooterLink.objects.count()}')

    def _seed_content_pages(self):
        for page_data in CONTENT_PAGES:
            obj, created = ContentPage.objects.get_or_create(
                slug=page_data['slug'],
                defaults={
                    'title': page_data['title'],
                    'overline': page_data.get('overline', ''),
                    'display_order': page_data['display_order'],
                },
            )
            if created:
                self.stdout.write(f'  Created: ContentPage "{page_data["title"]}" ({page_data["slug"]})')
            else:
                self.stdout.write(f'  Exists: ContentPage "{page_data["title"]}" ({page_data["slug"]})')

    def _update_footer_links(self):
        footer_section = HomepageSection.objects.filter(section_type='footer').first()
        if not footer_section:
            self.stdout.write(self.style.WARNING('  No footer section found — skipping FooterLink updates'))
            return

        for link_data in FOOTER_LINK_UPDATES:
            updated = FooterLink.objects.filter(
                section=footer_section,
                label=link_data['label'],
            ).update(url=link_data['url'])
            if updated:
                self.stdout.write(f'  Updated: FooterLink "{link_data["label"]}" -> {link_data["url"]}')

        for link_data in NEW_FOOTER_LINKS:
            obj, created = FooterLink.objects.get_or_create(
                section=footer_section,
                label=link_data['label'],
                defaults=link_data,
            )
            if created:
                self.stdout.write(f'  Created: FooterLink "{link_data["label"]}" -> {link_data["url"]}')
            else:
                self.stdout.write(f'  Exists: FooterLink "{link_data["label"]}"')
