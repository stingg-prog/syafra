from django.contrib import admin
from django.contrib.admin import AdminSite as DjangoAdminSite
from django.contrib.admin.models import LogEntry
from django.urls import reverse


CUSTOM_MODEL_NAMES = {
    'auth.User': 'Customers',
    'auth.Group': 'Permission Groups',
    'cms.TestimonialExtended': 'Extended Testimonials',
    'orders.OrderItem': 'Order Items',
    'orders.Payment': 'Payments',
    'cart.Cart': 'Carts',
    'products.ProductCollection': 'Promotions',
    'cms.SiteNavigation': 'Navigation',
    'cms.SEOSettings': 'SEO Settings',
    'cms.FAQCategory': 'FAQ Categories',
    'orders.WhatsAppSettings': 'WhatsApp Settings',
    'cms.PromotionalPopup': 'Popups',
    'cms.AnnouncementBarConfig': 'Announcement Bar',
    'cms.PromoBanner': 'Promo Banners',
    'products.HomepageSection': 'Homepage Builder',
    'products.NewsletterSubscriber': 'Subscribers',
    'products.ThemeSettings': 'Theme Settings',
    'products.WebsiteSettings': 'Website Settings',
    'products.Testimonial': 'Testimonials',
    'cms.BlogPost': 'Blog Posts',
    'cms.BlogCategory': 'Blog Categories',
    'cms.BlogAuthor': 'Blog Authors',
    'cms.BlogTag': 'Blog Tags',
    'cms.Lookbook': 'Lookbooks',
    'cms.LegalPage': 'Legal Pages',
    'products.ContentPage': 'Content Pages',
    'cms.Collection': 'Collections',
    'cms.Brand': 'Brands',
    'cms.SizeChart': 'Size Charts',
    'cms.ProductLabel': 'Product Labels',
    'cms.ProductBadge': 'Product Badges',
    'cms.CareInstruction': 'Care Instructions',
    'cms.ThemeBackup': 'Theme Backups',
    'products.ContactMessage': 'Contact Messages',
    'accounts.EmailLog': 'Email Logs',
    'accounts.EmailWebhookEvent': 'Email Webhook Events',
    'products.InstagramFeedItem': 'Instagram Feed',
    'products.Category': 'Categories',
}

CUSTOM_MODEL_ICONS = {
    'products.HomepageSection': '🏠',
    'products.ThemeSettings': '🎨',
    'products.WebsiteSettings': '🌐',
    'cms.SiteNavigation': '🧭',
    'cms.AnnouncementBarConfig': '📢',
    'cms.PromoBanner': '🏷️',
    'cms.PromotionalPopup': '🪟',
    'cms.SEOSettings': '🔍',
    'products.Product': '📦',
    'products.Category': '📂',
    'cms.Collection': '🗂️',
    'cms.Brand': '🏷️',
    'cms.SizeChart': '📏',
    'cms.ProductLabel': '🔖',
    'cms.ProductBadge': '⭐',
    'cms.CareInstruction': '🧺',
    'cms.BlogPost': '📝',
    'cms.BlogCategory': '📑',
    'cms.BlogAuthor': '✍️',
    'cms.BlogTag': '#️⃣',
    'cms.Lookbook': '📖',
    'cms.FAQCategory': '❓',
    'products.ContentPage': '📄',
    'cms.LegalPage': '⚖️',
    'products.Testimonial': '💬',
    'cms.TestimonialExtended': '📋',
    'products.InstagramFeedItem': '📸',
    'products.NewsletterSubscriber': '✉️',
    'products.ProductCollection': '🎯',
    'orders.Order': '🛒',
    'orders.OrderItem': '📦',
    'orders.Payment': '💳',
    'orders.PaymentSettings': '💰',
    'orders.WhatsAppSettings': '💬',
    'cart.Cart': '🛍️',
    'auth.User': '👤',
    'auth.Group': '👥',
    'cms.ThemeBackup': '💾',
    'products.ContactMessage': '📨',
    'accounts.EmailLog': '📧',
    'accounts.EmailWebhookEvent': '🔔',
}

