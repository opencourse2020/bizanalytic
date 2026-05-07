"""
URL configuration for consulting pages.

Add to your main urls.py:
    path('consulting/', include('consulting.urls')),

Or add these patterns directly to your existing urlpatterns.
"""

from django.urls import path
from . import views

app_name = "consulting"

urlpatterns = [

    # =================================================================
    # SHARED
    # =================================================================
    path(
        'freight/verify/<str:token>/',
        views.freight_verify,
        name='consulting_freight_verify',
    ),

    # =================================================================
    # FREIGHT SPEND AUDIT
    # =================================================================
    path(
        'freight/',
        views.freight_service,
        name='consulting_freight',
    ),
    path(
        'freight/sample/',
        views.freight_sample,
        name='consulting_freight_sample',
    ),
    path(
        'freight/sample/download/',
        views.freight_sample_download,
        name='consulting_freight_sample_download',
    ),
    path(
        'freight/book/',
        views.freight_book,
        name='consulting_freight_book',
    ),
    path(
        'freight/book/submit/',
        views.freight_book_submit,
        name='consulting_freight_book_submit',
    ),
    path(
        'freight/book/success/',
        views.freight_book_success,
        name='consulting_freight_book_success',
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

    # path(
    #     'freight/expired/',
    #     views.freight_book_success,
    #     name='consulting_freight_book_success',
    # ),
]