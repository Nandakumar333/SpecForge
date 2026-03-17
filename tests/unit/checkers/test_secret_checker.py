"""Tests for SecretChecker."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.checkers.secret_checker import SecretChecker, _shannon_entropy
from specforge.core.quality_models import CheckLevel, ErrorCategory


# ── Helpers ───────────────────────────────────────────────────────────


def _write_file(
    tmp_path: Path, name: str, content: str, *, subdir: str = ""
) -> Path:
    """Write a file and return its path."""
    if subdir:
        d = tmp_path / subdir
        d.mkdir(parents=True, exist_ok=True)
        p = d / name
    else:
        p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ── Properties ────────────────────────────────────────────────────────


class TestProperties:
    def test_name(self) -> None:
        assert SecretChecker().name == "secret"

    def test_category_is_security(self) -> None:
        assert SecretChecker().category == ErrorCategory.SECURITY

    def test_levels(self) -> None:
        assert SecretChecker().levels == (CheckLevel.TASK,)

    def test_applicable_all(self) -> None:
        checker = SecretChecker()
        assert checker.is_applicable("monolithic")
        assert checker.is_applicable("microservices")


# ── Pattern detection ─────────────────────────────────────────────────


class TestPatternDetection:
    def test_aws_key_detected(self, tmp_path: Path) -> None:
        content = 'aws_key = "AKIAIOSFODNN7EXAMPLE"\n'
        fpath = _write_file(tmp_path, "config.py", content)
        result = SecretChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False
        codes = [d.code for d in result.value.error_details]
        assert "aws_access_key" in codes

    def test_jwt_detected(self, tmp_path: Path) -> None:
        jwt = (
            "eyJhbGciOiJIUzI1NiJ9"
            ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
            ".abc123def456"
        )
        content = f"token = '{jwt}'\n"
        fpath = _write_file(tmp_path, "auth.py", content)
        result = SecretChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False
        codes = [d.code for d in result.value.error_details]
        assert "jwt_token" in codes

    def test_generic_api_key_detected(self, tmp_path: Path) -> None:
        content = 'api_key = "sk-1234567890abcdef1234567890abcdef"\n'
        fpath = _write_file(tmp_path, "settings.py", content)
        result = SecretChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False
        codes = [d.code for d in result.value.error_details]
        assert "generic_api_key" in codes or "generic_secret" in codes

    def test_normal_code_no_false_positive(self, tmp_path: Path) -> None:
        content = (
            "secret_count = 5\n"
            "password_length = 12\n"
            "api_version = 3\n"
            "x = 42\n"
        )
        fpath = _write_file(tmp_path, "clean.py", content)
        result = SecretChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is True
        assert result.value.error_details == ()


# ── Test fixture exemption ────────────────────────────────────────────


class TestFixtureExemption:
    def test_test_dir_exempted(self, tmp_path: Path) -> None:
        content = 'aws_key = "AKIAIOSFODNN7EXAMPLE"\n'
        fpath = _write_file(
            tmp_path, "test_config.py", content, subdir="tests"
        )
        result = SecretChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is True

    def test_fixture_dir_exempted(self, tmp_path: Path) -> None:
        content = 'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklm"\n'
        fpath = _write_file(
            tmp_path, "sample.py", content, subdir="fixtures"
        )
        result = SecretChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is True


# ── Entropy detection ─────────────────────────────────────────────────


class TestEntropyDetection:
    def test_high_entropy_string_detected(self, tmp_path: Path) -> None:
        high_entropy = "aB3$kL9!mN2@pQ5^rT8&vX1"
        content = f'value = "{high_entropy}"\n'
        fpath = _write_file(tmp_path, "data.py", content)
        result = SecretChecker().check([fpath], None)
        assert result.ok
        has_entropy = any(
            d.code == "high-entropy"
            for d in result.value.error_details
        )
        assert has_entropy

    def test_low_entropy_passes(self, tmp_path: Path) -> None:
        content = 'value = "aaaaaaaaaaaaaaaaaaaaaa"\n'
        fpath = _write_file(tmp_path, "boring.py", content)
        result = SecretChecker().check([fpath], None)
        assert result.ok
        has_entropy = any(
            d.code == "high-entropy"
            for d in result.value.error_details
        )
        assert not has_entropy


# ── Shannon entropy unit tests ────────────────────────────────────────


class TestShannonEntropy:
    def test_empty_string(self) -> None:
        assert _shannon_entropy("") == 0.0

    def test_single_char_repeated(self) -> None:
        assert _shannon_entropy("aaaa") == 0.0

    def test_two_equal_chars(self) -> None:
        result = _shannon_entropy("ab")
        assert abs(result - 1.0) < 0.01

    def test_high_entropy(self) -> None:
        import string
        result = _shannon_entropy(string.printable[:40])
        assert result > 4.0
