from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    Category, Product, ProductSize, ProductImage, InstagramPost, Testimonial,
    HomepageSection, HeroSlide, TrustBarItem, ShopByCategoryItem,
    ProductCollection, FooterLink, NewsletterSubscriber,
    PromotionalBannerConfig, ThemeSettings, WebsiteSettings,
    ContentPage, ContactMessage,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 1
    fields = ('size', 'stock')
    min_num = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image',)
    max_num = 10


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'price', 'stock', 'condition', 'created_at')
    list_filter = ('category', 'brand', 'condition')
    search_fields = ('name', 'brand', 'description')
    list_editable = ('stock',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProductSizeInline, ProductImageInline]


@admin.register(InstagramPost)
class InstagramPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('link',)
    list_editable = ('is_active',)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'review')
    list_editable = ('is_active',)


# =============================================================================
# Homepage CMS Admin
# =============================================================================

@admin.register(ProductCollection)
class ProductCollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count', 'created_at')
    search_fields = ('name',)
    filter_horizontal = ('products',)
    readonly_fields = ('created_at', 'updated_at')

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


class HeroSlideInline(admin.TabularInline):
    model = HeroSlide
    extra = 1
    fields = ('display_order', 'is_active', 'title', 'subtitle', 'button_text', 'button_url', 'desktop_image', 'mobile_image', 'overlay_opacity', 'image_position_x', 'image_position_y')
    ordering = ['display_order']


class TrustBarItemInline(admin.TabularInline):
    model = TrustBarItem
    extra = 3
    fields = ('display_order', 'is_active', 'title', 'description', 'icon_svg')
    ordering = ['display_order']


class ShopByCategoryItemInline(admin.TabularInline):
    model = ShopByCategoryItem
    extra = 2
    fields = ('display_order', 'is_active', 'category', 'headline', 'label', 'desktop_image', 'mobile_image')
    ordering = ['display_order']


class FooterLinkInline(admin.TabularInline):
    model = FooterLink
    extra = 3
    fields = ('display_order', 'is_active', 'column_heading', 'label', 'url', 'is_external')
    ordering = ['display_order']


class PromotionalBannerConfigInline(admin.StackedInline):
    model = PromotionalBannerConfig
    extra = 0
    max_num = 1
    fields = ('is_active', 'desktop_image', 'mobile_image')
    verbose_name = 'Promotional Banner Image'
    verbose_name_plural = 'Promotional Banner Image'
    can_delete = False


@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = ('section_type', 'title', 'display_order', 'is_active')
    list_filter = ('section_type', 'is_active')
    list_editable = ('display_order', 'is_active')
    search_fields = ('title', 'subtitle', 'overline')
    ordering = ['display_order']
    save_on_top = True

    def get_form(self, request, obj=None, **kwargs):
        from products.forms import HomepageSectionAdminForm
        kwargs['form'] = HomepageSectionAdminForm
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        section_type = self._get_section_type(request, obj)
        base = [
            (None, {'fields': ('section_type', 'title', 'overline', 'subtitle')}),
            ('Visibility', {'fields': ('display_order', 'is_active')}),
        ]

        if section_type == 'announcement_bar':
            base.append(('Content', {
                'fields': ('config_text', 'config_link_url', ('config_bg_color', 'config_text_color')),
            }))
        elif section_type == 'hero_slider':
            base.append(('Secondary Call-to-Action', {
                'fields': ('config_secondary_cta_label', 'config_secondary_cta_url'),
                'description': 'Optional secondary button below the main slide CTA.',
            }))
        elif section_type == 'trust_bar':
            pass  # Content managed via TrustBarItem inline
        elif section_type == 'shop_by_category':
            pass  # Content managed via ShopByCategoryItem inline
        elif section_type == 'product_collection':
            base.append(('Collection', {
                'fields': ('collection',),
                'description': 'Select a Product Collection to display in this section.',
            }))
        elif section_type in ('womens_tops', 'trending_now', 'best_sellers'):
            base.append(('Collection', {
                'fields': ('collection',),
                'description': 'Select a Product Collection to display in this section.',
            }))
        elif section_type == 'promotional_banner':
            base.append(('Content', {
                'fields': ('config_headline', 'config_description', 'config_button_text', 'config_button_url', ('config_bg_color', 'config_text_color')),
            }))
        elif section_type in ('customer_reviews', 'instagram_feed'):
            base.append(('Settings', {
                'fields': ('config_max_items',),
            }))
        elif section_type == 'newsletter':
            pass  # Content managed via NewsletterConfig (future) or config fields
        elif section_type == 'footer':
            pass  # Content managed via FooterLink inline

        base.append(('Desktop Settings', {
            'classes': ('collapse',),
            'fields': (
                'device_desktop_bg_image',
                'device_desktop_bg_color',
                'device_desktop_padding_y',
                'device_desktop_text_align',
                'device_desktop_max_width',
            ),
        }))
        base.append(('Tablet Settings', {
            'classes': ('collapse',),
            'fields': (
                'device_tablet_bg_image',
                'device_tablet_bg_color',
                'device_tablet_padding_y',
                'device_tablet_text_align',
                'device_tablet_max_width',
            ),
        }))
        base.append(('Mobile Settings', {
            'classes': ('collapse',),
            'fields': (
                'device_mobile_bg_image',
                'device_mobile_bg_color',
                'device_mobile_padding_y',
                'device_mobile_text_align',
                'device_mobile_max_width',
            ),
        }))
        return base

    def get_inlines(self, request, obj=None):
        section_type = self._get_section_type(request, obj)
        if section_type == 'hero_slider':
            return [HeroSlideInline]
        if section_type == 'trust_bar':
            return [TrustBarItemInline]
        if section_type == 'shop_by_category':
            return [ShopByCategoryItemInline]
        if section_type == 'promotional_banner':
            return [PromotionalBannerConfigInline]
        if section_type == 'footer':
            return [FooterLinkInline]
        return []

    def _get_section_type(self, request, obj):
        if obj and obj.pk:
            return obj.section_type
        return request.POST.get('section_type', '')


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'source', 'created_at')
    list_filter = ('is_active', 'source')
    search_fields = ('email',)
    readonly_fields = ('created_at', 'unsubscribed_at')
    actions = ['activate_subscribers', 'deactivate_subscribers']

    @admin.action(description='Activate selected subscribers')
    def activate_subscribers(self, request, queryset):
        queryset.update(is_active=True, unsubscribed_at=None)

    @admin.action(description='Deactivate selected subscribers')
    def deactivate_subscribers(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_active=False, unsubscribed_at=timezone.now())


