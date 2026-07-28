from django.db import models
from django.core.cache import cache
from django.core.validators import MaxValueValidator
from django.urls import reverse
from cloudinary.models import CloudinaryField
from syafra.validators import validate_image_file
from products.utils.hooks import normalize_before_save

THEME_SETTINGS_CACHE_KEY = 'theme_settings_singleton'
THEME_SETTINGS_CACHE_TIMEOUT = 300
WEBSITE_SETTINGS_CACHE_KEY = 'website_settings_singleton'
WEBSITE_SETTINGS_CACHE_TIMEOUT = 300


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.image:
            validate_image_file(self.image)

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
    brand_ref = models.ForeignKey('cms.Brand', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/', blank=True)
    stock = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0, help_text='Number of times this product has been viewed')
    is_featured = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Normalization tracking — prevents re-processing already normalized images
    image_hash = models.CharField(max_length=64, blank=True, default='',
                                  help_text='SHA-256 hash of the original uploaded image')
    image_norm_version = models.PositiveIntegerField(default=0,
                                                     help_text='Normalization algorithm version used')

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name='products_price_gte_0',
            ),
            models.CheckConstraint(
                condition=models.Q(stock__gte=0),
                name='products_stock_gte_0',
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.image:
            validate_image_file(self.image)

    def save(self, *args, **kwargs):
        #normalize_before_save(self, 'image')
        super().save(*args, **kwargs)

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
                condition=models.Q(stock__gte=0),
                name='product_sizes_stock_gte_0',
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.size}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    # Normalization tracking
    image_hash = models.CharField(max_length=64, blank=True, default='',
                                  help_text='SHA-256 hash of the original uploaded image')
    image_norm_version = models.PositiveIntegerField(default=0,
                                                     help_text='Normalization algorithm version used')

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.product.name} - Image {self.id}"

    def clean(self):
        super().clean()
        if self.image:
            validate_image_file(self.image)

    def save(self, *args, **kwargs):
        #normalize_before_save(self, 'image')
        super().save(*args, **kwargs)


class InstagramFeedItem(models.Model):
    image = CloudinaryField('image', blank=True)
    link = models.URLField(default='https://www.instagram.com/syafra.thrift/')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Instagram Feed Item'
        verbose_name_plural = 'Instagram Feed Items'

    def __str__(self):
        return f"Instagram Feed Item {self.id}"


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    review = models.TextField()
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.name


# =============================================================================
# CMS Content Page
# =============================================================================


# =============================================================================
# CMS Content Page
# =============================================================================


