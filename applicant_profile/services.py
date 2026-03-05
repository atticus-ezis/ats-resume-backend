import logging

import PyPDF2
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class PDFExtractor:
    def execute(self, pdf_file):
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        except PyPDF2.errors.PdfReadError as exc:
            logger.exception("Failed to read PDF file")
            raise ValidationError("Failed to read PDF file") from exc

        if text == "":
            raise ValidationError("No text found in PDF file")
        return text
