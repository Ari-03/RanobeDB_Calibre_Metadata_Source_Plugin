#!/usr/bin/env python3
"""
Batch test script for RanobeDB Light Novels plugin.

Runs predefined tests against the RanobeDB API to verify plugin functionality.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'tests'))
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

# Results directory
RESULTS_DIR = PROJECT_ROOT / 'tests' / 'results'


# =============================================================================
# BATCH TEST CASES
# =============================================================================

BATCH_TESTS = [
    # Popular light novels - Title only
    {
        'name': 'Sword Art Online',
        'type': 'title',
        'title': 'Sword Art Online',
        'expected': {
            'has_results': True,
            'min_results': 1,
            'title_contains': 'Sword Art Online',
        },
    },
    {
        'name': 'Spice and Wolf',
        'type': 'title',
        'title': 'Spice and Wolf',
        'expected': {
            'has_results': True,
            'min_results': 1,
            'title_contains': 'Spice',
        },
    },
    {
        'name': 'Re:Zero',
        'type': 'title',
        'title': 'Re:Zero',
        'expected': {
            'has_results': True,
            'min_results': 1,
        },
    },
    {
        'name': 'Overlord',
        'type': 'title',
        'title': 'Overlord',
        'expected': {
            'has_results': True,
            'min_results': 1,
        },
    },
    {
        'name': 'Konosuba',
        'type': 'title',
        'title': 'Konosuba',
        'expected': {
            'has_results': True,
            'min_results': 1,
        },
    },
    {
        'name': 'Mushoku Tensei',
        'type': 'title',
        'title': 'Mushoku Tensei',
        'expected': {
            'has_results': True,
            'min_results': 1,
        },
    },
    {
        'name': 'The Rising of the Shield Hero',
        'type': 'title',
        'title': 'Shield Hero',
        'expected': {
            'has_results': True,
            'min_results': 1,
        },
    },
    {
        'name': 'That Time I Got Reincarnated as a Slime',
        'type': 'title',
        'title': 'Reincarnated as a Slime',
        'expected': {
            'has_results': True,
            'min_results': 1,
        },
    },
    # Title + Author tests
    {
        'name': 'SAO by Reki Kawahara',
        'type': 'title_author',
        'title': 'Sword Art Online',
        'author': 'Reki Kawahara',
        'expected': {
            'has_results': True,
            'min_results': 1,
            'author_contains': 'Kawahara',
        },
    },
    {
        'name': 'Spice and Wolf by Isuna Hasekura',
        'type': 'title_author',
        'title': 'Spice and Wolf',
        'author': 'Isuna Hasekura',
        'expected': {
            'has_results': True,
            'min_results': 1,
        },
    },
    # Edge cases
    {
        'name': 'Nonexistent Book',
        'type': 'title',
        'title': 'This Book Does Not Exist XYZ123 Random String',
        'expected': {
            'has_results': False,
        },
    },
    {
        'name': 'Empty search',
        'type': 'title',
        'title': '',
        'expected': {
            'has_results': False,
        },
    },
    # Japanese title test
    {
        'name': 'Japanese Title (SAO)',
        'type': 'title',
        'title': 'ソードアート・オンライン',
        'expected': {
            'has_results': True,  # May or may not work depending on API
        },
    },
]


def ensure_results_dir():
    """Create results directory if it doesn't exist."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_single_test(tester, test_case: dict) -> dict:
    """Run a single test case and return results."""
    result = {
        'name': test_case['name'],
        'type': test_case['type'],
        'query': {},
        'success': False,
        'passed': False,
        'results_count': 0,
        'results': [],
        'errors': [],
        'expectations_met': {},
    }

    try:
        # Build query
        if test_case['type'] == 'title':
            result['query'] = {'title': test_case.get('title', '')}
            results = tester.search(title=test_case.get('title'))
        elif test_case['type'] == 'title_author':
            author = test_case.get('author')
            result['query'] = {'title': test_case.get('title', ''), 'author': author}
            results = tester.search(
                title=test_case.get('title'), authors=[author] if author else None
            )
        elif test_case['type'] == 'id':
            result['query'] = {'ranobedb_id': test_case.get('ranobedb_id')}
            results = tester.search(identifiers={'ranobedb': test_case.get('ranobedb_id')})
        else:
            result['errors'].append(f'Unknown test type: {test_case["type"]}')
            return result

        result['success'] = True
        result['results_count'] = len(results)
        result['results'] = [mi.to_dict() for mi in results]

        # Check expectations
        expected = test_case.get('expected', {})
        all_passed = True

        # Check has_results
        if 'has_results' in expected:
            has_results = len(results) > 0
            passed = has_results == expected['has_results']
            result['expectations_met']['has_results'] = passed
            if not passed:
                all_passed = False

        # Check min_results
        if 'min_results' in expected:
            passed = len(results) >= expected['min_results']
            result['expectations_met']['min_results'] = passed
            if not passed:
                all_passed = False

        # Check title_contains
        if 'title_contains' in expected and results:
            search_str = expected['title_contains'].lower()
            passed = any(search_str in mi.title.lower() for mi in results)
            result['expectations_met']['title_contains'] = passed
            if not passed:
                all_passed = False

        # Check author_contains
        if 'author_contains' in expected and results:
            search_str = expected['author_contains'].lower()
            passed = any(
                any(search_str in author.lower() for author in mi.authors) for mi in results
            )
            result['expectations_met']['author_contains'] = passed
            if not passed:
                all_passed = False

        result['passed'] = all_passed

    except Exception as e:
        result['errors'].append(str(e))
        result['success'] = False

    return result


