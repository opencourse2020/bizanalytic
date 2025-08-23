from django.db import models
# from ckeditor.fields import RichTextField
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from bizanalytic.profiles.formatChecker import ContentTypeRestrictedFileField
import os
from datetime import timedelta, datetime
from django.utils.timezone import now
from django.utils.text import slugify
# from django.db.models.signals import pre_save
from bizanalytic.profiles.models import User
# Create your models here.


def datafiles_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'data_files/route_files/company_id_{0}/report_{1}/{2}'.format(instance.client.id, instance.id, filename)


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
        ('onetime_lite', _("One-Time Lite Report")),
        ('onetime_advanced', _("One-Time Advanced Report")),
        ('starter', _("Starter Monthly Subscription")),
        ('pro', _("Pro Monthly Subscription")),
        ('quarterly', _("Pro Quarterly Plan")),
    ]
    name = models.CharField(max_length=50, choices=PLAN_CHOICES)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    stripe_price_id = models.CharField(max_length=200, blank=True, null=True)  # Stripe price ID

    def __str__(self):
        return f"{self.get_name_display()} - ${self.price}"


class ServicePayment(models.Model):
    client = models.ForeignKey(LogiFlexClient, on_delete=models.SET_NULL, null=True)
    stripe_checkout_id = models.CharField(max_length=200, null=True, blank=True)
    service_type = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    date_added = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    lite_credits = models.SmallIntegerField(default=0)
    advanced_credits = models.SmallIntegerField(default=0)
    advanced_reports_allowed = models.SmallIntegerField(default=0)
    advanced_reports_used = models.SmallIntegerField(default=0)
    reports_allowed = models.SmallIntegerField(default=0)
    reports_used = models.SmallIntegerField(default=0)
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
            if self.service_type.name == 'starter':
                self.reports_allowed = 3
                # self.advanced_reports_allowed = 1
                self.reset_date = now() + timedelta(days=30)
            elif self.service_type.name == 'pro':
                self.reports_allowed = 10
                self.advanced_reports_allowed = 2
                self.reset_date = now() + timedelta(days=30)
            elif self.service_type.name == 'quarterly':
                self.reports_allowed = 25
                self.advanced_reports_allowed = 4
                self.reset_date = now() + timedelta(days=90)
            # elif self.service_type.name == 'onetime_lite':
            #     self.reports_allowed = 1
            #     self.reset_date = now() + timedelta(days=30)
            self.save()

    def can_generate_report(self):
        """Check if user can generate a report."""
        self.reset_quota_if_needed()
        if self.reports_used >= self.reports_allowed:
            if self.lite_credits > 0:
                return True
            else:
                return False
        else:
            return True

    def mark_report_used(self):
        """Increment usage after generating a report."""
        if self.reports_used < self.reports_allowed:
            self.reports_used += 1
        elif self.lite_credits > 0:
            self.lite_credits -= 1
        self.save()

    def can_generate_advanced_report(self):
        """Check if user can generate a report."""
        self.reset_quota_if_needed()
        if self.advanced_reports_used >= self.advanced_reports_allowed:
            if self.advanced_credits > 0:
                return True
            else:
                return False
        else:
            return True

    def mark_advanced_report_used(self):
        """Increment usage after generating a report."""
        if self.advanced_reports_used < self.advanced_reports_allowed:
            self.advanced_reports_used += 1
        elif self.advanced_credits > 0:
            self.advanced_credits -= 1
        self.save()

    def __str__(self):
        return f"{self.client.id} - {self.service_type.name}"


class PaymentsHistory(models.Model):
    client = models.ForeignKey(LogiFlexClient, on_delete=models.SET_NULL, null=True)
    stripe_checkout_id = models.CharField(max_length=200, null=True, blank=True)
    service_type = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    quantity = models.SmallIntegerField(default=1)
    payment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "PaymentsHistory"
        verbose_name_plural = "PaymentsHistories"
        permissions = (("manage_paymenthistory", "Manage Payments History"),)

    def __str__(self):
        return f"{self.client.id} - {self.service_type.name}"