SYAFRA_SECTIONS_CONFIG = [
    {
        'name': 'Website',
        'icon': '🏠',
        'color': '#6366f1',
        'bg_color': '#eef2ff',
        'description': 'Homepage builder, theme, navigation and SEO settings',
        'models': [
            'products.HomepageSection', 'products.ThemeSettings', 'products.WebsiteSettings',
            'cms.SiteNavigation', 'cms.AnnouncementBarConfig', 'cms.PromoBanner',
            'cms.PromotionalPopup', 'cms.SEOSettings',
        ],
    },
    {
        'name': 'Products',
        'icon': '🛍️',
        'color': '#8b5cf6',
        'bg_color': '#f5f3ff',
        'description': 'Products, categories, collections, brands and size charts',
        'models': ['products.Product', 'products.Category', 'cms.Collection', 'cms.Brand', 'cms.SizeChart'],
    },
    {
        'name': 'Product Configuration',
        'icon': '👕',
        'color': '#f59e0b',
        'bg_color': '#fffbeb',
        'description': 'Labels, badges and care instructions for product details',
        'models': ['cms.ProductLabel', 'cms.ProductBadge', 'cms.CareInstruction'],
    },
    {
        'name': 'Content',
        'icon': '📰',
        'color': '#ec4899',
        'bg_color': '#fdf2f8',
        'description': 'Blog, lookbooks, FAQ, legal pages and content pages',
        'models': [
            'cms.BlogPost', 'cms.BlogCategory', 'cms.BlogAuthor', 'cms.BlogTag',
            'cms.Lookbook', 'cms.FAQCategory', 'products.ContentPage', 'cms.LegalPage',
        ],
    },
    {
        'name': 'Marketing',
        'icon': '📈',
        'color': '#10b981',
        'bg_color': '#ecfdf5',
        'description': 'Testimonials, Instagram feed, newsletter subscribers and promotions',
        'models': ['products.Testimonial', 'cms.TestimonialExtended', 'products.InstagramFeedItem', 'products.NewsletterSubscriber', 'products.ProductCollection'],
    },
    {
        'name': 'Sales',
        'icon': '📊',
        'color': '#3b82f6',
        'bg_color': '#eff6ff',
        'description': 'Orders, payments, customers and cart management',
        'models': ['orders.Order', 'orders.OrderItem', 'orders.Payment', 'orders.PaymentSettings', 'orders.WhatsAppSettings', 'cart.Cart', 'auth.User'],
    },
    {
        'name': 'Configuration',
        'icon': '⚙️',
        'color': '#6b7280',
        'bg_color': '#f9fafb',
        'description': 'Theme backups, contact messages, email logs and permission groups',
        'models': ['cms.ThemeBackup', 'products.ContactMessage', 'accounts.EmailLog', 'accounts.EmailWebhookEvent', 'auth.Group'],
    },
]

EXTERNAL_SECTION_LINKS = {
    'Configuration': [
        {'label': 'Export Theme', 'url_name': 'products:theme_export', 'icon': '📤'},
        {'label': 'Import Theme', 'url_name': 'products:theme_import', 'icon': '📥'},
        {'label': 'Manage Backups', 'url_name': 'products:backup_list', 'icon': '💾'},
    ],
}


def _model_key(model):
    return f'{model._meta.app_label}.{model._meta.object_name}'


