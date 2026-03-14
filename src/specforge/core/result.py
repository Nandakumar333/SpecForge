"""Result[T, E] monad — Ok and Err variants for recoverable errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True)
class Ok(Generic[T]):
    """Success variant carrying a value."""

    value: T

    @property
    def ok(self) -> bool:
        return True

    def map(self, fn: Callable[[T], U]) -> Ok[U]:
        return Ok(fn(self.value))

    def bind(self, fn: Callable[[T], Result]) -> Result:
        return fn(self.value)

    def unwrap_or(self, default: T) -> T:  # noqa: ARG002
        return self.value


@dataclass(frozen=True)
class Err(Generic[E]):
    """Failure variant carrying an error."""

    error: E

    @property
    def ok(self) -> bool:
        return False

    def map(self, fn: Callable) -> Err[E]:  # noqa: ARG002
        return self

    def bind(self, fn: Callable) -> Err[E]:  # noqa: ARG002
        return self

    def unwrap_or(self, default: T) -> T:
        return default


Result = Ok[T] | Err[E]
