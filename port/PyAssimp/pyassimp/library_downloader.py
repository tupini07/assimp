#-*- coding: UTF-8 -*-

"""
Downloads precompiled assimp shared libraries from official GitHub releases.

This module detects the current platform and downloads the appropriate
precompiled binary from https://github.com/assimp/assimp/releases,
placing it in the ``pyassimp/libs/`` directory so that pyassimp can
find and load it automatically.

Usage as a script::

    python -m pyassimp.library_downloader          # latest release
    python -m pyassimp.library_downloader v6.0.4   # specific tag

Usage from Python::

    from pyassimp.library_downloader import download_library
    download_library()                    # latest release
    download_library(tag="v6.0.4")        # specific tag
"""

import io
import json
import logging
import os
import platform
import struct
import sys
import zipfile
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("pyassimp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_API_URL = "https://api.github.com/repos/assimp/assimp/releases/latest"
GITHUB_RELEASE_TAG_URL = (
    "https://api.github.com/repos/assimp/assimp/releases/tags/{tag}"
)
GITHUB_DOWNLOAD_URL = (
    "https://github.com/assimp/assimp/releases/download/{tag}/{asset_name}"
)

LIBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")

# Library file extensions we care about, per platform.
_EXT_WHITELIST = {
    "linux": (".so",),
    "darwin": (".dylib",),
    "win32": (".dll",),
}

# Timeout (seconds) for HTTP requests.
_HTTP_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------


def _get_platform_asset_prefix():
    """Return the GitHub release asset prefix for this platform.

    The official CD workflow produces assets named like
    ``<platform>-<tag>.zip`` where ``<platform>`` is one of:
    ``windows-x64``, ``windows-x86``, ``linux-x64``,
    ``macos-x64``, ``macos-arm64``.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    bits = struct.calcsize("P") * 8

    if system == "windows":
        return "windows-x64" if bits == 64 else "windows-x86"
    elif system == "linux":
        if machine in ("x86_64", "amd64"):
            return "linux-x64"
        raise RuntimeError(
            f"No precompiled assimp binary for Linux {machine}. "
            "Please compile from source."
        )
    elif system == "darwin":
        if machine == "arm64":
            return "macos-arm64"
        return "macos-x64"
    else:
        raise RuntimeError(
            f"No precompiled assimp binary for {system}. "
            "Please compile from source."
        )


def _library_extensions():
    """Return the file extensions to look for inside the zip."""
    if sys.platform.startswith("linux"):
        return _EXT_WHITELIST["linux"]
    elif sys.platform == "darwin":
        return _EXT_WHITELIST["darwin"]
    elif sys.platform == "win32":
        return _EXT_WHITELIST["win32"]
    return ()


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def _fetch_json(url):
    """Fetch JSON from *url* and return the parsed dict."""
    req = Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "pyassimp-library-downloader")
    with urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resolve_tag(tag=None):
    """Return ``(tag, download_url)`` for the correct platform asset.

    If *tag* is ``None`` the latest release is used.
    """
    if tag is None:
        release = _fetch_json(GITHUB_API_URL)
    else:
        url = GITHUB_RELEASE_TAG_URL.format(tag=tag)
        release = _fetch_json(url)

    tag = release["tag_name"]
    prefix = _get_platform_asset_prefix()

    # Find the matching asset.
    expected_name = f"{prefix}-{tag}.zip"
    for asset in release.get("assets", []):
        if asset["name"] == expected_name:
            return tag, asset["browser_download_url"]

    raise RuntimeError(
        f"Could not find asset '{expected_name}' in release {tag}. "
        f"Available assets: {[a['name'] for a in release.get('assets', [])]}"
    )


def _download_zip(url):
    """Download a zip file from *url* and return its bytes."""
    logger.info("Downloading %s …", url)
    req = Request(url)
    req.add_header("User-Agent", "pyassimp-library-downloader")
    with urlopen(req, timeout=300) as resp:
        return resp.read()


def _extract_libraries(zip_bytes, dest_dir):
    """Extract library files from *zip_bytes* into *dest_dir*.

    Returns a list of extracted file paths.
    """
    extensions = _library_extensions()
    extracted = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            basename = os.path.basename(info.filename)
            # Check if the file has a library extension we want.
            # This also matches versioned names like libassimp.so.5.4.3
            if not any(basename.endswith(ext) or ext + "." in basename for ext in extensions):
                continue
            # Only extract files that contain 'assimp' in the name.
            if "assimp" not in basename.lower():
                continue
            dest_path = os.path.join(dest_dir, basename)
            logger.info("Extracting %s -> %s", info.filename, dest_path)
            with zf.open(info) as src, open(dest_path, "wb") as dst:
                dst.write(src.read())
            # Make the library executable on POSIX.
            if os.name == "posix":
                os.chmod(dest_path, 0o755)
            extracted.append(dest_path)

    return extracted


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def download_library(tag=None, dest_dir=None):
    """Download the precompiled assimp library for the current platform.

    Parameters
    ----------
    tag : str, optional
        Git tag of the release to download (e.g. ``"v6.0.4"``).
        Defaults to the latest release.
    dest_dir : str, optional
        Directory to store the downloaded library.
        Defaults to ``<pyassimp-package>/libs/``.

    Returns
    -------
    list[str]
        Paths to the extracted library files.

    Raises
    ------
    RuntimeError
        If the platform is unsupported or the download/extraction fails.
    """
    if dest_dir is None:
        dest_dir = LIBS_DIR
    os.makedirs(dest_dir, exist_ok=True)

    tag, download_url = _resolve_tag(tag)
    logger.info("Resolved assimp release: %s", tag)

    zip_bytes = _download_zip(download_url)
    extracted = _extract_libraries(zip_bytes, dest_dir)

    if not extracted:
        raise RuntimeError(
            "Downloaded the release archive but found no assimp library "
            "files inside it. Please compile from source instead."
        )

    logger.info(
        "Successfully downloaded assimp libraries: %s",
        ", ".join(os.path.basename(p) for p in extracted),
    )
    return extracted


def try_auto_download():
    """Attempt to download the library, suppressing errors.

    Intended to be called from :func:`helper.search_library` as a
    last-resort fallback.  Returns ``True`` if at least one library
    file was placed in the libs directory, ``False`` otherwise.
    """
    if os.environ.get("PYASSIMP_NO_AUTO_DOWNLOAD", "").strip() in ("1", "true", "yes"):
        logger.debug("Auto-download disabled via PYASSIMP_NO_AUTO_DOWNLOAD")
        return False

    tag_override = os.environ.get("PYASSIMP_RELEASE_TAG", "").strip() or None

    try:
        logger.info(
            "No assimp library found locally – attempting to download "
            "precompiled binary from GitHub releases …"
        )
        extracted = download_library(tag=tag_override)
        return len(extracted) > 0
    except Exception as exc:
        logger.warning("Auto-download of assimp library failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def main():
    """CLI wrapper: ``python -m pyassimp.library_downloader [tag]``."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    tag = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        paths = download_library(tag=tag)
        for p in paths:
            print(f"  ✓ {p}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
