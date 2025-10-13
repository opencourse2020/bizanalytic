from django import forms
from django.utils.translation import gettext_lazy as _
from . import models
# from ckeditor.widgets import CKEditorWidget

class NewsLetter_logiflexForm(forms.ModelForm):
    # body = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = models.NewsLetter_logiflex
        fields = ["title", "body"]
        labels = {
            "title": _("Title"),
            "body": _("Body")
        }


class NewsLetter_logiflex_subscriptionForm(forms.ModelForm):
    class Meta:
        model = models.NewsLetter_logiflex_subscription
        fields = ["email", "company", "area"]
        labels = {
            "email": _("Email"),
            "company": _("Company Name"),
            "area": _("Area")
        }


class Blog_logiflexForm(forms.ModelForm):
    # body = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = models.Blog_logiflex
        fields = ["title", "body", "body_bottom", "category", "picture", "meta_title", "meta_description",
                  "insidepicture", "cover_text", "relatedblog", "anchor_title"]
        labels = {
            "title": _("Title"),
            "anchor_title": _("Anchor Title"),
            "body": _("Body Top"),
            "body_bottom": _("Body Bottom"),
            "category": _("Category"),
            "cover_text": _("Cover Text"),
            "picture": _("Picture"),
            "insidepicture": _("Inside Picture"),
            # "coverpicture": _("Cover Picture"),
            "meta_title": _("Meta Title"),
            "meta_description": _("Meta Description"),
            "relatedblog": _("Related Blogs")
        }


class ServicePaymentForm(forms.ModelForm):
    class Meta:
        model = models.ServicePayment
        fields = ["client", "service_type", "lite_promotion_code", "lite_credits", ]
        labels = {
            "client": _("Client"),
            "service_type": _("Service Type"),
            "lite_promotion_code": _("Lite Promotion Code"),
            "lite_credits": _("Lite Credits"),

        }


class LogiFlexClientForm(forms.ModelForm):

    class Meta:
        model = models.LogiFlexClient
        fields = ["email", "manually_created", "activated", "company", "contact_name", "phone", "city", "state", "postal_code", "country"]
        labels = {
            "email": _("Client Email"),
            "manual_created": _("Manually Created"),
            "company": _("Company"),
            "contact_name": _("Contact Name"),
            "phone": _("Phone"),
            "city": _("City"),
            "state": _("State"),
            "postal_code": _("Postal Code"),
            "country": _("Country"),
        }