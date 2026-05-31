from dataclasses import dataclass
from typing import Generic, TypeVar

from application.application_error import ApplicationError

T = TypeVar("T")


@dataclass(frozen=True)
class Success(Generic[T]):
    value: T


@dataclass(frozen=True)
class Failure:
    error: ApplicationError


Result = Success[T] | Failure
