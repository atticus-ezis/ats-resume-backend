from django.http import HttpResponse
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_generation.models import Document, DocumentVersion
from ai_generation.serializers import (
    DocumentListSerializer,
    DocumentSerializer,
    DocumentVersionHistoryResponseSerializer,
    DocumentVersionResponseSerializer,
    MatchContextSerializer,
    UpdateContentSerializer,
)
from ai_generation.services import (  # noqa: F401
    APICall,
    DownloadMarkdown,
    UpdateContent,
)
from applicant_profile.models import UserContext
from job_profile.models import JobDescription
from resume_builder.pagination import CustomPageNumberPagination

from .tasks import generate_resume_and_cover_letter, update_content

# Create your views here.

# frontend must match context models


# needs celery and redis
class GenerateResumeAndCoverLetterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_data = self.get_context(request)
        task = generate_resume_and_cover_letter.delay(
            user_context_id=request_data["user_context"].id,
            job_description_id=request_data["job_description"].id,
            command=request_data["command"],
            regenerate_version=request_data.get("regenerate_version", False),
            user_id=request.user.id,
        )
        return Response({"task_id": task.id}, status=status.HTTP_200_OK)

    def get_context(self, request):
        # extract data
        serializer = MatchContextSerializer(data=request.data)

        serializer.fields["user_context_id"].queryset = UserContext.objects.filter(
            user=request.user
        )
        serializer.fields[
            "job_description_id"
        ].queryset = JobDescription.objects.filter(user=request.user)

        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class UpdateContentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpdateContentSerializer(data=request.data)
        serializer.fields[
            "document_version_id"
        ].queryset = DocumentVersion.objects.filter(document__user=request.user)
        serializer.is_valid(raise_exception=True)
        document_version = serializer.validated_data["document_version"]
        instructions = serializer.validated_data["instructions"]

        task = update_content.delay(
            document_version_id=document_version.id, instructions=instructions
        )
        return Response({"task_id": task.id}, status=status.HTTP_200_OK)


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["job_description__company_name", "job_description__job_position"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DocumentVersionHistory(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentVersionHistoryResponseSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ["-updated_at"]

    def get_queryset(self):
        queryset = DocumentVersion.objects.filter(
            document__user=self.request.user
        ).select_related("document")
        document_id = self.request.query_params.get("document")
        if document_id:
            queryset = queryset.filter(document_id=document_id)
        return queryset


class DocumentVersionViewSet(viewsets.ModelViewSet):
    """
    List/retrieve document versions. Filter by document: ?document=<document_id>
    When document is specified, uses DocumentVersionResponseSerializer.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DocumentVersionResponseSerializer
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = DocumentVersion.objects.filter(
            document__user=self.request.user
        ).select_related("document")
        return queryset

    @action(detail=True, methods=["get"], name="pdf_download", url_path="pdf")
    def pdf_download(self, request, pk=None):
        document_version = self.get_object()
        markdown = document_version.markdown
        file_name = document_version.version_name

        try:
            pdf_bytes = DownloadMarkdown(markdown, request).execute()
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{file_name}.pdf"'
            return response
        except Exception as e:
            return Response(
                {"message": f"Failed to generate PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
