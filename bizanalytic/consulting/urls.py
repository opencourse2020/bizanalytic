"""
Consulting URL Configuration
=============================
Handles both freight and e-commerce consulting services
plus the shared email verification endpoint.

Add to your main urls.py:
    path('consulting/', include('consulting.urls')),

Place at: consulting/urls.py
"""

from django.urls import path
from . import views

app_name = "consulting"

urlpatterns = [

    # =================================================================
    # SHARED
    # =================================================================
    path(
        "verify/<str:token>/",
        views.verify_lead,
        name="consulting_verify",
    ),
    path(
        "download/sample/<str:token>/",
        views.verify_download_sample,
        name="verify_download_sample",
    ),

    # =================================================================
    # FREIGHT SPEND AUDIT
    # =================================================================
    path(
        "freight/",
        views.freight_service,
        name="consulting_freight",
    ),
    path(
        "freight/sample/",
        views.freight_sample,
        name="consulting_freight_sample",
    ),
    path(
        "freight/sample/download/",
        views.freight_sample_download,
        name="consulting_freight_sample_download",
    ),
    path(
        "freight/book/",
        views.freight_book,
        name="consulting_freight_book",
    ),
    path(
        "freight/book/submit/",
        views.freight_book_submit,
        name="consulting_freight_book_submit",
    ),
    path(
        "freight/book/success/",
        views.freight_book_success,
        name="consulting_freight_book_success",
    ),

    # =================================================================
    # E-COMMERCE SHIPPING AUDIT
    # =================================================================
    path(
        "ecommerce/",
        views.ecommerce_service,
        name="consulting_ecommerce",
    ),
    path(
        "ecommerce/sample/",
        views.ecommerce_sample,
        name="consulting_ecommerce_sample",
    ),
    path(
        "ecommerce/sample/download/",
        views.ecommerce_sample_download,
        name="consulting_ecommerce_sample_download",
    ),
    path(
        "ecommerce/book/",
        views.ecommerce_book,
        name="consulting_ecommerce_book",
    ),
    path(
        "ecommerce/book/submit/",
        views.ecommerce_book_submit,
        name="consulting_ecommerce_book_submit",
    ),
    path(
        "ecommerce/book/success/",
        views.ecommerce_book_success,
        name="consulting_ecommerce_book_success",
    ),
]