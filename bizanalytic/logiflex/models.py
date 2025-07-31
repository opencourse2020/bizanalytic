from django.db import models
from ckeditor.fields import RichTextField
from django.utils.translation import gettext_lazy as _
from bizanalytic.profiles.formatChecker import ContentTypeRestrictedFileField
import os

from bizanalytic.profiles.models import User
# Create your models here.


def datafiles_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'data_files/route_files/company_id_{0}/{1}'.format(instance.id, filename)

def reportfiles_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'data_files/report_files/company_id_{0}/{1}'.format(instance.id, filename)


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


class LogiFlexClient(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    company = models.CharField(max_length=150)
    email = models.CharField(max_length=150)
    contact_name = models.CharField(max_length=100, null=True, blank=True)
    date_added = models.DateField(auto_now=True)

    class Meta:
        verbose_name = "LogiFlexClient"
        verbose_name_plural = "LogiFlexClients"
        permissions = (("manage_logiflexclient", "Manage LogiFlex Clients"),)

    def __str__(self):
        return str(self.company)


class LogiflexReport(models.Model):
    client = models.ForeignKey(LogiFlexClient, on_delete=models.CASCADE)
    routefile = ContentTypeRestrictedFileField(upload_to=datafiles_directory_path,
                                               content_types=['application/vnd.ms-excel', 'text/csv',
                                                              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', ],
                                               max_upload_size=20971520, blank=True, null=True)
    report = models.FileField(upload_to=reportfiles_directory_path, null=True, blank=True)
    date_created = models.DateField(auto_now=True)

    class Meta:
        verbose_name = "LogiFlexReport"
        verbose_name_plural = "LogiFlexReports"
        permissions = (("manage_Logiflexreport", "Manage LogiFlex Reports"),)

    def routefilename(self):
        return os.path.basename(self.routefile.name)

    def reportilename(self):
        return os.path.basename(self.report.name)

    def __str__(self):
        return str(self.client.id)


class RequestedCall(models.Model):
    client = models.ForeignKey(LogiFlexClient, on_delete=models.CASCADE)
    date_requested = models.DateTimeField(auto_now=True)
    called = models.BooleanField(default=False)
    date_called = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "RequestedCall"
        verbose_name_plural = "RequestedCalls"
        permissions = (("manage_requestedcall", "Manage RequestedCall"),)
