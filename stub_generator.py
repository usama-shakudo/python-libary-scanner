"""
Stub Package Generator for Security/Scanning Messages

This module generates fake Python packages (.tar.gz) that display
custom messages when pip tries to install them.

The technique works by creating a valid source distribution with a
setup.py that prints the message and raises an error, forcing pip
to display it during installation.
"""

import io
import tarfile
import time


def generate_security_stub(package_name: str, version: str, reason: str) -> bytes:
    """
    Generates an in-memory .tar.gz package that crashes on install
    with a custom security message.

    Args:
        package_name: Name of the package (e.g., "apache-libcloud")
        version: Version string (e.g., "999.9.9")
        reason: Message to display to the user

    Returns:
        bytes: Binary content of the .tar.gz file
    """

    # 1. Create the setup.py content
    # We use 'sys.stderr' to ensure the message isn't buffered and appears in logs
    setup_py_content = f"""
import sys
from setuptools import setup

def security_block():
    msg = \"\"\"
    {'=' * 70}
    ⚠️  PACKAGE SCANNING IN PROGRESS  ⚠️
    {'=' * 70}

    Package: {package_name}
    Status:  {reason}

    This package is currently being scanned by your organization's
    security team and will be available soon.

    Please try again in 2-3 minutes, or contact your administrator
    if this message persists.

    {'=' * 70}
    \"\"\"
    # Print to stderr so it shows up in pip's error logs
    sys.stderr.write(msg + "\\n")
    sys.stderr.flush()

    # Raise error to stop installation
    raise RuntimeError("Package scanning in progress - installation temporarily unavailable.")

if __name__ == "__main__":
    security_block()
"""

    # 2. Create an in-memory binary stream
    file_stream = io.BytesIO()

    # 3. Create the tarball structure expected by pip
    # Structure: package-version/setup.py
    folder_name = f"{package_name}-{version}"

    with tarfile.open(fileobj=file_stream, mode='w:gz') as tar:
        # Create the setup.py file info
        tar_info = tarfile.TarInfo(name=f"{folder_name}/setup.py")
        tar_info.size = len(setup_py_content)
        tar_info.mtime = time.time()
        tar_info.mode = 0o644

        # Write the file content into the tar
        tar.addfile(tar_info, io.BytesIO(setup_py_content.encode('utf-8')))

        # Add a PKG-INFO file to look more legitimate
        pkg_info = f"""Metadata-Version: 2.1
Name: {package_name}
Version: {version}
Summary: Package scanning in progress
Home-page: about:blank
Author: Security Team
Author-email: security@example.com
License: UNKNOWN
Platform: UNKNOWN

This is a temporary stub package.
"""
        info_info = tarfile.TarInfo(name=f"{folder_name}/PKG-INFO")
        info_info.size = len(pkg_info)
        info_info.mtime = time.time()
        info_info.mode = 0o644
        tar.addfile(info_info, io.BytesIO(pkg_info.encode('utf-8')))

    # 4. Reset stream position to the beginning
    file_stream.seek(0)
    return file_stream.read()


def generate_scanning_stub(package_name: str) -> bytes:
    """
    Convenience function for generating a "scanning in progress" stub.
    Uses a high version number (999.9.9) to ensure pip picks it.

    Args:
        package_name: Name of the package

    Returns:
        bytes: Binary content of the .tar.gz file
    """
    return generate_security_stub(
        package_name=package_name,
        version="999.9.9",
        reason="Being scanned by security team"
    )


# Example usage for testing:
if __name__ == "__main__":
    # Generate a test stub
    stub_data = generate_scanning_stub("test-package")

    # Save to file for testing
    with open("test-package-999.9.9.tar.gz", "wb") as f:
        f.write(stub_data)

    print(f"Generated stub package: test-package-999.9.9.tar.gz ({len(stub_data)} bytes)")
    print("Test with: pip install ./test-package-999.9.9.tar.gz")
