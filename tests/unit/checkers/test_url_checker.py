"""Unit tests for UrlChecker."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.checkers.url_checker import UrlChecker
from specforge.core.quality_models import CheckLevel, ErrorCategory


class TestUrlCheckerApplicability:
    """Verify architecture filtering."""

    def test_applicable_for_microservice(self) -> None:
        checker = UrlChecker()
        assert checker.is_applicable("microservice") is True

    def test_not_applicable_for_monolithic(self) -> None:
        checker = UrlChecker()
        assert checker.is_applicable("monolithic") is False

    def test_not_applicable_for_modular_monolith(self) -> None:
        checker = UrlChecker()
        assert checker.is_applicable("modular-monolith") is False

    def test_name_is_url(self) -> None:
        checker = UrlChecker()
        assert checker.name == "url"

    def test_category_is_boundary(self) -> None:
        checker = UrlChecker()
        assert checker.category == ErrorCategory.BOUNDARY

    def test_levels_is_task(self) -> None:
        checker = UrlChecker()
        assert checker.levels == (CheckLevel.TASK,)


class TestUrlCheckerExecution:
    """Verify URL detection logic."""

    def test_hardcoded_url_detected(self, tmp_path: Path) -> None:
        """A hardcoded service URL should be flagged."""
        f = tmp_path / "config.py"
        f.write_text('SERVICE_URL = "http://orders-service.prod:8080/api"\n')

        checker = UrlChecker()
        result = checker.check([f], object())
        assert result.ok
        cr = result.value
        assert cr.passed is False
        assert len(cr.error_details) > 0
        assert "Hardcoded URL" in cr.error_details[0].message

    def test_localhost_ignored(self, tmp_path: Path) -> None:
        """localhost URLs should not be flagged."""
        f = tmp_path / "dev.py"
        f.write_text('URL = "http://localhost:3000/api"\n')

        checker = UrlChecker()
        result = checker.check([f], object())
        assert result.ok
        assert result.value.passed is True

    def test_127_0_0_1_ignored(self, tmp_path: Path) -> None:
        """127.0.0.1 URLs should not be flagged."""
        f = tmp_path / "dev.py"
        f.write_text('URL = "http://127.0.0.1:5000/test"\n')

        checker = UrlChecker()
        result = checker.check([f], object())
        assert result.ok
        assert result.value.passed is True

    def test_example_com_ignored(self, tmp_path: Path) -> None:
        """example.com URLs should not be flagged."""
        f = tmp_path / "docs.py"
        f.write_text('SAMPLE = "https://example.com/api/v1"\n')

        checker = UrlChecker()
        result = checker.check([f], object())
        assert result.ok
        assert result.value.passed is True

    def test_comment_line_ignored(self, tmp_path: Path) -> None:
        """URLs in comment lines should not be flagged."""
        f = tmp_path / "main.py"
        f.write_text('# see http://orders-service.prod:8080/api\nx = 1\n')

        checker = UrlChecker()
        result = checker.check([f], object())
        assert result.ok
        assert result.value.passed is True

    def test_clean_file_passes(self, tmp_path: Path) -> None:
        """A file without any URLs should pass."""
        f = tmp_path / "clean.py"
        f.write_text("def add(a, b):\n    return a + b\n")

        checker = UrlChecker()
        result = checker.check([f], object())
        assert result.ok
        assert result.value.passed is True

    def test_test_domain_ignored(self, tmp_path: Path) -> None:
        """test.com URLs should not be flagged."""
        f = tmp_path / "test_config.py"
        f.write_text('URL = "http://test.com/api"\n')

        checker = UrlChecker()
        result = checker.check([f], object())
        assert result.ok
        assert result.value.passed is True
