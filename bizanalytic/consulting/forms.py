"""
Consulting Forms
================
Django forms for all consulting intake paths.
Handles validation, anti-bot checks, and disposable email blocking.

Place at: consulting/forms.py
"""

import time
from django import forms
from .models import ConsultingLead


# =====================================================================
# DISPOSABLE EMAIL DOMAINS
# =====================================================================
# Subset — for production use the full list from:
# https://github.com/disposable-email-domains/disposable-email-domains
DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "guerrillamail.com", "throwaway.email",
    "yopmail.com", "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "dispostable.com", "trashmail.com", "fakeinbox.com", "mailnesia.com",
    "maildrop.cc", "discard.email", "temp-mail.org", "getnada.com",
    "mohmal.com", "burnermail.io", "inboxkitten.com", "minutemail.com",
    "emailondeck.com", "crazymailing.com", "tempr.email", "bupmail.com",
    "mailcatch.com", "tempinbox.com", "harakirimail.com", "10minutemail.com",
    "guerrillamail.info", "guerrillamail.net", "guerrillamail.org",
}


def clean_disposable_email(email):
    """Raises ValidationError if email domain is disposable."""
    domain = email.split("@")[-1].lower()
    if domain in DISPOSABLE_DOMAINS:
        raise forms.ValidationError(
            "Please use a work email address. Temporary email services are not accepted."
        )
    return email


# =====================================================================
# ANTI-BOT MIXIN
# =====================================================================
class AntiBotMixin:
    """
    Mixin that adds honeypot, timestamp, and JS-check validation.
    Include hidden fields in your template:
      <input type="hidden" name="form_ts" value="{{ form_timestamp }}">
      <div style="position:absolute;left:-9999px;..."><input name="website"></div>
    """

    def clean_website(self):
        """Honeypot field — must be empty."""
        value = self.cleaned_data.get("website", "")
        if value:
            raise forms.ValidationError("Bot detected.")
        return value

    def clean_form_ts(self):
        """Timestamp check — form must have been open for at least 3 seconds."""
        ts = self.cleaned_data.get("form_ts", "0")
        try:
            elapsed = int(time.time()) - int(ts)
        except (ValueError, TypeError):
            elapsed = 0
        if elapsed < 3:
            raise forms.ValidationError("Submission too fast.")
        return ts


# =====================================================================
# SAMPLE DOWNLOAD FORM (shared by freight and e-commerce)
# =====================================================================
class SampleDownloadForm(AntiBotMixin, forms.Form):
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "cs-form-input",
            "placeholder": "Your name",
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "cs-form-input",
            "placeholder": "you@company.com",
        }),
    )
    company = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "cs-form-input",
            "placeholder": "Your company",
        }),
    )
    store_url = forms.URLField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "cs-form-input",
            "placeholder": "yourstore.com",
        }),
    )
    # Anti-bot fields
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    form_ts = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_email(self):
        return clean_disposable_email(self.cleaned_data["email"])


# =====================================================================
# FREIGHT DISCOVERY CALL FORM
# =====================================================================
class FreightDiscoveryCallForm(AntiBotMixin, forms.Form):
    SPEND_CHOICES = [
        ("", "Select range"),
        ("under_50k", "Under $50K/month"),
        ("50k_100k", "$50K - $100K/month"),
        ("100k_250k", "$100K - $250K/month"),
        ("250k_500k", "$250K - $500K/month"),
        ("over_500k", "Over $500K/month"),
        ("not_sure", "Not sure"),
    ]

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "cs-form-input"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "cs-form-input"}),
    )
    company = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "cs-form-input"}),
    )
    monthly_spend = forms.ChoiceField(
        choices=SPEND_CHOICES,
        widget=forms.Select(attrs={"class": "cs-form-input"}),
    )
    challenge = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "cs-form-input cs-form-textarea",
            "rows": 3,
            "placeholder": "e.g., rates keep climbing, no visibility into which carriers are cheapest...",
        }),
    )
    # Anti-bot
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    form_ts = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_email(self):
        return clean_disposable_email(self.cleaned_data["email"])


