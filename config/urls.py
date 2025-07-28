"""
URL configuration for coelinks project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.views.i18n import JavaScriptCatalog
# from api.verify.views import FileUpdateView, DocumentScanView, PictureVerifyView, FileUpdatetestView, \
#     DocumentVerifiedView, HeadshotVerifiedView

# from coelinks.profiles.views import ProfileView
# from rest_framework.routers import DefaultRouter
# from api.verify.views import FileUpdateView, DocumentScanView
# from api.chatbot.views import ChatGenerateView
#
# router = DefaultRouter()
#
# router.register(r"verify/", FileUpdateView, basename="verify")
# router.register(r"chat/", ChatGenerateView, basename="chat")

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    # path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    path("logiflex/", include("bizanalytic.logiflex.urls", namespace="logiflex")),
    path("", RedirectView.as_view(pattern_name="logiflex:index")),
    path("accounts/", include("allauth.urls")),
    # path("accounts/profile/", ProfileView.as_view()),
    # path("apis/chat/", include("api.chat.urls", namespace="chat")),
    path("profiles/", include("bizanalytic.profiles.urls", namespace="profiles")),
    # path("coeanalytics/", include("coelinks.coeanalytics.urls", namespace="coeanalytics")),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("i18n/", include("django.conf.urls.i18n")),




    # path('api/verify/', FileUpdateView.as_view(), name='verify'),
    # path('api/testverify/', FileUpdatetestView.as_view(), name='testverify'),
    # path('api/scan/', DocumentScanView.as_view(), name='scan'),
    # path('api/endverify/', DocumentVerifiedView.as_view(), name='endverify'),
    # path('api/headshotverified/', HeadshotVerifiedView.as_view(), name='headshotverified'),
    # path('api/checkimage/', PictureVerifyView.as_view(), name='checkimage'),
    # path('api/chat/', include('api.chatbot.urls', namespace='chat')),
    # path("api/ocr/", include('api.ocrserver.urls', namespace='ocr')),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
