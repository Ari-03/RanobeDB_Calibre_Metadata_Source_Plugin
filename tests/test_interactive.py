#!/usr/bin/env python3
"""
Interactive test script for RanobeDB Light Novels plugin.

Allows testing the RanobeDB API and plugin logic without Calibre installed.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from queue import Queue

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'tests'))
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

# Import mock calibre FIRST to set up the _ function
from mock_calibre import (
    MockMetadata,
    MockLog,
    MockAbort,
    MockSource,
    MockOption,
    MockPrefs,
    MockBrowser,
    check_isbn,
    parse_date,
)

# Now we can import the plugin
# We need to patch the imports before importing the plugin
import builtins

builtins._ = lambda x: x


# Mock the calibre modules
class MockCalibreMetadata:
    Metadata = MockMetadata


class MockCalibreSource:
    Source = MockSource
    Option = MockOption


class MockCalibreEbooksMetadata:
    check_isbn = check_isbn


class MockCalibreUtilsDate:
    parse_date = parse_date


# Patch sys.modules
sys.modules['calibre'] = type(sys)('calibre')
sys.modules['calibre.ebooks'] = type(sys)('calibre.ebooks')
sys.modules['calibre.ebooks.metadata'] = MockCalibreEbooksMetadata
sys.modules['calibre.ebooks.metadata.book'] = type(sys)('calibre.ebooks.metadata.book')
sys.modules['calibre.ebooks.metadata.book.base'] = MockCalibreMetadata
sys.modules['calibre.ebooks.metadata.sources'] = type(sys)('calibre.ebooks.metadata.sources')
sys.modules['calibre.ebooks.metadata.sources.base'] = MockCalibreSource
sys.modules['calibre.utils'] = type(sys)('calibre.utils')
sys.modules['calibre.utils.date'] = MockCalibreUtilsDate

# Now import the plugin
from ranobedb_light_novels import RanobeDBLightNovels


# Results directory
RESULTS_DIR = PROJECT_ROOT / 'tests' / 'results'


def ensure_results_dir():
    """Create results directory if it doesn't exist."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_result(test_type: str, query: dict, results: list, success: bool, error: str = None):
    """Save test result to JSON file."""
    ensure_results_dir()

    timestamp = datetime.now()

    # Create filename
    query_str = '_'.join(str(v) for v in query.values() if v)[:50]
    query_str = ''.join(c if c.isalnum() or c in '-_' else '_' for c in query_str)
    filename = f'{test_type}_{query_str}_{timestamp.strftime("%Y%m%d_%H%M%S")}.json'

    # Build result object
    result_data = {
        'test_type': test_type,
        'query': query,
        'timestamp': timestamp.isoformat(),
        'results_count': len(results),
        'results': results,
        'success': success,
        'error': error,
    }

    # Save to file
    filepath = RESULTS_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False, default=str)

    print(f'\nResult saved to: {filepath}')
    return filepath


def format_metadata(mi: MockMetadata, index: int = None) -> str:
    """Format metadata for display."""
    lines = []

    if index is not None:
        lines.append(f'[{index}] {mi.title}')
    else:
        lines.append('=' * 50)
        lines.append(f'Title: {mi.title}')
        lines.append('=' * 50)

    if mi.authors and mi.authors != ['Unknown']:
        lines.append(f'    Authors: {", ".join(mi.authors)}')

    if mi.series:
        series_str = mi.series
        if mi.series_index:
            series_str += f' #{int(mi.series_index)}'
        lines.append(f'    Series: {series_str}')

    if mi.tags:
        lines.append(
            f'    Tags: {", ".join(mi.tags[:5])}'
            + (f' (+{len(mi.tags) - 5} more)' if len(mi.tags) > 5 else '')
        )

    if mi.publisher:
        lines.append(f'    Publisher: {mi.publisher}')

    if mi.pubdate:
        lines.append(f'    Published: {mi.pubdate}')

    if mi.identifiers.get('ranobedb'):
        lines.append(f'    RanobeDB ID: {mi.identifiers["ranobedb"]}')

    if mi.isbn:
        lines.append(f'    ISBN: {mi.isbn}')

    return '\n'.join(lines)


