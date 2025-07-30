from django import forms
from django.utils.translation import gettext_lazy as _
from . import models


class NewsLetter_logiflexForm(forms.ModelForm):
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
        fields = ["email", "company"]
        labels = {
            "email": _("Email"),
            "company": _("Company Name")
        }