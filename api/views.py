"""HTTP endpoints: authentication, owner-scoped documents, and query history."""
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, QueryLog, UserSession
from .serializers import DocumentSerializer, LoginSerializer, QueryLogSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request=request, **serializer.validated_data)
        if user is None:
            raise AuthenticationFailed("Invalid username or password.")
        session = UserSession.objects.create(
            user=user,
            token=secrets.token_hex(32),
            expires_at=timezone.now() + timedelta(hours=settings.TOKEN_LIFETIME_HOURS),
        )
        return Response({"token": session.token, "expires_at": session.expires_at, "user_id": user.pk})


class LogoutView(APIView):
    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DocumentSerializer

    def get_object(self):
        # Assignment deliberately requires 404 for another user's GET but 403 for DELETE.
        if self.request.method in ("GET", "HEAD"):
            return get_object_or_404(Document, pk=self.kwargs["pk"], owner=self.request.user)
        document = get_object_or_404(Document, pk=self.kwargs["pk"])
        if document.owner_id != self.request.user.pk:
            raise PermissionDenied("You do not own this document.")
        return document


class QueryCreateView(generics.CreateAPIView):
    serializer_class = QueryLogSerializer

    def perform_create(self, serializer):
        text = serializer.validated_data["query_text"]
        matches = Document.objects.filter(owner=self.request.user).filter(
            Q(title__icontains=text) | Q(content__icontains=text)
        )
        total = matches.count()
        titles = list(matches.values_list("title", flat=True)[:5])
        summary = f"Found {total} matching document(s)."
        if titles:
            summary += " Titles (up to 5): " + "; ".join(titles)
        serializer.save(user=self.request.user, result_summary=summary)


class QueryListView(generics.ListAPIView):
    serializer_class = QueryLogSerializer

    def get_queryset(self):
        return QueryLog.objects.filter(user=self.request.user)
