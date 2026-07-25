from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from . import models


def _preview_link(model_name, object_id, label='Preview'):
    url = reverse('products:admin_preview', args=[model_name, object_id])
    return format_html(
        '<a class="button" href="{}" target="_blank" style="padding:2px 8px;font-size:11px;background:#417690;color:#fff;border-radius:3px;text-decoration:none;white-space:nowrap;">{}</a>',
        url, label
    )


@admin.register(models.Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'display_order', 'website_link', 'preview_link']
    list_editable = ['is_active', 'display_order']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['display_order', 'name']

    def preview_link(self, obj):
        return _preview_link('brand', obj.pk)
    preview_link.short_description = ''

    def website_link(self, obj):
        if obj.website:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.website, obj.website)
        return '-'
    website_link.short_description = 'Website'


@admin.register(models.ProductLabel)
class ProductLabelAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_preview', 'is_active', 'preview_link']
    list_editable = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def preview_link(self, obj):
        return _preview_link('productlabel', obj.pk)
    preview_link.short_description = ''

    def color_preview(self, obj):
        return format_html(
            '<span style="display:inline-block;width:20px;height:20px;border-radius:4px;background:{};border:1px solid #ccc;"></span>'
            ' <span style="background:{};padding:2px 6px;border-radius:3px;">{}</span>',
            obj.color, obj.bg_color, obj.name
        )
    color_preview.short_description = 'Preview'


@admin.register(models.ProductBadge)
class ProductBadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon_display', 'is_active', 'preview_link']
    list_editable = ['is_active']
    search_fields = ['name']

    def preview_link(self, obj):
        return _preview_link('productbadge', obj.pk)
    preview_link.short_description = ''

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i> {}', obj.icon, obj.icon)
        return '-'
    icon_display.short_description = 'Icon'


class SizeChartEntryInline(admin.TabularInline):
    model = models.SizeChartEntry
    extra = 1
    ordering = ['display_order']


@admin.register(models.SizeChart)
class SizeChartAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'entry_count', 'preview_link']
    list_filter = ['is_active', 'category']
    search_fields = ['name', 'description']
    inlines = [SizeChartEntryInline]

    def preview_link(self, obj):
        return _preview_link('sizechart', obj.pk)
    preview_link.short_description = ''

    def entry_count(self, obj):
        return obj.entries.count()
    entry_count.short_description = 'Entries'


@admin.register(models.CareInstruction)
class CareInstructionAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon_display', 'is_active', 'display_order', 'preview_link']
    list_editable = ['is_active', 'display_order']
    ordering = ['display_order']

    def preview_link(self, obj):
        return _preview_link('careinstruction', obj.pk)
    preview_link.short_description = ''

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i>', obj.icon)
        return '-'
    icon_display.short_description = 'Icon'


@admin.register(models.SiteNavigation)
class SiteNavigationAdmin(admin.ModelAdmin):
    list_display = ['label', 'placement', 'parent', 'is_mega_menu', 'is_active', 'display_order']
    list_editable = ['is_active', 'display_order']
    list_filter = ['placement', 'is_active', 'is_mega_menu']
    search_fields = ['label', 'url']
    ordering = ['placement', 'display_order']
    raw_id_fields = ['parent']


class BlogPostTagInline(admin.TabularInline):
    model = models.BlogPost.tags.through
    extra = 1
    verbose_name = 'Tag'
    verbose_name_plural = 'Tags'


@admin.register(models.BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'post_count']
    list_editable = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def post_count(self, obj):
        return obj.posts.count()
    post_count.short_description = 'Posts'


@admin.register(models.BlogAuthor)
class BlogAuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'is_active', 'post_count']
    list_editable = ['is_active']
    search_fields = ['name', 'email', 'bio']
    prepopulated_fields = {'slug': ('name',)}

    def post_count(self, obj):
        return obj.posts.count()
    post_count.short_description = 'Posts'


@admin.register(models.BlogTag)
class BlogTagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(models.BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'is_published', 'published_at', 'is_featured', 'preview_link']
    list_editable = ['is_published', 'is_featured']
    list_filter = ['is_published', 'is_featured', 'category', 'tags']
    search_fields = ['title', 'excerpt', 'content']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    raw_id_fields = ['category', 'author']
    filter_horizontal = ['tags']
    fieldsets = [
        ('Content', {'fields': ['title', 'slug', 'category', 'author', 'tags', 'featured_image', 'excerpt', 'content']}),
        ('Publishing', {'fields': ['is_published', 'is_featured', 'published_at']}),
        ('SEO', {'fields': ['seo_title', 'seo_description', 'seo_keywords'], 'classes': ['collapse']}),
    ]

    def preview_link(self, obj):
        return _preview_link('blogpost', obj.pk)
    preview_link.short_description = ''


