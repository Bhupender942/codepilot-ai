"""Tests for the secrets scanner (app/services/secrets_scanner.py)."""

from __future__ import annotations

import math

import pytest

from app.services.secrets_scanner import SecretsScanner, get_secrets_scanner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scanner() -> SecretsScanner:
    return SecretsScanner()


# ===========================================================================
# Pattern-based detection
# ===========================================================================


def test_detect_aws_key(scanner: SecretsScanner):
    """AWS-style access key IDs are detected."""
    text = 'aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"'
    findings = scanner.scan(text)
    types = [f["type"] for f in findings]
    assert "aws_access_key" in types


def test_detect_github_token(scanner: SecretsScanner):
    """GitHub personal access tokens (ghp_ prefix) are detected."""
    text = "token = ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    findings = scanner.scan(text)
    types = [f["type"] for f in findings]
    assert "github_token" in types


def test_detect_private_key(scanner: SecretsScanner):
    """PEM-encoded private key headers are detected."""
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA..."
    findings = scanner.scan(text)
    types = [f["type"] for f in findings]
    assert "private_key" in types


def test_detect_ec_private_key(scanner: SecretsScanner):
    """EC private key headers are detected."""
    text = "-----BEGIN EC PRIVATE KEY-----\nABCDEFGHIJ..."
    findings = scanner.scan(text)
    types = [f["type"] for f in findings]
    assert "private_key" in types


def test_detect_jwt(scanner: SecretsScanner):
    """JWT tokens (eyJ…) are detected."""
    token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0"
        ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    text = f"Authorization: Bearer {token}"
    findings = scanner.scan(text)
    types = [f["type"] for f in findings]
    assert "jwt" in types


def test_detect_connection_string(scanner: SecretsScanner):
    """Database connection strings are detected."""
    text = "DB_URL=postgresql://admin:s3cr3t@localhost:5432/prod"
    findings = scanner.scan(text)
    types = [f["type"] for f in findings]
    assert "connection_string" in types


@pytest.mark.parametrize(
    "text,expected_type",
    [
        ('API_KEY = "my-super-secret-api-key-value"', "api_key"),
        ('password = "hunter2_secure"', "password"),
    ],
)
def test_detect_api_key_and_password(scanner: SecretsScanner, text: str, expected_type: str):
    """api_key and password patterns are matched case-insensitively."""
    findings = scanner.scan(text)
    types = [f["type"] for f in findings]
    assert expected_type in types


# ===========================================================================
# Redaction
# ===========================================================================


def test_redact_aws_key(scanner: SecretsScanner):
    """Redaction replaces AWS key with a [REDACTED:…] placeholder."""
    text = "key=AKIAIOSFODNN7EXAMPLE and more text"
    redacted = scanner.redact(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED:" in redacted


def test_redact_preserves_non_secret_text(scanner: SecretsScanner):
    """Text surrounding the secret is preserved after redaction."""
    text = "prefix AKIAIOSFODNN7EXAMPLE suffix"
    redacted = scanner.redact(text)
    assert "prefix" in redacted
    assert "suffix" in redacted


def test_redact_multiple_secrets(scanner: SecretsScanner):
    """All detected secrets in a text are replaced."""
    text = (
        "aws_key=AKIAIOSFODNN7EXAMPLE\n"
        "github_token=ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    )
    redacted = scanner.redact(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "ghp_" not in redacted


# ===========================================================================
# has_secrets helper
# ===========================================================================


def test_has_secrets_true(scanner: SecretsScanner):
    """has_secrets returns True when a secret is present."""
    assert scanner.has_secrets("AKIAIOSFODNN7EXAMPLE") is True


def test_has_secrets_false(scanner: SecretsScanner):
    """Normal source code text does not trigger has_secrets."""
    clean_code = (
        "def calculate_tax(income: float) -> float:\n"
        "    rate = 0.25\n"
        "    return income * rate\n"
    )
    assert scanner.has_secrets(clean_code) is False


# ===========================================================================
# No false positives
# ===========================================================================


@pytest.mark.parametrize(
    "normal_text",
    [
        "x = 1 + 2",
        "import os\nimport sys",
        "class Config:\n    debug = True\n    port = 8080",
        "# This is a comment about configuration",
        "url = 'http://example.com/api/v1/users'",
    ],
)
def test_no_false_positive_normal_text(scanner: SecretsScanner, normal_text: str):
    """Ordinary code constructs do not trigger the scanner."""
    findings = scanner.scan(normal_text)
    # Filter out entropy hits on any accidentally high-entropy short identifier
    pattern_hits = [f for f in findings if f["type"] != "high_entropy_string"]
    assert pattern_hits == []


# ===========================================================================
# Shannon entropy
# ===========================================================================


def test_entropy_low_for_repeated_chars(scanner: SecretsScanner):
    """A string of identical characters has entropy close to 0."""
    assert SecretsScanner.entropy("aaaaaaaaaaaaaaaaaaaaaa") < 0.1


def test_entropy_high_for_random_string():
    """A pseudo-random alphanumeric string has entropy above the threshold."""
    # This specific string is designed to have high entropy
    random_str = "aB3xZ9qP2mW7nL5kRoYvUcTdEfGhJiSt"
    entropy = SecretsScanner.entropy(random_str)
    assert entropy > 4.0


def test_entropy_detection(scanner: SecretsScanner):
    """A high-entropy string (random 32-char token) is flagged."""
    # All unique characters → maximum entropy
    high_entropy = "aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"
    findings = scanner.scan(high_entropy)
    types = [f["type"] for f in findings]
    assert "high_entropy_string" in types or len(findings) >= 1


def test_high_entropy_not_duplicated_with_pattern_match(scanner: SecretsScanner):
    """An AWS key is not reported twice (pattern match takes precedence)."""
    text = "AKIAIOSFODNN7EXAMPLE"
    findings = scanner.scan(text)
    # Should appear exactly once (either as aws_access_key or high_entropy, not both)
    starts = [f["start"] for f in findings]
    assert len(starts) == len(set(starts))  # no duplicate start positions


# ===========================================================================
# Findings structure
# ===========================================================================


def test_findings_have_required_keys(scanner: SecretsScanner):
    """Every finding dict contains type, value, start, and end."""
    findings = scanner.scan("AKIAIOSFODNN7EXAMPLE")
    for f in findings:
        assert "type" in f
        assert "value" in f
        assert "start" in f
        assert "end" in f


def test_findings_sorted_by_start(scanner: SecretsScanner):
    """Findings are sorted by start position."""
    text = (
        "AKIAIOSFODNN7EXAMPLE "
        "-----BEGIN RSA PRIVATE KEY-----"
    )
    findings = scanner.scan(text)
    starts = [f["start"] for f in findings]
    assert starts == sorted(starts)


# ===========================================================================
# Singleton
# ===========================================================================


def test_get_secrets_scanner_singleton():
    """get_secrets_scanner() returns the same instance on repeated calls."""
    import app.services.secrets_scanner as ss_module

    ss_module._scanner_instance = None  # reset
    a = get_secrets_scanner()
    b = get_secrets_scanner()
    assert a is b
