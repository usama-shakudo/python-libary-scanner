#!/usr/bin/env python3
"""
Simple script to list all pip installed packages
"""

import subprocess
import sys


def list_packages():
    """List all pip installed packages"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error listing packages: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    list_packages()
