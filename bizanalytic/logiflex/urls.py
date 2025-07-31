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

urlpatterns = [

    path("", views.IndexView.as_view(), name="index"),
    path(
        "newsletters/",
        include((newsletter_patterns, "bizanalytic.logiflex"), namespace="newsletters"),
    ),
    path(
        "reports/",
        include((report_patterns, "bizanalytic.logiflex"), namespace="reports"),
    ),

]
