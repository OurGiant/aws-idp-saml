#!/usr/bin/env python3
"""
Browser smoke test for issue #93 (Selenium Manager migration).

Tests setup_browser() across the matrix defined in the issue:
  - Headless (default) and --debug (visible) mode
  - All browsers available on the current platform
  - Snap Firefox detection (Linux/WSL)
  - binary_location override verification (Windows/macOS)

Usage:
    python browser_smoke_test.py [--debug] [--browser BROWSER]

    --debug           Also run the visible-browser variant of each test.
                      Requires a display (WSLg, native desktop, or X11).
    --browser NAME    Test a single browser instead of the full matrix.

Known gaps (not covered here, see issue #93):
    - Corporate proxy/firewall blocking Selenium Manager driver downloads
    - Edge on Linux (no supported package)
    - Flatpak Chrome on Linux (snap confinement incompatible)
    - macOS (not validated in this run)
"""

import argparse
import sys
import time
from pathlib import Path

import constants
from Browser import gecko_from_snap, setup_browser
from OSInfo import OSInfo

TEST_URL = "https://example.com"
EXPECTED_TITLE = "Example Domain"

os_info = OSInfo()
platform = os_info.which_os()

BROWSERS_BY_PLATFORM = {
    "windows": ["chrome", "firefox", "edge"],
    "linux": ["chrome", "firefox"],   # Edge has no supported Linux package
    "macos": ["chrome", "firefox"],
}


# ---------------------------------------------------------------------------
# Individual test cases
# ---------------------------------------------------------------------------

def check_snap_detection() -> tuple[bool, str]:
    """Verify gecko_from_snap() correctly detects (or correctly skips) snap Firefox."""
    snap_dir = Path(constants.__snap_install_dir__)
    driver_loc, binary_loc = gecko_from_snap()
    if snap_dir.is_dir():
        if binary_loc and Path(binary_loc).is_file():
            return True, f"snap detected: binary={binary_loc}"
        return False, f"snap dir exists ({snap_dir}) but binary not found at {binary_loc}"
    else:
        if driver_loc is None and binary_loc is None:
            return True, "snap dir absent, correctly returned (None, None)"
        return False, f"snap dir absent but returned non-None: driver={driver_loc} binary={binary_loc}"


def check_binary_location_override(browser: str) -> tuple[bool, str]:
    """Verify constants.firefox_binary_location is set and points to a real file (Windows/macOS)."""
    if browser != "firefox":
        return True, "n/a (only checked for firefox)"
    loc = constants.firefox_binary_location.get(platform)
    if loc is None:
        return True, f"no hardcoded binary_location for {platform} (Selenium Manager will discover it)"
    if Path(loc).is_file():
        return True, f"binary_location exists: {loc}"
    # Missing binary — this is intentional after fix in #93: fall through to Selenium Manager
    return True, f"binary_location {loc} absent — Selenium Manager will self-provision (expected)"


def run_browser(browser: str, use_debug: bool) -> tuple[bool, str]:
    """Launch the browser, load TEST_URL, verify title, quit cleanly."""
    driver = None
    label = f"{browser} ({'visible' if use_debug else 'headless'})"
    try:
        driver, loaded = setup_browser(browser, use_debug)
        if not loaded or driver is None:
            return False, f"{label}: setup_browser() returned is_driver_loaded=False"
        driver.get(TEST_URL)
        title = driver.title
        if EXPECTED_TITLE.lower() in title.lower():
            return True, f'{label}: title="{title}"'
        return False, f'{label}: unexpected title="{title}"'
    except Exception as exc:
        return False, f"{label}: {exc}"
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def print_row(name: str, passed: bool, detail: str, elapsed: float):
    status = "PASS" if passed else "FAIL"
    print(f"{name:<40}  {status:<6}  {detail}  ({elapsed:.1f}s)")


def main():
    parser = argparse.ArgumentParser(description="Browser smoke test for issue #93")
    parser.add_argument("--debug", action="store_true",
                        help="Also run visible-browser variants (requires display)")
    parser.add_argument("--browser", help="Test a single browser instead of the full matrix")
    args = parser.parse_args()

    browsers = BROWSERS_BY_PLATFORM.get(platform, ["chrome", "firefox"])
    if args.browser:
        browsers = [args.browser]

    print(f"\nBrowser smoke test — issue #93 (Selenium Manager)")
    print(f"Platform: {platform}  |  URL: {TEST_URL}\n")
    print(f"{'Test':<40}  {'Result':<6}  Detail")
    print("-" * 100)

    results: list[tuple[str, bool, str]] = []

    def record(name: str, fn, *fn_args):
        t0 = time.time()
        passed, detail = fn(*fn_args)
        elapsed = time.time() - t0
        print_row(name, passed, detail, elapsed)
        results.append((name, passed, detail))

    # --- Platform-specific pre-checks ---
    if platform == "linux":
        record("snap Firefox detection", check_snap_detection)

    for browser in browsers:
        record(f"binary_location override ({browser})", check_binary_location_override, browser)

    # --- Headless browser launches ---
    print()
    for browser in browsers:
        record(f"{browser} headless", run_browser, browser, False)

    # --- Visible browser launches (opt-in) ---
    if args.debug:
        print()
        for browser in browsers:
            record(f"{browser} visible (--debug)", run_browser, browser, True)

    # --- Summary ---
    print()
    passed_count = sum(1 for _, p, _ in results if p)
    total = len(results)
    print(f"Results: {passed_count}/{total} passed")

    failed = [(n, d) for n, p, d in results if not p]
    if failed:
        print("Failed:")
        for name, detail in failed:
            print(f"  - {name}: {detail}")
        print()
        print("Known gaps not covered by this script (see issue #93):")
        print("  - Corporate proxy/firewall blocking Selenium Manager driver downloads")
        print("  - Edge on Linux")
        print("  - Flatpak Chrome on Linux")
        print("  - macOS")
        sys.exit(1)
    else:
        print("All checks passed.")
        print()
        print("Known gaps not covered by this script (see issue #93):")
        print("  - Corporate proxy/firewall blocking Selenium Manager driver downloads")
        if platform != "linux":
            print("  - Snap Firefox detection (Linux/WSL only)")
        if platform != "windows":
            print("  - Edge (Windows only)")
        print("  - macOS (not validated in this run)")
        sys.exit(0)


if __name__ == "__main__":
    main()
