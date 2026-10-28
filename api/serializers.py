"""Validate input and convert model objects into JSON-ready data."""
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .exceptions import PayloadTooLarge
from .models import Document, QueryLog

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "username", "password"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        try:
            validate_password(attrs["password"], User(username=attrs["username"]))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = Document
        fields = ["id", "title", "content", "uploaded_at", "owner", "file"]
        read_only_fields = ["id", "uploaded_at", "owner"]
        extra_kwargs = {"title": {"required": False}, "content": {"required": False}}

    def validate(self, attrs):
        uploaded_file = attrs.pop("file", None)
        if uploaded_file is not None:
            if "content" in attrs:
                raise serializers.ValidationError("Send either file or content, not both.")
            if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
                raise PayloadTooLarge()
            if Path(uploaded_file.name).suffix.lower() not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                raise serializers.ValidationError({"file": "Allowed types: .txt, .md, .csv."})
            try:
                content = uploaded_file.read(settings.MAX_UPLOAD_SIZE + 1).decode("utf-8")
            except UnicodeDecodeError:
                raise serializers.ValidationError({"file": "File must contain UTF-8 text."})
            if "\x00" in content:
                raise serializers.ValidationError({"file": "Binary content is not allowed."})
            if not content.strip():
                raise serializers.ValidationError({"file": "File must contain non-blank text."})
            attrs["content"] = content
            if "title" not in attrs:
                attrs["title"] = uploaded_file.name
        # PATCH may omit fields; creation and PUT require both (or a file).
        if not self.partial:
            for field in ("title", "content"):
                if field not in attrs:
                    raise serializers.ValidationError({field: "This field is required."})
        if "title" in attrs and len(attrs["title"]) > 255:
            raise serializers.ValidationError({"title": "Use at most 255 characters."})
        return attrs


class QueryLogSerializer(serializers.ModelSerializer):
    query_text = serializers.CharField(max_length=1000)

    class Meta:
        model = QueryLog
        fields = ["id", "query_text", "result_summary", "created_at", "user"]
        read_only_fields = ["id", "result_summary", "created_at", "user"]
