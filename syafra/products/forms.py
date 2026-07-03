import json
from django import forms
from .models import HomepageSection


class HomepageSectionAdminForm(forms.ModelForm):
    # Announcement Bar fields
    config_text = forms.CharField(required=False, label='Announcement Text', widget=forms.TextInput(attrs={'class': 'vTextField'}))
    config_link_url = forms.URLField(required=False, label='Link URL', widget=forms.URLInput(attrs={'class': 'vTextField'}))
    config_bg_color = forms.CharField(required=False, label='Background Color', widget=forms.TextInput(attrs={'class': 'vTextField', 'type': 'color'}))
    config_text_color = forms.CharField(required=False, label='Text Color', widget=forms.TextInput(attrs={'class': 'vTextField', 'type': 'color'}))

    # Promotional Banner fields
    config_headline = forms.CharField(required=False, label='Headline', widget=forms.TextInput(attrs={'class': 'vTextField'}))
    config_description = forms.CharField(required=False, label='Description', widget=forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 3}))
    config_button_text = forms.CharField(required=False, label='Button Text', widget=forms.TextInput(attrs={'class': 'vTextField'}))
    config_button_url = forms.CharField(required=False, label='Button URL', widget=forms.TextInput(attrs={'class': 'vTextField'}))

    # Review/Feed sections
    config_max_items = forms.IntegerField(required=False, label='Max Items to Show', min_value=1, max_value=20, widget=forms.NumberInput(attrs={'class': 'vSmallIntegerField'}))

    # Device settings - Desktop
    device_desktop_bg_image = forms.ImageField(required=False, label='Background Image')
    device_desktop_bg_color = forms.CharField(required=False, label='Background Color', widget=forms.TextInput(attrs={'class': 'vTextField', 'type': 'color'}))
    device_desktop_padding_y = forms.ChoiceField(required=False, label='Vertical Padding', choices=[('', '---------')] + HomepageSection.PADDING_CHOICES)
    device_desktop_text_align = forms.ChoiceField(required=False, label='Text Alignment', choices=[('', '---------')] + HomepageSection.ALIGN_CHOICES)
    device_desktop_max_width = forms.ChoiceField(required=False, label='Max Width', choices=[('', '---------')] + HomepageSection.WIDTH_CHOICES)

    # Device settings - Tablet
    device_tablet_bg_image = forms.ImageField(required=False, label='Background Image')
    device_tablet_bg_color = forms.CharField(required=False, label='Background Color', widget=forms.TextInput(attrs={'class': 'vTextField', 'type': 'color'}))
    device_tablet_padding_y = forms.ChoiceField(required=False, label='Vertical Padding', choices=[('', '---------')] + HomepageSection.PADDING_CHOICES)
    device_tablet_text_align = forms.ChoiceField(required=False, label='Text Alignment', choices=[('', '---------')] + HomepageSection.ALIGN_CHOICES)
    device_tablet_max_width = forms.ChoiceField(required=False, label='Max Width', choices=[('', '---------')] + HomepageSection.WIDTH_CHOICES)

    # Device settings - Mobile
    device_mobile_bg_image = forms.ImageField(required=False, label='Background Image')
    device_mobile_bg_color = forms.CharField(required=False, label='Background Color', widget=forms.TextInput(attrs={'class': 'vTextField', 'type': 'color'}))
    device_mobile_padding_y = forms.ChoiceField(required=False, label='Vertical Padding', choices=[('', '---------')] + HomepageSection.PADDING_CHOICES)
    device_mobile_text_align = forms.ChoiceField(required=False, label='Text Alignment', choices=[('', '---------')] + HomepageSection.ALIGN_CHOICES)
    device_mobile_max_width = forms.ChoiceField(required=False, label='Max Width', choices=[('', '---------')] + HomepageSection.WIDTH_CHOICES)

    class Meta:
        model = HomepageSection
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            config = self.instance.config or {}
            ds = self.instance.device_settings or {}

            # Announcement Bar
            self.fields['config_text'].initial = config.get('text', '')
            self.fields['config_link_url'].initial = config.get('link_url', '')
            self.fields['config_bg_color'].initial = config.get('bg_color', '')
            self.fields['config_text_color'].initial = config.get('text_color', '')

            # Promotional Banner
            self.fields['config_headline'].initial = config.get('headline', '')
            self.fields['config_description'].initial = config.get('description', '')
            self.fields['config_button_text'].initial = config.get('button_text', '')
            self.fields['config_button_url'].initial = config.get('button_url', '')

            # Reviews/Feed
            self.fields['config_max_items'].initial = config.get('max_items', 3)

            # Device settings
            for device in ('desktop', 'tablet', 'mobile'):
                device_data = ds.get(device, {})
                self.fields[f'device_{device}_bg_color'].initial = device_data.get('bg_color', '')
                self.fields[f'device_{device}_padding_y'].initial = device_data.get('padding_y', '')
                self.fields[f'device_{device}_text_align'].initial = device_data.get('text_align', '')
                self.fields[f'device_{device}_max_width'].initial = device_data.get('max_width', '')

    def _build_config(self, cleaned_data):
        section_type = cleaned_data.get('section_type', '')
        config = {}

        if section_type == 'announcement_bar':
            config = {
                'text': cleaned_data.get('config_text', ''),
                'link_url': cleaned_data.get('config_link_url', ''),
                'bg_color': cleaned_data.get('config_bg_color', ''),
                'text_color': cleaned_data.get('config_text_color', ''),
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
        elif section_type == 'newsletter':
            config = self.instance.config if self.instance.pk else {}
        elif section_type == 'product_collection':
            config = self.instance.config if self.instance.pk else {}
        else:
            config = self.instance.config if self.instance.pk else {}

        return config

    def _build_device_settings(self, cleaned_data):
        ds = {}
        for device in ('desktop', 'tablet', 'mobile'):
            bg_image = cleaned_data.get(f'device_{device}_bg_image')
            ds[device] = {
                'bg_image': bg_image.name if bg_image else '',
                'bg_color': cleaned_data.get(f'device_{device}_bg_color', ''),
                'padding_y': cleaned_data.get(f'device_{device}_padding_y', ''),
                'text_align': cleaned_data.get(f'device_{device}_text_align', ''),
                'max_width': cleaned_data.get(f'device_{device}_max_width', ''),
            }
        return ds

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.config = self._build_config(self.cleaned_data)
        instance.device_settings = self._build_device_settings(self.cleaned_data)
        if commit:
            instance.save()
        return instance
