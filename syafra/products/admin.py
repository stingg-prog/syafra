from django.contrib import admin
from .models import Category, Product, ProductSize, ProductImage, InstagramPost, Testimonial


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
