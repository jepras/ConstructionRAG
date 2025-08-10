import os
from io import BytesIO

import pytest
from fastapi import BackgroundTasks
from starlette.datastructures import UploadFile

# Ensure minimal env so importing src.api.* does not fail on settings
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")

from src.api.documents import upload_email_pdf
from src.shared.errors import ErrorCode
from src.utils.exceptions import ValidationError


@pytest.mark.asyncio
async def test_email_upload_invalid_file_type_returns_validation_error():
    # Build a dummy text file to violate PDF-only rule
    upload = UploadFile(file=BytesIO(b"hello"), filename="note.txt")

    with pytest.raises(ValidationError) as exc:
        await upload_email_pdf(
            files=[upload], email="test@example.com", background_tasks=BackgroundTasks()
        )

    assert exc.value.error_code == ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_email_upload_too_many_files_returns_validation_error():
    files = [
        UploadFile(file=BytesIO(b"%PDF-1.4"), filename=f"f{i}.pdf") for i in range(11)
    ]

    with pytest.raises(ValidationError) as exc:
        await upload_email_pdf(
            files=files, email="test@example.com", background_tasks=BackgroundTasks()
        )

    assert exc.value.error_code == ErrorCode.VALIDATION_ERROR
