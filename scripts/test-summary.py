#!/usr/bin/env python3
"""
Test result summarizer for Claude Observability Hub.
Aggregates test results across all stacks and provides a unified view.
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


def parse_junit_xml(file_path: Path) -> Dict:
    """Parse JUnit XML test results."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Handle both testsuite and testsuites root
    if root.tag == 'testsuites':
        stats = {
            'tests': int(root.get('tests', 0)),
            'failures': int(root.get('failures', 0)),
            'errors': int(root.get('errors', 0)),
            'skipped': int(root.get('skipped', 0)),
            'time': float(root.get('time', 0))
        }
    else:  # testsuite
        stats = {
            'tests': int(root.get('tests', 0)),
            'failures': int(root.get('failures', 0)),
            'errors': int(root.get('errors', 0)),
            'skipped': int(root.get('skipped', 0)),
            'time': float(root.get('time', 0))
        }
    
    stats['passed'] = stats['tests'] - stats['failures'] - stats['errors'] - stats['skipped']
    return stats


def parse_coverage_json(file_path: Path) -> Dict:
    """Parse coverage JSON files."""
    with open(file_path) as f:
        data = json.load(f)
    
    total_statements = 0
    covered_statements = 0
    
    for file_data in data.values():
        if isinstance(file_data, dict) and 's' in file_data:
            statements = file_data['s']
            total_statements += len(statements)
            covered_statements += sum(1 for v in statements.values() if v > 0)
    
    coverage = (covered_statements / total_statements * 100) if total_statements > 0 else 0
    
    return {
        'total': total_statements,
        'covered': covered_statements,
        'percentage': round(coverage, 2)
    }


def find_test_results(base_path: Path = Path('.')) -> Dict[str, List[Path]]:
    """Find all test result files."""
    results = {
        'junit': list(base_path.glob('**/test-results/*.xml')),
        'coverage': list(base_path.glob('**/coverage/coverage-final.json'))
    }
    return results


def format_time(seconds: float) -> str:
    """Format time duration."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"


def print_summary(test_stats: Dict, coverage_stats: Dict):
    """Print formatted test summary."""
    print(f"\n{BOLD}🧪 Test Summary{RESET}")
    print("=" * 50)
    
    # Test results
    total_tests = sum(s['tests'] for s in test_stats.values())
    total_passed = sum(s['passed'] for s in test_stats.values())
    total_failed = sum(s['failures'] + s['errors'] for s in test_stats.values())
    total_skipped = sum(s['skipped'] for s in test_stats.values())
    total_time = sum(s['time'] for s in test_stats.values())
    
    print(f"\n{BOLD}Test Results:{RESET}")
    for stack, stats in test_stats.items():
        status = GREEN + "✅" if stats['failures'] == 0 and stats['errors'] == 0 else RED + "❌"
        print(f"  {status} {stack:<15} {stats['passed']}/{stats['tests']} passed "
              f"({format_time(stats['time'])}){RESET}")
    
    print(f"\n{BOLD}Total:{RESET}")
    overall_status = GREEN if total_failed == 0 else RED
    print(f"  {overall_status}{total_passed}/{total_tests} tests passed{RESET}")
    
    if total_failed > 0:
        print(f"  {RED}{total_failed} failed{RESET}")
    if total_skipped > 0:
        print(f"  {YELLOW}{total_skipped} skipped{RESET}")
    
    print(f"  ⏱️  Total time: {format_time(total_time)}")
    
    # Coverage results
    if coverage_stats:
        print(f"\n{BOLD}Coverage:{RESET}")
        for stack, stats in coverage_stats.items():
            color = GREEN if stats['percentage'] >= 80 else YELLOW if stats['percentage'] >= 60 else RED
            print(f"  {stack:<15} {color}{stats['percentage']:.1f}%{RESET} "
                  f"({stats['covered']}/{stats['total']} statements)")
    
    # Success metric
    print(f"\n{BOLD}Success Metrics:{RESET}")
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"  Success Rate: {success_rate:.1f}%")
    
    avg_coverage = sum(s['percentage'] for s in coverage_stats.values()) / len(coverage_stats) if coverage_stats else 0
    coverage_color = GREEN if avg_coverage >= 70 else YELLOW if avg_coverage >= 50 else RED
    print(f"  Avg Coverage: {coverage_color}{avg_coverage:.1f}%{RESET}")
    
    # Final status
    if total_failed == 0 and avg_coverage >= 70:
        print(f"\n{GREEN}{BOLD}✅ All tests passed with good coverage!{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}❌ Tests or coverage need attention{RESET}")
        return 1


def main():
    """Main entry point."""
    print(f"{BLUE}Analyzing test results...{RESET}")
    
    # Find result files
    results = find_test_results()
    
    # Parse test results
    test_stats = {}
    for junit_file in results['junit']:
        stack_name = junit_file.stem.replace('-test', '').replace('test-', '')
        try:
            test_stats[stack_name] = parse_junit_xml(junit_file)
        except Exception as e:
            print(f"{YELLOW}Warning: Could not parse {junit_file}: {e}{RESET}")
    
    # Parse coverage results
    coverage_stats = {}
    for cov_file in results['coverage']:
        # Determine stack from path
        if 'server' in str(cov_file):
            stack_name = 'bun'
        elif 'dashboard' in str(cov_file):
            stack_name = 'vue'
        elif 'hooks' in str(cov_file):
            stack_name = 'python'
        else:
            stack_name = 'unknown'
        
        try:
            coverage_stats[stack_name] = parse_coverage_json(cov_file)
        except Exception as e:
            print(f"{YELLOW}Warning: Could not parse {cov_file}: {e}{RESET}")
    
    # Print summary
    if not test_stats and not coverage_stats:
        print(f"{YELLOW}No test results found. Run tests first!{RESET}")
        return 1
    
    return print_summary(test_stats, coverage_stats)


if __name__ == '__main__':
    sys.exit(main())