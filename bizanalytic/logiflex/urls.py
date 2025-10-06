from django.urls import path, include, re_path
from . import views

app_name = "logiflex"

admin_patterns = [
    path("reports/", views.AdminReportsListView.as_view(), name="reports"),
]

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
    path('fullreport/', views.FullReportView.as_view(), name='fullreport'),
    path('newfullreport/<int:pk>/', views.FullReportNewClientView.as_view(), name='newfullreport'),
    path('full-newclientreport-create/', views.FullNewClientReportCreateView.as_view(), name='full-newclientreport-create'),
    path('view/<int:pk>/', views.AdvancedReportView.as_view(), name='view'),
    path('full-report-create/', views.FullReportCreateView.as_view(), name='full-report-create'),
    path('samplereport/', views.SampleAdvancedReportView.as_view(), name='samplereport'),
    path('list/', views.Payment_SuccessView.as_view(), name='list'),
    path('detail/<int:pk>/', views.RouteFileView.as_view(), name='detail'),
    path('reportview/<int:pk>/', views.ReportView.as_view(), name="reportview"),
    path('summary/<int:pk>/', views.ReportSummaryView.as_view(), name="summary"),
    path('helper/', views.ReportHelpersView.as_view(), name='helper')
]

stripe_patterns = [
    path('', views.Pricing_PageView.as_view(), name='payment_page'),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('stripe_webhook/', views.WebhookView.as_view(), name='stripe_webhook'),
    path('success/', views.Payment_SuccessView.as_view(), name='success'),
    path('payment-successful/', views.PaymentSuccessfulView.as_view(), name="payment-successful"),
    path('cancel/', views.Payment_FailView.as_view(), name='cancel'),

]

payment_patterns = [
    path("px-vr/", views.PaymentView.as_view(), name="px-vr"),
    path("list/", views.Payments_ListView.as_view(), name="list"),
    path("receipt/", views.PaymentDetailView.as_view(), name="receipt"),
    path("order/", views.OrderDetailsView.as_view(), name="order"),
]

subscription_patterns = [
    path("resume/", views.ResumeSubscriptionView.as_view(), name="resume"),
    path("cancel/", views.CancelSubscriptionView.as_view(), name="cancel"),
    path("pause/", views.PauseSubscriptionView.as_view(), name="pause"),

]

urlpatterns = [

    path("", views.IndexView.as_view(), name="index"),
    path("updateprices/", views.UpdateGasPricesView.as_view(), name="updateprices"),
    path("rx-apr/", views.AdminApproveReportView.as_view(), name="rx-apr"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path('clean-csv/', views.clean_csv, name='clean_csv'),
    path("pricing/", views.Pricing_PageView.as_view(), name='pricing'),
    path("book-call/", views.RequestCallView.as_view(), name="book-call"),
    path("bookcall/", views.BookACallView.as_view(), name="bookcall"),
    path("aboutus/", views.AboutUsView.as_view(), name="aboutus"),
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
    path(
        "admin/",
        include((admin_patterns, "bizanalytic.logiflex"), namespace="admin"),
    ),
    path(
        "payments/",
        include((payment_patterns, "bizanalytic.logiflex"), namespace="payments"),
    ),
    path(
        "subscription/",
        include((subscription_patterns, "bizanalytic.logiflex"), namespace="subscription"),
    ),
]
