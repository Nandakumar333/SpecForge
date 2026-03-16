"""Unit tests for BoundaryAnalyzer — cross-service boundary ambiguity detection."""

from __future__ import annotations

from specforge.core.boundary_analyzer import BoundaryAnalyzer
from specforge.core.clarification_models import AmbiguityMatch
from specforge.core.config import REMAP_QUESTION_TOPICS


def _personal_finance_manifest() -> dict:
    """PersonalFinance manifest with 4 services.

    'categories' is shared by ledger-service and planning-service
    but NOT by identity-service or notification-service, so it passes
    the ubiquity threshold (2/4 = 0.5 ≤ 0.6).
    """
    return {
        "schema_version": "1.0",
        "architecture": "microservice",
        "project_description": "Personal Finance Tracker",
        "domain": "finance",
        "features": [
            {
                "id": "001",
                "name": "auth",
                "display_name": "Authentication",
                "description": "User login and session management",
                "priority": "P0",
                "category": "foundation",
                "service": "identity-service",
            },
            {
                "id": "002",
                "name": "accounts",
                "display_name": "Account Management",
                "description": (
                    "Track bank accounts, credit cards, and investment "
                    "accounts with balances and categories"
                ),
                "priority": "P1",
                "category": "core",
                "service": "ledger-service",
            },
            {
                "id": "003",
                "name": "transactions",
                "display_name": "Transaction Tracking",
                "description": (
                    "Record income, expenses, and transfers between "
                    "accounts with categories and tags"
                ),
                "priority": "P1",
                "category": "core",
                "service": "ledger-service",
            },
            {
                "id": "004",
                "name": "budgets",
                "display_name": "Budget Planning",
                "description": (
                    "Create monthly budgets by categories and track "
                    "spending against budget limits"
                ),
                "priority": "P1",
                "category": "core",
                "service": "planning-service",
            },
            {
                "id": "005",
                "name": "goals",
                "display_name": "Financial Goals",
                "description": (
                    "Set savings goals with target amounts and track "
                    "progress toward financial objectives"
                ),
                "priority": "P2",
                "category": "engagement",
                "service": "planning-service",
            },
            {
                "id": "006",
                "name": "bills",
                "display_name": "Bill Management",
                "description": (
                    "Track recurring bills and payments with due dates"
                ),
                "priority": "P2",
                "category": "core",
                "service": "planning-service",
            },
            {
                "id": "007",
                "name": "alerts",
                "display_name": "Alert Delivery",
                "description": "Send email and push alerts to users",
                "priority": "P2",
                "category": "engagement",
                "service": "notification-service",
            },
        ],
        "services": [
            {
                "name": "Identity Service",
                "slug": "identity-service",
                "features": ["001"],
                "rationale": "Auth isolation",
                "communication": [],
            },
            {
                "name": "Ledger Service",
                "slug": "ledger-service",
                "features": ["002", "003"],
                "rationale": "Core financial tracking",
                "communication": [
                    {
                        "target": "planning-service",
                        "pattern": "async-events",
                        "required": False,
                        "description": "Transaction categorization events",
                    }
                ],
            },
            {
                "name": "Planning Service",
                "slug": "planning-service",
                "features": ["004", "005", "006"],
                "rationale": "Financial planning",
                "communication": [
                    {
                        "target": "ledger-service",
                        "pattern": "sync-rest",
                        "required": True,
                        "description": "Read transaction data",
                    }
                ],
            },
            {
                "name": "Notification Service",
                "slug": "notification-service",
                "features": ["007"],
                "rationale": "Alert delivery",
                "communication": [],
            },
        ],
        "events": [],
    }


def _single_service_manifest() -> dict:
    """Manifest with only one service — no boundary ambiguity possible."""
    return {
        "schema_version": "1.0",
        "architecture": "monolithic",
        "project_description": "Simple App",
        "domain": "general",
        "features": [
            {
                "id": "001",
                "name": "core",
                "display_name": "Core",
                "description": "Core functionality with categories",
                "priority": "P1",
                "category": "core",
                "service": "app-service",
            },
        ],
        "services": [
            {
                "name": "App Service",
                "slug": "app-service",
                "features": ["001"],
                "rationale": "Monolith",
                "communication": [],
            },
        ],
        "events": [],
    }


def _three_service_manifest() -> dict:
    """Manifest with 5 services; 'notifications' shared by exactly 2."""
    return {
        "schema_version": "1.0",
        "architecture": "microservice",
        "project_description": "Multi-Service App",
        "domain": "general",
        "features": [
            {
                "id": "001",
                "name": "users",
                "display_name": "User Management",
                "description": "Manage users with notifications and alerts",
                "priority": "P1",
                "category": "core",
                "service": "user-service",
            },
            {
                "id": "002",
                "name": "orders",
                "display_name": "Order Processing",
                "description": "Process orders with notifications for status updates",
                "priority": "P1",
                "category": "core",
                "service": "order-service",
            },
            {
                "id": "003",
                "name": "billing",
                "display_name": "Billing",
                "description": "Handle billing and payment invoicing",
                "priority": "P1",
                "category": "core",
                "service": "billing-service",
            },
            {
                "id": "004",
                "name": "inventory",
                "display_name": "Inventory",
                "description": "Track warehouse inventory levels",
                "priority": "P1",
                "category": "core",
                "service": "inventory-service",
            },
            {
                "id": "005",
                "name": "shipping",
                "display_name": "Shipping",
                "description": "Manage shipment logistics and delivery",
                "priority": "P1",
                "category": "core",
                "service": "shipping-service",
            },
        ],
        "services": [
            {
                "name": "User Service",
                "slug": "user-service",
                "features": ["001"],
                "rationale": "User management",
                "communication": [],
            },
            {
                "name": "Order Service",
                "slug": "order-service",
                "features": ["002"],
                "rationale": "Order processing",
                "communication": [],
            },
            {
                "name": "Billing Service",
                "slug": "billing-service",
                "features": ["003"],
                "rationale": "Billing",
                "communication": [],
            },
            {
                "name": "Inventory Service",
                "slug": "inventory-service",
                "features": ["004"],
                "rationale": "Inventory",
                "communication": [],
            },
            {
                "name": "Shipping Service",
                "slug": "shipping-service",
                "features": ["005"],
                "rationale": "Shipping",
                "communication": [],
            },
        ],
        "events": [],
    }


