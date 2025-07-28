from django.urls import path, include, re_path
from . import views

app_name = "logiflex"

urlpatterns = [

    path("", views.IndexView.as_view(), name="index"),

]
