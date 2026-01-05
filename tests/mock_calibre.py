"""
Mock Calibre classes for standalone testing.

This module provides mock implementations of Calibre's classes so the plugin
can be tested without Calibre installed.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.parse import urlencode
import json
import ssl


# Mock the _() translation function
def _(text):
    """Mock translation function - returns text unchanged."""
    return text


# Make it available as a builtin for the plugin
import builtins

builtins._ = _


@dataclass
class MockMetadata:
    """
    Mock implementation of calibre.ebooks.metadata.book.base.Metadata
    """

    title: str
    authors: List[str] = field(default_factory=lambda: ["Unknown"])

    # Optional fields
    publisher: Optional[str] = None
    pubdate: Optional[Any] = None
    comments: Optional[str] = None
    series: Optional[str] = None
    series_index: Optional[float] = None
    language: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    isbn: Optional[str] = None
    identifiers: Dict[str, str] = field(default_factory=dict)
    cover_data: Optional[Tuple[str, bytes]] = None

    # Source relevance for sorting
    source_relevance: int = 0

    def set_identifier(self, key: str, value: str):
        """Set an identifier."""
        self.identifiers[key] = value

    def get_identifiers(self) -> Dict[str, str]:
        """Get all identifiers."""
        return self.identifiers

    def has_identifier(self, key: str) -> bool:
        """Check if identifier exists."""
        return key in self.identifiers

    def is_null(self, field_name: str) -> bool:
        """Check if a field is null/empty."""
        value = getattr(self, field_name, None)
        if value is None:
            return True
        if isinstance(value, (list, dict, str)) and len(value) == 0:
            return True
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "authors": self.authors,
            "publisher": self.publisher,
            "pubdate": str(self.pubdate) if self.pubdate else None,
            "comments": self.comments,
            "series": self.series,
            "series_index": self.series_index,
            "language": self.language,
            "tags": self.tags,
            "isbn": self.isbn,
            "identifiers": self.identifiers,
            "source_relevance": self.source_relevance,
        }


class MockBrowser:
    """
    Mock implementation of Calibre's browser for HTTP requests.
    Uses urllib for actual HTTP requests.
    """

    def __init__(self, user_agent: str = None):
        self.user_agent = user_agent or "Mozilla/5.0 (compatible; CalibrePlugin/1.0)"
        # Create SSL context that doesn't verify certificates (for testing)
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

    def open_novisit(self, url: str, timeout: int = 30) -> "MockResponse":
        """Open a URL without adding to history."""
        request = Request(url)
        request.add_header("User-Agent", self.user_agent)
        request.add_header("Accept", "application/json")

        response = urlopen(request, timeout=timeout, context=self._ssl_context)
        return MockResponse(response)

    def clone_browser(self) -> "MockBrowser":
        """Clone the browser."""
        return MockBrowser(self.user_agent)


class MockResponse:
    """Mock HTTP response wrapper."""

    def __init__(self, response):
        self._response = response
        self._data = None

    def read(self) -> bytes:
        """Read response data."""
        if self._data is None:
            self._data = self._response.read()
        return self._data


class MockLog:
    """Mock log object for debugging output."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.messages = []

    def _log(self, level: str, msg: str):
        self.messages.append((level, msg))
        if self.verbose:
            print(f"[{level}] {msg}")

    def info(self, msg: str):
        self._log("INFO", msg)

    def warning(self, msg: str):
        self._log("WARN", msg)

    def error(self, msg: str):
        self._log("ERROR", msg)

    def exception(self, msg: str):
        self._log("EXCEPTION", msg)


class MockAbort:
    """Mock abort event."""

    def __init__(self):
        self._is_set = False

    def is_set(self) -> bool:
        return self._is_set

    def set(self):
        self._is_set = True

    def clear(self):
        self._is_set = False


class MockOption:
    """Mock Option class for plugin configuration."""

    def __init__(self, name, type_, default, label, desc, choices=None):
        self.name = name
        self.type = type_
        self.default = default
        self.label = label
        self.desc = desc
        self.choices = choices


class MockPrefs:
    """Mock preferences storage."""

    def __init__(self):
        self._prefs = {}
        self.defaults = {}

    def get(self, key, default=None):
        if key in self._prefs:
            return self._prefs[key]
        if key in self.defaults:
            return self.defaults[key]
        return default

    def __setitem__(self, key, value):
        self._prefs[key] = value

    def __getitem__(self, key):
        return self.get(key)