# =============================================================================
# Theme & Website Settings Admin (Singleton)
# =============================================================================

@admin.register(ThemeSettings)
class ThemeSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Branding', {
            'fields': ('store_name', 'tagline', ('primary_color', 'secondary_color', 'accent_color'), 'logo', 'favicon'),
        }),
        ('Website Loader', {
            'fields': ('enable_loader', 'loader_type', 'loader_color'),
        }),
    )

    def has_add_permission(self, request):
        return not ThemeSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        obj = ThemeSettings.get_settings()
        return redirect(reverse('admin:products_themesettings_change', args=[obj.pk]))


@admin.register(WebsiteSettings)
class WebsiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone', 'business_address', 'business_hours'),
        }),
        ('WhatsApp', {
            'fields': ('whatsapp_number', 'whatsapp_default_message'),
        }),
        ('Maintenance Mode', {
            'fields': ('maintenance_mode', 'maintenance_message'),
            'description': 'When enabled, non-staff visitors see the maintenance page. Admin and staff can still access the site.',
        }),
        ('SEO (Search Engine Optimization)', {
            'fields': ('seo_title', 'seo_description', 'seo_keywords', 'og_image', 'google_search_console_verification'),
            'description': 'Controls how your website appears in search results and social media shares.',
        }),
        ('Analytics & Tracking', {
            'fields': ('google_analytics_id', 'meta_pixel_id'),
        }),
        ('Social Media', {
            'fields': (
                ('instagram_url', 'facebook_url'),
                ('twitter_url', 'tiktok_url'),
                ('youtube_url', 'pinterest_url'),
                ('threads_url', 'linkedin_url'),
            ),
        }),
        ('Footer', {
            'fields': ('copyright_text',),
        }),
    )

    def has_add_permission(self, request):
        return not WebsiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        obj = WebsiteSettings.get_settings()
        return redirect(reverse('admin:products_websitesettings_change', args=[obj.pk]))


@admin.register(ContentPage)
class ContentPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'display_order')
    list_filter = ('is_active',)
    list_editable = ('display_order',)
    search_fields = ('title', 'slug')
    ordering = ['display_order', 'title']
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'overline'),
        }),
        ('Content', {
            'fields': ('summary', 'content'),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
        }),
        ('Settings', {
            'fields': ('is_active', 'display_order'),
        }),
    )
    save_on_top = True


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('name', 'email', 'subject')
    readonly_fields = ('name', 'email', 'phone', 'subject', 'message', 'created_at')
    list_editable = ('is_read',)
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False
