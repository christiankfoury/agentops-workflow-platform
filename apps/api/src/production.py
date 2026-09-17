"""Shared production startup policy; development behavior remains explicit."""

from urllib.parse import urlparse

from src.config import settings


def validate_configuration():
    if settings.environment in {"development", "test"}:
        return
    if (
        not settings.identity_enabled
        or not settings.oidc_audience
        or any(
            not value or urlparse(value).scheme != "https" or not urlparse(value).hostname
            for value in [settings.oidc_issuer, settings.oidc_jwks_url]
        )
    ):
        raise RuntimeError(
            "Public deployment requires configured verified identity and HTTPS OIDC endpoints"
        )
    if not settings.trusted_hosts or "*" in settings.trusted_hosts:
        raise RuntimeError("Public deployment requires explicit trusted hosts")
