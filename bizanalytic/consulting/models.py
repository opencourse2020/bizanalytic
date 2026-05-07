import secrets
from django.db import models
from django.utils import timezone


# class ConsultingLead(models.Model):
#     name = models.CharField(max_length=200)
#     email = models.EmailField()
#     company = models.CharField(max_length=200, blank=True)
#     lead_type = models.CharField(max_length=50)
#     service = models.CharField(max_length=50, default='freight')
#     extra_json = models.JSONField(default=dict, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     is_contacted = models.BooleanField(default=False)
#     is_verified = models.BooleanField(default=False)
#     verification_token = models.CharField(max_length=64, unique=True, db_index=True)
#     notes = models.TextField(blank=True)
#
#     class Meta:
#         verbose_name = "ConsultingLead"
#         verbose_name_plural = "ConsultingLeads"
#         permissions = (("manage_consultinglead", "Manage ConsultingLead"),)
#
#     def __str__(self):
#         return str(self.email)


class ConsultingLead(models.Model):
    """
    A single consulting lead from any service page.
    Tracks the full lifecycle: submission → verification → contact → conversion.
    """

    # =====================================================================
    # IDENTITY
    # =====================================================================
    class Service(models.TextChoices):
        FREIGHT = "freight", "Freight Spend Audit"
        ECOMMERCE = "ecommerce", "E-Commerce Shipping Audit"

    class LeadType(models.TextChoices):
        DISCOVERY_CALL = "discovery_call", "Discovery Call"
        MINI_AUDIT = "mini_audit", "Mini-Audit / Snapshot"
        SAMPLE_DOWNLOAD = "sample_download", "Sample Report Download"

    class LeadStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Awaiting email verification"
        VERIFIED = "verified", "Verified — ready to contact"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified — proposal sent"
        CONVERTED = "converted", "Converted to paid engagement"
        DISQUALIFIED = "disqualified", "Disqualified"
        STALE = "stale", "Stale — no response"

    service = models.CharField(
        max_length=20,
        choices=Service.choices,
        db_index=True,
    )
    lead_type = models.CharField(
        max_length=20,
        choices=LeadType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=LeadStatus.choices,
        default=LeadStatus.UNVERIFIED,
        db_index=True,
    )

    # =====================================================================
    # CONTACT INFO
    # =====================================================================
    name = models.CharField(max_length=200)
    email = models.EmailField(db_index=True)
    company = models.CharField(
        max_length=200, blank=True,
        help_text="Company name (freight) or store name (e-commerce)",
    )
    store_url = models.URLField(
        blank=True,
        help_text="E-commerce store URL (e-commerce leads only)",
    )

    # =====================================================================
    # QUALIFICATION DATA
    # =====================================================================
    # Freight-specific
    monthly_freight_spend = models.CharField(
        max_length=20, blank=True,
        help_text="Estimated monthly freight spend range",
    )
    carrier_count = models.CharField(
        max_length=10, blank=True,
        help_text="Number of carriers (freight leads)",
    )

    # E-commerce-specific
    monthly_order_volume = models.CharField(
        max_length=20, blank=True,
        help_text="Monthly order volume range",
    )
    monthly_shipping_spend = models.CharField(
        max_length=20, blank=True,
        help_text="Estimated monthly shipping spend range",
    )
    carriers_used = models.JSONField(
        default=list, blank=True,
        help_text="List of carriers: ['ups', 'fedex', 'usps', ...]",
    )
    shipping_platform = models.CharField(
        max_length=50, blank=True,
        help_text="Shopify, ShipStation, ShipBob, etc.",
    )

    # Shared
    challenge = models.TextField(
        blank=True,
        help_text="Prospect's biggest challenge (free text)",
    )
    extra_json = models.JSONField(
        default=dict, blank=True,
        help_text="Any additional data captured from the form",
    )

    # =====================================================================
    # FILE UPLOAD (mini-audit / snapshot)
    # =====================================================================
    uploaded_file = models.FileField(
        upload_to="consulting/uploads/%Y/%m/",
        blank=True,
        help_text="CSV/Excel uploaded for mini-audit or shipping snapshot",
    )
    uploaded_file_name = models.CharField(max_length=255, blank=True)
    uploaded_file_size = models.PositiveIntegerField(
        default=0,
        help_text="File size in bytes",
    )

    # =====================================================================
    # VERIFICATION & ANTI-BOT
    # =====================================================================
    verification_token = models.CharField(
        max_length=64, unique=True, db_index=True,
        default=secrets.token_urlsafe,
    )
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Anti-bot tracking
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    form_load_timestamp = models.PositiveIntegerField(
        default=0,
        help_text="Unix timestamp when the form page was loaded",
    )
    submission_elapsed_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Seconds between form load and submission",
    )

    # =====================================================================
    # LIFECYCLE
    # =====================================================================
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    contacted_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(
        blank=True,
        help_text="Internal notes on this lead",
    )

    # =====================================================================
    # META
    # =====================================================================
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["service", "status"]),
            models.Index(fields=["email", "service"]),
            models.Index(fields=["is_verified", "-created_at"]),
        ]
        verbose_name = "Consulting Lead"
        verbose_name_plural = "Consulting Leads"

    def __str__(self):
        return f"{self.name} — {self.get_service_display()} — {self.get_status_display()}"

    @property
    def is_expired(self):
        """Verification token expires after 7 days."""
        if self.is_verified:
            return False
        return timezone.now() - self.created_at > timezone.timedelta(days=7)

    def verify(self):
        """Mark this lead as verified."""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.status = self.LeadStatus.VERIFIED
        self.save(update_fields=["is_verified", "verified_at", "status"])

    def mark_contacted(self):
        self.status = self.LeadStatus.CONTACTED
        self.contacted_at = timezone.now()
        self.save(update_fields=["status", "contacted_at"])

    def mark_converted(self):
        self.status = self.LeadStatus.CONVERTED
        self.converted_at = timezone.now()
        self.save(update_fields=["status", "converted_at"])

    def mark_disqualified(self, reason=""):
        self.status = self.LeadStatus.DISQUALIFIED
        if reason:
            self.notes = f"{self.notes}\nDisqualified: {reason}".strip()
        self.save(update_fields=["status", "notes"])