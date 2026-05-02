from django.db import models
# from ckeditor.fields import RichTextField
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from bizanalytic.profiles.formatChecker import ContentTypeRestrictedFileField
import os
import json
import uuid
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
    client_number = models.CharField(max_length=50, null=True, blank=True)
    company = models.CharField(max_length=150, null=True, blank=True)
    email = models.CharField(max_length=150, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    contact_name = models.CharField(max_length=100, null=True, blank=True)
    address_line1 = models.CharField(max_length=100, null=True, blank=True)
    address_line2 = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=70, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    postal_code = models.CharField(max_length=15, null=True, blank=True)
    country = models.CharField(max_length=70, null=True, blank=True)
    date_added = models.DateField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    activated = models.BooleanField(default=False)  # Client activated means he is an existing client
    manually_created = models.BooleanField(default=False)

    class Meta:
        verbose_name = "LogiFlexClient"
        verbose_name_plural = "LogiFlexClients"
        permissions = (("manage_logiflexclient", "Manage LogiFlex Clients"),)

    def __str__(self):
        return f"{self.company} - {self.email}"


class PricingPlan(models.Model):
    PLAN_CHOICES = [
        ('onetime_lite', _("One-Time Lite Report")),
        ('onetime_advanced', _("One-Time Advanced Report")),
        ('starter', _("Starter Monthly Subscription")),
        ('pro', _("Pro Monthly Subscription")),
        ('quarterly', _("Pro Quarterly Plan")),
        ('daily', _("Daily Plan")),
        ('free_lite_report', _("Free One-Time Lite Report")),
        ('discounted_advanced_report', _("Discounted One-Time Advanced Report")),
    ]
    name = models.CharField(max_length=50, choices=PLAN_CHOICES)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    stripe_price_id = models.CharField(max_length=200, blank=True, null=True)  # Stripe price ID
    description = models.CharField(max_length=255, null=True, blank=True)
    buybuttonid = models.CharField(max_length=100, null=True, blank=True)
    publishablekey = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.get_name_display()} - ${self.price}"


class ServicePayment(models.Model):
    statustype = (
        ('0', _("None")),
        ('1', _("Active")),
        ('2', _("Paused")),
        ('3', _("Canceled")),
        ('4', _("Resumed")),
    )
    client = models.ForeignKey(LogiFlexClient, on_delete=models.SET_NULL, null=True)
    stripe_checkout_id = models.CharField(max_length=200, null=True, blank=True)
    subscription_id = models.CharField(max_length=200, null=True, blank=True)
    service_type = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    date_added = models.DateTimeField(auto_now=True)
    end_date = models.DateTimeField(blank=True, null=True)
    lite_credits = models.SmallIntegerField(default=0)
    advanced_credits = models.SmallIntegerField(default=0)
    advanced_reports_allowed = models.SmallIntegerField(default=0)
    advanced_reports_used = models.SmallIntegerField(default=0)
    reports_allowed = models.SmallIntegerField(default=0)
    reports_used = models.SmallIntegerField(default=0)
    reset_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=1, choices=statustype, default=0)
    date_canceled = models.DateTimeField(null=True, blank=True)
    lite_promotion_code = models.CharField(max_length=8, null=True, blank=True)
    lite_promotion_code_used = models.BooleanField(default=False)
    advanced_promotion_code = models.CharField(max_length=8, null=True, blank=True)
    advanced_promotion_code_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "ServicePayment"
        verbose_name_plural = "ServicePayments"
        permissions = (("manage_servicepayment", "Manage Service Payments"),)

    def set_quota(self):
        if self.service_type.name == 'starter':
            self.reports_allowed = 3
            self.advanced_reports_allowed = 0
            self.advanced_credits = 1
            self.reset_date = now() + timedelta(days=30)
        elif self.service_type.name == 'pro':
            self.reports_allowed = 10
            self.advanced_reports_allowed = 2
            self.reset_date = now() + timedelta(days=30)
        elif self.service_type.name == 'quarterly':
            self.reports_allowed = 25
            self.advanced_reports_allowed = 4
            self.reset_date = now() + timedelta(days=90)
        elif self.service_type.name == 'daily':
            self.reports_allowed = 1
            self.advanced_reports_allowed = 0
            self.advanced_credits = 1
            self.lite_credits = 1
            self.reset_date = now() + timedelta(days=7)
        # elif self.service_type.name == 'onetime_lite':
        #     self.reports_allowed = 1
        #     self.reset_date = now() + timedelta(days=30)
        self.save()


    def reset_quota_if_needed(self):
        """Reset quota when billing cycle renews."""
        # if self.reset_date and now() >= self.reset_date:
        self.reports_used = 0
        self.advanced_reports_used = 0
        # Reset based on plan
        if self.service_type.name == 'starter':
            self.reports_allowed = 3
            self.advanced_reports_allowed = 0
            self.reset_date = now() + timedelta(days=30)
        elif self.service_type.name == 'pro':
            self.reports_allowed = 10
            self.advanced_reports_allowed = 2
            self.reset_date = now() + timedelta(days=30)
        elif self.service_type.name == 'quarterly':
            self.reports_allowed = 25
            self.advanced_reports_allowed = 4
            self.reset_date = now() + timedelta(days=90)
        elif self.service_type.name == 'daily':
            self.reports_allowed = 1
            self.advanced_reports_allowed = 0
            self.advanced_credits += 1
            self.lite_credits += 1
            self.reset_date = now() + timedelta(days=7)
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

    def pause_subscription(self):
        self.is_active = False
        self.save()

    def cancel_subscription(self):
        self.reports_allowed = 0
        self.advanced_reports_allowed = 0
        self.reports_used = 0
        self.advanced_reports_used = 0
        self.is_active = False
        self.end_date = now()
        self.subscription_id = None
        self.save()

    def __str__(self):
        return f"{self.client.id} - {self.service_type.name}"