class LogiflexReport(models.Model):
    reporttype = (
        ('Free', _("Free")),
        ('Paid', _("Paid")),

    )
    status = (
        ('processing', _("Processing")),
        ('download', _("Download")),
        ('canceled', _("Canceled")),
        ('late', _("Late")),
    )
    report_id = models.CharField(max_length=50, null=True, blank=True)
    report_number = models.IntegerField(null=True, blank=True, default=0)
    client = models.ForeignKey(LogiFlexClient, on_delete=models.CASCADE)
    payment = models.ForeignKey(ServicePayment, on_delete=models.SET_NULL, null=True)
    routefile = ContentTypeRestrictedFileField(upload_to=datafiles_directory_path,
                                               content_types=['application/vnd.ms-excel', 'text/csv',
                                                              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', ],
                                               max_upload_size=5242880, blank=True, null=True)
    report = ContentTypeRestrictedFileField(upload_to=reportfiles_directory_path,
                                                   content_types=['application/pdf'],
                                                   max_upload_size=5242880, null=True, blank=True)
    report_text = models.JSONField(blank=True, null=True, default=dict)
    report_summary = models.TextField(null=True, blank=True)
    report_carrier = models.TextField(null=True, blank=True)
    report_driver = models.TextField(null=True, blank=True)
    report_route = models.TextField(null=True, blank=True)
    report_type = models.CharField(max_length=5, choices=reporttype, null=True, blank=True)
    download_code = models.CharField(max_length=8, null=True, blank=True)
    report_status = models.CharField(max_length=10, choices=status, default="processing")
    date_created = models.DateTimeField(auto_now_add=True)
    report_date = models.DateTimeField(null=True)
    expected_delivery = models.DateTimeField(null=True, blank=True)
    report_prompt = models.TextField(null=True, blank=True)
    report_approved = models.BooleanField(default=False)
    viewed = models.BooleanField(default=False)
    contingency_result = models.JSONField(default=list)
    highvariance = models.CharField(max_length=255, null=True, blank=True)
    lowvariance = models.CharField(max_length=255, null=True, blank=True)
    costreliability_action = models.JSONField(default=list)
    contingency_action = models.JSONField(default=list)
    predictable = models.JSONField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "LogiFlexReport"
        verbose_name_plural = "LogiFlexReports"
        permissions = (("manage_Logiflexreport", "Manage LogiFlex Reports"),)

    def save(self, *args, **kwargs):
        if self.report_date and self.report_date > self.expected_delivery:
            if not self.report_status == "download":
                self.report_status = "late"
        super().save(*args, **kwargs)

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
        ('distribute', _("Delivery & Distribution")),
        ('driver', _("Drivers & Trucking")),
        ('cost', _("Cost Optimization")),
        # ('ai_insight', _("AI-Powered Insights")),
        ('predict', _("Forecasting & Predictions")),
    )
    title = models.CharField(max_length=250, null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    body_bottom = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=20, choices=categorytype, null=True, blank=True)
    meta_title = models.CharField(max_length=250, null=True, blank=True)
    meta_description = models.CharField(max_length=250, null=True, blank=True)
    date_created = models.DateField(auto_now_add=True)
    cover_text = models.TextField(max_length=300, null=True, blank=True)
    relatedblog = models.CharField(max_length=24, null=True, blank=True)
    anchor_title = models.CharField(max_length=100, null=True, blank=True)
    picture = ContentTypeRestrictedFileField(upload_to=blogfiles_directory_path,
                                             content_types=['image/bmp', 'image/gif', 'image/jpeg', 'image/png', ],
                                             max_upload_size=52428800, blank=True, null=True)
    coverpicture = ContentTypeRestrictedFileField(upload_to=blogfiles_directory_path,
                                             content_types=['image/bmp', 'image/gif', 'image/jpeg', 'image/png', ],
                                             max_upload_size=52428800, blank=True, null=True)
    insidepicture = ContentTypeRestrictedFileField(upload_to=blogfiles_directory_path,
                                             content_types=['image/bmp', 'image/gif', 'image/jpeg', 'image/png', ],
                                             max_upload_size=52428800, blank=True, null=True)
    slug = models.SlugField(max_length=50, unique=True, null=True)

    class Meta:
        verbose_name = "Blog_Logiflex"
        verbose_name_plural = "Blogs_logiflex"
        permissions = (("manage_blog_logiflex", "Manage Logiflex Blogs"),)

    def picturefilename(self):
        return os.path.basename(self.picture.name)

    def save(self, *args, **kwargs):
        if not self.slug:  # Generate slug only if it's not already set
            self.slug = slugify(self.anchor_title)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.title)


class LogEntry(models.Model):
    report = models.ForeignKey(LogiflexReport, on_delete=models.CASCADE)
    date_added = models.DateField(auto_now_add=True)
    column_report = models.TextField(null=True, blank=True)
    date_report = models.TextField(null=True, blank=True)
    citi_report = models.TextField(null=True, blank=True)
    level = models.CharField(max_length=20, null=True, blank=True)
    flags = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "LogEntry"
        verbose_name_plural = "LogEntries"
        permissions = (("manage_logentry", "Manage LogEntries"),)

    def __str__(self):
        return f"[{self.report.id}] {self.level} ({self.date_added})"


