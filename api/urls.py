from django.urls import path

from .views import (
    DocumentDetailView,
    DocumentListCreateView,
    LoginView,
    LogoutView,
    QueryCreateView,
    QueryListView,
    RegisterView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("documents", DocumentListCreateView.as_view(), name="documents"),
    path("documents/<int:pk>", DocumentDetailView.as_view(), name="document-detail"),
    path("query", QueryCreateView.as_view(), name="query"),
    path("queries", QueryListView.as_view(), name="queries"),
]