# =====================================================================
# FREIGHT MINI-AUDIT FORM
# =====================================================================
class FreightMiniAuditForm(AntiBotMixin, forms.Form):
    CARRIER_COUNT_CHOICES = [
        ("", "Select"),
        ("1-3", "1-3 carriers"),
        ("4-8", "4-8 carriers"),
        ("9-15", "9-15 carriers"),
        ("15+", "15+ carriers"),
    ]

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "cs-form-input"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "cs-form-input"}),
    )
    company = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "cs-form-input"}),
    )
    carrier_count = forms.ChoiceField(
        choices=CARRIER_COUNT_CHOICES,
        widget=forms.Select(attrs={"class": "cs-form-input"}),
    )
    freight_data = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            "class": "cs-form-input cs-form-file",
            "accept": ".csv,.xlsx,.xls",
        }),
    )
    # Anti-bot
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    form_ts = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_email(self):
        return clean_disposable_email(self.cleaned_data["email"])

    def clean_freight_data(self):
        f = self.cleaned_data["freight_data"]
        # Max 25MB
        if f.size > 25 * 1024 * 1024:
            raise forms.ValidationError("File too large. Maximum size is 25MB.")
        # Extension check
        ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        if ext not in ("csv", "xlsx", "xls"):
            raise forms.ValidationError("Only CSV and Excel files are accepted.")
        return f


# =====================================================================
# ECOMMERCE DISCOVERY CALL FORM
# =====================================================================
class EcommerceDiscoveryCallForm(AntiBotMixin, forms.Form):
    SPEND_CHOICES = [
        ("", "Select range"),
        ("under_5k", "Under $5K/month"),
        ("5k_15k", "$5K - $15K/month"),
        ("15k_40k", "$15K - $40K/month"),
        ("over_40k", "Over $40K/month"),
        ("not_sure", "Not sure"),
    ]

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "cs-form-input"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "cs-form-input"}),
    )
    store_url = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "cs-form-input",
            "placeholder": "yourstore.com",
        }),
    )
    monthly_spend = forms.ChoiceField(
        choices=SPEND_CHOICES,
        widget=forms.Select(attrs={"class": "cs-form-input"}),
    )
    challenge = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "cs-form-input cs-form-textarea",
            "rows": 3,
            "placeholder": "e.g., costs keep climbing, not sure if our rates are competitive...",
        }),
    )
    # Anti-bot
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    form_ts = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_email(self):
        return clean_disposable_email(self.cleaned_data["email"])


# =====================================================================
# ECOMMERCE SHIPPING SNAPSHOT FORM
# =====================================================================
class EcommerceSnapshotForm(AntiBotMixin, forms.Form):
    VOLUME_CHOICES = [
        ("", "Select range"),
        ("under_500", "Under 500 orders/month"),
        ("500_2000", "500 - 2,000 orders/month"),
        ("2000_5000", "2,000 - 5,000 orders/month"),
        ("5000_10000", "5,000 - 10,000 orders/month"),
        ("over_10000", "10,000+ orders/month"),
    ]

    PLATFORM_CHOICES = [
        ("", "Select"),
        ("shopify", "Shopify"),
        ("shipstation", "ShipStation"),
        ("shipbob", "ShipBob"),
        ("pirateship", "Pirate Ship"),
        ("easypost", "EasyPost"),
        ("carrier_portal", "Carrier portal directly"),
        ("other", "Other"),
    ]

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "cs-form-input"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "cs-form-input",
            "placeholder": "you@brand.com",
        }),
    )
    store_url = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "cs-form-input",
            "placeholder": "yourstore.com",
        }),
    )
    monthly_volume = forms.ChoiceField(
        choices=VOLUME_CHOICES,
        widget=forms.Select(attrs={"class": "cs-form-input"}),
    )
    carriers = forms.MultipleChoiceField(
        required=False,
        choices=[
            ("ups", "UPS"),
            ("fedex", "FedEx"),
            ("usps", "USPS"),
            ("dhl", "DHL"),
            ("regional", "Regional carrier"),
        ],
        widget=forms.CheckboxSelectMultiple(),
    )
    platform = forms.ChoiceField(
        required=False,
        choices=PLATFORM_CHOICES,
        widget=forms.Select(attrs={"class": "cs-form-input"}),
    )
    shipping_data = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            "class": "cs-form-input cs-form-file",
            "accept": ".csv,.xlsx,.xls",
        }),
    )
    # Anti-bot
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    form_ts = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_email(self):
        return clean_disposable_email(self.cleaned_data["email"])

    def clean_shipping_data(self):
        f = self.cleaned_data["shipping_data"]
        if f.size > 25 * 1024 * 1024:
            raise forms.ValidationError("File too large. Maximum size is 25MB.")
        ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        if ext not in ("csv", "xlsx", "xls"):
            raise forms.ValidationError("Only CSV and Excel files are accepted.")
        return f