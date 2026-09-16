class DocumentError(ValueError):
    """The supplied document cannot be processed reliably."""


class OCRDependencyError(DocumentError):
    """A required local OCR executable, language model or renderer is unavailable."""


class OCRProcessingError(DocumentError):
    """OCR failed; partial text must not be reported as a successful document."""


class ExtractionError(ValueError):
    """Structured extraction failed validation."""


class ProviderError(RuntimeError):
    """An external extraction provider failed; do not expose credentials or payloads."""