class SyafraAdminSite(DjangoAdminSite):

    def get_model_name(self, model_key):
        return CUSTOM_MODEL_NAMES.get(model_key, None)

    def get_model_icon(self, model_key):
        return CUSTOM_MODEL_ICONS.get(model_key, '📄')

    def get_grouped_app_list(self, request):
        model_map = {}
        for model, model_admin in self._registry.items():
            key = _model_key(model)
            has_perm = True
            if hasattr(model_admin, 'has_module_permission'):
                has_perm = model_admin.has_module_permission(request)
            if not has_perm:
                continue
            admin_url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist', current_app=self.name)
            add_url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_add', current_app=self.name)
            count = None
            try:
                count = model.objects.count()
            except Exception:
                pass
            orig_name = model._meta.verbose_name_plural.title() if hasattr(model._meta, 'verbose_name_plural') else model._meta.object_name
            display_name = CUSTOM_MODEL_NAMES.get(key, orig_name)
            icon = CUSTOM_MODEL_ICONS.get(key, '📄')
            model_map[key] = {
                'name': display_name,
                'admin_url': admin_url,
                'add_url': add_url,
                'object_name': model._meta.object_name,
                'perms': {'change': True},
                'count': count,
                'icon': icon,
            }
        sections = []
        for section_config in SYAFRA_SECTIONS_CONFIG:
            section_models = []
            for model_key in section_config['models']:
                if model_key in model_map:
                    section_models.append(model_map[model_key])
            external_links = EXTERNAL_SECTION_LINKS.get(section_config['name'], [])
            resolved_links = []
            for link in external_links:
                try:
                    resolved_links.append({
                        'label': link['label'],
                        'icon': link.get('icon', '🔗'),
                        'url': reverse(link['url_name'], current_app=self.name),
                    })
                except Exception:
                    resolved_links.append({
                        'label': link['label'],
                        'icon': link.get('icon', '🔗'),
                        'url': '#',
                    })
            name_models = section_models + resolved_links
            if name_models:
                section_url = section_models[0]['admin_url'] if section_models else '#'
                sections.append({
                    'name': section_config['name'],
                    'description': section_config['description'],
                    'icon': section_config['icon'],
                    'color': section_config['color'],
                    'bg_color': section_config['bg_color'],
                    'url': section_url,
                    'models': section_models,
                    'external_links': resolved_links,
                })
        grouped_keys = set()
        for sc in SYAFRA_SECTIONS_CONFIG:
            for mk in sc['models']:
                grouped_keys.add(mk)
        ungrouped = [m for k, m in model_map.items() if k not in grouped_keys]
        if ungrouped:
            sections.append({
                'name': 'Other',
                'icon': '📋',
                'color': '#9ca3af',
                'bg_color': '#f3f4f6',
                'description': 'Additional management tools',
                'models': ungrouped,
                'external_links': [],
            })
        return sections

    def get_dashboard_stats(self, request):
        from cms.models import Collection, Brand, BlogPost
        from orders.models import Order
        from products.models import Product, HomepageSection, NewsletterSubscriber, Testimonial
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            order_base = Order.objects
            return {
                'products': Product.objects.count(),
                'orders': order_base.count(),
                'pending_orders': order_base.filter(status='pending').count(),
                'customers': User.objects.filter(is_staff=False).count(),
                'collections': Collection.objects.filter(is_active=True).count(),
                'brands': Brand.objects.filter(is_active=True).count(),
                'blog_posts': BlogPost.objects.filter(is_published=True).count(),
                'subscribers': NewsletterSubscriber.objects.filter(is_active=True).count(),
                'testimonials': Testimonial.objects.filter(is_active=True).count(),
                'sections': HomepageSection.objects.filter(is_active=True).count(),
            }
        except Exception:
            return {}

    def get_quick_actions(self, request):
        return [
            {'url': reverse('admin:products_homepagesection_changelist', current_app=self.name), 'label': 'Homepage Builder', 'icon': '🏠'},
            {'url': reverse('admin:products_themesettings_change', args=[1], current_app=self.name), 'label': 'Edit Theme', 'icon': '🎨'},
            {'url': reverse('admin:products_product_add', current_app=self.name), 'label': 'Create Product', 'icon': '📦'},
            {'url': reverse('admin:cms_collection_add', current_app=self.name), 'label': 'Create Collection', 'icon': '🗂️'},
            {'url': reverse('admin:cms_blogpost_add', current_app=self.name), 'label': 'Create Blog Post', 'icon': '📝'},
            {'url': reverse('admin:cms_faqcategory_add', current_app=self.name), 'label': 'Create FAQ', 'icon': '❓'},
            {'url': reverse('admin:auth_user_changelist', current_app=self.name), 'label': 'View Customers', 'icon': '👤'},
            {'url': reverse('admin:orders_order_changelist', current_app=self.name), 'label': 'View Orders', 'icon': '🛒'},
        ]

    def get_recent_items(self, request):
        entries = LogEntry.objects.select_related('content_type', 'user').order_by('-action_time')[:12]
        recent = []
        for entry in entries:
            url = ''
            if entry.is_change() or entry.is_addition():
                try:
                    url = reverse(
                        f'admin:{entry.content_type.app_label}_{entry.content_type.model}_change',
                        args=[entry.object_id],
                        current_app=self.name,
                    )
                except Exception:
                    pass
            model_key = f'{entry.content_type.app_label}.{entry.content_type.model}'
            icon = CUSTOM_MODEL_ICONS.get(model_key, '📄')
            recent.append({
                'action': 'added' if entry.is_addition() else 'changed' if entry.is_change() else 'deleted',
                'object_repr': entry.object_repr,
                'user': str(entry.user),
                'time': entry.action_time,
                'url': url,
                'icon': icon,
            })
        return recent

    def index(self, request, extra_context=None):
        context = {
            'stats': self.get_dashboard_stats(request),
            'quick_actions': self.get_quick_actions(request),
            'syafra_sections': self.get_grouped_app_list(request),
            'recent_items': self.get_recent_items(request),
        }
        if extra_context:
            context.update(extra_context)
        return super().index(request, extra_context=context)

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label=app_label)
        grouped = self.get_grouped_app_list(request)
        for section in grouped:
            for model_entry in section['models']:
                model_entry['admin_url'] = model_entry.get('admin_url', '#')
        return app_list


admin.site.__class__ = SyafraAdminSite
