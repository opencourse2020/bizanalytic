"""
Consulting Views
================
Handles both freight and e-commerce consulting services.

Shared infrastructure:
  - Anti-bot: honeypot + timestamp + disposable email blocking + rate limiting
  - Email verification: leads are unverified until they click the link
  - Notifications: you only get emailed about verified leads

Place at: consulting/views.py
"""

import time
import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
from django.contrib import messages
from django.views.decorators.http import require_POST
import os

from .models import ConsultingLead
from .forms import (
    SampleDownloadForm,
    FreightDiscoveryCallForm,
    FreightMiniAuditForm,
    EcommerceDiscoveryCallForm,
    EcommerceSnapshotForm,
)


# =====================================================================
# SHARED HELPERS
# =====================================================================

def _get_client_ip(request):
    """Extract client IP, handling proxies."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _is_rate_limited(email, ip):
    """
    Rate limiting:
      - 1 submission per email per 24 hours
      - 3 submissions per IP per hour
    Returns True if rate limited.
    """
    email_key = f"consult_lead:{email.lower()}"
    ip_key = f"consult_ip:{ip}"

    if cache.get(email_key):
        return True

    ip_count = cache.get(ip_key, 0)
    if ip_count >= 3:
        return True

    cache.set(email_key, True, 86400)  # 24 hours
    cache.set(ip_key, ip_count + 1, 3600)  # 1 hour

    return False


def _get_form_timestamp():
    """Returns the current timestamp for anti-bot timing."""
    return str(int(time.time()))


def _send_verification_email(lead, request):
    """Sends the email verification link to the prospect."""
    verify_url = request.build_absolute_uri(
        f"/consulting/verify/{lead.verification_token}/"
    )

    service_name = "freight spend audit" if lead.service == "freight" else "shipping audit"

    send_mail(
        subject="Confirm your request — BizAnalytic",
        message=(
            f"Hi {lead.name},\n\n"
            f"Click here to confirm your {service_name} request:\n"
            f"{verify_url}\n\n"
            f"This link expires in 7 days.\n\n"
            f"If you didn't submit this form, ignore this email.\n\n"
            f"— Adil, BizAnalytic"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[lead.email],
        fail_silently=True,
    )


def _notify_owner(lead):
    """Sends you an email notification about a verified lead."""
    lines = [
        f"NEW VERIFIED LEAD",
        f"",
        f"Service: {lead.get_service_display()}",
        f"Type: {lead.get_lead_type_display()}",
        f"Name: {lead.name}",
        f"Email: {lead.email}",
    ]

    if lead.company:
        lines.append(f"Company: {lead.company}")
    if lead.store_url:
        lines.append(f"Store: {lead.store_url}")
    if lead.monthly_freight_spend:
        lines.append(f"Monthly freight spend: {lead.monthly_freight_spend}")
    if lead.monthly_shipping_spend:
        lines.append(f"Monthly shipping spend: {lead.monthly_shipping_spend}")
    if lead.monthly_order_volume:
        lines.append(f"Monthly volume: {lead.monthly_order_volume}")
    if lead.carriers_used:
        lines.append(f"Carriers: {', '.join(lead.carriers_used)}")
    if lead.shipping_platform:
        lines.append(f"Platform: {lead.shipping_platform}")
    if lead.carrier_count:
        lines.append(f"Carrier count: {lead.carrier_count}")
    if lead.challenge:
        lines.append(f"Challenge: {lead.challenge}")
    if lead.uploaded_file_name:
        lines.append(f"File: {lead.uploaded_file_name} ({lead.uploaded_file_size // 1024}KB)")

    send_mail(
        subject=f"[BizAnalytic] VERIFIED lead: {lead.get_lead_type_display()} — {lead.name}",
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.DEFAULT_FROM_EMAIL],
        fail_silently=True,
    )


def _save_uploaded_file(uploaded_file, service):
    """Saves an uploaded file and returns the path."""
    upload_dir = os.path.join(
        settings.MEDIA_ROOT, "consulting", service, "uploads"
    )
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, uploaded_file.name)

    with open(file_path, "wb+") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    return file_path


# =====================================================================
# VERIFICATION VIEW (shared by both services)
# =====================================================================

def verify_lead(request, token):
    """Handles the email verification click."""
    lead = get_object_or_404(
        ConsultingLead,
        verification_token=token,
        is_verified=False,
    )

    # Check expiry
    if lead.is_expired:
        return render(request, "consulting/verify_expired.html")

    lead.verify()
    _notify_owner(lead)

    # Determine which success template to use
    template = (
        "consulting/freight/verified.html"
        if lead.service == ConsultingLead.Service.FREIGHT
        else "consulting/ecommerce/verified.html"
    )

    return render(request, template, {"lead": lead})


# =====================================================================
# FREIGHT VIEWS
# =====================================================================

def freight_service(request):
    """Main freight consulting service page."""
    return render(request, "consulting/freight/service.html")


def freight_sample(request):
    """Sample report page with email-gated download."""
    return render(request, "consulting/freight/sample.html", {
        "form_timestamp": _get_form_timestamp(),
    })


def freight_book(request):
    """Booking page — discovery call or mini-audit intake."""
    return render(request, "consulting/freight/book.html", {
        "form_timestamp": _get_form_timestamp(),
        "call_form": FreightDiscoveryCallForm(),
        "audit_form": FreightMiniAuditForm(),
    })


def freight_book_success(request):
    """Confirmation page after form submission."""
    return render(request, "consulting/freight/book_success.html", {
        "intake_type": request.GET.get("type", "discovery_call"),
    })


@require_POST
def freight_sample_download(request):
    """Handles sample report download with email capture."""
    form = SampleDownloadForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Please provide a valid name and work email.")
        return redirect("consulting_freight_sample")

    ip = _get_client_ip(request)
    if _is_rate_limited(form.cleaned_data["email"], ip):
        messages.info(request, "You've already downloaded the sample report.")
        return redirect("consulting_freight_sample")

    # Save as verified lead (sample downloads don't need email verification)
    ConsultingLead.objects.create(
        service=ConsultingLead.Service.FREIGHT,
        lead_type=ConsultingLead.LeadType.SAMPLE_DOWNLOAD,
        status=ConsultingLead.LeadStatus.VERIFIED,
        is_verified=True,
        name=form.cleaned_data["name"],
        email=form.cleaned_data["email"],
        company=form.cleaned_data.get("company", ""),
        ip_address=ip,
    )

    # Serve the PDF
    sample_path = os.path.join(
        settings.BASE_DIR, "static", "consulting",
        "freight-spend-audit-sample.pdf"
    )
    if not os.path.exists(sample_path):
        raise Http404("Sample report not found.")

    return FileResponse(
        open(sample_path, "rb"),
        content_type="application/pdf",
        as_attachment=True,
        filename="BizAnalytic-Freight-Spend-Audit-Sample.pdf",
    )


@require_POST
def freight_book_submit(request):
    """Handles both freight discovery call and mini-audit submissions."""
    intake_type = request.POST.get("intake_type", "discovery_call")
    ip = _get_client_ip(request)

    if intake_type == "discovery_call":
        form = FreightDiscoveryCallForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please fill in all required fields.")
            return redirect("consulting_freight_book")

        email = form.cleaned_data["email"]
        if _is_rate_limited(email, ip):
            messages.info(request, "You've already submitted a request. Check your email.")
            return redirect("consulting_freight_book")

        lead = ConsultingLead.objects.create(
            service=ConsultingLead.Service.FREIGHT,
            lead_type=ConsultingLead.LeadType.DISCOVERY_CALL,
            name=form.cleaned_data["name"],
            email=email,
            company=form.cleaned_data["company"],
            monthly_freight_spend=form.cleaned_data["monthly_spend"],
            challenge=form.cleaned_data.get("challenge", ""),
            ip_address=ip,
            form_load_timestamp=int(form.cleaned_data.get("form_ts", 0)),
            submission_elapsed_seconds=int(time.time()) - int(form.cleaned_data.get("form_ts", 0) or 0),
        )

        _send_verification_email(lead, request)

    elif intake_type == "mini_audit":
        form = FreightMiniAuditForm(request.POST, request.FILES)
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("consulting_freight_book")

        email = form.cleaned_data["email"]
        if _is_rate_limited(email, ip):
            messages.info(request, "You've already submitted a request. Check your email.")
            return redirect("consulting_freight_book")

        uploaded_file = form.cleaned_data["freight_data"]
        file_path = _save_uploaded_file(uploaded_file, "freight")

        lead = ConsultingLead.objects.create(
            service=ConsultingLead.Service.FREIGHT,
            lead_type=ConsultingLead.LeadType.MINI_AUDIT,
            name=form.cleaned_data["name"],
            email=email,
            company=form.cleaned_data["company"],
            carrier_count=form.cleaned_data["carrier_count"],
            uploaded_file=file_path,
            uploaded_file_name=uploaded_file.name,
            uploaded_file_size=uploaded_file.size,
            ip_address=ip,
            form_load_timestamp=int(form.cleaned_data.get("form_ts", 0)),
            submission_elapsed_seconds=int(time.time()) - int(form.cleaned_data.get("form_ts", 0) or 0),
        )

        _send_verification_email(lead, request)

    return redirect(f"/consulting/freight/book/success/?type={intake_type}")


# =====================================================================
# ECOMMERCE VIEWS
# =====================================================================

def ecommerce_service(request):
    """Main e-commerce shipping audit service page."""
    return render(request, "consulting/ecommerce/service.html")


def ecommerce_sample(request):
    """Sample report page with email-gated download."""
    return render(request, "consulting/ecommerce/sample.html", {
        "form_timestamp": _get_form_timestamp(),
    })


def ecommerce_book(request):
    """Booking page — shipping snapshot or discovery call."""
    return render(request, "consulting/ecommerce/book.html", {
        "form_timestamp": _get_form_timestamp(),
        "snapshot_form": EcommerceSnapshotForm(),
        "call_form": EcommerceDiscoveryCallForm(),
    })


def ecommerce_book_success(request):
    """Confirmation page after form submission."""
    return render(request, "consulting/ecommerce/book_success.html", {
        "intake_type": request.GET.get("type", "discovery_call"),
    })


@require_POST
def ecommerce_sample_download(request):
    """Handles sample report download with email capture."""
    form = SampleDownloadForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Please provide a valid name and work email.")
        return redirect("consulting_ecommerce_sample")

    ip = _get_client_ip(request)
    if _is_rate_limited(form.cleaned_data["email"], ip):
        messages.info(request, "You've already downloaded the sample report.")
        return redirect("consulting_ecommerce_sample")

    ConsultingLead.objects.create(
        service=ConsultingLead.Service.ECOMMERCE,
        lead_type=ConsultingLead.LeadType.SAMPLE_DOWNLOAD,
        status=ConsultingLead.LeadStatus.VERIFIED,
        is_verified=True,
        name=form.cleaned_data["name"],
        email=form.cleaned_data["email"],
        store_url=form.cleaned_data.get("store_url", ""),
        ip_address=ip,
    )

    sample_path = os.path.join(
        settings.BASE_DIR, "static", "consulting",
        "ecommerce-shipping-audit-sample.pdf"
    )
    if not os.path.exists(sample_path):
        raise Http404("Sample report not found.")

    return FileResponse(
        open(sample_path, "rb"),
        content_type="application/pdf",
        as_attachment=True,
        filename="BizAnalytic-Shipping-Audit-Sample.pdf",
    )


@require_POST
def ecommerce_book_submit(request):
    """Handles both e-commerce snapshot and discovery call submissions."""
    intake_type = request.POST.get("intake_type", "discovery_call")
    ip = _get_client_ip(request)

    if intake_type == "discovery_call":
        form = EcommerceDiscoveryCallForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please fill in all required fields.")
            return redirect("consulting_ecommerce_book")

        email = form.cleaned_data["email"]
        if _is_rate_limited(email, ip):
            messages.info(request, "You've already submitted a request. Check your email.")
            return redirect("consulting_ecommerce_book")

        lead = ConsultingLead.objects.create(
            service=ConsultingLead.Service.ECOMMERCE,
            lead_type=ConsultingLead.LeadType.DISCOVERY_CALL,
            name=form.cleaned_data["name"],
            email=email,
            store_url=form.cleaned_data["store_url"],
            monthly_shipping_spend=form.cleaned_data["monthly_spend"],
            challenge=form.cleaned_data.get("challenge", ""),
            ip_address=ip,
            form_load_timestamp=int(form.cleaned_data.get("form_ts", 0)),
            submission_elapsed_seconds=int(time.time()) - int(form.cleaned_data.get("form_ts", 0) or 0),
        )

        _send_verification_email(lead, request)

    elif intake_type == "shipping_snapshot":
        form = EcommerceSnapshotForm(request.POST, request.FILES)
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("consulting_ecommerce_book")

        email = form.cleaned_data["email"]
        if _is_rate_limited(email, ip):
            messages.info(request, "You've already submitted a request. Check your email.")
            return redirect("consulting_ecommerce_book")

        uploaded_file = form.cleaned_data["shipping_data"]
        file_path = _save_uploaded_file(uploaded_file, "ecommerce")

        lead = ConsultingLead.objects.create(
            service=ConsultingLead.Service.ECOMMERCE,
            lead_type=ConsultingLead.LeadType.MINI_AUDIT,
            name=form.cleaned_data["name"],
            email=email,
            store_url=form.cleaned_data["store_url"],
            monthly_order_volume=form.cleaned_data["monthly_volume"],
            carriers_used=form.cleaned_data.get("carriers", []),
            shipping_platform=form.cleaned_data.get("platform", ""),
            uploaded_file=file_path,
            uploaded_file_name=uploaded_file.name,
            uploaded_file_size=uploaded_file.size,
            ip_address=ip,
            form_load_timestamp=int(form.cleaned_data.get("form_ts", 0)),
            submission_elapsed_seconds=int(time.time()) - int(form.cleaned_data.get("form_ts", 0) or 0),
        )

        _send_verification_email(lead, request)

    return redirect(f"/consulting/ecommerce/book/success/?type={intake_type}")