class ContentPage(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    overline = models.CharField(max_length=200, blank=True, default='')
    summary = models.TextField(blank=True, default='')
    content = models.TextField(blank=True, default='')
    meta_title = models.CharField(max_length=200, blank=True, default='')
    meta_description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']

    def __str__(self):
        return self.title


# =============================================================================
# Contact Message
# =============================================================================


class ContactMessage(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, default='')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"


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
        ('hero_banner', 'Hero Banner'),
        ('shop_by_category', 'Shop By Category'),
        ('featured_products', 'Featured Products'),
        ('new_arrivals', 'New Arrivals'),
        ('trending_products', 'Trending Products'),
        ('best_sellers', 'Best Sellers'),
        ('collections', 'Collections'),
        ('brands', 'Brands'),
        ('womens_tops', "Women's Tops"),
        ('jackets', 'Jackets'),
        ('lookbook', 'Lookbook'),
        ('customer_reviews', 'Customer Reviews'),
        ('instagram_feed', 'Instagram Feed'),
        ('newsletter', 'Newsletter'),
        ('promotional_banner', 'Promotional Banner'),
        ('faq_section', 'FAQ'),
        ('custom_html', 'Custom HTML'),
        ('custom_template', 'Custom Template'),
        ('video_banner', 'Video Banner'),
        ('image_gallery', 'Image Gallery'),
        ('countdown_banner', 'Countdown Banner'),
        ('recently_viewed', 'Recently Viewed'),
        ('recommended_products', 'Recommended Products'),
        ('flash_sale', 'Flash Sale'),
        ('trust_bar', 'Trust Bar'),
        ('product_collection', 'Product Collection'),
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
    MARGIN_CHOICES = [
        ('m-0', 'None'),
        ('mt-4', 'Top Small'),
        ('mt-8', 'Top Medium'),
        ('mt-16', 'Top Large'),
        ('mb-4', 'Bottom Small'),
        ('mb-8', 'Bottom Medium'),
        ('mb-16', 'Bottom Large'),
        ('my-4', 'Both Small'),
        ('my-8', 'Both Medium'),
        ('my-16', 'Both Large'),
    ]
    ANIMATION_CHOICES = [
        ('', 'None'),
        ('fade-in', 'Fade In'),
        ('fade-up', 'Fade Up'),
        ('fade-down', 'Fade Down'),
        ('slide-left', 'Slide Left'),
        ('slide-right', 'Slide Right'),
        ('zoom-in', 'Zoom In'),
        ('zoom-out', 'Zoom Out'),
        ('flip', 'Flip'),
    ]
    BORDER_RADIUS_CHOICES = [
        ('rounded-none', 'None'),
        ('rounded-sm', 'Small'),
        ('rounded', 'Medium'),
        ('rounded-lg', 'Large'),
        ('rounded-xl', 'Extra Large'),
        ('rounded-full', 'Full'),
    ]

    section_type = models.CharField(max_length=50, choices=SECTION_TYPE_CHOICES)
    title = models.CharField(max_length=200, blank=True, default='')
    subtitle = models.CharField(max_length=300, blank=True, default='')
    overline = models.CharField(max_length=100, blank=True, default='', help_text='Small label above the title (e.g. "NEW ARRIVALS", "THE EDIT")')
    collection = models.ForeignKey(
        ProductCollection, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sections', help_text='Required for Product Collection sections.'
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    publish_at = models.DateTimeField(null=True, blank=True, db_index=True, help_text='Schedule publish date')
    unpublish_at = models.DateTimeField(null=True, blank=True, db_index=True, help_text='Schedule unpublish date')

    bg_color = models.CharField(max_length=7, blank=True, default='', help_text='Section background color (hex)')
    bg_image = models.ImageField(upload_to='sections/bg/', blank=True, help_text='Section background image')
    padding_top = models.CharField(max_length=20, blank=True, default='', choices=[('', 'Default')] + [(c, c) for c in ['py-8', 'py-12', 'py-16', 'py-20', 'py-24', 'py-32']])
    padding_bottom = models.CharField(max_length=20, blank=True, default='', choices=[('', 'Default')] + [(c, c) for c in ['py-8', 'py-12', 'py-16', 'py-20', 'py-24', 'py-32']])
    margin = models.CharField(max_length=20, blank=True, default='', choices=MARGIN_CHOICES, help_text='Section margin')
    border_radius = models.CharField(max_length=20, blank=True, default='', choices=BORDER_RADIUS_CHOICES, help_text='Section border radius')
    container_width = models.CharField(max_length=20, blank=True, default='', choices=[('', 'Default')] + [(c, c) for c in ['max-w-5xl', 'max-w-6xl', 'max-w-7xl', 'max-w-full']])
    full_width = models.BooleanField(default=False, help_text='Stretch to full viewport width')
    animation = models.CharField(max_length=50, blank=True, default='', choices=ANIMATION_CHOICES, help_text='Scroll animation')
    hide_on_mobile = models.BooleanField(default=False, help_text='Hide on mobile devices')
    hide_on_tablet = models.BooleanField(default=False, help_text='Hide on tablet devices')
    hide_on_desktop = models.BooleanField(default=False, help_text='Hide on desktop devices')
    custom_css_class = models.CharField(max_length=200, blank=True, default='', help_text='Custom CSS class(es) for the section')
    anchor_id = models.CharField(max_length=200, blank=True, default='', help_text='Section anchor ID for linking')

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
    image_position_x = models.PositiveSmallIntegerField(default=60, validators=[MaxValueValidator(100)], help_text='Image horizontal focal point: 0=left, 50=center, 100=right')
    image_position_y = models.PositiveSmallIntegerField(default=50, validators=[MaxValueValidator(100)], help_text='Image vertical focal point: 0=top, 50=center, 100=bottom')
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


class PromotionalBannerConfig(models.Model):
    section = models.OneToOneField(HomepageSection, on_delete=models.CASCADE, related_name='promo_config')
    desktop_image = models.ImageField(upload_to='homepage/promo/', blank=True)
    mobile_image = models.ImageField(upload_to='homepage/promo/', blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Promotional Banner Image'
        verbose_name_plural = 'Promotional Banner Images'

    def __str__(self):
        name = self.section.title or 'Promotional Banner'
        return f"Promo: {name}"


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
    HEADER_STYLE_CHOICES = [
        ('classic', 'Classic'),
        ('centered', 'Centered'),
        ('minimal', 'Minimal'),
        ('hamburger', 'Hamburger Only'),
    ]
    LAYOUT_CHOICES = [
        ('boxed', 'Boxed'),
        ('full_width', 'Full Width'),
    ]
    SORTING_CHOICES = [
        ('newest', 'Newest First'),
        ('oldest', 'Oldest First'),
        ('price_low', 'Price: Low to High'),
        ('price_high', 'Price: High to Low'),
        ('name_az', 'Name: A-Z'),
        ('name_za', 'Name: Z-A'),
    ]
    GRID_LAYOUT_CHOICES = [
        ('2cols', '2 Columns'),
        ('3cols', '3 Columns'),
        ('4cols', '4 Columns'),
        ('5cols', '5 Columns'),
    ]
    GALLERY_LAYOUT_CHOICES = [
        ('single', 'Single Image'),
        ('grid', 'Grid'),
        ('carousel', 'Carousel'),
        ('sticky', 'Sticky Gallery'),
    ]

    store_name = models.CharField(max_length=100, default='SYAFRA')
    tagline = models.CharField(max_length=200, blank=True, default='Fashion-Forward Vintage Streetwear')
    logo = models.ImageField(upload_to='theme/', blank=True)
    favicon = models.ImageField(upload_to='theme/', blank=True)
    enable_loader = models.BooleanField(default=False)
    loader_type = models.CharField(max_length=20, choices=LOADER_TYPE_CHOICES, default='spinner')
    loader_color = models.CharField(max_length=7, default='#000000')

    # Brand colors
    primary_color = models.CharField(max_length=7, default='#000000', help_text='Primary brand color')
    secondary_color = models.CharField(max_length=7, default='#FFFFFF', help_text='Secondary brand color')
    accent_color = models.CharField(max_length=7, default='#E8DCC4', help_text='Accent/highlight color')
    success_color = models.CharField(max_length=7, default='#10b981', help_text='Success/confirmation color')
    warning_color = models.CharField(max_length=7, default='#f59e0b', help_text='Warning color')
    danger_color = models.CharField(max_length=7, default='#ef4444', help_text='Danger/error color')
    info_color = models.CharField(max_length=7, default='#3b82f6', help_text='Info color')
    background_color = models.CharField(max_length=7, default='#ffffff', help_text='Page background')
    surface_color = models.CharField(max_length=7, default='#f9fafb', help_text='Surface background')
    card_color = models.CharField(max_length=7, default='#ffffff', help_text='Card background')
    border_color = models.CharField(max_length=7, default='#e5e7eb', help_text='Border color')
    text_color = models.CharField(max_length=7, default='#111827', help_text='Body text color')
    muted_text_color = models.CharField(max_length=7, default='#6b7280', help_text='Muted/secondary text')

    # Typography
    heading_font = models.CharField(max_length=100, default='Cormorant Garamond', help_text='Heading font family')
    body_font = models.CharField(max_length=100, default='Inter', help_text='Body font family')
    font_size_scale = models.DecimalField(max_digits=3, decimal_places=1, default=1.0, help_text='Font size scale multiplier (0.8 - 1.5)')
    heading_font_weight = models.CharField(max_length=20, default='600', help_text='Heading font weight (e.g. 400, 500, 600, 700)')
    body_font_weight = models.CharField(max_length=20, default='400', help_text='Body font weight')
    letter_spacing = models.CharField(max_length=20, default='normal', help_text='Global letter spacing (e.g. normal, 0.5px, 1px)')
    line_height = models.DecimalField(max_digits=3, decimal_places=1, default=1.6, help_text='Global line height')

    # Buttons
    primary_btn_bg = models.CharField(max_length=7, default='#000000', help_text='Primary button background')
    primary_btn_text = models.CharField(max_length=7, default='#ffffff', help_text='Primary button text color')
    primary_btn_border_radius = models.CharField(max_length=20, default='rounded', choices=[('rounded-none', 'None'), ('rounded-sm', 'Small'), ('rounded', 'Medium'), ('rounded-lg', 'Large'), ('rounded-full', 'Full')])
    primary_btn_shadow = models.BooleanField(default=False, help_text='Enable shadow on primary button')
    primary_btn_hover_animation = models.CharField(max_length=50, blank=True, default='', help_text='Hover animation effect')
    secondary_btn_bg = models.CharField(max_length=7, default='#ffffff', help_text='Secondary button background')
    secondary_btn_text = models.CharField(max_length=7, default='#000000', help_text='Secondary button text color')
    secondary_btn_border_radius = models.CharField(max_length=20, default='rounded', choices=[('rounded-none', 'None'), ('rounded-sm', 'Small'), ('rounded', 'Medium'), ('rounded-lg', 'Large'), ('rounded-full', 'Full')])
    secondary_btn_shadow = models.BooleanField(default=False)
    secondary_btn_hover_animation = models.CharField(max_length=50, blank=True, default='')

    # Navigation
    header_style = models.CharField(max_length=20, choices=HEADER_STYLE_CHOICES, default='classic')
    sticky_header = models.BooleanField(default=True)
    transparent_header = models.BooleanField(default=False)
    mega_menu_enabled = models.BooleanField(default=True)
    mobile_menu_style = models.CharField(max_length=50, blank=True, default='slide', help_text='Mobile menu animation style')

    # Footer
    footer_columns = models.PositiveIntegerField(default=4, help_text='Number of footer columns')
    footer_copyright = models.CharField(max_length=200, blank=True, default='', help_text='Copyright text')
    social_links_enabled = models.BooleanField(default=True, help_text='Show social media links in footer')
    payment_icons_enabled = models.BooleanField(default=True, help_text='Show payment method icons in footer')
    footer_newsletter_enabled = models.BooleanField(default=True, help_text='Show newsletter signup in footer')

    # Layout
    layout_style = models.CharField(max_length=20, choices=LAYOUT_CHOICES, default='full_width')
    container_width = models.CharField(max_length=20, default='max-w-7xl', help_text='Main container width class')
    sidebar_width = models.CharField(max_length=20, default='w-72', help_text='Sidebar width class')
    product_grid_layout = models.CharField(max_length=20, choices=GRID_LAYOUT_CHOICES, default='4cols')
    category_grid_layout = models.CharField(max_length=20, choices=GRID_LAYOUT_CHOICES, default='3cols')
    blog_layout = models.CharField(max_length=20, default='grid', choices=[('list', 'List'), ('grid', 'Grid')])
    spacing_scale = models.CharField(max_length=20, default='default', help_text='Global spacing scale')

    # Shop settings
    products_per_page = models.PositiveIntegerField(default=12)
    default_sorting = models.CharField(max_length=20, choices=SORTING_CHOICES, default='newest')
    wishlist_enabled = models.BooleanField(default=True)
    compare_enabled = models.BooleanField(default=False)
    quick_view_enabled = models.BooleanField(default=True)
    recently_viewed_enabled = models.BooleanField(default=True)
    infinite_scroll_enabled = models.BooleanField(default=False)
    pagination_style = models.CharField(max_length=20, default='numbers', choices=[('numbers', 'Page Numbers'), ('prev_next', 'Prev/Next'), ('load_more', 'Load More')])

    # Product page
    image_zoom_enabled = models.BooleanField(default=True)
    gallery_layout = models.CharField(max_length=20, choices=GALLERY_LAYOUT_CHOICES, default='carousel')
    sticky_gallery_enabled = models.BooleanField(default=False)
    sticky_buy_box_enabled = models.BooleanField(default=False)
    size_chart_enabled = models.BooleanField(default=True)
    delivery_info_enabled = models.BooleanField(default=True)
    related_products_enabled = models.BooleanField(default=True)
    recently_viewed_products_enabled = models.BooleanField(default=True)
    trust_badges_enabled = models.BooleanField(default=True)

    # Cart
    mini_cart_enabled = models.BooleanField(default=True)
    slide_cart_enabled = models.BooleanField(default=False)
    cart_notes_enabled = models.BooleanField(default=False)
    shipping_progress_bar_enabled = models.BooleanField(default=False)
    cross_sell_enabled = models.BooleanField(default=True)
    upsell_enabled = models.BooleanField(default=False)

    # Animations
    page_transitions_enabled = models.BooleanField(default=False)
    button_animations_enabled = models.BooleanField(default=True)
    hover_effects_enabled = models.BooleanField(default=True)
    card_animations_enabled = models.BooleanField(default=True)
    scroll_animations_enabled = models.BooleanField(default=True)
    loading_animations_enabled = models.BooleanField(default=True)

    # Custom CSS/JS
    global_css = models.TextField(blank=True, default='', help_text='Custom CSS applied globally')
    header_css = models.TextField(blank=True, default='', help_text='Custom CSS for header')
    footer_css = models.TextField(blank=True, default='', help_text='Custom CSS for footer')
    homepage_css = models.TextField(blank=True, default='', help_text='Custom CSS for homepage')
    product_css = models.TextField(blank=True, default='', help_text='Custom CSS for product pages')
    checkout_css = models.TextField(blank=True, default='', help_text='Custom CSS for checkout')
    custom_js = models.TextField(blank=True, default='', help_text='Custom JavaScript')

    # Preview mode
    preview_mode = models.BooleanField(default=False, help_text='Enable live preview mode')

    class Meta:
        verbose_name = 'Theme Settings'
        verbose_name_plural = 'Theme Settings'

    def __str__(self):
        return 'Theme Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        cache.delete(THEME_SETTINGS_CACHE_KEY)
        super().save(*args, **kwargs)

    def reset_to_defaults(self):
        defaults = {f.name: f.default for f in self._meta.fields if f.name != 'pk' and f.has_default()}
        for attr, value in defaults.items():
            setattr(self, attr, value)
        self.save()

    def delete(self, *args, **kwargs):
        self.reset_to_defaults()

    @classmethod
    def get_settings(cls):
        cached = cache.get(THEME_SETTINGS_CACHE_KEY)
        if cached is not None:
            return cached
        obj, _ = cls.objects.get_or_create(pk=1)
        cache.set(THEME_SETTINGS_CACHE_KEY, obj, THEME_SETTINGS_CACHE_TIMEOUT)
        return obj

    def export_to_dict(self):
        return {
            'store_name': self.store_name,
            'tagline': self.tagline,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'accent_color': self.accent_color,
            'success_color': self.success_color,
            'warning_color': self.warning_color,
            'danger_color': self.danger_color,
            'info_color': self.info_color,
            'background_color': self.background_color,
            'surface_color': self.surface_color,
            'card_color': self.card_color,
            'border_color': self.border_color,
            'text_color': self.text_color,
            'muted_text_color': self.muted_text_color,
            'heading_font': self.heading_font,
            'body_font': self.body_font,
            'font_size_scale': float(self.font_size_scale),
            'heading_font_weight': self.heading_font_weight,
            'body_font_weight': self.body_font_weight,
            'letter_spacing': self.letter_spacing,
            'line_height': float(self.line_height),
            'header_style': self.header_style,
            'sticky_header': self.sticky_header,
            'transparent_header': self.transparent_header,
            'mega_menu_enabled': self.mega_menu_enabled,
            'layout_style': self.layout_style,
            'container_width': self.container_width,
            'products_per_page': self.products_per_page,
            'default_sorting': self.default_sorting,
            'product_grid_layout': self.product_grid_layout,
        }

    def import_from_dict(self, data):
        allowed_fields = {f.name for f in self._meta.fields if f.name != 'pk'}
        for key, value in data.items():
            if key in allowed_fields:
                setattr(self, key, value)
        self.save()


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
    seo_description = models.CharField(max_length=160, default='Discover curated fashion, distinctive silhouettes, and modern essentials at SYAFRA. Explore new arrivals and collections designed for everyday expression.')
    seo_keywords = models.CharField(max_length=255, default='curated fashion, modern style, new arrivals, streetwear, designer pieces, fashion brand')
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
        cache.delete(WEBSITE_SETTINGS_CACHE_KEY)
        super().save(*args, **kwargs)

    def reset_to_defaults(self):
        defaults = {f.name: f.default for f in self._meta.fields if f.name != 'pk' and f.has_default()}
        for attr, value in defaults.items():
            setattr(self, attr, value)
        self.save()

    def delete(self, *args, **kwargs):
        self.reset_to_defaults()

    @classmethod
    def get_settings(cls):
        cached = cache.get(WEBSITE_SETTINGS_CACHE_KEY)
        if cached is not None:
            return cached
        obj, _ = cls.objects.get_or_create(pk=1)
        cache.set(WEBSITE_SETTINGS_CACHE_KEY, obj, WEBSITE_SETTINGS_CACHE_TIMEOUT)
        return obj
