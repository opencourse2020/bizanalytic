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

blog_patterns = [
    path("create/", views.BlogCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", views.BlogEditView.as_view(), name="edit"),
    path("detail/<str:slug>/", views.BlogDetailView.as_view(), name="detail"),
    path("list/", views.BlogListView.as_view(), name="list"),
    path("", views.BlogsView.as_view(), name="blogs")
]

report_patterns = [
    path("sample-report-create/", views.SampleReportCreateView.as_view(), name="sample-report-create"),
    path('fullreport/<int:pk>/', views.FullReportView.as_view(), name='fullreport'),
    path('view/<int:pk>/', views.AdvancedReportView.as_view(), name='view'),
    path('full-report-create/', views.FullReportCreateView.as_view(), name='full-report-create'),
    path('samplereport/', views.SampleAdvancedReportView.as_view(), name='samplereport'),

]

stripe_patterns = [
    path('', views.Payment_PageView.as_view(), name='payment_page'),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('stripe_webhook/', views.WebhookView.as_view(), name='stripe_webhook'),
    path('success/', views.Payment_SuccessView.as_view(), name='success'),
    path('cancel/', views.Payment_FailView.as_view(), name='cancel'),

]

urlpatterns = [

    path("", views.IndexView.as_view(), name="index"),
    path("pricing/", views.Payment_PageView.as_view(), name='pricing'),
    path("book-call/", views.RequestCallView.as_view(), name="book-call"),
    path("bookcall/", views.BookACallView.as_view(), name="bookcall"),
    path(
        "newsletters/",
        include((newsletter_patterns, "bizanalytic.logiflex"), namespace="newsletters"),
    ),
    path(
        "blog/",
        include((blog_patterns, "bizanalytic.logiflex"), namespace="blog"),
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
