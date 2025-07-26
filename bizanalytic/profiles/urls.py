from django.urls import path, include, re_path
from . import views

app_name = "profiles"

enterprise_patterns = [
    path("create/", views.EnterpriseCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", views.EnterpriseEditView.as_view(), name="edit"),
]


urlpatterns = [
    path("language/<int:pk>/", views.LanguageUpdateView.as_view(), name="language"),
    path("userinfo/<int:pk>/", views.ProfilesUpdateView.as_view(), name="userinfo"),
    path("activate/<int:pk>/", views.ProfileActivateView.as_view(), name="activate"),
    path("", views.ProfileDetailView.as_view(), name="profile"),
    path("edit/", views.ProfileView.as_view(), name="editprofile"),
    path("dispatch-login/", views.DispatchLoginView.as_view(), name="dispatch_login"),
    path("member/", views.RegularUpdateView.as_view(), name="regular"),
    path("admin/", views.AdminUpdateView.as_view(), name="admin"),
    path("<int:pk>/add-review", views.ReviewCreateView.as_view(), name="review_create"),
    path("<int:pk>/contact-request/", views.ContactRequestView.as_view(), name="contact_request"),
    path("detail/<int:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("403/", views.ForbiddenView.as_view(), name="403"),
    path("conditions/", views.ConditionsView.as_view(), name="conditions"),
    path("privacy/", views.PrivacyView.as_view(), name="privacy"),
    # path("Freecourses/", views.FreecoursesView.as_view(), name="freecourses"),
    # path("uploadusers/", views.user_upload, name="userupload"),
    # path("uploadposts/", views.posts_upload, name="uploadposts"),
    # path("createusers/", views.UsersCreate.as_view(), name="createusers"),
    # url('^createnewusers$', views.NewUserCreateView.as_view(), name="createnewusers"),
    # path("tenants/", include((tenants_patterns, "syndicma.profiles"), namespace="tenants")),
    path(
        "enterprise/",
        include((enterprise_patterns, "bizanalytic.profiles"), namespace="enterprise"),
    ),
    # path(
    #     "activeyear/",
    #     include((activeyear_patterns, "syndicma.profiles"), namespace="activeyears"),
    # ),
]
