from django.db import IntegrityError
from rest_framework import serializers

from ai_generation.constants import COMMAND_CHOICES
from ai_generation.models import (
    CONSTRAINT_UNIQUE_TYPE,
    CONSTRAINT_UNIQUE_VERSION_MARKDOWN,
    CONSTRAINT_UNIQUE_VERSION_NAME,
    Document,
    DocumentVersion,
)
from applicant_profile.models import UserContext
from job_profile.models import JobDescription


class MatchContextSerializer(serializers.Serializer):
    user_context_id = serializers.PrimaryKeyRelatedField(
        queryset=UserContext.objects.none(), source="user_context", required=True
    )
    job_description_id = serializers.PrimaryKeyRelatedField(
        queryset=JobDescription.objects.none(), source="job_description", required=True
    )
    command = serializers.ChoiceField(choices=COMMAND_CHOICES, required=True)

    regenerate_version = serializers.BooleanField(required=False, default=False)


class UpdateContentSerializer(serializers.Serializer):
    document_version_id = serializers.PrimaryKeyRelatedField(
        queryset=DocumentVersion.objects.none(),
        source="document_version",
        required=True,
    )
    instructions = serializers.CharField(
        required=False, allow_null=True, max_length=5000
    )

    def validate(self, val):
        if not val.get("instructions"):
            raise serializers.ValidationError("New instructions, must be provided")

        return val


class DocumentVersionHistoryResponseSerializer(serializers.ModelSerializer):
    version_type = serializers.SerializerMethodField()

    class Meta:
        model = DocumentVersion
        fields = ["id", "version_name", "version_type", "updated_at"]
        read_only_fields = ["id", "updated_at", "version_name", "version_type"]

    def get_version_type(self, obj):
        return obj.document.document_type


class DocumentVersionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = ["id", "markdown", "version_name", "document"]
        read_only_fields = ["id"]


class DocumentVersionResponseSerializer(serializers.ModelSerializer):
    """Serializer for DocumentVersion response format used across multiple views."""

    document = serializers.SerializerMethodField()

    class Meta:
        model = DocumentVersion
        fields = ["id", "markdown", "document", "version_name", "updated_at"]
        read_only_fields = ["id", "document", "updated_at"]

    def get_document(self, obj):
        return {
            "id": obj.document.id,
            "type": obj.document.document_type,
        }

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError as e:
            return handle_integrity_error(e)


class DocumentSerializer(serializers.ModelSerializer):
    final_version = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    job_position = serializers.SerializerMethodField()

    def get_company_name(self, obj):
        return obj.job_description.company_name

    def get_job_position(self, obj):
        return obj.job_description.job_position

    def get_final_version(self, obj):
        if obj.final_version:
            return {
                "id": obj.final_version.id,
                "version_name": obj.final_version.version_name,
                "created_at": obj.final_version.created_at,
                "updated_at": obj.final_version.updated_at,
            }
        return None

    def get_versions(self, obj):
        versions = obj.versions.all().order_by("-created_at")
        return [
            {
                "id": version.id,
                "version_name": version.version_name,
                "created_at": version.created_at,
                "updated_at": version.updated_at,
            }
            for version in versions
        ]

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError as e:
            return handle_integrity_error(e)

    class Meta:
        model = Document
        fields = [
            "id",
            "company_name",
            "job_position",
            "document_type",
            "created_at",
            "final_version",
            "versions",
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    job_position = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "document_type",
            "company_name",
            "job_position",
            "created_at",
        ]

    def get_company_name(self, obj):
        return obj.job_description.company_name

    def get_job_position(self, obj):
        return obj.job_description.job_position


def handle_integrity_error(exc):
    msg = str(exc)
    if CONSTRAINT_UNIQUE_VERSION_NAME in msg:
        raise serializers.ValidationError(
            "A version with this name already exists for this document"
        )
    if CONSTRAINT_UNIQUE_VERSION_MARKDOWN in msg:
        raise serializers.ValidationError(
            "A version with this markdown already exists for this document"
        )
    if CONSTRAINT_UNIQUE_TYPE in msg:
        raise serializers.ValidationError(
            "A document with this type already exists for this user, job description and personal info"
        )
    raise serializers.ValidationError(msg)
