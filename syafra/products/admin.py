import json
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from .models import (
    Category, Product, ProductSize, ProductImage, InstagramFeedItem, Testimonial,
    HomepageSection, HeroSlide, TrustBarItem, ShopByCategoryItem,
    ProductCollection, FooterLink, NewsletterSubscriber,
    PromotionalBannerConfig, ThemeSettings, WebsiteSettings,
    ContentPage, ContactMessage,
)


def _admin_preview_link(model_name, object_id, label='Preview'):
    url = reverse('products:admin_preview', args=[model_name, object_id])
    return format_html(
        '<a class="button" href="{}" target="_blank" style="padding:2px 8px;font-size:11px;background:#417690;color:#fff;border-radius:3px;text-decoration:none;white-space:nowrap;">{}</a>',
        url, label
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order')
    list_editable = ('display_order',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    ordering = ['display_order', 'name']


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


@admin.register(InstagramFeedItem)
class InstagramFeedItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_active', 'display_order', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('link',)
    list_editable = ('is_active', 'display_order')


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'display_order', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'review')
    list_editable = ('is_active', 'display_order')


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
    fields = ('display_order', 'is_active', 'title', 'subtitle', 'description', 'button_text', 'button_url', 'desktop_image', 'mobile_image', 'overlay_opacity', 'image_position_x', 'image_position_y')
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
    list_display = ('section_type', 'title', 'display_order', 'is_active', 'publish_status', 'section_preview_link')
    list_filter = ('section_type', 'is_active')
    list_editable = ('display_order', 'is_active')
    search_fields = ('title', 'subtitle', 'overline')
    ordering = ['display_order']
    save_on_top = True
    actions = ['duplicate_section', 'publish_now', 'unpublish_now', 'enable_selected', 'disable_selected']

    def get_form(self, request, obj=None, **kwargs):
        from products.forms import HomepageSectionAdminForm
        kwargs['form'] = HomepageSectionAdminForm
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        section_type = self._get_section_type(request, obj)
        base = [
            (None, {'fields': ('section_type', 'title', 'overline', 'subtitle')}),
            ('Scheduling', {
                'fields': ('display_order', 'is_active', 'publish_at', 'unpublish_at'),
                'classes': ('collapse',),
            }),
            ('Design & Layout', {
                'fields': (
                    'bg_color', 'bg_image',
                    ('padding_top', 'padding_bottom'),
                    'margin', 'border_radius',
                    'container_width', 'full_width',
                    'animation',
                ),
                'classes': ('collapse',),
            }),
            ('Responsive Visibility', {
                'fields': ('hide_on_mobile', 'hide_on_tablet', 'hide_on_desktop'),
                'classes': ('collapse',),
            }),
            ('Advanced', {
                'fields': ('custom_css_class', 'anchor_id'),
                'classes': ('collapse',),
            }),
        ]

        if section_type == 'announcement_bar':
            base.append(('Content', {
                'fields': ('config_text', 'config_link_url', ('config_bg_color', 'config_text_color'), 'config_dismissible', 'config_is_sticky'),
            }))
        elif section_type == 'hero_slider':
            base.append(('Hero Settings', {
                'fields': ('config_autoplay', 'config_autoplay_speed', 'config_transition_speed', 'config_transition_type'),
            }))
            base.append(('Secondary Call-to-Action', {
                'fields': ('config_secondary_cta_label', 'config_secondary_cta_url'),
                'description': 'Optional secondary button below the main slide CTA.',
            }))
        elif section_type == 'hero_banner':
            base.append(('Banner Content', {
                'fields': ('collection', 'config_headline', 'config_description', 'config_button_text', 'config_button_url'),
            }))
        elif section_type == 'trust_bar':
            pass
        elif section_type == 'shop_by_category':
            pass
        elif section_type in ('product_collection', 'womens_tops', 'jackets', 'trending_products', 'trending_now', 'best_sellers', 'featured_products', 'new_arrivals'):
            base.append(('Collection', {
                'fields': ('collection',),
                'description': 'Select a Product Collection to display products from.',
            }))
        elif section_type == 'promotional_banner':
            base.append(('Content', {
                'fields': ('config_headline', 'config_description', 'config_button_text', 'config_button_url', ('config_bg_color', 'config_text_color')),
            }))
        elif section_type in ('customer_reviews', 'instagram_feed'):
            base.append(('Settings', {
                'fields': ('config_max_items',),
            }))
        elif section_type == 'brands':
            base.append(('Brands', {
                'fields': ('config_brand_ids',),
                'description': 'Leave blank to show all active brands. Enter comma-separated brand IDs to filter.',
            }))
        elif section_type == 'countdown_banner':
            base.append(('Countdown', {
                'fields': ('config_countdown_end', 'config_countdown_label'),
            }))
        elif section_type == 'video_banner':
            base.append(('Video', {
                'fields': ('config_video_url', 'config_video_autoplay', 'config_video_muted', 'config_video_loop'),
            }))
            base.append(('Overlay Content', {
                'fields': ('config_headline', 'config_description', 'config_button_text', 'config_button_url'),
            }))
        elif section_type == 'custom_html':
            base.append(('Custom HTML', {
                'fields': ('config_custom_html',),
                'description': 'Enter raw HTML. Use with caution.',
            }))
        elif section_type == 'custom_template':
            base.append(('Custom Template', {
                'fields': ('config_custom_template_name',),
                'description': 'Enter template name (e.g. "sections/my_custom.html"). File must exist in templates/.',
            }))
        elif section_type == 'flash_sale':
            base.append(('Flash Sale', {
                'fields': ('collection', 'config_flash_sale_end', 'config_flash_sale_discount', 'config_flash_sale_original_price_label'),
            }))
        elif section_type == 'image_gallery':
            base.append(('Gallery', {
                'fields': ('config_gallery_images',),
                'description': 'Enter comma-separated image URLs.',
            }))
        elif section_type == 'faq_section':
            base.append(('FAQ', {
                'fields': ('config_faq_category_id',),
                'description': 'Enter the FAQ Category ID to display. Leave blank for all.',
            }))
        elif section_type == 'lookbook':
            pass
        elif section_type in ('recently_viewed', 'recommended_products'):
            base.append(('Settings', {
                'fields': ('config_max_products',),
            }))
        elif section_type == 'newsletter':
            pass
        elif section_type == 'footer':
            pass
        elif section_type == 'collections':
            pass

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

    def publish_status(self, obj):
        now = timezone.now()
        if not obj.is_active:
            return mark_safe('<span style="color:#999;">Inactive</span>')
        if obj.publish_at and obj.publish_at > now:
            return format_html('<span style="color:#f59e0b;">Scheduled: {}</span>', obj.publish_at.strftime('%b %d, %Y %H:%M'))
        if obj.unpublish_at and obj.unpublish_at <= now:
            return mark_safe('<span style="color:#ef4444;">Expired</span>')
        return mark_safe('<span style="color:#10b981;">Active</span>')
    publish_status.short_description = 'Status'
    publish_status.admin_order_field = 'publish_at'

    def section_preview_link(self, obj):
        return format_html(
            '<a class="button" href="{}" target="_blank" style="padding:2px 8px;font-size:11px;">Preview</a>',
            reverse('products:section_preview', args=[obj.pk])
        )
    section_preview_link.short_description = ''

    @admin.action(description='Duplicate selected sections')
    def duplicate_section(self, request, queryset):
        for original in queryset:
            old_id = original.pk
            original.pk = None
            original.title = f'{original.title} (Copy)' if original.title else '(Copy)'
            original.is_active = False
            original.publish_at = None
            original.unpublish_at = None
            original.save()
            new_id = original.pk
            # Duplicate related HeroSlide items
            if original.section_type == 'hero_slider':
                for slide in HeroSlide.objects.filter(section_id=old_id):
                    slide.pk = None
                    slide.section_id = new_id
                    slide.save()
            # Related items are harder to duplicate generically; inline items
            # for trust_bar, shop_by_category, footer will need manual re-creation
        self.message_user(request, f'{queryset.count()} section(s) duplicated.', messages.SUCCESS)

    @admin.action(description='Publish selected sections now')
    def publish_now(self, request, queryset):
        updated = queryset.update(is_active=True, publish_at=timezone.now())
        self.message_user(request, f'{updated} section(s) published.', messages.SUCCESS)

    @admin.action(description='Unpublish selected sections')
    def unpublish_now(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} section(s) unpublished.', messages.SUCCESS)

    @admin.action(description='Enable selected')
    def enable_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} section(s) enabled.', messages.SUCCESS)

    @admin.action(description='Disable selected')
    def disable_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} section(s) disabled.', messages.SUCCESS)


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