def _remap_manifest() -> dict:
    """Manifest with previous_architecture differing from architecture."""
    m = _personal_finance_manifest()
    m["previous_architecture"] = "monolithic"
    return m


class TestAnalyzeSharedConcepts:
    """BoundaryAnalyzer.analyze() detects shared concepts across services."""

    def test_detects_categories_shared_between_services(self) -> None:
        manifest = _personal_finance_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        matches = analyzer.analyze("ledger-service")
        texts = [m.text.lower() for m in matches]
        assert any("categor" in t for t in texts)

    def test_matches_are_service_boundary_category(self) -> None:
        manifest = _personal_finance_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        matches = analyzer.analyze("ledger-service")
        assert len(matches) >= 1
        for m in matches:
            assert m.category == "service_boundary"

    def test_returns_ambiguity_match_instances(self) -> None:
        manifest = _personal_finance_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        matches = analyzer.analyze("ledger-service")
        for m in matches:
            assert isinstance(m, AmbiguityMatch)

    def test_single_service_returns_empty(self) -> None:
        manifest = _single_service_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        matches = analyzer.analyze("app-service")
        assert matches == ()


class TestAnalyzeThreeServices:
    """Boundary analysis with multiple services sharing a concept."""

    def test_detects_notifications_shared_between_two(self) -> None:
        manifest = _three_service_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        matches = analyzer.analyze("user-service")
        texts = [m.text.lower() for m in matches]
        assert any("notif" in t for t in texts)

    def test_includes_boundary_from_sharing_service(self) -> None:
        manifest = _three_service_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        # Both user-service and order-service share "notification"
        user_matches = analyzer.analyze("user-service")
        order_matches = analyzer.analyze("order-service")
        assert len(user_matches) >= 1
        assert len(order_matches) >= 1


class TestKeywordExtraction:
    """Keyword extraction filters stop words and applies stemming."""

    def test_stop_words_filtered(self) -> None:
        manifest = _personal_finance_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        matches = analyzer.analyze("ledger-service")
        # Common stop words like "the", "and", "with" should not appear as
        # the primary matched text
        for m in matches:
            assert m.text.lower() not in ("the", "and", "with", "a", "or")

    def test_stemming_matches_variants(self) -> None:
        # "categories" (plural) in feature descriptions → stemmed to "category"
        # shared by ledger-service and planning-service (2/4 ≤ 0.6 threshold)
        manifest = _personal_finance_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        matches = analyzer.analyze("ledger-service")
        texts = [m.text.lower() for m in matches]
        assert any("categor" in t for t in texts)


class TestDetectRemap:
    """BoundaryAnalyzer.detect_remap() checks architecture transitions."""

    def test_true_when_previous_differs(self) -> None:
        manifest = _remap_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        assert analyzer.detect_remap(manifest) is True

    def test_false_when_no_previous(self) -> None:
        manifest = _personal_finance_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        assert analyzer.detect_remap(manifest) is False

    def test_false_when_same_architecture(self) -> None:
        manifest = _personal_finance_manifest()
        manifest["previous_architecture"] = "microservice"
        analyzer = BoundaryAnalyzer(manifest)
        assert analyzer.detect_remap(manifest) is False


class TestGetRemapQuestions:
    """BoundaryAnalyzer.get_remap_questions() for architecture transitions."""

    def test_generates_questions_for_all_topics(self) -> None:
        manifest = _remap_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        questions = analyzer.get_remap_questions("ledger-service")
        assert len(questions) >= len(REMAP_QUESTION_TOPICS)

    def test_returns_at_least_five_questions(self) -> None:
        manifest = _remap_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        questions = analyzer.get_remap_questions("ledger-service")
        assert len(questions) >= 5

    def test_all_are_ambiguity_matches(self) -> None:
        manifest = _remap_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        questions = analyzer.get_remap_questions("ledger-service")
        for q in questions:
            assert isinstance(q, AmbiguityMatch)

    def test_covers_each_remap_topic(self) -> None:
        manifest = _remap_manifest()
        analyzer = BoundaryAnalyzer(manifest)
        questions = analyzer.get_remap_questions("ledger-service")
        question_texts = [q.text.lower() for q in questions]
        for topic in REMAP_QUESTION_TOPICS:
            # Each topic keyword should appear in at least one question
            assert any(
                topic.split()[0].lower() in t for t in question_texts
            ), f"Topic '{topic}' not covered in remap questions"
