from django import forms
from .models import HomepageSection


class HomepageSectionAdminForm(forms.ModelForm):
    # Announcement Bar fields
    config_text = forms.CharField(required=False, label='Announcement Text', widget=forms.TextInput(attrs={'class': 'vTextField'}))
    config_link_url = forms.URLField(required=False, label='Link URL', widget=forms.URLInput(attrs={'class': 'vTextField'}))
    config_bg_color = forms.CharField(required=False, label='Background Color', widget=forms.TextInput(attrs={'class': 'vTextField', 'type': 'color'}))
    config_text_color = forms.CharField(required=False, label='Text Color', widget=forms.TextInput(attrs={'class': 'vTextField', 'type': 'color'}))
    config_dismissible = forms.BooleanField(required=False, label='Dismissible', initial=True)
    config_is_sticky = forms.BooleanField(required=False, label='Sticky', initial=False)

    # Promotional Banner fields
    config_headline = forms.CharField(required=False, label='Headline', widget=forms.TextInput(attrs={'class': 'vTextField'}))
    config_description = forms.CharField(required=False, label='Description', widget=forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 3}))
    config_button_text = forms.CharField(required=False, label='Button Text', widget=forms.TextInput(attrs={'class': 'vTextField'}))
    config_button_url = forms.CharField(required=False, label='Button URL', widget=forms.TextInput(attrs={'class': 'vTextField'}))

    # Hero Secondary CTA fields
    config_secondary_cta_label = forms.CharField(required=False, label='Secondary CTA Label', widget=forms.TextInput(attrs={'class': 'vTextField'}))
    config_secondary_cta_url = forms.CharField(required=False, label='Secondary CTA URL', widget=forms.TextInput(attrs={'class': 'vTextField'}))
    config_autoplay = forms.BooleanField(required=False, label='Autoplay', initial=True)
    config_autoplay_speed = forms.IntegerField(required=False, label='Autoplay Speed (ms)', initial=5000, min_value=1000, max_value=30000, widget=forms.NumberInput(attrs={'class': 'vSmallIntegerField'}))
    config_transition_speed = forms.IntegerField(required=False, label='Transition Speed (ms)', initial=600, min_value=200, max_value=5000, widget=forms.NumberInput(attrs={'class': 'vSmallIntegerField'}))
    config_transition_type = forms.ChoiceField(required=False, label='Transition Type', choices=[
        ('', 'Default (fade)'),
        ('fade', 'Fade'),
        ('slide', 'Slide'),
        ('zoom', 'Zoom'),
    ], initial='')

    # Review/Feed sections
    config_max_items = forms.IntegerField(required=False, label='Max Items to Show', min_value=1, max_value=20, widget=forms.NumberInput(attrs={'class': 'vSmallIntegerField'}))

    # Countdown Banner
    config_countdown_end = forms.DateTimeField(required=False, label='Countdown End Date/Time', widget=forms.DateTimeInput(attrs={'class': 'vTextField', 'type': 'datetime-local'}))
    config_countdown_label = forms.CharField(required=False, label='Countdown Label', widget=forms.TextInput(attrs={'class': 'vTextField'}))

    # Video Banner
    config_video_url = forms.URLField(required=False, label='Video URL', widget=forms.URLInput(attrs={'class': 'vTextField'}))
    config_video_autoplay = forms.BooleanField(required=False, label='Video Autoplay', initial=True)
    config_video_muted = forms.BooleanField(required=False, label='Video Muted', initial=True)
    config_video_loop = forms.BooleanField(required=False, label='Video Loop', initial=True)

    # Custom HTML / Custom Template
    config_custom_html = forms.CharField(required=False, label='Custom HTML', widget=forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 10}))
    config_custom_template_name = forms.CharField(required=False, label='Template Name', widget=forms.TextInput(attrs={'class': 'vTextField'}))

    # Flash Sale
    config_flash_sale_end = forms.DateTimeField(required=False, label='Flash Sale End', widget=forms.DateTimeInput(attrs={'class': 'vTextField', 'type': 'datetime-local'}))
    config_flash_sale_discount = forms.IntegerField(required=False, label='Discount Percentage', min_value=1, max_value=99, widget=forms.NumberInput(attrs={'class': 'vSmallIntegerField'}))
    config_flash_sale_original_price_label = forms.CharField(required=False, label='Original Price Label', widget=forms.TextInput(attrs={'class': 'vTextField'}))

    # Recently Viewed / Recommended
    config_product_ids = forms.CharField(required=False, label='Product IDs (comma-separated)', widget=forms.TextInput(attrs={'class': 'vTextField'}), help_text='Override product selection')
    config_max_products = forms.IntegerField(required=False, label='Max Products', initial=8, min_value=1, max_value=50, widget=forms.NumberInput(attrs={'class': 'vSmallIntegerField'}))

    # Brands
    config_brand_ids = forms.CharField(required=False, label='Brand IDs (comma-separated)', widget=forms.TextInput(attrs={'class': 'vTextField'}))

    # Image Gallery
    config_gallery_images = forms.CharField(required=False, label='Image URLs (comma-separated)', widget=forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 3}))

    # FAQ
    config_faq_category_id = forms.IntegerField(required=False, label='FAQ Category ID', widget=forms.NumberInput(attrs={'class': 'vSmallIntegerField'}))

    class Meta:
        model = HomepageSection
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            config = self.instance.config or {}

            # Announcement Bar
            self.fields['config_text'].initial = config.get('text', '')
            self.fields['config_link_url'].initial = config.get('link_url', '')
            self.fields['config_bg_color'].initial = config.get('bg_color', '')
            self.fields['config_text_color'].initial = config.get('text_color', '')
            self.fields['config_dismissible'].initial = config.get('dismissible', True)
            self.fields['config_is_sticky'].initial = config.get('is_sticky', False)

            # Promotional Banner
            self.fields['config_headline'].initial = config.get('headline', '')
            self.fields['config_description'].initial = config.get('description', '')
            self.fields['config_button_text'].initial = config.get('button_text', '')
            self.fields['config_button_url'].initial = config.get('button_url', '')

            # Hero
            self.fields['config_secondary_cta_label'].initial = config.get('secondary_cta_label', '')
            self.fields['config_secondary_cta_url'].initial = config.get('secondary_cta_url', '')
            self.fields['config_autoplay'].initial = config.get('autoplay', True)
            self.fields['config_autoplay_speed'].initial = config.get('autoplay_speed', 5000)
            self.fields['config_transition_speed'].initial = config.get('transition_speed', 600)
            self.fields['config_transition_type'].initial = config.get('transition_type', '')

            # Reviews/Feed
            self.fields['config_max_items'].initial = config.get('max_items', 3)

            # Countdown
            self.fields['config_countdown_end'].initial = config.get('countdown_end', '')
            self.fields['config_countdown_label'].initial = config.get('countdown_label', '')

            # Video
            self.fields['config_video_url'].initial = config.get('video_url', '')
            self.fields['config_video_autoplay'].initial = config.get('video_autoplay', True)
            self.fields['config_video_muted'].initial = config.get('video_muted', True)
            self.fields['config_video_loop'].initial = config.get('video_loop', True)

            # Custom HTML/Template
            self.fields['config_custom_html'].initial = config.get('custom_html', '')
            self.fields['config_custom_template_name'].initial = config.get('custom_template_name', '')

            # Flash Sale
            self.fields['config_flash_sale_end'].initial = config.get('flash_sale_end', '')
            self.fields['config_flash_sale_discount'].initial = config.get('flash_sale_discount', 20)
            self.fields['config_flash_sale_original_price_label'].initial = config.get('flash_sale_original_price_label', '')

            # Recently Viewed / Recommended
            self.fields['config_product_ids'].initial = config.get('product_ids', '')
            self.fields['config_max_products'].initial = config.get('max_products', 8)

            # Brands
            self.fields['config_brand_ids'].initial = config.get('brand_ids', '')

            # Image Gallery
            self.fields['config_gallery_images'].initial = config.get('gallery_images', '')

            # FAQ
            self.fields['config_faq_category_id'].initial = config.get('faq_category_id', '')

    def _build_config(self, cleaned_data):
        section_type = cleaned_data.get('section_type', '')
        config = {}

        if section_type == 'announcement_bar':
            config = {
                'text': cleaned_data.get('config_text', ''),
                'link_url': cleaned_data.get('config_link_url', ''),
                'bg_color': cleaned_data.get('config_bg_color', ''),
                'text_color': cleaned_data.get('config_text_color', ''),
                'dismissible': cleaned_data.get('config_dismissible', True),
                'is_sticky': cleaned_data.get('config_is_sticky', False),
            }
        elif section_type == 'hero_slider':
            config = {
                'secondary_cta_label': cleaned_data.get('config_secondary_cta_label', ''),
                'secondary_cta_url': cleaned_data.get('config_secondary_cta_url', ''),
                'autoplay': cleaned_data.get('config_autoplay', True),
                'autoplay_speed': cleaned_data.get('config_autoplay_speed', 5000),
                'transition_speed': cleaned_data.get('config_transition_speed', 600),
                'transition_type': cleaned_data.get('config_transition_type', ''),
            }
        elif section_type == 'promotional_banner':
            config = {
                'headline': cleaned_data.get('config_headline', ''),
                'description': cleaned_data.get('config_description', ''),
                'button_text': cleaned_data.get('config_button_text', ''),
                'button_url': cleaned_data.get('config_button_url', ''),
                'bg_color': cleaned_data.get('config_bg_color', ''),
                'text_color': cleaned_data.get('config_text_color', ''),
            }
        elif section_type in ('customer_reviews', 'instagram_feed'):
            config = {
                'max_items': cleaned_data.get('config_max_items', 3),
            }
        elif section_type == 'countdown_banner':
            config = {
                'countdown_end': cleaned_data.get('config_countdown_end', ''),
                'countdown_label': cleaned_data.get('config_countdown_label', ''),
            }
        elif section_type == 'video_banner':
            config = {
                'video_url': cleaned_data.get('config_video_url', ''),
                'video_autoplay': cleaned_data.get('config_video_autoplay', True),
                'video_muted': cleaned_data.get('config_video_muted', True),
                'video_loop': cleaned_data.get('config_video_loop', True),
            }
        elif section_type == 'custom_html':
            config = {
                'custom_html': cleaned_data.get('config_custom_html', ''),
            }
        elif section_type == 'custom_template':
            config = {
                'custom_template_name': cleaned_data.get('config_custom_template_name', ''),
            }
        elif section_type == 'flash_sale':
            config = {
                'flash_sale_end': cleaned_data.get('config_flash_sale_end', ''),
                'flash_sale_discount': cleaned_data.get('config_flash_sale_discount', 20),
                'flash_sale_original_price_label': cleaned_data.get('config_flash_sale_original_price_label', ''),
            }
        elif section_type == 'brands':
            config = {
                'brand_ids': cleaned_data.get('config_brand_ids', ''),
            }
        elif section_type == 'image_gallery':
            config = {
                'gallery_images': cleaned_data.get('config_gallery_images', ''),
            }
        elif section_type == 'faq_section':
            config = {
                'faq_category_id': cleaned_data.get('config_faq_category_id', ''),
            }
        else:
            config = self.instance.config if self.instance.pk else {}

        return config

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.config = self._build_config(self.cleaned_data)
        if commit:
            instance.save()
        return instance


class ContactForm(forms.Form):
    name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'placeholder': 'Your Name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'your@email.com'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'placeholder': 'Optional'}))
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'placeholder': 'How can we help?'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Tell us more...', 'rows': 5}))
