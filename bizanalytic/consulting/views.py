"""
Views for the freight consulting service pages.

Handles:
  - Static page rendering (service, sample, booking)
  - Sample report download (email capture)
  - Booking form submission (discovery call + mini-audit intake)
"""

from django.shortcuts import render, redirect
from django.http import FileResponse, Http404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
import os


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
        return redirect('consulting_freight_sample')

    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    company = request.POST.get('company', '').strip()

    if not name or not email:
        messages.error(request, 'Please provide your name and email.')
        return redirect('consulting_freight_sample')

    # Save the lead (create a simple model or log to your CRM)
    _save_consulting_lead(
        name=name,
        email=email,
        company=company,
        lead_type='sample_download',
        service='freight',
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
        return redirect('consulting_freight_book')

    intake_type = request.POST.get('intake_type', 'discovery_call')
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    company = request.POST.get('company', '').strip()

    if not name or not email or not company:
        messages.error(request, 'Please fill in all required fields.')
        return redirect('consulting_freight_book')

    if intake_type == 'discovery_call':
        monthly_spend = request.POST.get('monthly_spend', '')
        challenge = request.POST.get('challenge', '').strip()

        _save_consulting_lead(
            name=name,
            email=email,
            company=company,
            lead_type='discovery_call',
            service='freight',
            extra={
                'monthly_spend': monthly_spend,
                'challenge': challenge,
            },
        )

        _notify_new_lead(
            lead_type='Discovery call request',
            name=name,
            email=email,
            company=company,
            extra_lines=[
                f'Monthly spend: {monthly_spend}',
                f'Challenge: {challenge}' if challenge else '',
            ],
        )

        # Send confirmation to the prospect
        send_mail(
            subject='Your discovery call request — BizAnalytic',
            message=(
                f'Hi {name},\n\n'
                f'Thanks for your interest in a freight spend audit. '
                f'I\'ll reply within 1 business day with available times '
                f'for a 15-minute call.\n\n'
                f'In the meantime, you can see a sample of what we deliver:\n'
                f'https://bizanalytic.com/consulting/freight/sample/\n\n'
                f'Best,\n'
                f'Adil Akaaboune\n'
                f'BizAnalytic\n'
                f'+1 (832) 430-2434'
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=True,
        )

    elif intake_type == 'mini_audit':
        carrier_count = request.POST.get('carrier_count', '')
        freight_data = request.FILES.get('freight_data')

        if not freight_data:
            messages.error(request, 'Please upload your freight data file.')
            return redirect('consulting_freight_book')

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
            extra={
                'carrier_count': carrier_count,
                'file_name': freight_data.name,
                'file_size': freight_data.size,
            },
        )

        _notify_new_lead(
            lead_type='Mini-audit request (FILE ATTACHED)',
            name=name,
            email=email,
            company=company,
            extra_lines=[
                f'Carriers: {carrier_count}',
                f'File: {freight_data.name} ({freight_data.size // 1024}KB)',
                f'Saved to: {file_path}',
            ],
        )

        # Send confirmation to the prospect
        send_mail(
            subject='Your freight data received — BizAnalytic',
            message=(
                f'Hi {name},\n\n'
                f'We\'ve received your freight data file ({freight_data.name}). '
                f'Your free 3-page mini-audit will be ready within 3 business days.\n\n'
                f'If we have any questions about the data format, '
                f'we\'ll reach out to {email} directly.\n\n'
                f'Best,\n'
                f'Adil Akaaboune\n'
                f'BizAnalytic\n'
                f'+1 (832) 430-2434'
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=True,
        )

    return redirect(f"{settings.LOGIN_URL}?next=/consulting/freight/book/success/?type={intake_type}"
                    if False else f'/consulting/freight/book/success/?type={intake_type}')


# =====================================================================
# HELPERS
# =====================================================================

def _save_consulting_lead(name, email, company, lead_type, service, extra=None):
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
    # ConsultingLead.objects.create(
    #     name=name, email=email, company=company,
    #     lead_type=lead_type, service=service,
    #     extra_json=extra or {},
    # )
    pass


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