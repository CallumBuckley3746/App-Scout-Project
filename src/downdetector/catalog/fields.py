import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from downdetector.catalog.errors import CatalogError
from downdetector.db.check import CHECK_KINDS, CHECK_PURPOSES

_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_DOMAIN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
_BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}
_BLOCKED_SUFFIXES = (".local", ".localhost", ".internal")


@dataclass(frozen=True)
class ServiceInput:
    name: str
    slug: str
    domain: str
    homepage_url: str
    company_name: str | None
    description: str | None


@dataclass(frozen=True)
class CheckInput:
    kind: str
    purpose: str
    url: str | None
    interval_seconds: int
    timeout_ms: int
    slow_threshold_ms: int
    failure_threshold: int
    recovery_threshold: int
    enabled: bool


def parse_service_form(
    *,
    name: str,
    slug: str,
    domain: str,
    homepage_url: str,
    company_name: str,
    description: str,
) -> ServiceInput:
    clean_name = _limited(name, 100, "Name")
    clean_slug = slug.strip().casefold()
    if not _SLUG.fullmatch(clean_slug) or len(clean_slug) > 64:
        raise CatalogError("Slug: lowercase letters, digits, and single hyphens.")
    clean_domain = domain.strip().casefold().rstrip(".")
    if not _DOMAIN.fullmatch(clean_domain) or len(clean_domain) > 253:
        raise CatalogError("Domain without a scheme, for example spotify.com.")
    return ServiceInput(
        name=clean_name,
        slug=clean_slug,
        domain=clean_domain,
        homepage_url=public_https(homepage_url),
        company_name=_optional(company_name, 100, "Company"),
        description=_optional(description, 4000, "Description"),
    )


def parse_check_form(
    *,
    kind: str,
    purpose: str,
    url: str,
    interval_seconds: str,
    timeout_ms: str,
    slow_threshold_ms: str,
    failure_threshold: str,
    recovery_threshold: str,
    enabled: bool,
) -> CheckInput:
    clean_kind = kind.strip()
    clean_purpose = purpose.strip()
    if clean_kind not in CHECK_KINDS or clean_purpose not in CHECK_PURPOSES:
        raise CatalogError("Unknown check type.")
    clean_url = url.strip() or None
    if clean_kind == "breach" or clean_purpose == "breach":
        if clean_kind != "breach" or clean_purpose != "breach":
            raise CatalogError("A breach check uses kind and purpose breach, with no URL.")
        clean_kind, clean_purpose, clean_url = "breach", "breach", None
    else:
        if clean_url is None:
            raise CatalogError("This check needs an https URL.")
        clean_url = public_https(clean_url)
    interval = _int(interval_seconds, "Interval", 30, 86400)
    timeout = _int(timeout_ms, "Timeout", 100, 30000)
    slow = _int(slow_threshold_ms, "Slow threshold", 1, 29999)
    if slow >= timeout:
        raise CatalogError("The slow threshold must be lower than the timeout.")
    return CheckInput(
        kind=clean_kind,
        purpose=clean_purpose,
        url=clean_url,
        interval_seconds=interval,
        timeout_ms=timeout,
        slow_threshold_ms=slow,
        failure_threshold=_int(failure_threshold, "Failure threshold", 1, 20),
        recovery_threshold=_int(recovery_threshold, "Recovery threshold", 1, 20),
        enabled=enabled,
    )


def public_https(url: str) -> str:
    raw = url.strip()
    if len(raw) > 2048 or raw[:8].lower() != "https://":
        raise CatalogError("Use https on a public host.")
    normalized = "https://" + raw[8:]
    parts = urlsplit(normalized)
    host = (parts.hostname or "").casefold().rstrip(".")
    if (
        parts.username
        or parts.password
        or not host
        or host in _BLOCKED_HOSTS
        or host.endswith(_BLOCKED_SUFFIXES)
        or _blocked_ip(host)
    ):
        raise CatalogError("Use https on a public host.")
    return normalized


def _blocked_ip(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def _limited(value: str, limit: int, label: str) -> str:
    text = value.strip()
    if not text or len(text) > limit:
        raise CatalogError(f"{label} must be 1 to {limit} characters.")
    return text


def _optional(value: str, limit: int, label: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    if len(text) > limit:
        raise CatalogError(f"{label} must be at most {limit} characters.")
    return text


def _int(raw: str, label: str, low: int, high: int) -> int:
    text = raw.strip()
    if not re.fullmatch(r"-?\d+", text):
        raise CatalogError(f"{label} must be a whole number.")
    number = int(text)
    if number < low or number > high:
        raise CatalogError(f"{label} must be from {low} to {high}.")
    return number
