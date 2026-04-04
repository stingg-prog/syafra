import re

from django import forms
from django.core.validators import RegexValidator


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ('razorpay', 'Pay Online (Card/UPI/Bank)'),
        ('upi', 'Pay via UPI'),
    ]
    
    customer_name = forms.CharField(
        max_length=200,
        strip=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 px-4 py-3 focus:outline-none focus:border-black transition-colors',
            'placeholder': 'Enter your full name',
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full border border-gray-300 px-4 py-3 focus:outline-none focus:border-black transition-colors',
            'placeholder': 'your@email.com',
        }),
    )
    phone_number = forms.CharField(
        max_length=24,
        strip=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 px-4 py-3 focus:outline-none focus:border-black transition-colors',
            'placeholder': '+91 98765 43210',
            'inputmode': 'tel',
        }),
    )
    pincode = forms.CharField(
        max_length=6,
        min_length=6,
        strip=True,
        validators=[RegexValidator(r'^\d{6}$', 'Enter a valid 6-digit pincode.')],
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 px-4 py-3 focus:outline-none focus:border-black transition-colors',
            'placeholder': '560001',
            'inputmode': 'numeric',
            'pattern': '\\d{6}',
            'title': 'Enter a 6-digit pincode',
        }),
    )
    shipping_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full border border-gray-300 px-4 py-3 focus:outline-none focus:border-black transition-colors resize-none',
            'rows': 4,
            'placeholder': 'Enter your full shipping address',
        }),
        strip=True,
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        required=False,
        widget=forms.RadioSelect(attrs={
            'class': 'payment-method-radio',
        }),
    )

    def clean_payment_method(self):
        payment_method = self.cleaned_data.get('payment_method')
        if not payment_method:
            return 'razorpay'  # Default
        return payment_method

    def clean_phone_number(self):
        raw_phone = self.cleaned_data.get('phone_number', '')
        digits = re.sub(r'\D', '', raw_phone)
        if len(digits) < 10:
            raise forms.ValidationError('Enter a valid phone number.')

        # Normalize common local formats to international form.
        if len(digits) == 10:
            digits = '91' + digits
        return f'+{digits}'