def format_metadata_full(mi: MockMetadata) -> str:
    """Format full metadata for display."""
    lines = []
    lines.append('=' * 60)
    lines.append(f'Title: {mi.title}')
    lines.append('=' * 60)
    lines.append('')

    lines.append(f'Authors: {", ".join(mi.authors)}')

    if mi.series:
        series_str = mi.series
        if mi.series_index:
            series_str += f' #{int(mi.series_index)}'
        lines.append(f'Series: {series_str}')

    if mi.tags:
        lines.append(f'Tags: {", ".join(mi.tags)}')

    if mi.publisher:
        lines.append(f'Publisher: {mi.publisher}')

    if mi.pubdate:
        lines.append(f'Published: {mi.pubdate}')

    if mi.language:
        lines.append(f'Language: {mi.language}')

    if mi.isbn:
        lines.append(f'ISBN: {mi.isbn}')

    lines.append('')
    lines.append('Identifiers:')
    for key, value in mi.identifiers.items():
        lines.append(f'  {key}: {value}')

    # Check for cached cover URL
    ranobedb_id = mi.identifiers.get('ranobedb')
    if ranobedb_id:
        lines.append('')
        lines.append(f'RanobeDB URL: https://ranobedb.org/book/{ranobedb_id}')

    if mi.comments:
        lines.append('')
        lines.append('Description:')
        # Truncate long descriptions
        desc = mi.comments[:500] + '...' if len(mi.comments) > 500 else mi.comments
        lines.append(desc)

    lines.append('=' * 60)

    return '\n'.join(lines)


class PluginTester:
    """Interactive plugin tester."""

    def __init__(self):
        self.plugin = RanobeDBLightNovels()
        self.log = MockLog(verbose=True)
        self.abort = MockAbort()

    def search(self, title: str = None, authors: list = None, identifiers: dict = None) -> list:
        """Run a search and return results."""
        result_queue = Queue()

        self.plugin.identify(
            log=self.log,
            result_queue=result_queue,
            abort=self.abort,
            title=title,
            authors=authors,
            identifiers=identifiers or {},
            timeout=30,
        )

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Sort by relevance
        results.sort(key=lambda x: x.source_relevance)

        return results

    def test_cover(self, identifiers: dict) -> bool:
        """Test cover download."""
        result_queue = Queue()

        self.plugin.download_cover(
            log=self.log,
            result_queue=result_queue,
            abort=self.abort,
            identifiers=identifiers,
            timeout=30,
        )

        if not result_queue.empty():
            source, cover_data = result_queue.get()
            print(f'\nCover downloaded successfully!')
            print(f'Size: {len(cover_data)} bytes')

            # Optionally save cover
            save = input('Save cover image? (y/n): ').strip().lower()
            if save == 'y':
                ensure_results_dir()
                ranobedb_id = identifiers.get('ranobedb', 'unknown')
                filepath = RESULTS_DIR / f'cover_{ranobedb_id}.jpg'
                with open(filepath, 'wb') as f:
                    f.write(cover_data)
                print(f'Cover saved to: {filepath}')

            return True
        else:
            print('\nNo cover found.')
            return False


def menu_search_title(tester: PluginTester):
    """Search by title only."""
    print('\n--- Search by Title ---')
    title = input('Enter title: ').strip()

    if not title:
        print('No title entered.')
        return

    print(f'\nSearching for: {title}')
    print('-' * 40)

    results = tester.search(title=title)

    if not results:
        print('No results found.')
        save_result('search_title', {'title': title}, [], False, 'No results')
        return

    print(f'\nFound {len(results)} result(s):\n')

    for i, mi in enumerate(results, 1):
        print(format_metadata(mi, i))
        print()

    # Save results
    results_data = [mi.to_dict() for mi in results]
    save_result('search_title', {'title': title}, results_data, True)

    # Option to view details
    while True:
        choice = input(f'\nView details (1-{len(results)}) or 0 to go back: ').strip()
        if choice == '0' or not choice:
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                print('\n' + format_metadata_full(results[idx]))
            else:
                print('Invalid selection.')
        except ValueError:
            print('Invalid input.')


def menu_search_title_author(tester: PluginTester):
    """Search by title and author."""
    print('\n--- Search by Title + Author ---')
    title = input('Enter title: ').strip()
    author = input('Enter author: ').strip()

    if not title and not author:
        print('No search terms entered.')
        return

    authors = [author] if author else None

    print(f'\nSearching for: {title or "(any)"} by {author or "(any)"}')
    print('-' * 40)

    results = tester.search(title=title, authors=authors)

    if not results:
        print('No results found.')
        save_result(
            'search_title_author',
            {'title': title, 'author': author},
            [],
            False,
            'No results',
        )
        return

    print(f'\nFound {len(results)} result(s):\n')

    for i, mi in enumerate(results, 1):
        print(format_metadata(mi, i))
        print()

    # Save results
    results_data = [mi.to_dict() for mi in results]
    save_result('search_title_author', {'title': title, 'author': author}, results_data, True)

    # Option to view details
    while True:
        choice = input(f'\nView details (1-{len(results)}) or 0 to go back: ').strip()
        if choice == '0' or not choice:
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                print('\n' + format_metadata_full(results[idx]))
            else:
                print('Invalid selection.')
        except ValueError:
            print('Invalid input.')


