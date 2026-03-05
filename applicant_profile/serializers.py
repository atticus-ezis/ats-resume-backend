from django.db import IntegrityError
from rest_framework import serializers

from resume_builder.utils import compute_context_hash

from .models import CONSTRAINT_UNIQUE_CONTEXT, CONSTRAINT_UNIQUE_NAME, UserContext


def _integrity_error_to_validation_error(exc, validated_data, user):
    """Convert DB IntegrityError to ValidationError with a clear message."""
    message = str(exc)
    if CONSTRAINT_UNIQUE_NAME in message:
        name = validated_data.get("name")
        detail = (
            f"You already have a context with this name: {name}."
            if name
            else "You already have a context with this name."
        )
        raise serializers.ValidationError(detail)
    if CONSTRAINT_UNIQUE_CONTEXT in message:
        context_hash = (
            compute_context_hash(validated_data.get("context"))
            if validated_data.get("context") is not None
            else None
        )
        existing = (
            UserContext.objects.filter(user=user, context_hash=context_hash).first()
            if context_hash
            else None
        )
        existing_name = existing.name if existing else None
        detail = (
            f"This content already exists under the name: {existing_name}."
            if existing_name
            else "This content already exists."
        )
        raise serializers.ValidationError(detail)
    raise serializers.ValidationError(
        "A context with this name or content already exists for your account."
    )


class UserContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserContext
        fields = ["id", "name", "context", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user:
            return attrs

        user = request.user
        name = attrs.get("name")

        qs = UserContext.objects.filter(user=user)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if name is not None and qs.filter(name=name).exists():
            raise serializers.ValidationError({"name": "This name already exists."})
        # Duplicate context (same context_hash) is handled in the view: it returns
        # the existing instance with 200 instead of raising here.
        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError as e:
            request = self.context.get("request")
            user = request.user if request else None
            _integrity_error_to_validation_error(e, validated_data, user)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError as e:
            _integrity_error_to_validation_error(e, validated_data, instance.user)


class UserContextListSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserContext
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "name", "created_at", "updated_at"]


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    name = serializers.CharField(required=True)

    def validate_file(self, value):
        if value.content_type != "application/pdf":
            raise serializers.ValidationError("File must be a PDF")

        if not value.name.endswith(".pdf"):
            raise serializers.ValidationError("File must be a PDF")

        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("File must be less than 10MB")

        file_signature = value.read(4)
        value.seek(0)

        if file_signature != b"%PDF":
            raise serializers.ValidationError("Invalid PDF file format")

        return value
