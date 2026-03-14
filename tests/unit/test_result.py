"""Unit tests for Result[T, E] — Ok and Err variants."""

from specforge.core.result import Err, Ok


class TestOk:
    def test_ok_creation(self) -> None:
        result = Ok(42)
        assert result.value == 42

    def test_ok_property_is_true(self) -> None:
        assert Ok("hello").ok is True

    def test_ok_map_transforms_value(self) -> None:
        result = Ok(5).map(lambda x: x * 2)
        assert isinstance(result, Ok)
        assert result.value == 10

    def test_ok_bind_chains(self) -> None:
        result = Ok(5).bind(lambda x: Ok(x + 1))
        assert isinstance(result, Ok)
        assert result.value == 6

    def test_ok_bind_to_err(self) -> None:
        result = Ok(5).bind(lambda _: Err("oops"))
        assert isinstance(result, Err)
        assert result.error == "oops"

    def test_ok_unwrap_or_returns_value(self) -> None:
        assert Ok(42).unwrap_or(0) == 42


class TestErr:
    def test_err_creation(self) -> None:
        result = Err("something failed")
        assert result.error == "something failed"

    def test_err_property_is_false(self) -> None:
        assert Err("fail").ok is False

    def test_err_map_is_noop(self) -> None:
        result = Err("fail").map(lambda x: x * 2)
        assert isinstance(result, Err)
        assert result.error == "fail"

    def test_err_bind_is_noop(self) -> None:
        result = Err("fail").bind(lambda x: Ok(x))
        assert isinstance(result, Err)
        assert result.error == "fail"

    def test_err_unwrap_or_returns_default(self) -> None:
        assert Err("fail").unwrap_or(99) == 99