class FAQItemInline(admin.TabularInline):
    model = models.FAQItem
    extra = 1
    ordering = ['display_order']


@admin.register(models.FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'display_order', 'item_count', 'preview_link']
    list_editable = ['is_active', 'display_order']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [FAQItemInline]

    def preview_link(self, obj):
        return _preview_link('faqcategory', obj.pk)
    preview_link.short_description = ''

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'FAQs'


class LookbookItemInline(admin.TabularInline):
    model = models.LookbookItem
    extra = 1
    ordering = ['display_order']
    raw_id_fields = ['product']


@admin.register(models.Lookbook)
class LookbookAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_published', 'published_at', 'display_order', 'item_count', 'preview_link']
    list_editable = ['is_published', 'display_order']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LookbookItemInline]

    def preview_link(self, obj):
        return _preview_link('lookbook', obj.pk)
    preview_link.short_description = ''

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'


@admin.register(models.PromotionalPopup)
class PromotionalPopupAdmin(admin.ModelAdmin):
    list_display = ['title', 'popup_type', 'trigger', 'is_active', 'preview_link']
    list_editable = ['is_active']
    list_filter = ['popup_type', 'trigger', 'is_active']
    search_fields = ['title', 'description']
    fieldsets = [
        ('Content', {'fields': ['popup_type', 'title', 'description', 'image', 'button_text', 'button_url']}),
        ('Trigger Settings', {'fields': ['trigger', 'display_frequency', 'delay_seconds', 'scroll_percent']}),
        ('Visibility', {'fields': ['is_active', 'show_on_mobile', 'show_on_desktop', 'show_on_pages']}),
    ]

    def preview_link(self, obj):
        return _preview_link('promotionalpopup', obj.pk)
    preview_link.short_description = ''


@admin.register(models.AnnouncementBarConfig)
class AnnouncementBarConfigAdmin(admin.ModelAdmin):
    list_display = ['text', 'is_active', 'is_sticky', 'dismissible', 'preview_link']
    list_editable = ['is_active', 'is_sticky', 'dismissible']

    def preview_link(self, obj):
        return _preview_link('announcementbarconfig', obj.pk)
    preview_link.short_description = ''

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        if models.AnnouncementBarConfig.objects.exists():
            return False
        return True


@admin.register(models.PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'display_order', 'preview_link']
    list_editable = ['is_active', 'display_order']
    search_fields = ['title', 'subtitle', 'description']

    def preview_link(self, obj):
        return _preview_link('promobanner', obj.pk)
    preview_link.short_description = ''


@admin.register(models.SEOSettings)
class SEOSettingsAdmin(admin.ModelAdmin):
    list_display = ['page_type', 'meta_title', 'meta_description_short', 'preview_link']
    list_editable = ['meta_title']
    search_fields = ['page_type', 'meta_title', 'meta_description']

    def preview_link(self, obj):
        return _preview_link('seosettings', obj.pk)
    preview_link.short_description = ''

    def meta_description_short(self, obj):
        return (obj.meta_description[:100] + '...') if len(obj.meta_description) > 100 else obj.meta_description
    meta_description_short.short_description = 'Meta Description'


class CollectionProductInline(admin.TabularInline):
    model = models.CollectionProduct
    extra = 1
    ordering = ['display_order']
    raw_id_fields = ['product']


@admin.register(models.Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'display_order', 'product_count', 'preview_link']
    list_editable = ['is_active', 'display_order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    inlines = [CollectionProductInline]

    def preview_link(self, obj):
        return _preview_link('collection', obj.pk)
    preview_link.short_description = ''

    def product_count(self, obj):
        return obj.collection_products.count()
    product_count.short_description = 'Products'


@admin.register(models.LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'display_order', 'updated_at', 'preview_link']
    list_editable = ['is_active', 'display_order']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title', 'content']

    def preview_link(self, obj):
        return _preview_link('legalpage', obj.pk)
    preview_link.short_description = ''


@admin.register(models.TestimonialExtended)
class TestimonialExtendedAdmin(admin.ModelAdmin):
    list_display = ['testimonial', 'rating', 'is_featured', 'display_order']
    list_editable = ['rating', 'is_featured', 'display_order']
    list_filter = ['is_featured', 'rating']


@admin.register(models.ThemeBackup)
class ThemeBackupAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'created_by__username']
    readonly_fields = ['name', 'data', 'created_by', 'created_at']

    def has_add_permission(self, request):
        return False
