"""
Consulting Admin
================
Admin interface for managing consulting leads.
Optimized for a solo operator who needs to quickly:
  - See new verified leads
  - Filter by service and status
  - Mark leads as contacted/converted/disqualified
  - View uploaded files

Place at: consulting/admin.py
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import ConsultingLead


@admin.register(ConsultingLead)
class ConsultingLeadAdmin(admin.ModelAdmin):

    # ---- List view ----
    list_display = [
        "name",
        "email",
        "service_badge",
        "lead_type_badge",
        "status_badge",
        "is_verified",
        "has_file",
        "created_at",
    ]
    list_filter = [
        "service",
        "lead_type",
        "status",
        "is_verified",
        ("created_at", admin.DateFieldListFilter),
    ]
    search_fields = ["name", "email", "company", "store_url"]
    list_per_page = 30
    ordering = ["-created_at"]

    # ---- Detail view ----
    fieldsets = [
        ("Lead info", {
            "fields": (
                "status", "service", "lead_type",
                "name", "email", "company", "store_url",
            ),
        }),
        ("Qualification", {
            "fields": (
                "monthly_freight_spend", "carrier_count",
                "monthly_order_volume", "monthly_shipping_spend",
                "carriers_used", "shipping_platform",
                "challenge",
            ),
        }),
        ("File upload", {
            "fields": (
                "uploaded_file", "uploaded_file_name", "uploaded_file_size",
            ),
        }),
        ("Verification & anti-bot", {
            "fields": (
                "is_verified", "verified_at", "verification_token",
                "ip_address", "form_load_timestamp",
                "submission_elapsed_seconds",
            ),
            "classes": ("collapse",),
        }),
        ("Lifecycle", {
            "fields": (
                "created_at", "contacted_at", "converted_at", "notes",
            ),
        }),
        ("Extra data", {
            "fields": ("extra_json",),
            "classes": ("collapse",),
        }),
    ]

    readonly_fields = [
        "created_at", "verified_at", "contacted_at", "converted_at",
        "verification_token", "ip_address",
        "form_load_timestamp", "submission_elapsed_seconds",
        "uploaded_file_size",
    ]

    # ---- Bulk actions ----
    actions = [
        "mark_contacted",
        "mark_qualified",
        "mark_converted",
        "mark_disqualified",
    ]

    @admin.action(description="Mark selected as Contacted")
    def mark_contacted(self, request, queryset):
        for lead in queryset:
            lead.mark_contacted()
        self.message_user(request, f"{queryset.count()} leads marked as contacted.")

    @admin.action(description="Mark selected as Qualified")
    def mark_qualified(self, request, queryset):
        queryset.update(status=ConsultingLead.LeadStatus.QUALIFIED)
        self.message_user(request, f"{queryset.count()} leads marked as qualified.")

    @admin.action(description="Mark selected as Converted")
    def mark_converted(self, request, queryset):
        for lead in queryset:
            lead.mark_converted()
        self.message_user(request, f"{queryset.count()} leads marked as converted.")

    @admin.action(description="Mark selected as Disqualified")
    def mark_disqualified(self, request, queryset):
        queryset.update(status=ConsultingLead.LeadStatus.DISQUALIFIED)
        self.message_user(request, f"{queryset.count()} leads marked as disqualified.")

    # ---- Display helpers ----
    @admin.display(description="Service")
    def service_badge(self, obj):
        colors = {"freight": "#1a4fbd", "ecommerce": "#dc2626"}
        color = colors.get(obj.service, "#666")
        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>',
            color,
            obj.get_service_display(),
        )

    @admin.display(description="Type")
    def lead_type_badge(self, obj):
        return obj.get_lead_type_display()

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "unverified": "#9b9ba3",
            "verified": "#047857",
            "contacted": "#1a4fbd",
            "qualified": "#92400e",
            "converted": "#047857",
            "disqualified": "#b91c1c",
            "stale": "#9b9ba3",
        }
        color = colors.get(obj.status, "#666")
        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="File", boolean=True)
    def has_file(self, obj):
        return bool(obj.uploaded_file_name)