"""
Stub Package Generator for Security/Scanning Messages

This module generates fake Python packages (.tar.gz) that display
custom messages when pip tries to install them.
"""

import io
import tarfile
import time


def generate_security_stub(package_name: str, version: str, reason: str) -> bytes:
    """
    Generates an in-memory .tar.gz package that crashes on install
    with a custom security message.
    """

    # Create the setup.py content
    setup_py_content = f"""import sys
from setuptools import setup

def security_block():
    msg = '''
    ======================================================================
    WARNING: PACKAGE SCANNING IN PROGRESS
    ======================================================================

    Package: {package_name}
    Status:  {reason}

    This package is currently being scanned by your organization's
    security team and will be available soon.

    Please try again in 2-3 minutes, or contact your administrator
    if this message persists.

    ======================================================================
    '''
    sys.stderr.write(msg)
    sys.stderr.flush()
    raise RuntimeError("Package scanning in progress - installation temporarily unavailable.")

if __name__ == "__main__":
    security_block()
"""

    # Create an in-memory binary stream
    file_stream = io.BytesIO()

    # Create the tarball structure expected by pip
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
"""
        info_info = tarfile.TarInfo(name=f"{folder_name}/PKG-INFO")
        info_info.size = len(pkg_info)
        info_info.mtime = time.time()
        info_info.mode = 0o644
        tar.addfile(info_info, io.BytesIO(pkg_info.encode('utf-8')))

    # Reset stream position to the beginning
    file_stream.seek(0)
    return file_stream.read()


def generate_scanning_stub(package_name: str) -> bytes:
    """
    Convenience function for generating a "scanning in progress" stub.
    Uses version 999.9.9
    """
    return generate_security_stub(
        package_name=package_name,
        version="999.9.9",
        reason="Being scanned by security team"
    )
