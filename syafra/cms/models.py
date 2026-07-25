from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.validators import MaxValueValidator, MinValueValidator


class Brand(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'

    def __str__(self):
        return self.name


class ProductLabel(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#ef4444', help_text='Label color (hex)')
    bg_color = models.CharField(max_length=7, default='#fef2f2', help_text='Background color (hex)')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Product Label'
        verbose_name_plural = 'Product Labels'

    def __str__(self):
        return self.name


class ProductBadge(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, help_text='Font Awesome icon class (e.g. fa-leaf)')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Product Badge'
        verbose_name_plural = 'Product Badges'

    def __str__(self):
        return self.name


class SizeChart(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey('products.Category', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='size-charts/', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Size Chart'
        verbose_name_plural = 'Size Charts'

    def __str__(self):
        return self.name


class SizeChartEntry(models.Model):
    size_chart = models.ForeignKey(SizeChart, on_delete=models.CASCADE, related_name='entries')
    label = models.CharField(max_length=50, help_text='e.g. XS, S, M, L, XL')
    measurements = models.JSONField(default=dict, blank=True, help_text='JSON of measurements e.g. {"Bust": "32", "Waist": "26"}')
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Size Chart Entry'
        verbose_name_plural = 'Size Chart Entries'

    def __str__(self):
        return f"{self.size_chart.name} - {self.label}"


class CareInstruction(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Font Awesome icon class')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Care Instruction'
        verbose_name_plural = 'Care Instructions'

    def __str__(self):
        return self.name


class SiteNavigation(models.Model):
    PLACEMENT_CHOICES = [
        ('header_center', 'Header - Center'),
        ('header_right', 'Header - Right'),
        ('header_mobile', 'Header - Mobile'),
        ('footer', 'Footer'),
    ]

    label = models.CharField(max_length=100)
    url = models.CharField(max_length=500, blank=True, help_text='Internal URL path or external URL')
    placement = models.CharField(max_length=50, choices=PLACEMENT_CHOICES, default='header_center')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_mega_menu = models.BooleanField(default=False, help_text='Enable mega menu dropdown')
    mega_menu_content = models.TextField(blank=True, help_text='HTML content for mega menu')
    icon = models.CharField(max_length=50, blank=True, help_text='Font Awesome icon class')
    is_external = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['placement', 'display_order']
        verbose_name = 'Navigation Item'
        verbose_name_plural = 'Navigation Items'

    def __str__(self):
        return f"[{self.get_placement_display()}] {self.label}"


class BlogCategory(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Blog Category'
        verbose_name_plural = 'Blog Categories'

    def __str__(self):
        return self.name


class BlogAuthor(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='blog/authors/', blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Blog Author'
        verbose_name_plural = 'Blog Authors'

    def __str__(self):
        return self.name


class BlogTag(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Blog Tag'
        verbose_name_plural = 'Blog Tags'

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    author = models.ForeignKey(BlogAuthor, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    tags = models.ManyToManyField(BlogTag, blank=True, related_name='posts')
    featured_image = models.ImageField(upload_to='blog/', blank=True)
    excerpt = models.TextField(blank=True, help_text='Short summary for listings')
    content = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    seo_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('cms:blog_detail', kwargs={'slug': self.slug})


class FAQCategory(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'FAQ Category'
        verbose_name_plural = 'FAQ Categories'

    def __str__(self):
        return self.name


class FAQItem(models.Model):
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='items')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__display_order', 'display_order']
        verbose_name = 'FAQ Item'
        verbose_name_plural = 'FAQ Items'

    def __str__(self):
        return self.question


class Lookbook(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='lookbook/', blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Lookbook'
        verbose_name_plural = 'Lookbooks'

    def __str__(self):
        return self.title


class LookbookItem(models.Model):
    lookbook = models.ForeignKey(Lookbook, on_delete=models.CASCADE, related_name='items')
    image = models.ImageField(upload_to='lookbook/items/', blank=True)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Lookbook Item'
        verbose_name_plural = 'Lookbook Items'

    def __str__(self):
        return f"{self.lookbook.title} - {self.title or 'Item ' + str(self.display_order)}"


class PromotionalPopup(models.Model):
    POPUP_TYPE_CHOICES = [
        ('newsletter', 'Newsletter Signup'),
        ('exit_intent', 'Exit Intent'),
        ('promotion', 'Promotional Offer'),
        ('announcement', 'Announcement'),
    ]

    POPUP_TRIGGER_CHOICES = [
        ('on_load', 'On Page Load'),
        ('on_scroll', 'On Scroll'),
        ('on_exit', 'On Exit Intent'),
        ('after_delay', 'After Delay (seconds)'),
        ('on_click', 'On Click'),
    ]

    DISPLAY_FREQ_CHOICES = [
        ('once_session', 'Once per session'),
        ('once_day', 'Once per day'),
        ('always', 'Every page load'),
    ]

    popup_type = models.CharField(max_length=50, choices=POPUP_TYPE_CHOICES, default='newsletter')
    trigger = models.CharField(max_length=50, choices=POPUP_TRIGGER_CHOICES, default='on_exit')
    display_frequency = models.CharField(max_length=50, choices=DISPLAY_FREQ_CHOICES, default='once_session')
    delay_seconds = models.PositiveIntegerField(default=5, help_text='Delay in seconds (for after_delay trigger)')
    scroll_percent = models.PositiveIntegerField(default=50, help_text='Scroll percentage (for on_scroll trigger)')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='popups/', blank=True)
    button_text = models.CharField(max_length=100, default='Subscribe')
    button_url = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=False)
    show_on_mobile = models.BooleanField(default=True)
    show_on_desktop = models.BooleanField(default=True)
    show_on_pages = models.CharField(max_length=500, blank=True, help_text='Comma-separated URL patterns or leave blank for all pages')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Promotional Popup'
        verbose_name_plural = 'Promotional Popups'

    def __str__(self):
        return f"{self.get_popup_type_display()}: {self.title}"


class AnnouncementBarConfig(models.Model):
    text = models.CharField(max_length=500, default='Free shipping on orders over ₹999!')
    link_url = models.URLField(blank=True)
    link_text = models.CharField(max_length=100, blank=True, default='Shop Now')
    bg_color = models.CharField(max_length=7, default='#000000')
    text_color = models.CharField(max_length=7, default='#FFFFFF')
    is_sticky = models.BooleanField(default=False)
    dismissible = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Announcement Bar'
        verbose_name_plural = 'Announcement Bar'

    def __str__(self):
        return 'Announcement Bar Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
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
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class PromoBanner(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    button_text = models.CharField(max_length=100, blank=True, default='Shop Now')
    button_url = models.CharField(max_length=500, blank=True)
    desktop_image = models.ImageField(upload_to='promo-banners/', blank=True)
    mobile_image = models.ImageField(upload_to='promo-banners/mobile/', blank=True)
    bg_color = models.CharField(max_length=7, blank=True, help_text='Background color (hex)')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Promo Banner'
        verbose_name_plural = 'Promo Banners'

    def __str__(self):
        return self.title


class SEOSettings(models.Model):
    PAGE_TYPE_CHOICES = [
        ('home', 'Homepage'),
        ('shop', 'Shop / Collection'),
        ('product', 'Product Page'),
        ('category', 'Category Page'),
        ('blog', 'Blog'),
        ('blog_post', 'Blog Post'),
        ('content', 'Content Page'),
        ('contact', 'Contact Page'),
        ('faq', 'FAQ Page'),
    ]

    page_type = models.CharField(max_length=50, choices=PAGE_TYPE_CHOICES, unique=True)
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    og_title = models.CharField(max_length=70, blank=True)
    og_description = models.CharField(max_length=160, blank=True)
    og_image = models.ImageField(upload_to='seo/', blank=True)
    twitter_title = models.CharField(max_length=70, blank=True)
    twitter_description = models.CharField(max_length=160, blank=True)
    canonical_url = models.URLField(blank=True)
    robots = models.CharField(max_length=100, blank=True, default='index, follow')
    extra_meta = models.TextField(blank=True, help_text='Additional meta tags (JSON or raw HTML)')

    class Meta:
        verbose_name = 'SEO Settings'
        verbose_name_plural = 'SEO Settings'

    def __str__(self):
        return f"SEO: {self.get_page_type_display()}"


class Collection(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='collections/', blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Collection'
        verbose_name_plural = 'Collections'

    def __str__(self):
        return self.name


class CollectionProduct(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='collection_products')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='collection_memberships')
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']
        unique_together = ('collection', 'product')
        verbose_name = 'Collection Product'
        verbose_name_plural = 'Collection Products'

    def __str__(self):
        return f"{self.collection.name} - {self.product.name}"


class LegalPage(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = 'Legal Page'
        verbose_name_plural = 'Legal Pages'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('cms:legal_page', kwargs={'slug': self.slug})


class TestimonialExtendedManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)


class TestimonialExtended(models.Model):
    testimonial = models.OneToOneField('products.Testimonial', on_delete=models.CASCADE, related_name='extended')
    rating = models.PositiveIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    photo = models.ImageField(upload_to='testimonials/', blank=True)
    video_url = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Testimonial Details'
        verbose_name_plural = 'Testimonial Details'

    def __str__(self):
        return f"Details: {self.testimonial.name}"


class ThemeBackup(models.Model):
    name = models.CharField(max_length=200)
    data = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Theme Backup'
        verbose_name_plural = 'Theme Backups'

    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
