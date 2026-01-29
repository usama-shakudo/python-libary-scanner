#!/usr/bin/env python3
"""
List pip installed packages for multiple Python versions (3.9, 3.10, 3.11, 3.12, 3.13)
"""

import subprocess
import sys
import argparse
import json
import shutil
from typing import List, Dict, Optional


def find_python_executables(versions: List[str]) -> Dict[str, str]:
    """Find Python executables for specified versions"""
    executables = {}

    for version in versions:
        executable = shutil.which(f'python{version}')
        if executable:
            executables[version] = executable

    return executables


def get_python_full_version(executable: str) -> Optional[str]:
    """Get the full version string of a Python executable"""
    try:
        result = subprocess.run(
            [executable, '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        version_text = result.stdout.strip() or result.stderr.strip()
        return version_text
    except subprocess.CalledProcessError:
        return None


def list_packages_for_python(executable: str, format_type: str = 'text') -> Optional[str]:
    """List all pip installed packages for a specific Python version"""
    try:
        if format_type == 'json':
            result = subprocess.run(
                [executable, '-m', 'pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                check=True
            )
        else:
            result = subprocess.run(
                [executable, '-m', 'pip', 'list'],
                capture_output=True,
                text=True,
                check=True
            )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def main():
    parser = argparse.ArgumentParser(
        description='List pip packages for Python versions 3.9, 3.10, 3.11, 3.12, 3.13'
    )
    parser.add_argument(
        '-v', '--versions',
        nargs='+',
        choices=['3.9', '3.10', '3.11', '3.12', '3.13'],
        help='Specific Python versions to check (default: all available)'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--current',
        action='store_true',
        help='Only check current Python version'
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Show package comparison across versions'
    )

    args = parser.parse_args()

    # Determine which versions to check
    if args.current:
        version_info = sys.version_info
        current_version = f"{version_info.major}.{version_info.minor}"
        print(f"Checking current Python version: {current_version}\n")
        packages = list_packages_for_python(sys.executable, args.format)
        if packages:
            print(packages)
        else:
            print("Failed to list packages", file=sys.stderr)
            sys.exit(1)
        return

    # Default to all supported versions
    versions_to_check = args.versions or ['3.9', '3.10', '3.11', '3.12', '3.13']

    # Find available Python executables
    executables = find_python_executables(versions_to_check)

    if not executables:
        print("No Python executables found for specified versions", file=sys.stderr)
        sys.exit(1)

    # Collect packages for each version
    results = {}
    for version, executable in sorted(executables.items()):
        full_version = get_python_full_version(executable)
        packages = list_packages_for_python(executable, args.format)
        if packages:
            results[version] = {
                'full_version': full_version,
                'packages': packages
            }

    # Output results
    if args.format == 'json':
        json_results = {}
        for version, data in results.items():
            try:
                json_results[version] = {
                    'full_version': data['full_version'],
                    'packages': json.loads(data['packages'])
                }
            except json.JSONDecodeError:
                json_results[version] = {
                    'full_version': data['full_version'],
                    'packages': []
                }
        print(json.dumps(json_results, indent=2))

    elif args.compare:
        # Compare packages across versions
        all_packages = {}
        for version, data in results.items():
            try:
                packages_json = json.loads(list_packages_for_python(
                    executables[version], 'json'
                ))
                for pkg in packages_json:
                    pkg_name = pkg['name']
                    if pkg_name not in all_packages:
                        all_packages[pkg_name] = {}
                    all_packages[pkg_name][version] = pkg['version']
            except (json.JSONDecodeError, TypeError):
                continue

        print(f"\n{'Package':<30}", end='')
        for version in sorted(results.keys()):
            print(f" {version:<15}", end='')
        print()
        print("=" * (30 + 15 * len(results)))

        for pkg_name in sorted(all_packages.keys()):
            print(f"{pkg_name:<30}", end='')
            for version in sorted(results.keys()):
                pkg_version = all_packages[pkg_name].get(version, '-')
                print(f" {pkg_version:<15}", end='')
            print()

        print(f"\nTotal unique packages: {len(all_packages)}")
        print(f"Python versions checked: {', '.join(sorted(results.keys()))}")

    else:
        # Text format output
        for version in sorted(results.keys()):
            data = results[version]
            print(f"\n{'='*70}")
            print(f"{data['full_version']}")
            print(f"{'='*70}")
            print(data['packages'])

        print(f"\n{'='*70}")
        print(f"Summary: Checked {len(results)} Python version(s)")
        print(f"Versions: {', '.join(sorted(results.keys()))}")
        print(f"{'='*70}")


if __name__ == '__main__':
    main()