class City(models.Model):
    cityname = models.CharField(max_length=100, null=True, blank=True)
    state_name = models.CharField(max_length=100, null=True, blank=True)
    state_code = models.CharField(max_length=6, null=True, blank=True)

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"
        permissions = (("manage_city", "Manage Cities"),)

    def __str__(self):
        return f"{str(self.cityname)}, {str(self.state_code)}"


class State(models.Model):
    state_name = models.CharField(max_length=100, null=True, blank=True)
    state_code = models.CharField(max_length=6, null=True, blank=True)

    class Meta:
        verbose_name = "State"
        verbose_name_plural = "States"
        permissions = (("manage_state", "Manage States"),)

    def __str__(self):
        return f"{str(self.state_name)}, {str(self.state_code)}"


class GasPriceState(models.Model):
    state_code = models.CharField(max_length=6, null=True, blank=True)
    premiumprice = models.DecimalField(max_digits=6, decimal_places=3)
    regularprice = models.DecimalField(max_digits=6, decimal_places=3)
    midgradeprice = models.DecimalField(max_digits=6, decimal_places=3)
    dieselprice = models.DecimalField(max_digits=6, decimal_places=3)

    class Meta:
        verbose_name = "GasPrice"
        verbose_name_plural = "GasPrices"
        permissions = (("manage_gasprice", "Manage GasPrices"),)

    def __str__(self):
        return f"{str(self.state_code)}, Prem: {str(self.premiumprice)}, Reg: {str(self.regularprice)}, Mid: {str(self.midgradeprice)}, Dies: {str(self.dieselprice)}"



# **************************************************************************************************
# ******     Models related to advanced Report     *************************************************
# **************************************************************************************************

#
# class ReportMetadata(models.Model):
#     report = models.ForeignKey(LogiflexReport, on_delete=models.SET_NULL, null=True)
#     title = models.CharField(max_length=255)
#     subtitle = models.CharField(max_length=255)
#     audience = models.CharField(max_length=255)
#     generated_date = models.DateField()
#
# class ExecutiveSummary(models.Model):
#     report_metadata = models.OneToOneField(ReportMetadata, on_delete=models.CASCADE, related_name='executive_summary')
#     primary_finding = models.TextField()
#     primary_recommendation = models.TextField()
#
# class Carrier(models.Model):
#     name = models.CharField(max_length=255)
#     cost_per_mile = models.DecimalField(max_digits=5, decimal_places=2)
#     on_time_rate = models.DecimalField(max_digits=5, decimal_places=1)
#     quadrant = models.CharField(max_length=50)
#
# class DiagnosticAnalysis(models.Model):
#     report_metadata = models.OneToOneField(ReportMetadata, on_delete=models.CASCADE, related_name='diagnostic_analysis')
#     carrier_matrix_description = models.TextField()
#     bottleneck_title = models.CharField(max_length=255)
#     bottleneck_description = models.TextField()
#
# class BottleneckFinding(models.Model):
#     diagnostic_analysis = models.ForeignKey(DiagnosticAnalysis, on_delete=models.CASCADE, related_name='findings')
#     title = models.CharField(max_length=255)
#     details = models.TextField()
#
# class ActionPlan(models.Model):
#     report_metadata = models.ForeignKey(ReportMetadata, on_delete=models.CASCADE, related_name='action_plans')
#     priority = models.IntegerField()
#     title = models.CharField(max_length=255)
#     description = models.TextField()
#     expected_outcome = models.TextField()
#     estimated_impact = models.TextField()
#     level_of_effort = models.CharField(max_length=50)
#
# class ScenarioModeling(models.Model):
#     report_metadata = models.OneToOneField(ReportMetadata, on_delete=models.CASCADE, related_name='scenario_modeling')
#     carrier_shift_title = models.CharField(max_length=255)
#     carrier_shift_description = models.TextField()
#     new_delay_rate = models.CharField(max_length=50)
#     new_total_cost = models.CharField(max_length=50)
#     quarterly_savings = models.CharField(max_length=50)
#     fuel_cost_title = models.CharField(max_length=255)
#     fuel_cost_description = models.TextField()
#     projected_cost_increase = models.CharField(max_length=50)
#
#
#
#
#
#








# def create_slug(instance, new_slug=None):
#     slug = slugify(instance.anchor_title)
#     slug = slug[:30]
#     qs = Blog_logiflex.objects.filter(slug__startswith=slug).order_by("-id")
#     exists = qs.exists()
#     if exists:
#         pki = qs.first().id + 1
#         slug = "%s_%s" %(slug, pki)
#     return slug
#
#
# def pre_save_blog_receiver(sender, instance, *args, **kwargs):
#     if not instance.slug:
#         instance.slug = create_slug(instance)
#
#
# pre_save.connect(pre_save_blog_receiver, sender=Blog_logiflex)