@admin.register(ThemeSettings)
class ThemeSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Branding', {
            'fields': ('store_name', 'tagline', 'logo', 'favicon'),
        }),
        ('Colors', {
            'fields': (
                ('primary_color', 'secondary_color', 'accent_color'),
                ('success_color', 'warning_color', 'danger_color', 'info_color'),
                ('background_color', 'surface_color', 'card_color'),
                ('border_color', 'text_color', 'muted_text_color'),
            ),
        }),
        ('Typography', {
            'fields': ('heading_font', 'body_font', 'font_size_scale', ('heading_font_weight', 'body_font_weight'), 'letter_spacing', 'line_height'),
            'classes': ('collapse',),
        }),
        ('Buttons', {
            'fields': (
                ('primary_btn_bg', 'primary_btn_text'),
                ('primary_btn_border_radius', 'primary_btn_shadow'),
                'primary_btn_hover_animation',
                ('secondary_btn_bg', 'secondary_btn_text'),
                ('secondary_btn_border_radius', 'secondary_btn_shadow'),
                'secondary_btn_hover_animation',
            ),
            'classes': ('collapse',),
        }),
        ('Navigation', {
            'fields': ('header_style', 'sticky_header', 'transparent_header', 'mega_menu_enabled', 'mobile_menu_style'),
            'classes': ('collapse',),
        }),
        ('Footer', {
            'fields': ('footer_columns', 'footer_copyright', 'social_links_enabled', 'payment_icons_enabled', 'footer_newsletter_enabled'),
            'classes': ('collapse',),
        }),
        ('Layout', {
            'fields': ('layout_style', 'container_width', 'sidebar_width', 'product_grid_layout', 'category_grid_layout', 'blog_layout', 'spacing_scale'),
            'classes': ('collapse',),
        }),
        ('Shop Settings', {
            'fields': ('products_per_page', 'default_sorting', 'wishlist_enabled', 'compare_enabled', 'quick_view_enabled', 'recently_viewed_enabled', 'infinite_scroll_enabled', 'pagination_style'),
            'classes': ('collapse',),
        }),
        ('Product Page', {
            'fields': ('image_zoom_enabled', 'gallery_layout', 'sticky_gallery_enabled', 'sticky_buy_box_enabled', 'size_chart_enabled', 'delivery_info_enabled', 'related_products_enabled', 'recently_viewed_products_enabled', 'trust_badges_enabled'),
            'classes': ('collapse',),
        }),
        ('Cart', {
            'fields': ('mini_cart_enabled', 'slide_cart_enabled', 'cart_notes_enabled', 'shipping_progress_bar_enabled', 'cross_sell_enabled', 'upsell_enabled'),
            'classes': ('collapse',),
        }),
        ('Animations', {
            'fields': ('page_transitions_enabled', 'button_animations_enabled', 'hover_effects_enabled', 'card_animations_enabled', 'scroll_animations_enabled', 'loading_animations_enabled'),
            'classes': ('collapse',),
        }),
        ('Custom CSS', {
            'fields': ('global_css', 'header_css', 'footer_css', 'homepage_css', 'product_css', 'checkout_css'),
            'classes': ('collapse',),
        }),
        ('Custom JavaScript', {
            'fields': ('custom_js',),
            'classes': ('collapse',),
        }),
        ('Preview Mode', {
            'fields': ('preview_mode',),
            'description': 'Enable preview mode to see real-time theme changes without publishing.',
        }),
    )

    def has_add_permission(self, request):
        return not ThemeSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = ThemeSettings.get_settings()
        return redirect(reverse('admin:products_themesettings_change', args=[obj.pk]))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = True
        extra_context['show_save'] = True
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        from django.urls import reverse
        context['import_export_buttons'] = True
        context['theme_export_url'] = reverse('products:theme_export')
        context['theme_import_url'] = reverse('products:theme_import')
        context['theme_reset_url'] = reverse('products:theme_reset')
        context['backup_create_url'] = reverse('products:backup_create')
        context['backup_list_url'] = reverse('products:backup_list')
        context['preview_url'] = reverse('products:admin_preview', args=['themesettings', 1]) if obj else reverse('products:admin_preview', args=['themesettings', 1])
        return super().render_change_form(request, context, add, change, form_url, obj)


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
        }),
        ('SEO', {
            'fields': ('seo_title', 'seo_description', 'seo_keywords', 'og_image', 'google_search_console_verification'),
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
        obj = WebsiteSettings.get_settings()
        return redirect(reverse('admin:products_websitesettings_change', args=[obj.pk]))


@admin.register(ContentPage)
class ContentPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'display_order', 'preview_link')
    list_filter = ('is_active',)
    list_editable = ('display_order',)
    search_fields = ('title', 'slug')
    ordering = ['display_order', 'title']
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'overline')}),
        ('Content', {'fields': ('summary', 'content')}),
        ('SEO', {'fields': ('meta_title', 'meta_description')}),
        ('Settings', {'fields': ('is_active', 'display_order')}),
    )
    save_on_top = True

    def preview_link(self, obj):
        return _admin_preview_link('contentpage', obj.pk)
    preview_link.short_description = ''


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
