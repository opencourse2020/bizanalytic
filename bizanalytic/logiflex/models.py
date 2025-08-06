from django.db import models
# from ckeditor.fields import RichTextField
from django.utils.translation import gettext_lazy as _
from bizanalytic.profiles.formatChecker import ContentTypeRestrictedFileField
import os
from datetime import timedelta
from django.utils.timezone import now

from bizanalytic.profiles.models import User
# Create your models here.


def datafiles_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'data_files/route_files/company_id_{0}/{1}'.format(instance.client.id, filename)

def reportfiles_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'data_files/report_files/company_id_{0}/{1}'.format(instance.client.id, filename)

def blogfiles_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'data_files/blog_files/blog_id_{0}/{1}'.format(instance.id, filename)


class NewsLetter_logiflex(models.Model):
    title = models.CharField(max_length=250, null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
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
    date_added = models.DateField(auto_now_add=True)
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
    phone = models.CharField(max_length=20)
    contact_name = models.CharField(max_length=100, null=True, blank=True)
    date_added = models.DateField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LogiFlexClient"
        verbose_name_plural = "LogiFlexClients"
        permissions = (("manage_logiflexclient", "Manage LogiFlex Clients"),)

    def __str__(self):
        return str(self.company)


class PricingPlan(models.Model):
    PLAN_CHOICES = [
        ('short', _("Free Short Report")),
        ('onetime', _("One-Time Report")),
        ('monthly', _("Paid Monthly Subscription")),
        ('quarterly', _("Paid Quarterly Plan")),
    ]
    name = models.CharField(max_length=50, choices=PLAN_CHOICES)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    stripe_price_id = models.CharField(max_length=200, blank=True, null=True)  # Stripe price ID

    def __str__(self):
        return f"{self.get_name_display()} - ${self.price}"


class ServicePayment(models.Model):
    servicetype = (
        ('short', _("Free Short Report")),
        ('onetime', _("One-Time Report")),
        ('monthly', _("Paid Monthly Subscription")),
        ('quarterly', _("Paid Quarterly Plan")),
    )
    client = models.ForeignKey(LogiFlexClient, on_delete=models.SET_NULL, null=True)
    stripe_checkout_id = models.CharField(max_length=200, null=True, blank=True)
    service_type = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    date_added = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    # payment_success = models.BooleanField(default=False)
    # amount = models.DecimalField(max_digits=6, decimal_places=2)
    # refund_issued = models.BooleanField(default=False)
    # refund_amount = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    # date_refund = models.DateField(null=True, blank=True)

    # Report quota
    reports_allowed = models.IntegerField(default=0)
    reports_used = models.IntegerField(default=0)
    reset_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "ServicePayment"
        verbose_name_plural = "ServicePayments"
        permissions = (("manage_servicepayment", "Manage Service Payments"),)

    def reset_quota_if_needed(self):
        """Reset quota when billing cycle renews."""
        if self.reset_date and now() >= self.reset_date:
            self.reports_used = 0
            # Reset based on plan
            if self.service_type.name == 'monthly':
                self.reports_allowed = 2
                self.reset_date = now() + timedelta(days=30)
            elif self.service_type.name == 'quarterly':
                self.reports_allowed = 6
                self.reset_date = now() + timedelta(days=90)
            elif self.service_type.name == 'onetime':
                self.reports_allowed = 1
                self.reset_date = now() + timedelta(days=30)
            self.save()

    def can_generate_report(self):
        """Check if user can generate a report."""
        self.reset_quota_if_needed()
        return self.reports_used < self.reports_allowed

    def mark_report_used(self):
        """Increment usage after generating a report."""
        self.reports_used += 1
        self.save()

    def __str__(self):
        return f"{self.client.id} - {self.service_type.name}"


class LogiflexReport(models.Model):
    reporttype = (
        ('short', _("Free Short Report")),
        ('full', _("Paid Report")),

    )
    client = models.ForeignKey(LogiFlexClient, on_delete=models.CASCADE)
    payment = models.ForeignKey(ServicePayment, on_delete=models.SET_NULL, null=True)
    routefile = ContentTypeRestrictedFileField(upload_to=datafiles_directory_path,
                                               content_types=['application/vnd.ms-excel', 'text/csv',
                                                              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', ],
                                               max_upload_size=20971520, blank=True, null=True)
    report = models.FileField(upload_to=reportfiles_directory_path, null=True, blank=True)
    report_type = models.CharField(max_length=5, choices=reporttype, null=True, blank=True)
    download_code = models.CharField(max_length=8, null=True, blank=True)
    # report_created = models.BooleanField(default=False)
    date_created = models.DateField(auto_now_add=True)

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

    def __str__(self):
        return str(self.client.id)


class Blog_logiflex(models.Model):
    categorytype = (
        ('logi_freight', _("Logistics & Freight")),
        # ('optimize', _("Optimization")),
        ('warehouse', _("Warehousing")),
        ('distribute', _("Distribution")),
        ('driver', _("Drivers & Trucking")),
        ('cost', _("Cost Optimization")),
        # ('ai_insight', _("AI-Powered Insights")),
        ('predict', _("Forecasting & Predictions")),
    )
    title = models.CharField(max_length=250, null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=20, choices=categorytype, null=True, blank=True)
    meta_title = models.CharField(max_length=250, null=True, blank=True)
    meta_description = models.CharField(max_length=250, null=True, blank=True)
    date_created = models.DateField(auto_now_add=True)
    picture = ContentTypeRestrictedFileField(upload_to=blogfiles_directory_path,
                                             content_types=['image/bmp', 'image/gif', 'image/jpeg', 'image/png', ],
                                             max_upload_size=52428800, blank=True, null=True)

    class Meta:
        verbose_name = "Blog_Logiflex"
        verbose_name_plural = "Blogs_logiflex"
        permissions = (("manage_blog_logiflex", "Manage Logiflex Blogs"),)

    def picturefilename(self):
        return os.path.basename(self.picture.name)

    def __str__(self):
        return str(self.title)

