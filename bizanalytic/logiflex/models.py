from django.db import models
from ckeditor.fields import RichTextField
from django.utils.translation import gettext_lazy as _
# Create your models here.


class NewsLetter_logiflex(models.Model):
    title = models.CharField(max_length=250, null=True, blank=True)
    body = RichTextField()
    date_created = models.DateTimeField(auto_now=True)
    dispatched = models.BooleanField(default=False)

    class Meta:
        verbose_name = "NewsLetter_logiflex"
        verbose_name_plural = "NewsLetters_logiflex"
        permissions = (("manage_logiflex_newsletters", "Manage Logiflex NewsLetters"),)

    def __str__(self):
        return str(self.title)


class NewsLetter_logiflex_subscription(models.Model):
    areatype = (
        ('lo', _("LogiFlex")),
        ('ki', _("KPI-Insights")),
    )
    email = models.CharField(max_length=150)
    company = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=2, choices=areatype, null=True, blank=True)
    date_added = models.DateField(auto_now=True)
    removed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "NewsLetter_logiflex_subscription"
        verbose_name_plural = "NewsLetter_logiflex_subscriptions"
        permissions = (("manage_logiflex_newsletters_subscription", "Manage Logiflex NewsLetters Subscription"),)

    def __str__(self):
        return str(self.email)

