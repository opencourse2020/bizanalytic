"""
Views for the freight consulting service pages.

Handles:
  - Static page rendering (service, sample, booking)
  - Sample report download (email capture)
  - Booking form submission (discovery call + mini-audit intake)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
import os
import secrets
from django.utils import timezone
from datetime import timedelta

from .models import ConsultingLead
from .utils.consulting_emails import *

# =====================================================================
# PAGE VIEWS
# =====================================================================

def freight_service(request):
    """Main freight consulting service page."""
    return render(request, 'consulting/freight/service.html')


def freight_sample(request):
    """Sample report page with email-gated download."""
    return render(request, 'consulting/freight/sample.html')


def freight_book(request):
    """Booking page — discovery call or mini-audit intake."""
    return render(request, 'consulting/freight/book.html')


def freight_book_success(request):
    """Confirmation page after form submission."""
    intake_type = request.GET.get('type', 'discovery_call')
    return render(request, 'consulting/freight/book_success.html', {
        'intake_type': intake_type,
    })


# =====================================================================
# FORM HANDLERS
# =====================================================================

def freight_sample_download(request):
    """
    Handles sample report download.
    Captures email, then serves the PDF.
    """
    if request.method != 'POST':
        return redirect('consulting:consulting_freight_sample')

    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    company = request.POST.get('company', '').strip()

    if not name or not email:
        messages.error(request, 'Please provide your name and email.')
        return redirect('consulting:consulting_freight_sample')

    # Save the lead (create a simple model or log to your CRM)
    _save_consulting_lead(
        name=name,
        email=email,
        company=company,
        lead_type='sample_download',
        service='freight',
    )

    # Fetch Email's body and subject with the company name
    subject, body = get_sample_download_followup(
        name=name, company=company)

    # Send confirmation to the prospect
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=True,
    )

    # Send notification to yourself
    _notify_new_lead(
        lead_type='Sample download',
        name=name,
        email=email,
        company=company,
    )

    # Serve the PDF
    sample_path = os.path.join(
        settings.BASE_DIR, 'static', 'consulting',
        'freight-spend-audit-sample.pdf'
    )
    print(sample_path)
    if not os.path.exists(sample_path):
        raise Http404('Sample report not found.')

    return FileResponse(
        open(sample_path, 'rb'),
        content_type='application/pdf',
        as_attachment=True,
        filename='BizAnalytic-Freight-Spend-Audit-Sample.pdf',
    )


def freight_book_submit(request):
    """
    Handles both discovery call and mini-audit form submissions.
    Differentiates by the hidden 'intake_type' field.
    """
    if request.method != 'POST':
        return redirect('consulting:consulting_freight_book')

    intake_type = request.POST.get('intake_type', 'discovery_call')
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    company = request.POST.get('company', '').strip()
    website = request.POST.get('website', '').strip()
    address = request.POST.get('address', '').strip()
    token = secrets.token_urlsafe(32)

    if website or address:
        return redirect('consulting_freight_book_success')

    if not name or not email or not company:
        messages.error(request, 'Please fill in all required fields.')
        return redirect('consulting:consulting_freight_book')

    if intake_type == 'discovery_call':
        monthly_spend = request.POST.get('monthly_spend', '')
        challenge = request.POST.get('challenge', '').strip()

        _save_consulting_lead(
            name=name,
            email=email,
            company=company,
            lead_type='discovery_call',
            service='freight',
            token=token,
            extra={
                'monthly_spend': monthly_spend,
                'challenge': challenge,
            },
        )

        # _notify_new_lead(
        #     lead_type='Discovery call request',
        #     name=name,
        #     email=email,
        #     company=company,
        #     extra_lines=[
        #         f'Monthly spend: {monthly_spend}',
        #         f'Challenge: {challenge}' if challenge else '',
        #     ],
        # )
        #
        # # Fetch Email's body and subject with the company name
        # subject, body = get_discovery_call_followup(
        #     name=name, company=company,
        #     monthly_spend=monthly_spend, challenge=challenge,
        # )
        #
        # # Send confirmation to the prospect
        # send_mail(
        #     subject=subject,
        #     message=body,
        #     from_email=settings.EMAIL_HOST_USER,
        #     recipient_list=[email],
        #     fail_silently=True,
        # )

    elif intake_type == 'mini_audit':
        carrier_count = request.POST.get('carrier_count', '')
        freight_data = request.FILES.get('freight_data')

        if not freight_data:
            messages.error(request, 'Please upload your freight data file.')
            return redirect('consulting:consulting_freight_book')

        # Save uploaded file
        upload_dir = os.path.join(
            settings.MEDIA_ROOT, 'consulting', 'freight', 'uploads'
        )
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f'{company}_{freight_data.name}')
        with open(file_path, 'wb+') as f:
            for chunk in freight_data.chunks():
                f.write(chunk)

        _save_consulting_lead(
            name=name,
            email=email,
            company=company,
            lead_type='mini_audit',
            service='freight',
            token=token,
            extra={
                'carrier_count': carrier_count,
                'file_name': freight_data.name,
                'file_size': freight_data.size,
            },
        )

    # Send verification email
    verify_url = request.build_absolute_uri(
        f'/consulting/freight/verify/{token}/'
    )
    send_mail(
        subject='Confirm your request — BizAnalytic',
        message=(
            f'Hi {name},\n\n'
            f'Click here to confirm your request:\n'
            f'{verify_url}\n\n'
            f'If you didn\'t submit this form, ignore this email.\n\n'
            f'— Adil, BizAnalytic'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
        # _notify_new_lead(
        #     lead_type='Mini-audit request (FILE ATTACHED)',
        #     name=name,
        #     email=email,
        #     company=company,
        #     extra_lines=[
        #         f'Carriers: {carrier_count}',
        #         f'File: {freight_data.name} ({freight_data.size // 1024}KB)',
        #         f'Saved to: {file_path}',
        #     ],
        # )



    return redirect(f"{settings.LOGIN_URL}?next=/consulting/freight/book/success/?type={intake_type}"
                    if False else f'/consulting/freight/book/success/?type={intake_type}')


def freight_verify(request, token):
    lead = get_object_or_404(ConsultingLead, verification_token=token, is_verified=False)

    if timezone.now() - lead.created_at > timedelta(days=7):
        return render(request, 'consulting/freight/expired.html')

    lead.is_verified = True
    lead.save()

    # NOW notify yourself — this is a real lead
    if lead.lead_type == "mini_audit":
        carrier_count = ""
        file_name = ""
        file_size = 0
        if lead.extra_json:
            carrier_count = lead.extra_json["carrier_count"]
            file_name = lead.extra_json["file_name"]
            file_size = lead.extra_json["file_size"]
        _notify_new_lead(
            lead_type='Mini-audit request (FILE ATTACHED)',
            name=lead.name,
            email=lead.email,
            company=lead.company,
            extra_lines=[
                f'Carriers: {carrier_count}',
                f'File: {file_name} ({file_size // 1024}KB)',
            ],
        )
        # Fetch Email's body and subject with the company name
        subject, body = get_mini_audit_followup(
            name=lead.name, company=lead.company,
            file_name=file_name
        )

        # Send confirmation to the prospect
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[lead.email],
            fail_silently=True,
        )

    elif lead.lead_type == "discovery_call":

        monthly_spend = ""
        challenge = ""

        if lead.extra_json:
            monthly_spend = lead.extra_json["monthly_spend"]
            challenge = lead.extra_json["challenge"]

        _notify_new_lead(
            lead_type='Discovery call request',
            name=lead.name,
            email=lead.email,
            company=lead.company,
            extra_lines=[
                f'Monthly spend: {monthly_spend}',
                f'Challenge: {challenge}' if challenge else '',
            ],
        )

        # Fetch Email's body and subject with the company name
        subject, body = get_discovery_call_followup(
            name=lead.name, company=lead.company,
            monthly_spend=monthly_spend, challenge=challenge,
        )

        # Send confirmation to the prospect
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[lead.email],
            fail_silently=True,
        )

    return render(request, 'consulting/freight/verified.html', {'lead': lead})


# =====================================================================
# HELPERS
# =====================================================================

def _save_consulting_lead(name, email, company, lead_type, service, token, extra=None):
    """
    Saves a consulting lead to the database.

    You can use a simple model like:
        class ConsultingLead(models.Model):
            name = models.CharField(max_length=200)
            email = models.EmailField()
            company = models.CharField(max_length=200, blank=True)
            lead_type = models.CharField(max_length=50)
            service = models.CharField(max_length=50)
            extra_json = models.JSONField(default=dict, blank=True)
            created_at = models.DateTimeField(auto_now_add=True)
            is_contacted = models.BooleanField(default=False)
            notes = models.TextField(blank=True)

    Or just log to a CSV file for now.
    """
    # TODO: Replace with your actual model save
    ConsultingLead.objects.create(
        name=name, email=email, company=company,
        lead_type=lead_type, service=service,
        is_verified=False, verification_token=token,
        extra_json=extra or {},
    )


def _notify_new_lead(lead_type, name, email, company, extra_lines=None):
    """Sends you an email notification when a new lead comes in."""
    body_lines = [
        f'New consulting lead:',
        f'',
        f'Type: {lead_type}',
        f'Name: {name}',
        f'Email: {email}',
        f'Company: {company}',
    ]
    if extra_lines:
        body_lines.extend([l for l in extra_lines if l])

    send_mail(
        subject=f'[BizAnalytic] New lead: {lead_type} — {company}',
        message='\n'.join(body_lines),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[settings.EMAIL_HOST_USER],
        fail_silently=True,
    )