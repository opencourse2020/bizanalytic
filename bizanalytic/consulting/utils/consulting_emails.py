"""
Consulting Lead Follow-Up Emails
=================================
Call these from your views after a lead submits a form.

Each function returns (subject, body) so you can use them
with Django's send_mail or your preferred email backend.

Usage:
    from .emails import get_discovery_call_followup, get_mini_audit_followup

    subject, body = get_discovery_call_followup(name="John", company="Acme Freight")
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [lead_email])
"""


def get_discovery_call_followup(name, company="", monthly_spend="", challenge=""):
    """
    Sent immediately after a discovery call form submission.
    Acknowledges the request, sets expectations, and offers value upfront.
    """
    subject = f"Your discovery call request — BizAnalytic"

    body = f"""Hi {name},

Thanks for reaching out. I'll reply within one business day with a few available times for a 15-minute call.

To make the most of our conversation, here's what I'll want to understand:

  - How many carriers you're working with and on which lanes
  - Where you feel the most uncertainty about your freight costs
  - Whether you have TMS exports or carrier invoices in CSV/Excel format

You don't need to prepare anything — these are just the questions I'll ask so you know what to expect.

In the meantime, you can see exactly what a freight spend audit delivers:
https://bizanalytic.com/consulting/freight/sample/

Or if you'd like to try the self-serve version right now, upload your data and get a free Fleet Health Check in under 60 seconds:
https://bizanalytic.com/logiflex/

Talk soon.

Adam Akaaboune
BizAnalytic
+1 (832) 430-2434
support@bizanalytic.com"""

    return subject, body


def get_mini_audit_followup(name, company="", file_name=""):
    """
    Sent immediately after a mini-audit form submission with file upload.
    Confirms receipt, sets the 3-day timeline, and manages expectations.
    """
    subject = f"Your freight data received — BizAnalytic"

    file_note = f" ({file_name})" if file_name else ""

    body = f"""Hi {name},

I've received your freight data{file_note}. Here's what happens next:

  1. I'll review the file format today and flag any issues immediately
  2. The analysis runs over the next 2-3 business days
  3. You'll receive a 3-page mini-audit PDF in your inbox

The mini-audit covers your Fleet Health Score, top savings opportunities, and any invoice anomalies flagged by our statistical models. It's a diagnostic — enough to show you whether a full engagement would find meaningful savings.

If the data format needs adjustment, I'll reach out directly to {name.split()[0] if ' ' in name else name}@{company.lower().replace(' ', '')}.com — or whatever email you prefer.

One thing to note: the mini-audit uses anonymized benchmarks. The full 15-page Freight Spend Intelligence Report includes named carriers, specific shipment IDs, LP-optimized allocation plans, and a 30-minute video walkthrough. You can see a sample here:
https://bizanalytic.com/consulting/freight/sample/

Talk soon.

Adam Akaaboune
BizAnalytic
+1 (832) 430-2434
support@bizanalytic.com"""

    return subject, body


def get_mini_audit_delivery(name, company="", fleet_score=0, total_savings=0):
    """
    Sent when the mini-audit PDF is ready.
    Delivers the report and pitches the full engagement.
    """
    subject = f"Your freight mini-audit is ready — Fleet Score: {fleet_score}/100"

    body = f"""Hi {name},

Your mini-audit is attached. Here's the headline:

  Fleet Health Score: {fleet_score}/100
  Estimated annual savings identified: ${total_savings:,.0f}

The attached 3-page report covers the top findings across your carrier network, the biggest cost anomalies we detected, and the single highest-impact action you could take this month.

What the mini-audit doesn't include (and the full audit does):

  - Named carriers with specific rate comparisons
  - Every flagged invoice with shipment IDs and overpayment amounts
  - LP-optimized carrier allocation plan (exact shipment shifts)
  - Lane-by-lane contribution margin analysis
  - Driver performance profiles with coaching recommendations
  - 30-minute recorded video walkthrough of your results

If you'd like to discuss the findings or explore a full engagement, I have a few slots open this week for a 15-minute call:
https://bizanalytic.com/consulting/freight/book/

The full Freight Spend Intelligence Report runs $2,500-$5,000 depending on data volume and network complexity. Based on what I've seen in your data, I'd estimate yours at $XX,XXX — but I'd rather discuss scope on a call before quoting precisely.

No pressure either way. The mini-audit is yours to keep regardless.

Best,

Adam Akaaboune
BizAnalytic
+1 (832) 430-2434
support@bizanalytic.com"""

    return subject, body


def get_no_follow_up_needed(name, company=""):
    """
    Sent when the mini-audit shows minimal savings potential.
    Honesty builds more long-term trust than a forced upsell.
    """
    subject = f"Your freight mini-audit results — BizAnalytic"

    body = f"""Hi {name},

Your mini-audit is attached. I want to be straightforward with you: based on the data you submitted, the savings potential is modest — likely under $5,000/year.

Your Fleet Health Score is solid, your carrier rates are competitive for your lane mix, and we didn't flag any significant invoice anomalies.

That's good news. It means your freight operation is running reasonably well.

I don't think a full $3,500 audit would deliver enough return to justify the cost for {company or 'your operation'} right now. I'd rather tell you that honestly than sell you something that won't pay for itself.

Two things I'd recommend instead:

  1. Run a free LogiFlex Health Check every quarter to track your Fleet Score over time. If costs drift, you'll see it early:
     https://bizanalytic.com/logiflex/

  2. If your freight spend grows significantly or you add new carriers, that's when a full audit becomes worthwhile. Reach out anytime.

Best,

Adam Akaaboune
BizAnalytic
+1 (832) 430-2434
support@bizanalytic.com"""

    return subject, body


def get_sample_download_followup(name, company=""):
    """
    Sent 2 days after someone downloads the sample report.
    Light touch — one question, not a pitch.
    """
    subject = f"Quick question about the sample report"

    body = f"""Hi {name},

You downloaded our sample Freight Spend Intelligence Report a couple of days ago. I'm curious — did it match what you were looking for?

If you have freight invoice data available (CSV or Excel from your TMS or carrier portal), I can run a free 3-page mini-audit on your actual numbers. Same format as the sample, but with your carriers, your lanes, and your costs. Takes about 3 business days.

Just reply to this email with the file attached, or upload it here:
https://bizanalytic.com/consulting/freight/book/

No obligation either way.

Adam Akaaboune
BizAnalytic
+1 (832) 430-2434"""

    return subject, body