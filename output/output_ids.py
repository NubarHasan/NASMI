import uuid
from typing import NewType

OutputDocumentId = NewType("OutputDocumentId", str)

_OUTPUT_DOCUMENT_PREFIX = "odoc_"


def generate_output_document_id() -> OutputDocumentId:
    return OutputDocumentId(f"{_OUTPUT_DOCUMENT_PREFIX}{uuid.uuid4().hex}")


def is_valid_output_document_id(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if not value.startswith(_OUTPUT_DOCUMENT_PREFIX):
        return False
    tail = value[len(_OUTPUT_DOCUMENT_PREFIX) :]
    if len(tail) != 32:
        return False
    return all(c in "0123456789abcdef" for c in tail)
