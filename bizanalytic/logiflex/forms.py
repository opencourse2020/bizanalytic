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
        fields = ["title", "body", "category", "picture", "meta_title", "meta_description", "insidepicture", "coverpicture", "cover_text"]
        labels = {
            "title": _("Title"),
            "body": _("Body"),
            "category": _("Category"),
            "cover_text": _("Cover Text"),
            "picture": _("Picture"),
            "insidepicture": _("Inside Picture"),
            "coverpicture": _("Cover Picture"),
            "meta_title": _("Meta Title"),
            "meta_description": _("Meta Description")
        }