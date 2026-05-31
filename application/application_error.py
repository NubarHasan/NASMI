from dataclasses import dataclass

from application.error_code import ErrorCode
from core.guards import require


@dataclass(frozen=True)
class ApplicationError:
    code: ErrorCode
    message: str

    def __post_init__(self) -> None:
        require(isinstance(self.code, ErrorCode), "code must be an ErrorCode")
        require(bool(self.message.strip()), "message must not be blank")
