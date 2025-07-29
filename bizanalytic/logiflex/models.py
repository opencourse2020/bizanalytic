from django.db import models
from ckeditor.fields import RichTextField
# Create your models here.


class NewsLetter_logiflex(models.Model):
    title = models.CharField(max_length=250, null=True, blank=True)
    body = RichTextField()
    date_created = models.DateTimeField(auto_now=True)
    dispatched = models.BooleanField(default=False)

    class Meta:
        verbose_name = "NewsLetter_logiflex"
        verbose_name_plural = "NewsLetters_logiflex"

    def __str__(self):
        return str(self.title)


class NewsLetter_logiflex_subscription(models.Model):
    email = models.CharField(max_length=150)
    company = models.CharField(max_length=150, null=True, blank=True)
    date_added = models.DateField(auto_now=True)
    removed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "NewsLetter_logiflex_subscription"
        verbose_name_plural = "NewsLetter_logiflex_subscriptions"

    def __str__(self):
        return str(self.email)

