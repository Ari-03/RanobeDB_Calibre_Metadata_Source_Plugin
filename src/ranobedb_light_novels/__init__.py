#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
"""
RanobeDB Light Novels - Calibre Metadata Source Plugin

Downloads metadata and covers from RanobeDB (https://ranobedb.org) for light novels.

License: GPL v3
"""

from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GPL v3'
__copyright__ = '2024, RanobeDB Plugin Author'
__docformat__ = 'restructuredtext en'

import json
import time
from threading import Lock
from urllib.parse import urlencode, quote_plus

try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue

from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.book.base import Metadata
from calibre.ebooks.metadata.sources.base import Option, Source


class RanobeDBLightNovels(Source):
    """
    Calibre metadata source plugin for RanobeDB.

    Downloads metadata and covers for light novels from https://ranobedb.org
    """

    name = 'RanobeDB Light Novels'
    description = 'Downloads metadata and covers from RanobeDB for light novels'
    author = 'RanobeDB Plugin Author'
    version = (1, 0, 0)
    minimum_calibre_version = (5, 0, 0)

    # Plugin capabilities
    capabilities = frozenset({'identify', 'cover'})

    # Metadata fields this plugin can provide
    touched_fields = frozenset(
        {
            'title',
            'authors',
            'tags',
            'pubdate',
            'comments',
            'publisher',
            'identifier:ranobedb',
            'identifier:isbn',
            'series',
            'series_index',
            'languages',
        }
    )

    # Plugin settings
    has_html_comments = False
    supports_gzip_transfer_encoding = True
    cached_cover_url_is_reliable = True
    prefer_results_with_isbn = False

    # API settings
    BASE_URL = 'https://ranobedb.org/api/v0'
    WEBSITE_URL = 'https://ranobedb.org'
    IMAGE_BASE_URL = 'https://images.ranobedb.org'

    # Rate limiting: 60 requests/minute = 1 second between requests
    RATE_LIMIT_DELAY = 1.0
    _last_request_time = 0
    _rate_lock = Lock()

    # Configuration options
    options = (
        Option(
            'language_order',
            'string',
            'en,romaji,ja',
            _('Language preference order:'),
            _(
                'Comma-separated order for titles, authors, series names. '
                'Options: en (English), romaji, ja (Japanese). '
                'Example: "en,romaji,ja" means English first, then Romaji, then Japanese.'
            ),
        ),
        Option(
            'description_language',
            'choices',
            'en',
            _('Description language:'),
            _('Preferred language for book descriptions'),
            choices={
                'en': _('English'),
                'ja': _('Japanese'),
                'both': _('Both (English first)'),
            },
        ),
        Option(
            'max_results',
            'number',
            10,
            _('Maximum results:'),
            _('Maximum number of search results to return (1-25)'),
        ),
    )

    def __init__(self, *args, **kwargs):
        Source.__init__(self, *args, **kwargs)

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------

    def _rate_limit(self):
        """
        Ensure we don't exceed RanobeDB's rate limit of 60 requests/minute.
        """
        with self._rate_lock:
            elapsed = time.time() - RanobeDBLightNovels._last_request_time
            if elapsed < self.RATE_LIMIT_DELAY:
                time.sleep(self.RATE_LIMIT_DELAY - elapsed)
            RanobeDBLightNovels._last_request_time = time.time()

    # -------------------------------------------------------------------------
    # Language Preference Helpers
    # -------------------------------------------------------------------------

    def _parse_language_order(self):
        """
        Parse user's language preference string into ordered list.

        :return: List of language codes in preferred order, e.g. ['en', 'romaji', 'ja']
        """
        order_str = self.prefs.get('language_order', 'en,romaji,ja')

        order = []
        for lang in order_str.split(','):
            lang = lang.strip().lower()
            # Normalize language codes
            if lang in ('en', 'english'):
                lang = 'en'
            elif lang in ('ja', 'japanese', 'jp'):
                lang = 'ja'
            elif lang == 'romaji':
                lang = 'romaji'
            else:
                continue

            if lang not in order:
                order.append(lang)

        # Ensure all languages are included as fallbacks
        for lang in ['en', 'romaji', 'ja']:
            if lang not in order:
                order.append(lang)

        return order

    def _select_by_language(self, options):
        """
        Select value based on user's language preference order.

        :param options: Dict with keys 'en', 'romaji', 'ja' and corresponding values
        :return: First non-empty value in preferred order, or None
        """
        order = self._parse_language_order()

        for lang in order:
            value = options.get(lang)
            if value:
                return value

        # Fallback to any non-None value
        for value in options.values():
            if value:
                return value

        return None

    # -------------------------------------------------------------------------
    # API Request Helpers
    # -------------------------------------------------------------------------

    def _make_api_request(self, endpoint, params=None, log=None, timeout=30):
        """
        Make a rate-limited request to the RanobeDB API.

        :param endpoint: API endpoint (e.g., '/books' or '/book/123')
        :param params: Optional query parameters dict
        :param log: Log object for debugging
        :param timeout: Request timeout in seconds
        :return: Parsed JSON response or None on error
        """
        self._rate_limit()

        url = self.BASE_URL + endpoint
        if params:
            url += '?' + urlencode(params)

        if log:
            log.info('RanobeDB API request: %s' % url)

        try:
            br = self.browser
            response = br.open_novisit(url, timeout=timeout)
            raw = response.read()
            return json.loads(raw)
        except Exception as e:
            if log:
                log.exception('RanobeDB API request failed: %s' % str(e))
            return None

    # -------------------------------------------------------------------------
    # Title/Language Helpers
    # -------------------------------------------------------------------------

    def _get_preferred_title(self, book_data, log=None):
        """
        Get the title in the user's preferred language order.

        :param book_data: Book data from API
        :param log: Log object
        :return: Tuple of (title, language_code)
        """
        titles_list = book_data.get('titles', [])

        # Build options dict with available titles
        options = {
            'en': None,
            'romaji': book_data.get('romaji') or book_data.get('romaji_orig'),
            'ja': book_data.get('title_orig'),
        }

        # Extract titles from titles array
        for t in titles_list:
            lang = t.get('lang')
            title_text = t.get('title')
            if lang == 'en' and title_text:
                options['en'] = title_text
            elif lang == 'ja' and title_text:
                options['ja'] = title_text
            # Also check for romaji in title entries
            romaji = t.get('romaji')
            if romaji and not options['romaji']:
                options['romaji'] = romaji

        # Use main title as fallback based on its language
        main_title = book_data.get('title')
        main_lang = book_data.get('lang', 'ja')

        if main_lang == 'en' and not options['en']:
            options['en'] = main_title
        elif main_lang == 'ja' and not options['ja']:
            options['ja'] = main_title

        # If main title looks like English (mostly ASCII), use as English fallback
        if main_title and not options['en']:
            if all(
                ord(c) < 128 for c in main_title.replace(' ', '').replace(':', '').replace('-', '')
            ):
                options['en'] = main_title

        # Select based on user preference
        title = self._select_by_language(options)

        # Determine the language of the selected title
        selected_lang = main_lang
        if title == options['en']:
            selected_lang = 'en'
        elif title == options['ja']:
            selected_lang = 'ja'

        return title or main_title, selected_lang

    def _extract_authors(self, book_data, log=None):
        """
        Extract authors from book editions data.
        Only includes staff with role_type 'author'.
        Uses user's language preference order.

        :param book_data: Book data from API
        :param log: Log object
        :return: List of author names
        """
        authors = []
        editions = book_data.get('editions', [])

        for edition in editions:
            for staff in edition.get('staff', []):
                if staff.get('role_type') == 'author':
                    # Build options for this author
                    # Note: API uses 'romaji' for romanized names, 'name' for Japanese
                    options = {
                        'en': staff.get('romaji'),  # Romaji serves as English
                        'romaji': staff.get('romaji'),
                        'ja': staff.get('name'),
                    }

                    author_name = self._select_by_language(options)
                    if author_name and author_name not in authors:
                        authors.append(author_name)

        return authors if authors else [_('Unknown')]

    def _extract_tags(self, series_data, log=None):
        """
        Extract tags from series data.
        Only includes 'genre' and 'tag' types (not 'demographic' or 'content').

        :param series_data: Series data from book API response
        :param log: Log object
        :return: List of tag names
        """
        if not series_data:
            return []

        tags = []
        for tag in series_data.get('tags', []):
            ttype = tag.get('ttype')
            if ttype in ('genre', 'tag'):
                name = tag.get('name')
                if name and name not in tags:
                    tags.append(name)

        return tags

    def _extract_isbn(self, book_data, log=None):
        """
        Extract ISBN from book releases.

        :param book_data: Book data from API
        :param log: Log object
        :return: ISBN string or None
        """
        releases = book_data.get('releases', [])

        for release in releases:
            isbn = release.get('isbn13')
            if isbn:
                validated = check_isbn(isbn)
                if validated:
                    return validated

        return None

    def _parse_date(self, date_int, log=None):
        """
        Parse RanobeDB date integer (YYYYMMDD format) to datetime.

        :param date_int: Date as integer (e.g., 20240115)
        :param log: Log object
        :return: datetime object or None
        """
        if not date_int or date_int <= 0:
            return None

        try:
            from calibre.utils.date import parse_date

            date_str = str(date_int)
            if len(date_str) == 8:
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
                return parse_date(f'{year}-{month}-{day}')
        except Exception as e:
            if log:
                log.warning('Failed to parse date %s: %s' % (date_int, str(e)))

        return None

    def _get_cover_url(self, book_data, log=None):
        """
        Get cover image URL from book data.

        :param book_data: Book data from API
        :param log: Log object
        :return: Cover URL string or None
        """
        image = book_data.get('image')
        if image and image.get('filename'):
            return f'{self.IMAGE_BASE_URL}/{image["filename"]}'
        return None

    def _get_description(self, book_data, log=None):
        """
        Get book description based on user's language preference.

        :param book_data: Book data from API
        :param log: Log object
        :return: Description string or None
        """
        pref = self.prefs.get('description_language', 'en')

        desc_en = book_data.get('description')
        desc_ja = book_data.get('description_ja')

        if pref == 'en':
            return desc_en or desc_ja
        elif pref == 'ja':
            return desc_ja or desc_en
        elif pref == 'both':
            parts = []
            if desc_en:
                parts.append(desc_en)
            if desc_ja:
                parts.append('\n\n---\n\n' + desc_ja)
            return ''.join(parts) if parts else None

        return desc_en or desc_ja

    # -------------------------------------------------------------------------
    # Series Helpers
    # -------------------------------------------------------------------------

    def _get_series_name(self, series_data, log=None):
        """
        Get series name in user's preferred language.

        :param series_data: Series data from API
        :param log: Log object
        :return: Series name string or None
        """
        if not series_data:
            return None

        # Build options from available series data
        options = {
            'en': None,
            'romaji': series_data.get('romaji'),
            'ja': None,
        }

        # Check titles array if available
        for t in series_data.get('titles', []):
            lang = t.get('lang')
            title_text = t.get('title')
            if lang == 'en' and title_text:
                options['en'] = title_text
            elif lang == 'ja' and title_text:
                options['ja'] = title_text

        # Use main title as fallback
        main_title = series_data.get('title')
        olang = series_data.get('olang', 'ja')

        if olang == 'en' and not options['en']:
            options['en'] = main_title
        elif olang == 'ja' and not options['ja']:
            options['ja'] = main_title

        # If main title looks like English (mostly ASCII), use as English
        if main_title and not options['en']:
            if all(
                ord(c) < 128
                for c in main_title.replace(' ', '')
                .replace(':', '')
                .replace('-', '')
                .replace("'", '')
            ):
                options['en'] = main_title

        return self._select_by_language(options) or main_title

    def _get_series_info(self, book_data, log=None):
        """
        Extract series information from book data.

        :param book_data: Book data from API
        :param log: Log object
        :return: Tuple of (series_name, series_index) or (None, None)
        """
        series = book_data.get('series')
        if not series:
            return None, None

        # Get series name in preferred language
        series_name = self._get_series_name(series, log)

        # Find series index from the books list in series
        series_index = None
        book_id = book_data.get('id')
        books = series.get('books', [])

        for idx, book in enumerate(books, start=1):
            if book.get('id') == book_id:
                # Use sort_order if available, otherwise use position in list
                sort_order = book.get('sort_order')
                if sort_order is not None:
                    series_index = sort_order
                else:
                    series_index = idx
                break

        return series_name, series_index

    # -------------------------------------------------------------------------
    # Book URL Methods
    # -------------------------------------------------------------------------

    def get_book_url(self, identifiers):
        """
        Return the URL for the book on RanobeDB website.

        :param identifiers: Dict of identifiers
        :return: Tuple of (id_type, id_value, url) or None
        """
        ranobedb_id = identifiers.get('ranobedb')
        if ranobedb_id:
            url = f'{self.WEBSITE_URL}/book/{ranobedb_id}'
            return ('ranobedb', ranobedb_id, url)
        return None

    def get_book_url_name(self, idtype, idval, url):
        """Return human-readable name for the book URL."""
        return 'RanobeDB'

    def id_from_url(self, url):
        """
        Parse a RanobeDB URL and extract the book ID.

        :param url: URL string
        :return: Tuple of (id_type, id_value) or None
        """
        import re

        match = re.search(r'ranobedb\.org/book/(\d+)', url)
        if match:
            return ('ranobedb', match.group(1))
        return None

    # -------------------------------------------------------------------------
    # Cover URL Caching
    # -------------------------------------------------------------------------

    def get_cached_cover_url(self, identifiers):
        """
        Return cached cover URL for the book.

        :param identifiers: Dict of identifiers
        :return: Cover URL or None
        """
        ranobedb_id = identifiers.get('ranobedb')
        if ranobedb_id:
            return self.cached_identifier_to_cover_url(ranobedb_id)
        return None

    # -------------------------------------------------------------------------
    # Search/Identify
    # -------------------------------------------------------------------------

    def _create_search_query(self, title=None, authors=None):
        """
        Create search query string from title and authors.

        Passes title through unchanged for best search accuracy.
        Special characters like & are handled by urlencode().

        :param title: Book title
        :param authors: List of authors
        :return: Query string
        """
        parts = []

        if title:
            parts.append(title)

        if authors:
            if isinstance(authors, list) and authors:
                first_author = authors[0]
                if first_author and first_author.lower() != 'unknown':
                    parts.append(first_author)

        return ' '.join(parts)

    def _search_books(self, query, log, timeout=30):
        """
        Search for books on RanobeDB.

        :param query: Search query string
        :param log: Log object
        :param timeout: Request timeout
        :return: List of book results
        """
        max_results = min(max(1, self.prefs.get('max_results', 10)), 25)

        params = {
            'q': query,
            'limit': max_results,
        }

        # Add English language filter for releases if English is first preference
        lang_order = self._parse_language_order()
        if lang_order and lang_order[0] == 'en':
            params['rl[]'] = 'en'

        response = self._make_api_request('/books', params, log, timeout)

        if response and 'books' in response:
            return response['books']

        return []

    def _get_book_details(self, book_id, log, timeout=30):
        """
        Get detailed book information from RanobeDB.

        :param book_id: RanobeDB book ID
        :param log: Log object
        :param timeout: Request timeout
        :return: Book details dict or None
        """
        response = self._make_api_request(f'/book/{book_id}', None, log, timeout)
        if response and 'book' in response:
            return response['book']
        return None

    def _book_to_metadata(self, book_data, relevance, log):
        """
        Convert RanobeDB book data to Calibre Metadata object.

        :param book_data: Book data from API
        :param relevance: Source relevance integer
        :param log: Log object
        :return: Metadata object
        """
        # Get title in preferred language
        title, lang = self._get_preferred_title(book_data, log)

        # Get authors (only 'author' role)
        authors = self._extract_authors(book_data, log)

        # Create Metadata object
        mi = Metadata(title, authors)

        # Set identifiers
        book_id = str(book_data.get('id'))
        mi.set_identifier('ranobedb', book_id)

        # Set ISBN if available
        isbn = self._extract_isbn(book_data, log)
        if isbn:
            mi.isbn = isbn
            self.cache_isbn_to_identifier(isbn, book_id)

        # Set description/comments based on language preference
        description = self._get_description(book_data, log)
        if description:
            mi.comments = description

        # Set publisher (first publisher)
        publishers = book_data.get('publishers', [])
        if publishers:
            mi.publisher = publishers[0].get('name')

        # Set publication date
        pubdate = self._parse_date(book_data.get('c_release_date'), log)
        if pubdate:
            mi.pubdate = pubdate

        # Set language
        if lang:
            mi.language = lang

        # Set series information
        series_name, series_index = self._get_series_info(book_data, log)
        if series_name:
            mi.series = series_name
            if series_index is not None:
                mi.series_index = float(series_index)

        # Set tags from series (genres + tags only)
        series_data = book_data.get('series')
        tags = self._extract_tags(series_data, log)
        if tags:
            mi.tags = tags

        # Cache cover URL
        cover_url = self._get_cover_url(book_data, log)
        if cover_url:
            self.cache_identifier_to_cover_url(book_id, cover_url)

        # Set source relevance for sorting
        mi.source_relevance = relevance

        return mi

    def identify(
        self,
        log,
        result_queue,
        abort,
        title=None,
        authors=None,
        identifiers={},
        timeout=30,
    ):
        """
        Identify a book by its title/author/identifiers.

        :param log: Log object for debugging
        :param result_queue: Queue to put Metadata results into
        :param abort: Event to check for abort signal
        :param title: Book title (optional)
        :param authors: List of authors (optional)
        :param identifiers: Dict of identifiers (optional)
        :param timeout: Request timeout in seconds
        :return: None on success, error string on failure
        """
        log.info(
            'RanobeDB: Starting identify for title=%s, authors=%s, identifiers=%s'
            % (title, authors, identifiers)
        )

        # Check if we have a RanobeDB ID
        ranobedb_id = identifiers.get('ranobedb')

        if ranobedb_id:
            # Direct lookup by ID
            log.info('RanobeDB: Looking up book by ID: %s' % ranobedb_id)

            if abort.is_set():
                return None

            book_data = self._get_book_details(ranobedb_id, log, timeout)

            if book_data:
                mi = self._book_to_metadata(book_data, 0, log)
                self.clean_downloaded_metadata(mi)
                result_queue.put(mi)
                log.info('RanobeDB: Found book: %s' % mi.title)
                return None
            else:
                log.warning('RanobeDB: Book not found with ID: %s' % ranobedb_id)

        # Check for ISBN
        isbn = identifiers.get('isbn')
        if isbn:
            isbn = check_isbn(isbn)

        # Build search query
        query = self._create_search_query(title, authors)

        if not query and not isbn:
            log.error('RanobeDB: Insufficient metadata for search')
            return None

        # If we have ISBN, add it to query
        if isbn:
            query = isbn if not query else f'{query} {isbn}'

        log.info('RanobeDB: Searching with query: %s' % query)

        if abort.is_set():
            return None

        # Search for books
        search_results = self._search_books(query, log, timeout)

        if not search_results:
            log.info('RanobeDB: No results found')
            return None

        log.info('RanobeDB: Found %d results' % len(search_results))

        # Fetch details for each result
        for relevance, book in enumerate(search_results):
            if abort.is_set():
                break

            book_id = book.get('id')
            if not book_id:
                continue

            log.info('RanobeDB: Fetching details for book ID: %s' % book_id)

            book_data = self._get_book_details(book_id, log, timeout)

            if book_data:
                mi = self._book_to_metadata(book_data, relevance, log)
                self.clean_downloaded_metadata(mi)
                result_queue.put(mi)
                log.info('RanobeDB: Added result: %s by %s' % (mi.title, mi.authors))

        return None

    # -------------------------------------------------------------------------
    # Cover Download
    # -------------------------------------------------------------------------

    def download_cover(
        self,
        log,
        result_queue,
        abort,
        title=None,
        authors=None,
        identifiers={},
        timeout=30,
        get_best_cover=False,
    ):
        """
        Download a cover image for the book.

        :param log: Log object for debugging
        :param result_queue: Queue to put (self, cover_data) into
        :param abort: Event to check for abort signal
        :param title: Book title (optional)
        :param authors: List of authors (optional)
        :param identifiers: Dict of identifiers (optional)
        :param timeout: Request timeout in seconds
        :param get_best_cover: If True, only get the best cover
        """
        log.info('RanobeDB: Starting cover download')

        # Try to get cached cover URL
        cached_url = self.get_cached_cover_url(identifiers)

        if cached_url is None:
            # No cached URL, try to identify first
            log.info('RanobeDB: No cached cover URL, running identify')

            rq = Queue()
            self.identify(
                log,
                rq,
                abort,
                title=title,
                authors=authors,
                identifiers=identifiers,
                timeout=timeout,
            )

            if abort.is_set():
                return

            # Get results and find cover URL
            results = []
            while True:
                try:
                    results.append(rq.get_nowait())
                except Empty:
                    break

            # Sort by relevance
            results.sort(key=lambda x: x.source_relevance)

            for mi in results:
                cached_url = self.get_cached_cover_url(mi.identifiers)
                if cached_url:
                    break

        if cached_url is None:
            log.info('RanobeDB: No cover URL found')
            return

        if abort.is_set():
            return

        log.info('RanobeDB: Downloading cover from: %s' % cached_url)

        try:
            self._rate_limit()
            br = self.browser
            cover_data = br.open_novisit(cached_url, timeout=timeout).read()

            if cover_data:
                result_queue.put((self, cover_data))
                log.info('RanobeDB: Cover downloaded successfully')
        except Exception as e:
            log.exception('RanobeDB: Failed to download cover: %s' % str(e))


if __name__ == '__main__':
    # Test the plugin
    from calibre.ebooks.metadata.sources.test import (
        test_identify_plugin,
        title_test,
        authors_test,
    )

    tests = [
        (
            {'title': 'Sword Art Online', 'authors': ['Reki Kawahara']},
            [
                title_test('Sword Art Online', exact=False),
            ],
        ),
        (
            {
                'title': 'Spice and Wolf',
            },
            [
                title_test('Spice', exact=False),
            ],
        ),
    ]

    test_identify_plugin(RanobeDBLightNovels.name, tests)
