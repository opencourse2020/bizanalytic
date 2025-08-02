from django.urls import path, include, re_path
from . import views

app_name = "logiflex"


newsletter_patterns = [
    path("create/", views.NewsletterCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", views.NewsletterEditView.as_view(), name="edit"),
    path("list/", views.NewsletterListView.as_view(), name="list"),
    path("subscrib/", views.NewsletterSubscriptionCreateView.as_view(), name="subscrib"),
    path("editsubscrib/<int:pk>/", views.NewsletterSubscriptionEditView.as_view(), name="editsubscrib"),
    path("subscribtionlist/", views.NewsletterSubscriptionListView.as_view(), name="subscribtionlist"),
]

report_patterns = [
    path("create/", views.SampleReportCreateView.as_view(), name="create"),

]

stripe_patterns = [
    path('', views.Payment_PageView.as_view(), name='payment_page'),
    path('create-checkout-session/', views.CreateCheckoutSessionView.as_view(), name='create_checkout_session'),
    path('webhook/', views.WebhookView.as_view(), name='stripe_webhook'),
    path('success/', views.Payment_SuccessView.as_view(), name='success'),
    path('cancel/', views.Payment_FailView.as_view(), name='cancel'),
]

urlpatterns = [

    path("", views.IndexView.as_view(), name="index"),
    path("book-call/", views.RequestCallView.as_view(), name="book-call"),
    path("bookcall/", views.BookACallView.as_view(), name="bookcall"),
    path(
        "newsletters/",
        include((newsletter_patterns, "bizanalytic.logiflex"), namespace="newsletters"),
    ),
    path(
        "reports/",
        include((report_patterns, "bizanalytic.logiflex"), namespace="reports"),
    ),
    path(
        "securepay/",
        include((stripe_patterns, "bizanalytic.logiflex"), namespace="securepay"),
    ),

]