def menu_lookup_id(tester: PluginTester):
    """Lookup by RanobeDB ID."""
    print('\n--- Lookup by RanobeDB ID ---')
    book_id = input('Enter RanobeDB book ID: ').strip()

    if not book_id:
        print('No ID entered.')
        return

    print(f'\nLooking up book ID: {book_id}')
    print('-' * 40)

    results = tester.search(identifiers={'ranobedb': book_id})

    if not results:
        print('Book not found.')
        save_result('lookup_id', {'ranobedb_id': book_id}, [], False, 'Not found')
        return

    mi = results[0]
    print('\n' + format_metadata_full(mi))

    # Save result
    save_result('lookup_id', {'ranobedb_id': book_id}, [mi.to_dict()], True)

    # Option to test cover
    test_cover = input('\nTest cover download? (y/n): ').strip().lower()
    if test_cover == 'y':
        tester.test_cover({'ranobedb': book_id})


def menu_test_cover(tester: PluginTester):
    """Test cover download."""
    print('\n--- Test Cover Download ---')
    book_id = input('Enter RanobeDB book ID: ').strip()

    if not book_id:
        print('No ID entered.')
        return

    print(f'\nDownloading cover for book ID: {book_id}')
    print('-' * 40)

    tester.test_cover({'ranobedb': book_id})


def menu_view_results():
    """View saved results."""
    print('\n--- Saved Results ---')

    if not RESULTS_DIR.exists():
        print('No results directory found.')
        return

    files = sorted(RESULTS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)

    if not files:
        print('No saved results found.')
        return

    print(f'\nFound {len(files)} saved result(s):\n')

    for i, f in enumerate(files[:20], 1):
        print(f'[{i}] {f.name}')

    if len(files) > 20:
        print(f'\n... and {len(files) - 20} more')

    while True:
        choice = input(f'\nView result (1-{min(len(files), 20)}) or 0 to go back: ').strip()
        if choice == '0' or not choice:
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                with open(files[idx], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print('\n' + json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print('Invalid selection.')
        except (ValueError, json.JSONDecodeError) as e:
            print(f'Error: {e}')


def menu_change_language(tester: PluginTester):
    """Change language preference."""
    print('\n--- Change Language Preference ---')
    print()
    print('Language codes: en (English), romaji, ja (Japanese)')
    print('Enter comma-separated order, e.g.: en,romaji,ja')
    print()
    print('Presets:')
    print('  1. English first: en,romaji,ja')
    print('  2. Japanese first: ja,romaji,en')
    print('  3. Romaji first: romaji,en,ja')
    print('  4. Custom')
    print('  0. Cancel')
    print()

    choice = input('Enter choice (0-4): ').strip()

    if choice == '0':
        return
    elif choice == '1':
        new_order = 'en,romaji,ja'
    elif choice == '2':
        new_order = 'ja,romaji,en'
    elif choice == '3':
        new_order = 'romaji,en,ja'
    elif choice == '4':
        new_order = input('Enter custom order: ').strip()
    else:
        print('Invalid choice.')
        return

    tester.plugin._prefs['language_order'] = new_order
    print(f'\nLanguage order changed to: {new_order}')


def main_menu():
    """Main interactive menu."""
    tester = PluginTester()

    while True:
        print('\n')
        current_lang = tester.plugin.prefs.get('language_order', 'en,romaji,ja')
        print('=' * 50)
        print('  RanobeDB Light Novels - Plugin Tester')
        print('=' * 50)
        print()
        print(f'  Current language order: {current_lang}')
        print()
        print('  1. Search by title')
        print('  2. Search by title + author')
        print('  3. Lookup by RanobeDB ID')
        print('  4. Test cover download')
        print('  5. View saved results')
        print('  6. Run batch tests')
        print('  7. Change language preference')
        print('  8. Exit')
        print()

        choice = input('Enter choice (1-8): ').strip()

        if choice == '1':
            menu_search_title(tester)
        elif choice == '2':
            menu_search_title_author(tester)
        elif choice == '3':
            menu_lookup_id(tester)
        elif choice == '4':
            menu_test_cover(tester)
        elif choice == '5':
            menu_view_results()
        elif choice == '6':
            from test_batch import run_batch_tests

            run_batch_tests(tester)
        elif choice == '7':
            menu_change_language(tester)
        elif choice == '8':
            print('\nGoodbye!')
            break
        else:
            print('\nInvalid choice. Please try again.')


if __name__ == '__main__':
    main_menu()