def run_batch_tests(tester=None, save_results: bool = True) -> List[dict]:
    """
    Run all batch tests.

    :param tester: PluginTester instance (created if not provided)
    :param save_results: Whether to save results to JSON
    :return: List of test results
    """
    # Create tester if not provided
    if tester is None:
        # Need to set up imports
        from test_interactive import PluginTester

        tester = PluginTester()

    print('\n' + '=' * 60)
    print('  RanobeDB Light Novels - Batch Tests')
    print('=' * 60)
    print(f'\nRunning {len(BATCH_TESTS)} tests...\n')

    all_results = []
    passed_count = 0
    failed_count = 0

    for i, test_case in enumerate(BATCH_TESTS, 1):
        print(f'[{i}/{len(BATCH_TESTS)}] {test_case["name"]}...', end=' ', flush=True)

        result = run_single_test(tester, test_case)
        all_results.append(result)

        if result['passed']:
            print(f'PASSED ({result["results_count"]} results)')
            passed_count += 1
        else:
            print(f'FAILED')
            if result['errors']:
                print(f'        Errors: {result["errors"]}')
            for exp, met in result['expectations_met'].items():
                if not met:
                    print(f'        {exp}: FAILED')
            failed_count += 1

        # Rate limiting - wait between tests
        time.sleep(1.1)

    # Summary
    print('\n' + '-' * 60)
    print(f'Results: {passed_count} passed, {failed_count} failed')
    print('-' * 60)

    # Save results
    if save_results:
        ensure_results_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = RESULTS_DIR / f'batch_test_{timestamp}.json'

        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(BATCH_TESTS),
            'passed': passed_count,
            'failed': failed_count,
            'tests': all_results,
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

        print(f'\nResults saved to: {filepath}')

    return all_results


def main():
    """Run batch tests from command line."""
    # Set up imports
    import builtins

    builtins._ = lambda x: x

    from mock_calibre import (
        MockMetadata,
        MockLog,
        MockAbort,
        MockSource,
        MockOption,
        MockPrefs,
        MockBrowser,
        check_isbn as _check_isbn,
        parse_date as _parse_date,
    )

    # Mock calibre modules
    class MockCalibreMetadata:
        Metadata = MockMetadata

    class MockCalibreSource:
        Source = MockSource
        Option = MockOption

    class MockCalibreEbooksMetadata:
        pass

    MockCalibreEbooksMetadata.check_isbn = staticmethod(_check_isbn)

    class MockCalibreUtilsDate:
        pass

    MockCalibreUtilsDate.parse_date = staticmethod(_parse_date)

    sys.modules['calibre'] = type(sys)('calibre')
    sys.modules['calibre.ebooks'] = type(sys)('calibre.ebooks')
    sys.modules['calibre.ebooks.metadata'] = MockCalibreEbooksMetadata
    sys.modules['calibre.ebooks.metadata.book'] = type(sys)('calibre.ebooks.metadata.book')
    sys.modules['calibre.ebooks.metadata.book.base'] = MockCalibreMetadata
    sys.modules['calibre.ebooks.metadata.sources'] = type(sys)('calibre.ebooks.metadata.sources')
    sys.modules['calibre.ebooks.metadata.sources.base'] = MockCalibreSource
    sys.modules['calibre.utils'] = type(sys)('calibre.utils')
    sys.modules['calibre.utils.date'] = MockCalibreUtilsDate

    # Now import and run
    from test_interactive import PluginTester

    tester = PluginTester()

    results = run_batch_tests(tester)

    # Exit with error code if any tests failed
    failed = sum(1 for r in results if not r['passed'])
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