class MockSource:
    """
    Mock implementation of calibre.ebooks.metadata.sources.base.Source

    Provides the base class interface without Calibre dependencies.
    """

    name = "Mock Source"
    description = "Mock metadata source"
    author = "Test"
    version = (1, 0, 0)
    minimum_calibre_version = (5, 0, 0)

    capabilities = frozenset()
    touched_fields = frozenset()

    has_html_comments = False
    supports_gzip_transfer_encoding = False
    cached_cover_url_is_reliable = True
    prefer_results_with_isbn = True

    options = ()

    def __init__(self):
        self._browser = None
        self._isbn_to_identifier_cache = {}
        self._identifier_to_cover_url_cache = {}
        self._prefs = MockPrefs()

        # Set default prefs from options
        for opt in self.options:
            self._prefs.defaults[opt.name] = opt.default

    @property
    def prefs(self):
        return self._prefs

    @property
    def browser(self):
        if self._browser is None:
            self._browser = MockBrowser()
        return self._browser.clone_browser()

    def cache_isbn_to_identifier(self, isbn: str, identifier: str):
        """Cache ISBN to identifier mapping."""
        self._isbn_to_identifier_cache[isbn] = identifier

    def cached_isbn_to_identifier(self, isbn: str) -> Optional[str]:
        """Get cached identifier for ISBN."""
        return self._isbn_to_identifier_cache.get(isbn)

    def cache_identifier_to_cover_url(self, identifier: str, url: str):
        """Cache identifier to cover URL mapping."""
        self._identifier_to_cover_url_cache[identifier] = url

    def cached_identifier_to_cover_url(self, identifier: str) -> Optional[str]:
        """Get cached cover URL for identifier."""
        return self._identifier_to_cover_url_cache.get(identifier)

    def get_title_tokens(
        self, title: str, strip_joiners: bool = True, strip_subtitle: bool = False
    ):
        """Extract tokens from title for search."""
        if not title:
            return

        # Strip subtitle if requested
        if strip_subtitle:
            title = re.sub(r"[\(\[\{].*?[\)\]\}]", "", title)
            title = re.sub(r"[/:\\].*$", "", title)

        # Clean and tokenize
        title = re.sub(r'[,:;!@$%^&*(){}.`~"\[\]/]', " ", title)
        tokens = title.split()

        joiners = {"a", "and", "the", "&"} if strip_joiners else set()

        for token in tokens:
            token = token.strip().strip('"').strip("'")
            if token and token.lower() not in joiners:
                yield token

    def get_author_tokens(self, authors: List[str], only_first_author: bool = True):
        """Extract tokens from authors for search."""
        if not authors:
            return

        if only_first_author:
            authors = authors[:1]

        for author in authors:
            # Handle "Last, First" format
            has_comma = "," in author
            parts = re.sub(r"[-+.:;,]", " ", author).split()

            if has_comma:
                parts = parts[1:] + parts[:1]

            for token in parts:
                token = re.sub(r'[!@#$%^&*(){}~"\s\[\]/]', "", token).strip()
                if len(token) > 2 and token.lower() not in ("von", "van", "unknown"):
                    yield token

    def clean_downloaded_metadata(self, mi: MockMetadata):
        """Clean/normalize downloaded metadata."""
        # Title case for English
        if mi.title and (
            mi.language == "eng" or mi.language == "en" or not mi.language
        ):
            mi.title = mi.title.title()

        # Clean authors
        if mi.authors:
            mi.authors = [a.strip() for a in mi.authors if a.strip()]


def check_isbn(isbn: str) -> Optional[str]:
    """
    Mock implementation of calibre.ebooks.metadata.check_isbn

    Validates and normalizes ISBN.
    """
    if not isbn:
        return None

    # Remove hyphens and spaces
    isbn = re.sub(r"[-\s]", "", isbn)

    # Check length
    if len(isbn) == 10:
        # ISBN-10 validation
        if isbn[:-1].isdigit() and (isbn[-1].isdigit() or isbn[-1].upper() == "X"):
            return isbn
    elif len(isbn) == 13:
        # ISBN-13 validation
        if isbn.isdigit():
            return isbn

    return None


def parse_date(date_str: str):
    """
    Mock implementation of calibre.utils.date.parse_date
    """
    from datetime import datetime

    # Try various formats
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None
