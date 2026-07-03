from django.db import models
from django.urls import reverse
from cloudinary.models import CloudinaryField


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:category_detail', kwargs={'slug': self.slug})


class Product(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('used', 'Used'),
        ('refurbished', 'Refurbished'),
    ]

    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/', blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0),
                name='products_price_gte_0',
            ),
            models.CheckConstraint(
                check=models.Q(stock__gte=0),
                name='products_stock_gte_0',
            ),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:product_detail', kwargs={'pk': self.pk})

    def get_all_images(self):
        images = []
        if self.image:
            images.append(self.image.url)
        images.extend([img.image.url for img in self.images.all()])
        return images

    def get_available_sizes(self):
        return [s.size for s in self.sizes.filter(stock__gt=0).order_by('id')]

    @property
    def has_sizes(self):
        return self.sizes.exists()


class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes')
    size = models.CharField(max_length=10)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product', 'size')
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                check=models.Q(stock__gte=0),
                name='product_sizes_stock_gte_0',
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.size}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.product.name} - Image {self.id}"


class InstagramPost(models.Model):
    image = CloudinaryField('image', blank=True)
    link = models.URLField(default='https://www.instagram.com/syafra.thrift/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Instagram Post {self.id}"


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    review = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


# =============================================================================
# Homepage CMS Models
# =============================================================================

class ProductCollection(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True, default='')
    products = models.ManyToManyField('Product', blank=True, related_name='collections')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class HomepageSection(models.Model):
    SECTION_TYPE_CHOICES = [
        ('announcement_bar', 'Announcement Bar'),
        ('hero_slider', 'Hero Slider'),
        ('trust_bar', 'Trust Bar'),
        ('shop_by_category', 'Shop By Category'),
        ('product_collection', 'Product Collection'),
        ('promotional_banner', 'Promotional Banner'),
        ('customer_reviews', 'Customer Reviews'),
        ('instagram_feed', 'Instagram Feed'),
        ('newsletter', 'Newsletter'),
        ('footer', 'Footer'),
    ]

    PADDING_CHOICES = [
        ('py-8', 'Small'),
        ('py-12', 'Medium'),
        ('py-16', 'Large'),
        ('py-20', 'Extra Large'),
        ('py-24', '2XL'),
        ('py-32', '3XL'),
    ]
    ALIGN_CHOICES = [
        ('text-left', 'Left'),
        ('text-center', 'Center'),
        ('text-right', 'Right'),
    ]
    WIDTH_CHOICES = [
        ('max-w-full', 'Full Width'),
        ('max-w-5xl', 'Narrow'),
        ('max-w-6xl', 'Medium'),
        ('max-w-7xl', 'Wide'),
    ]

    section_type = models.CharField(max_length=50, choices=SECTION_TYPE_CHOICES, unique=True)
    title = models.CharField(max_length=200, blank=True, default='')
    subtitle = models.CharField(max_length=300, blank=True, default='')
    collection = models.ForeignKey(
        ProductCollection, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sections', help_text='Required for Product Collection sections.'
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    config = models.JSONField(default=dict, blank=True)
    device_settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Homepage Section'
        verbose_name_plural = 'Homepage Sections'

    def __str__(self):
        return f"{self.get_section_type_display()} (order={self.display_order})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if HomepageSection.objects.filter(section_type=self.section_type).exclude(pk=self.pk).exists():
            raise ValidationError(f'A section of type "{self.get_section_type_display()}" already exists.')

    def get_device_setting(self, device, key, default=''):
        return self.device_settings.get(device, {}).get(key, default)


class HeroSlide(models.Model):
    PADDING_CHOICES = HomepageSection.PADDING_CHOICES
    ALIGN_CHOICES = HomepageSection.ALIGN_CHOICES
    WIDTH_CHOICES = HomepageSection.WIDTH_CHOICES

    section = models.ForeignKey(HomepageSection, on_delete=models.CASCADE, related_name='hero_slides')
    title = models.CharField(max_length=200, blank=True, default='')
    subtitle = models.CharField(max_length=300, blank=True, default='')
    description = models.CharField(max_length=500, blank=True, default='')
    button_text = models.CharField(max_length=50, default='SHOP NOW')
    button_url = models.CharField(max_length=500, default='/shop/')
    desktop_image = models.ImageField(upload_to='homepage/hero/desktop/', blank=True)
    mobile_image = models.ImageField(upload_to='homepage/hero/mobile/', blank=True)
    overlay_opacity = models.PositiveIntegerField(default=60, help_text='Overlay darkness 0-100')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"Hero Slide: {self.title or 'Untitled'} ({self.display_order})"


class TrustBarItem(models.Model):
    section = models.ForeignKey(HomepageSection, on_delete=models.CASCADE, related_name='trust_items')
    icon_svg = models.TextField(help_text='SVG path data for icon', blank=True, default='')
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True, default='')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"Trust: {self.title}"


class ShopByCategoryItem(models.Model):
    section = models.ForeignKey(HomepageSection, on_delete=models.CASCADE, related_name='category_items')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    headline = models.CharField(max_length=100, blank=True, default='')
    label = models.CharField(max_length=50, default='EXPLORE')
    desktop_image = models.ImageField(upload_to='homepage/categories/desktop/', blank=True)
    mobile_image = models.ImageField(upload_to='homepage/categories/mobile/', blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        unique_together = ('section', 'category')

    def __str__(self):
        return f"Category: {self.category.name}"


class FooterLink(models.Model):
    section = models.ForeignKey(HomepageSection, on_delete=models.CASCADE, related_name='footer_links')
    column_heading = models.CharField(max_length=100, help_text='Group label (e.g. SHOP, HELP)')
    label = models.CharField(max_length=100)
    url = models.CharField(max_length=500)
    is_external = models.BooleanField(default=False, help_text='Opens in new tab')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"{self.column_heading}: {self.label}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    source = models.CharField(max_length=50, default='homepage')
    created_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


# =============================================================================
# Theme & Website Settings (Singleton Pattern)
# =============================================================================

class ThemeSettings(models.Model):
    LOADER_TYPE_CHOICES = [
        ('spinner', 'Spinner'),
        ('dots', 'Dots'),
        ('pulse', 'Pulse'),
        ('bar', 'Bar'),
    ]

    store_name = models.CharField(max_length=100, default='SYAFRA')
    tagline = models.CharField(max_length=200, blank=True, default='Fashion-Forward Vintage Streetwear')
    primary_color = models.CharField(max_length=7, default='#000000', help_text='Primary brand color')
    secondary_color = models.CharField(max_length=7, default='#FFFFFF', help_text='Secondary brand color')
    accent_color = models.CharField(max_length=7, default='#E8DCC4', help_text='Accent/highlight color')
    logo = models.ImageField(upload_to='theme/', blank=True)
    favicon = models.ImageField(upload_to='theme/', blank=True)
    enable_loader = models.BooleanField(default=False)
    loader_type = models.CharField(max_length=20, choices=LOADER_TYPE_CHOICES, default='spinner')
    loader_color = models.CharField(max_length=7, default='#000000')

    class Meta:
        verbose_name = 'Theme Settings'
        verbose_name_plural = 'Theme Settings'

    def __str__(self):
        return 'Theme Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class WebsiteSettings(models.Model):
    contact_email = models.EmailField(blank=True, default='')
    contact_phone = models.CharField(max_length=20, blank=True, default='')
    business_address = models.TextField(blank=True, default='')
    business_hours = models.CharField(max_length=200, default='Mon-Sat: 10AM - 8PM')
    whatsapp_number = models.CharField(max_length=20, default='919037626684')
    whatsapp_default_message = models.CharField(
        max_length=500, default='Hi, I am interested in your products. Please share more details.'
    )
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.CharField(
        max_length=500, default='We are currently undergoing maintenance. Please check back later.'
    )
    seo_title = models.CharField(max_length=70, default='SYAFRA - Fashion-Forward Vintage Streetwear')
    seo_description = models.CharField(max_length=160, default='Curated vintage jackets and streetwear. Authentic pieces, modern style.')
    seo_keywords = models.CharField(max_length=255, default='vintage jackets, streetwear, fashion, thrift')
    og_image = models.ImageField(upload_to='theme/', blank=True)
    google_search_console_verification = models.CharField(max_length=100, blank=True, default='')
    google_analytics_id = models.CharField(max_length=50, blank=True, default='')
    meta_pixel_id = models.CharField(max_length=50, blank=True, default='')
    instagram_url = models.URLField(blank=True, default='')
    facebook_url = models.URLField(blank=True, default='')
    twitter_url = models.URLField(blank=True, default='')
    tiktok_url = models.URLField(blank=True, default='')
    youtube_url = models.URLField(blank=True, default='')
    pinterest_url = models.URLField(blank=True, default='')
    threads_url = models.URLField(blank=True, default='')
    linkedin_url = models.URLField(blank=True, default='')
    copyright_text = models.CharField(max_length=200, default='2026 SYAFRA. All rights reserved.')

    class Meta:
        verbose_name = 'Website Settings'
        verbose_name_plural = 'Website Settings'

    def __str__(self):
        return 'Website Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