class PaymentsHistory(models.Model):
    client = models.ForeignKey(LogiFlexClient, on_delete=models.SET_NULL, null=True)
    stripe_checkout_id = models.CharField(max_length=200, null=True, blank=True)
    subscription_id = models.CharField(max_length=200, null=True, blank=True)
    service_type = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    quantity = models.SmallIntegerField(default=1)
    payment_date = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, null=True, blank=True)
    ipaddress = models.CharField(max_length=39, blank=True, null=True)
    user_device = models.CharField(max_length=100, blank=True, null=True)
    user_os = models.CharField(max_length=40, blank=True, null=True)
    user_browser = models.CharField(max_length=40, blank=True, null=True)
    user_language = models.CharField(max_length=40, blank=True, null=True)
    user_referee = models.CharField(max_length=100, blank=True, null=True)
    name_on_card = models.CharField(max_length=100, blank=True, null=True)
    address_line1 = models.CharField(max_length=100, null=True, blank=True)
    address_line2 = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=70, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    postal_code = models.CharField(max_length=15, null=True, blank=True)
    country = models.CharField(max_length=70, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    company = models.CharField(max_length=150, null=True, blank=True)
    download_code = models.CharField(max_length=8, null=True, blank=True)

    class Meta:
        verbose_name = "PaymentsHistory"
        verbose_name_plural = "PaymentsHistories"
        permissions = (("manage_paymenthistory", "Manage Payments History"),)

    def __str__(self):
        return f"{self.client.id} - {self.service_type.name}"


class LogPayments(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    session = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.date_created}"


class ChangeSubscriptionRequest(models.Model):
    requesttype = (
        ('1', _("Pause")),
        ('2', _("Cancel")),
        ('3', _("Resume")),
    )
    client = models.ForeignKey(LogiFlexClient, on_delete=models.SET_NULL, null=True)
    subscription = models.ForeignKey(ServicePayment, on_delete=models.SET_NULL, null=True)
    request = models.CharField(max_length=1, choices=requesttype, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "CancelSubscriptionRequest"
        verbose_name_plural = "CancelSubscriptionRequests"
        permissions = (("manage_cancelsubscription", "Manage Cancel Subscriptions"),)

    def __str__(self):
        return f"{self.subscription.client.company} - {self.subscription.service_type.name}"


class LogiflexReport(models.Model):
    reporttype = (
        ('Free', _("Free")),
        ('lite', _("Lite")),
        ('advanced', _("Advanced")),
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
    routefile_ext = models.CharField(max_length=10, null=True, blank=True)
    report = ContentTypeRestrictedFileField(upload_to=reportfiles_directory_path,
                                                   content_types=['application/pdf'],
                                                   max_upload_size=5242880, null=True, blank=True)
    report_text = models.JSONField(blank=True, null=True, default=dict)
    report_summary = models.TextField(null=True, blank=True)
    report_carrier = models.TextField(null=True, blank=True)
    report_driver = models.TextField(null=True, blank=True)
    report_route = models.TextField(null=True, blank=True)
    report_type = models.CharField(max_length=25, choices=reporttype, null=True, blank=True)
    download_code = models.CharField(max_length=8, null=True, blank=True)
    report_status = models.CharField(max_length=10, choices=status, default="processing")
    flags = models.TextField(max_length=1000, null=True, blank=True)
    date_created = models.DateTimeField(default=timezone.now)
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
        # if self.report_date and self.report_date > self.expected_delivery:
        #     if not self.report_status == "download":
        #         self.report_status = "late"
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


class FreightData(models.Model):
    report = models.ForeignKey(LogiflexReport, on_delete=models.SET_NULL, null=True)
    ShipmentID = models.CharField(max_length=50, null=True, blank=True)                 # Unique identifier for each shipment
    Date_ship = models.DateField(null=True, blank=True)                                 # Actual shipment date
    OriginCity = models.CharField(max_length=50, null=True, blank=True)                 # Origine City Name and State
    OriginZIP = models.CharField(max_length=12, null=True, blank=True)                  # 5-digit ZIP code of origin
    DestinationCity = models.CharField(max_length=50, null=True, blank=True)            # Destination City Name and State
    DestinationZIP = models.CharField(max_length=12, null=True, blank=True)             # 5-digit ZIP code of destination
    Distance_Miles = models.SmallIntegerField(null=True, blank=True)                    # Estimated shipment distance (miles)
    ShipmentMode = models.CharField(max_length=20, null=True, blank=True)               # Transport mode: LTL, FTL, Parcel, Air, Ocean
    CarrierName = models.CharField(max_length=100, null=True, blank=True)                # Freight carrier handling the load
    DriverName = models.CharField(max_length=60, null=True, blank=True)                 # Driver handling the load
    FreightCost_USD = models.FloatField(null=True, blank=True)                              # Total freight charge (before fuel & accessorials)
    FuelCost_USD = models.FloatField(null=True, blank=True)                                 # Fuel surcharge amount
    LoadWeight_lbs = models.FloatField(null=True, blank=True)                           # Total load weight (lbs)
    DeliveryStatus = models.CharField(max_length=15, null=True, blank=True)             # On-Time, Late, or In-Transit
    DeliveryTime_hrs = models.FloatField(null=True, blank=True)                         # Actual transit time (hours)
    LoadType = models.CharField(max_length=20, null=True, blank=True)                   # Equipment type: Dry Van, Reefer, Flatbed, etc.
    PalletCount = models.SmallIntegerField(null=True, blank=True)                       # Number of pallets shipped
    Volume_CuFt = models.FloatField(null=True, blank=True)                              # Volume of load in cubic feet
    RateType = models.CharField(max_length=20, null=True, blank=True)                   # Contract or Spot
    ContractRate = models.FloatField(null=True, blank=True)                             # Agreed rate (if available)
    AccessorialCharges = models.FloatField(null=True, blank=True)                       # Total accessorial charges
    Accessorials_Detail = models.CharField(max_length=100, null=True, blank=True)       # Accessorial types, separated by commas (Detention,Liftgate, ...)
    Surcharges = models.CharField(max_length=50, null=True, blank=True)                 # Extra charges not in accessorials (Hazmat Fee 25.00)
    InvoiceDate = models.DateField(null=True, blank=True)                               # Date invoice was issued
    PaymentDate = models.DateField(null=True, blank=True)                               # Date invoice was paid
    PlannedDelivery_hrs = models.FloatField(null=True, blank=True)                      # Expected transit time (hours)
    Currency = models.CharField(max_length=10, null=True, blank=True)                   # Currency used in invoice
    CommodityType = models.CharField(max_length=30, null=True, blank=True)              # Type of goods: Food, Retail, Industrial, etc.
    Date = models.DateField(null=True, blank=True)
    Diesel_Price = models.FloatField(null=True, blank=True)
    CostPerMile = models.FloatField(null=True, blank=True)
    CostPerHour = models.FloatField(null=True, blank=True)
    TotalCostPerMile = models.FloatField(null=True, blank=True)
    CostPerPound = models.FloatField(null=True, blank=True)
    CostPerPoundMile = models.FloatField(null=True, blank=True)
    Speed = models.FloatField(null=True, blank=True)
    OnTime = models.SmallIntegerField(null=True, blank=True)
    MilesPerHour = models.FloatField(null=True, blank=True)
    StopsPerDay = models.FloatField(null=True, blank=True)
    FuelEfficiency = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "FreightData"
        verbose_name_plural = "FreightDatas"
        permissions = (("manage_freightdata", "Manage FreightData"),)

        unique_together = ('report', 'ShipmentID')

    def __str__(self):
        return f"Report: {str(self.report.pk)}"


class FreightOpsReport(models.Model):
    """
    A single FreightOps Performance Report generated from a user's CSV upload.

    Architecture:
      - Raw upload stored as reference (not re-processed)
      - Structured analysis stored as JSON (deterministic, from OR models)
      - Narrative stored as JSON (from Sonnet, regenerable)
      - Fleet score stored as indexed fields (for querying/trending)
    """

    # =====================================================================
    # IDENTITY & OWNERSHIP
    # =====================================================================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    # user = models.ForeignKey(
    #     settings.AUTH_USER_MODEL,
    #     on_delete=models.CASCADE,
    #     related_name="freight_reports",
    #     db_index=True,
    # )
    client = models.ForeignKey(LogiFlexClient, on_delete=models.CASCADE, related_name="freight_reports",db_index=True,)
    payment = models.ForeignKey(ServicePayment, on_delete=models.SET_NULL, null=True)
    report_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Human-readable report ID, e.g., RPT-2025-000190",
    )
    download_code = models.CharField(max_length=8, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class ReportType(models.TextChoices):
        HEALTH_CHECK = "health_check", "Freight Health Check (free diagnostic)"
        FULL_REPORT = "full_report", "FreightOps Performance Report"

    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        default=ReportType.FULL_REPORT,
        db_index=True,
    )

    class ReportStatus(models.TextChoices):
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PROCESSING,
        db_index=True,
    )

    # =====================================================================
    # RAW DATA REFERENCE
    # =====================================================================
    uploaded_file = ContentTypeRestrictedFileField(upload_to=datafiles_directory_path,
                                               content_types=['application/vnd.ms-excel', 'text/csv',
                                                              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', ],
                                               max_upload_size=5242880, blank=True, null=True, max_length=255)
    file_name = models.CharField(max_length=255, blank=True)
    file_extension = models.CharField(max_length=10, null=True, blank=True)
    total_rows = models.PositiveIntegerField(default=0)
    total_columns = models.PositiveIntegerField(default=0)

    # Data completeness flags (from run_phase1_analysis.data_quality)
    has_fuel_cost = models.BooleanField(default=False)
    has_distance = models.BooleanField(default=False)
    has_weight = models.BooleanField(default=False)
    has_accessorials = models.BooleanField(default=False)
    has_delivery_time = models.BooleanField(default=False)

    # =====================================================================
    # DATA SUMMARY (for display without re-parsing)
    # =====================================================================
    total_shipments = models.PositiveIntegerField(default=0)
    total_carriers = models.PositiveSmallIntegerField(default=0)
    total_drivers = models.PositiveSmallIntegerField(default=0)
    total_lanes = models.PositiveSmallIntegerField(default=0)
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)

    # =====================================================================
    # FLEET HEALTH SCORE (from compute_fleet_score)
    # =====================================================================
    # Indexed fields for querying, sorting, trending across reports
    fleet_score = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
        help_text="Composite 0-100 score",
    )

    class FleetGrade(models.TextChoices):
        CRITICAL = "Critical", "Critical (0-39)"
        NEEDS_WORK = "Needs work", "Needs work (40-59)"
        COMPETENT = "Competent", "Competent (60-74)"
        STRONG = "Strong", "Strong (75-89)"
        ELITE = "Elite", "Elite (90-100)"
        INSUFFICIENT = "Insufficient data", "Insufficient data"

    fleet_grade = models.CharField(
        max_length=20,
        choices=FleetGrade.choices,
        default=FleetGrade.INSUFFICIENT,
        db_index=True,
    )

    # Individual dimension scores (0-100 each)
    score_ontime_delivery = models.FloatField(
        null=True, blank=True,
        help_text="On-time delivery dimension score (weight: 30%)",
    )
    score_cost_efficiency = models.FloatField(
        null=True, blank=True,
        help_text="Cost efficiency dimension score (weight: 25%)",
    )
    score_fuel_efficiency = models.FloatField(
        null=True, blank=True,
        help_text="Fuel efficiency dimension score (weight: 20%)",
    )
    score_route_utilization = models.FloatField(
        null=True, blank=True,
        help_text="Route utilization dimension score (weight: 15%)",
    )
    score_cost_predictability = models.FloatField(
        null=True, blank=True,
        help_text="Cost predictability dimension score (weight: 10%)",
    )

    # Biggest drag/strength (for quick display)
    biggest_drag_dimension = models.CharField(max_length=30, blank=True)
    biggest_drag_score = models.FloatField(null=True, blank=True)
    biggest_strength_dimension = models.CharField(max_length=30, blank=True)
    biggest_strength_score = models.FloatField(null=True, blank=True)

    # Improvement scenario
    improvement_current = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Current fleet score",
    )
    improvement_projected = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Projected score if biggest drag improved to 75",
    )
    improvement_delta = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Point gain from fixing biggest drag",
    )

    # Full score JSON (complete compute_fleet_score output)
    fleet_score_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full fleet score output including all dimensions and benchmarks",
    )

    # =====================================================================
    # COMPOSITE SAVINGS (the money headline)
    # =====================================================================
    total_annual_savings = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0,
        db_index=True,
        help_text="Total identified annual savings across all models",
    )
    savings_carrier_reallocation = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Annual savings from LP-optimized carrier allocation",
    )
    savings_lane_optimization = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Annual savings from lane profitability optimization",
    )
    savings_driver_coaching = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Annual savings from addressing SPC-flagged driver inefficiencies",
    )
    savings_invoice_anomalies = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Recoverable from IQR-detected cost anomalies",
    )

    # =====================================================================
    # OR MODEL OUTPUTS (structured analysis — deterministic)
    # =====================================================================
    # Each JSON field stores the full output dict from the corresponding model.
    # These feed both the LLM prompt and the report charts/tables.

    carrier_optimization_json = models.JSONField(
        default=dict, blank=True,
        help_text="Output from optimize_carrier_allocation() — LP model",
    )
    lane_profitability_json = models.JSONField(
        default=dict, blank=True,
        help_text="Output from analyze_lane_profitability() — ABC model",
    )
    driver_spc_json = models.JSONField(
        default=dict, blank=True,
        help_text="Output from analyze_driver_spc() — SPC control charts",
    )
    cost_anomalies_json = models.JSONField(
        default=dict, blank=True,
        help_text="Output from detect_cost_anomalies() — IQR outlier detection",
    )

    # =====================================================================
    # STATISTICS SUMMARIES (pre-computed for the LLM prompt)
    # =====================================================================
    carrier_stats_json = models.JSONField(
        default=dict, blank=True,
        help_text="Carrier statistics",
    )
    carrier_statdata_json = models.JSONField(
        default=dict, blank=True,
        help_text="Carrier statistics for charts",
    )
    driver_stats_json = models.JSONField(
        default=dict, blank=True,
        help_text="Driver statistics with per-driver KPIs",
    )
    driver_statdata_json = models.JSONField(
        default=dict, blank=True,
        help_text="Carrier statistics for charts",
    )
    route_stats_json = models.JSONField(
        default=dict, blank=True,
        help_text="Route statistics with network balance analysis",
    )
    route_statdata_json = models.JSONField(
        default=dict, blank=True,
        help_text="Carrier statistics for charts",
    )
    contingency_analysis = models.JSONField(
        default=dict, blank=True,
        help_text="Carrier contingency analysis",
    )
    intransit_analysis = models.JSONField(
        default=dict, blank=True,
        help_text="in transit analysis",
    )
    # =====================================================================
    # LLM-GENERATED NARRATIVE (from Sonnet — the prose sections)
    # =====================================================================
    # Stored as a single JSON blob matching the output format spec
    # in report_generator.py. Individual fields extracted for convenience.

    narrative_json = models.JSONField(
        default=dict, blank=True,
        help_text="Complete LLM-generated narrative — all sections",
    )

    # Denormalized fields for template rendering without JSON parsing
    # (optional — you can always read from narrative_json instead)
    money_headline_sub = models.TextField(
        blank=True,
        help_text="One-sentence summary below the savings number",
    )
    carriers_summary = models.TextField(
        blank=True,
        help_text="Executive carrier analysis (default view)",
    )
    carriers_detailed = models.TextField(
        blank=True,
        help_text="Expanded carrier analysis (toggle view)",
    )
    drivers_summary = models.TextField(
        blank=True,
        help_text="Executive driver analysis (default view)",
    )
    drivers_detailed = models.TextField(
        blank=True,
        help_text="Expanded driver analysis (toggle view)",
    )
    routes_summary = models.TextField(
        blank=True,
        help_text="Executive route analysis (default view)",
    )
    routes_detailed = models.TextField(
        blank=True,
        help_text="Expanded route analysis (toggle view)",
    )
    improvement_scenario_text = models.TextField(
        blank=True,
        help_text="'Improving X to Y would raise your score from A to B'",
    )

    # Top actions and week actions stored in narrative_json
    # (list fields — access via self.get_top_actions(), self.get_week_actions())

    # =====================================================================
    # WHITE-LABEL SETTINGS (Pro tier)
    # =====================================================================
    is_white_labeled = models.BooleanField(
        default=False,
        help_text="Whether this report uses the user's branding",
    )
    white_label_company = models.CharField(
        max_length=200, blank=True,
        help_text="Company name to display instead of LogiFlex",
    )
    white_label_logo_url = models.URLField(
        blank=True,
        help_text="Logo URL to replace the LogiFlex logo",
    )
    white_label_accent_color = models.CharField(
        max_length=7, blank=True,
        help_text="Hex color for report accents, e.g., #1a56db",
    )

    # =====================================================================
    # LLM COST TRACKING
    # =====================================================================
    llm_model = models.CharField(
        max_length=50, blank=True,
        default="claude-sonnet-4-6",
    )
    llm_input_tokens = models.PositiveIntegerField(default=0)
    llm_output_tokens = models.PositiveIntegerField(default=0)
    llm_cost_usd = models.DecimalField(
        max_digits=6, decimal_places=4, default=0,
        help_text="Estimated API cost for this report generation",
    )
    generation_time_seconds = models.FloatField(
        null=True, blank=True,
        help_text="Wall-clock time from upload to report completion",
    )

    # =====================================================================
    # HEALTH CHECK SPECIFIC (free diagnostic)
    # =====================================================================
    health_check_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Free Health Check expires 7 days after creation",
    )
    health_check_converted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this Health Check led to a paid subscription",
    )

    # =====================================================================
    # DATA FINGERPRINT (abuse prevention)
    # =====================================================================
    data_fingerprint = models.CharField(
        max_length=64, blank=True, db_index=True,
        help_text="SHA-256 hash of carrier+driver+lane+daterange for dedup",
    )

    # =====================================================================
    # LLM Raw Data
    # =====================================================================
    llm_result = models.TextField(blank=True, null=True)

    # =====================================================================
    # Prompts
    # =====================================================================
    user_prompt = models.TextField(blank=True, null=True)
    system_prompt = models.TextField(blank=True, null=True)

    # =====================================================================
    # META
    # =====================================================================

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client", "-created_at"]),
            models.Index(fields=["client", "report_type"]),
            models.Index(fields=["fleet_score"]),
            models.Index(fields=["data_fingerprint"]),
        ]
        verbose_name = "FreightOps Report"
        verbose_name_plural = "FreightOps Reports"

    def __str__(self):
        return f"{self.report_number} — {self.client} — Score: {self.fleet_score}"

    # =====================================================================
    # CLASS METHODS
    # =====================================================================

    @classmethod
    def generate_report_number(cls):
        """Generates the next sequential report number: RPT-YYYY-NNNNNN"""
        year = timezone.now().year
        prefix = f"RPT-{year}-"
        last = (
            cls.objects.filter(report_number__startswith=prefix)
            .order_by("-report_number")
            .values_list("report_number", flat=True)
            .first()
        )
        if last:
            last_num = int(last.split("-")[-1])
            return f"{prefix}{last_num + 1:06d}"
        return f"{prefix}000001"

    # =====================================================================
    # INSTANCE METHODS — Data access helpers
    # =====================================================================

    def get_top_actions(self):
        """Returns the top 3 ranked actions from the narrative."""
        return self.narrative_json.get("top_actions", [])

    def get_week_actions(self):
        """Returns the 'what to do this week' actions."""
        return self.narrative_json.get("week_actions", [])

    def get_carriers_insights(self):
        """Returns carrier insight bullets with type markers."""
        return self.narrative_json.get("carriers_insights", [])

    def get_routes_insights(self):
        """Returns route insight bullets with type markers."""
        return self.narrative_json.get("routes_insights", [])

    def get_financial_impact(self):
        """Returns the financial impact line items."""
        return self.narrative_json.get("financial_impact", [])

    def get_anomalies(self):
        """Returns flagged invoice anomalies for the table."""
        ca = self.cost_anomalies_json
        return ca.get("anomalies", []) if ca else []

    def get_driver_flags(self):
        """Returns SPC-flagged drivers with their violations."""
        spc = self.driver_spc_json
        if not spc:
            return []
        return [d for d in spc.get("drivers", []) if d.get("is_out_of_control")]

    def get_network_balance(self):
        """Returns network balance data for deadhead analysis."""
        rs = self.route_stats_json
        return rs.get("network_balance", []) if rs else []

    def get_score_dimensions(self):
        """Returns fleet score dimensions for the bar chart."""
        fs = self.fleet_score_json
        return fs.get("dimensions", []) if fs else []

    @property
    def is_health_check(self):
        return self.report_type == self.ReportType.HEALTH_CHECK

    @property
    def is_expired(self):
        """Check if a Health Check has expired (7-day window)."""
        if not self.is_health_check or not self.health_check_expires_at:
            return False
        return timezone.now() > self.health_check_expires_at

    @property
    def savings_breakdown(self):
        """Returns savings as a list of (label, amount) tuples, sorted by amount."""
        items = [
            ("Carrier reallocation", self.savings_carrier_reallocation),
            ("Lane optimization", self.savings_lane_optimization),
            ("Driver coaching", self.savings_driver_coaching),
            ("Invoice anomalies", self.savings_invoice_anomalies),
        ]
        return sorted(items, key=lambda x: x[1], reverse=True)

    # =====================================================================
    # POPULATE FROM ANALYSIS RESULTS
    # =====================================================================
    # self, result: dict
    def populate_from_results(self, narrative, analysis, score, carrier_stats, driver_stats, route_stats):
        """
        Populates all model fields from the output of generate_full_report().

        Call this after generating the report, before .save().

        Parameters
        ----------
        result : dict
            Output from report_generator.generate_full_report(df)
        """
        # analysis = result["analysis"]
        # score = result["fleet_score"]
        # if result["narrative"].get("raw_response"):
        #     narrative = result["narrative"].get("raw_response")
        # else:
        #     narrative = result["narrative"]
        # narrative = json.loads(narrative)
        # --- Fleet Score ---
        self.fleet_score = score.get("score", 0)
        self.fleet_grade = score.get("grade", "Insufficient data")
        self.fleet_score_json = score
        print("*********************************************************************************")
        print(narrative)
        print("*********************************************************************************")
        print(carrier_stats)
        print("*********************************************************************************")
        print(driver_stats)
        print("*********************************************************************************")
        print(route_stats)
        print("*********************************************************************************")
        print(score)
        print("*********************************************************************************")
        print(analysis)
        print("*********************************************************************************")
        # Map dimension scores
        dim_map = {
            "On-time delivery": "score_ontime_delivery",
            "Cost efficiency": "score_cost_efficiency",
            "Fuel efficiency": "score_fuel_efficiency",
            "Route utilization": "score_route_utilization",
            "Cost predictability": "score_cost_predictability",
        }
        for dim in score.get("dimensions", []):
            field = dim_map.get(dim["name"])
            if field:
                setattr(self, field, dim["score"])

        # Drag/strength
        drag = score.get("biggest_drag", {})
        self.biggest_drag_dimension = drag.get("dimension", "")
        self.biggest_drag_score = drag.get("dimension_score")

        strength = score.get("biggest_strength", {})
        self.biggest_strength_dimension = strength.get("dimension", "")
        self.biggest_strength_score = strength.get("dimension_score")

        imp = score.get("improvement_scenario", {})
        self.improvement_current = imp.get("current_fleet_score")
        self.improvement_projected = imp.get("projected_fleet_score")
        self.improvement_delta = imp.get("point_gain")

        # --- Composite Savings ---
        savings = analysis.get("composite_savings", {})
        self.total_annual_savings = savings.get("total_identified_annual_savings", 0)
        self.savings_carrier_reallocation = savings.get("carrier_reallocation_annual", 0)
        self.savings_lane_optimization = savings.get("lane_excess_cost_annual", 0)
        self.savings_driver_coaching = savings.get("driver_inefficiency_annual", 0)
        self.savings_invoice_anomalies = savings.get("cost_anomalies_annual", 0)

        # --- OR Model Outputs ---
        self.carrier_optimization_json = analysis.get("carrier_optimization", {})
        self.lane_profitability_json = analysis.get("lane_profitability", {})
        self.driver_spc_json = analysis.get("driver_spc", {})
        self.cost_anomalies_json = analysis.get("cost_anomalies", {})

        # --- Statistics ---
        self.carrier_stats_json = carrier_stats
        self.driver_stats_json = driver_stats
        self.route_stats_json = route_stats

        # --- Data Quality ---
        dq = analysis.get("data_quality", {})
        self.total_rows = dq.get("total_rows", 0)
        self.total_columns = dq.get("total_columns", 0)
        self.has_fuel_cost = dq.get("has_fuel_cost", False)
        self.has_distance = dq.get("has_distance", False)
        self.has_weight = dq.get("has_weight", False)
        self.has_accessorials = dq.get("has_accessorials", False)
        self.has_delivery_time = dq.get("has_delivery_time", False)

        # --- Narrative ---
        self.narrative_json = narrative
        self.money_headline_sub = narrative.get("money_headline_sub", "")
        self.carriers_summary = narrative.get("carriers_summary", "")
        self.carriers_detailed = narrative.get("carriers_detailed", "")
        self.drivers_summary = narrative.get("drivers_summary", "")
        self.drivers_detailed = narrative.get("drivers_detailed", "")
        self.routes_summary = narrative.get("routes_summary", "")
        self.routes_detailed = narrative.get("routes_detailed", "")
        self.improvement_scenario_text = narrative.get("improvement_scenario", "")

        # --- LLM Cost ---
        meta = narrative.get("_meta", {})
        self.llm_model = meta.get("model", "")
        self.llm_input_tokens = meta.get("input_tokens", 0)
        self.llm_output_tokens = meta.get("output_tokens", 0)
        self.llm_cost_usd = meta.get("estimated_cost_usd", 0)

        # LLM Result as raw data
        # self.llm_result = narrative

        # --- Summary counts ---
        cs = carrier_stats
        ds = driver_stats
        rs = route_stats
        self.total_carriers = cs.get("total_carriers", 0)
        self.total_drivers = ds.get("total_drivers", 0)
        self.total_lanes = rs.get("total_lanes", 0)

        # --- Health Check expiry ---
        if self.report_type == self.ReportType.HEALTH_CHECK:
            self.health_check_expires_at = timezone.now() + timezone.timedelta(days=7)

        self.status = self.ReportStatus.COMPLETED

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
