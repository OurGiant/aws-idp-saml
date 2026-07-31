#!/usr/bin/env python3
"""
samlstat - CLI tool to display AWS SAML credential status and authenticate.

Shows the same info as the aws-idp-saml-ui Java desktop app:
  - Profile names from ~/.aws/samlsts
  - Credential status from ~/.aws/credentials
  - Token expiration from ~/.aws/aws_saml.db

Authentication uses the existing aws-idp-saml getCredentials flow.
"""

import argparse
import configparser
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


# --- ANSI color codes ---

class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


def supports_color() -> bool:
    """Check if the terminal supports color output."""
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    return True


class NoColor:
    """Fallback when color is disabled."""
    RESET = ""
    BOLD = ""
    DIM = ""
    GREEN = ""
    RED = ""
    YELLOW = ""
    CYAN = ""
    WHITE = ""


# --- Data loading ---

def get_aws_dir() -> Path:
    return Path.home() / ".aws"


def load_samlsts_profiles(aws_dir: Path) -> list[str]:
    """Load profile names from ~/.aws/samlsts (excluding Fed-* and global sections)."""
    config_path = aws_dir / "samlsts"
    if not config_path.exists():
        return []

    config = configparser.ConfigParser()
    config.read(str(config_path))

    profiles = []
    for section in config.sections():
        if not section.startswith("Fed-") and section.lower() != "global":
            profiles.append(section)

    return sorted(profiles, key=str.lower)


def load_credentials_profiles(aws_dir: Path) -> set[str]:
    """Load profile names from ~/.aws/credentials."""
    creds_path = aws_dir / "credentials"
    if not creds_path.exists():
        return set()

    config = configparser.ConfigParser()
    config.read(str(creds_path))
    return set(config.sections())


def load_token_expirations(aws_dir: Path) -> dict[str, datetime]:
    """Load token expirations from ~/.aws/aws_saml.db SQLite database."""
    db_path = aws_dir / "aws_saml.db"
    if not db_path.exists():
        return {}

    expirations = {}
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT profile_name, expiration FROM token_state")
        for row in cursor:
            profile_name, expiration_str = row
            try:
                exp = datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
                expirations[profile_name] = exp
            except (ValueError, TypeError):
                pass
        conn.close()
    except sqlite3.Error:
        pass

    return expirations


# --- Status computation ---

def compute_status(expiration: datetime | None, now: datetime) -> tuple[str, str, str]:
    """
    Compute status, expiration display, and time remaining for a profile.
    Returns (status, expires_at, time_remaining).
    """
    if expiration is None:
        return ("UNKNOWN", "N/A", "Unknown")

    if expiration > now:
        expires_at = expiration.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        remaining = expiration - now
        time_remaining = format_duration(remaining.total_seconds())
        return ("VALID", expires_at, time_remaining)
    else:
        expires_at = expiration.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        return ("EXPIRED", expires_at, "Expired")


def format_duration(total_seconds: float) -> str:
    """Format seconds into a human-readable duration."""
    seconds = int(total_seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    if minutes > 0:
        return f"{minutes}m {secs:02d}s"
    return f"{secs:02d}s"


def status_sort_key(status: str) -> int:
    """Sort order: VALID first, UNKNOWN second, EXPIRED last."""
    if status == "VALID":
        return 0
    if status == "UNKNOWN":
        return 1
    return 2


# --- Display ---

def print_status_table(rows: list[tuple[str, str, str, str]], c, filter_text: str | None = None):
    """Print the credential status table with colors."""
    if filter_text:
        filter_lower = filter_text.lower()
        rows = [r for r in rows if filter_lower in r[0].lower()]

    if not rows:
        print(f"{c.DIM}No profiles found.{c.RESET}")
        return

    headers = ("Profile", "Status", "Expires At", "Time Remaining")
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    header_line = "  ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers))
    print(f"{c.BOLD}{header_line}{c.RESET}")
    print(f"{c.DIM}{'─' * (sum(widths) + 6)}{c.RESET}")

    for profile, status, expires_at, time_remaining in rows:
        if status == "VALID":
            status_colored = f"{c.GREEN}{status:<{widths[1]}}{c.RESET}"
        elif status == "EXPIRED":
            status_colored = f"{c.RED}{status:<{widths[1]}}{c.RESET}"
        else:
            status_colored = f"{c.YELLOW}{status:<{widths[1]}}{c.RESET}"

        if time_remaining == "Expired":
            time_colored = f"{c.RED}{time_remaining:<{widths[3]}}{c.RESET}"
        elif time_remaining == "Unknown":
            time_colored = f"{c.YELLOW}{time_remaining:<{widths[3]}}{c.RESET}"
        else:
            time_colored = f"{c.GREEN}{time_remaining:<{widths[3]}}{c.RESET}"

        profile_col = f"{profile:<{widths[0]}}"
        expires_col = f"{expires_at:<{widths[2]}}"
        print(f"{profile_col}  {status_colored}  {expires_col}  {time_colored}")


def print_summary(rows: list[tuple[str, str, str, str]], c):
    """Print a summary line below the table."""
    valid = sum(1 for r in rows if r[1] == "VALID")
    expired = sum(1 for r in rows if r[1] == "EXPIRED")
    unknown = sum(1 for r in rows if r[1] == "UNKNOWN")
    total = len(rows)

    parts = [f"{total} profiles"]
    if valid:
        parts.append(f"{c.GREEN}{valid} valid{c.RESET}")
    if expired:
        parts.append(f"{c.RED}{expired} expired{c.RESET}")
    if unknown:
        parts.append(f"{c.YELLOW}{unknown} unknown{c.RESET}")

    print(f"\n{' | '.join(parts)}")


# --- Status command ---

def cmd_status(args):
    """Show credential status for all profiles."""
    if args.no_color or not supports_color():
        c = NoColor
    else:
        c = Color

    aws_dir = get_aws_dir()

    samlsts_profiles = load_samlsts_profiles(aws_dir)
    credential_profiles = load_credentials_profiles(aws_dir)
    token_expirations = load_token_expirations(aws_dir)

    all_profiles = sorted(
        set(samlsts_profiles) | credential_profiles | set(token_expirations.keys()),
        key=str.lower,
    )

    if not all_profiles:
        print(f"{c.YELLOW}No AWS SAML profiles found.{c.RESET}")
        print(f"{c.DIM}Expected config at: {aws_dir / 'samlsts'}{c.RESET}")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    rows: list[tuple[str, str, str, str]] = []

    for profile in all_profiles:
        expiration = token_expirations.get(profile)
        status, expires_at, time_remaining = compute_status(expiration, now)
        rows.append((profile, status, expires_at, time_remaining))

    rows.sort(key=lambda r: (status_sort_key(r[1]), r[0].lower()))

    # Single profile mode
    if hasattr(args, "profile") and args.profile:
        rows = [r for r in rows if r[0] == args.profile]
        if not rows:
            print(f"{c.RED}Profile '{args.profile}' not found.{c.RESET}")
            sys.exit(1)

    print(f"\n{c.BOLD}{c.CYAN}AWS SAML Credential Status{c.RESET}")
    print(f"{c.DIM}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{c.RESET}\n")

    # Apply status filter (-v, -u, -x)
    if getattr(args, "valid", False):
        rows = [r for r in rows if r[1] == "VALID"]
    elif getattr(args, "unknown", False):
        rows = [r for r in rows if r[1] == "UNKNOWN"]
    elif getattr(args, "expired", False):
        rows = [r for r in rows if r[1] == "EXPIRED"]

    filter_text = getattr(args, "filter", None)
    print_status_table(rows, c, filter_text=filter_text)
    filtered_rows = rows if not filter_text else [r for r in rows if filter_text.lower() in r[0].lower()]
    print_summary(filtered_rows, c)
    print()


# --- Auth command ---

def save_token_expiration(aws_dir: Path, profile: str, duration_seconds: int):
    """Write token expiration to the SQLite DB after successful auth."""
    db_path = aws_dir / "aws_saml.db"
    expiration = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    now_str = datetime.now().isoformat()

    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS token_state "
            "(profile_name TEXT PRIMARY KEY, expiration TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT OR REPLACE INTO token_state (profile_name, expiration, created_at) VALUES (?, ?, ?)",
            (profile, expiration.isoformat(), now_str),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass


def get_session_duration(aws_dir: Path, profile: str) -> int:
    """Read session duration from samlsts config (profile or global), default 14400."""
    config_path = aws_dir / "samlsts"
    if not config_path.exists():
        return 14400

    config = configparser.ConfigParser()
    config.read(str(config_path))

    # Check profile section
    if config.has_section(profile) and config.has_option(profile, "sessionduration"):
        try:
            return int(config.get(profile, "sessionduration"))
        except ValueError:
            pass

    # Check global section
    if config.has_section("global") and config.has_option("global", "sessionduration"):
        try:
            return int(config.get("global", "sessionduration"))
        except ValueError:
            pass

    return 14400


def cmd_auth(args):
    """Authenticate a profile using the existing getCredentials.py flow."""
    if args.no_color or not supports_color():
        c = NoColor
    else:
        c = Color

    # Validate profile exists
    aws_dir = get_aws_dir()
    samlsts_profiles = load_samlsts_profiles(aws_dir)

    if args.profile not in samlsts_profiles:
        print(f"{c.RED}Profile '{args.profile}' not found in ~/.aws/samlsts{c.RESET}")
        print(f"{c.DIM}Available profiles:{c.RESET}")
        for p in samlsts_profiles:
            print(f"  {p}")
        sys.exit(1)

    # Locate getCredentials.py relative to this script
    script_dir = Path(__file__).resolve().parent
    get_creds = script_dir / "getCredentials.py"

    if not get_creds.exists():
        print(f"{c.RED}Cannot find getCredentials.py at: {get_creds}{c.RESET}")
        sys.exit(1)

    # Build command
    cmd = [sys.executable, str(get_creds), "--profilename", args.profile]

    if args.fastpass:
        cmd.append("--fastpass")
    if args.stored_password and not args.no_stored_password:
        cmd.append("--storedpw")
    if args.debug:
        cmd.append("--debug")
    if args.browser:
        cmd.extend(["--browser", args.browser])
    if args.encrypted:
        cmd.append("--encrypted")

    print(f"{c.BOLD}{c.CYAN}Authenticating profile: {args.profile}{c.RESET}\n")

    # Run interactively (inherits stdin/stdout for password prompts)
    try:
        result = subprocess.run(cmd, cwd=str(script_dir))
        if result.returncode == 0:
            # Write expiration to SQLite so 'samlstat' status picks it up
            duration = get_session_duration(aws_dir, args.profile)
            save_token_expiration(aws_dir, args.profile, duration)
            print(f"\n{c.GREEN}✓ Authentication successful for: {args.profile}{c.RESET}")
        else:
            print(f"\n{c.RED}✗ Authentication failed (exit code: {result.returncode}){c.RESET}")
            sys.exit(result.returncode)
    except KeyboardInterrupt:
        print(f"\n{c.YELLOW}Cancelled.{c.RESET}")
        sys.exit(130)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        prog="samlstat",
        description="AWS SAML credential status and authentication CLI.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output",
    )
    # Top-level filter/profile flags so 'samlstat -f prod' works without 'status' subcommand
    parser.add_argument(
        "-f", "--filter",
        help="Filter profiles by name (case-insensitive substring match)",
    )
    parser.add_argument(
        "-v", "--valid",
        action="store_true",
        help="Show only VALID profiles",
    )
    parser.add_argument(
        "-u", "--unknown",
        action="store_true",
        help="Show only UNKNOWN profiles",
    )
    parser.add_argument(
        "-x", "--expired",
        action="store_true",
        help="Show only EXPIRED profiles",
    )
    parser.add_argument(
        "-p", "--profile",
        help="Show status for a single profile only",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- status ---
    status_parser = subparsers.add_parser(
        "status",
        aliases=["s"],
        help="Show credential status for all profiles (default)",
    )
    status_parser.add_argument(
        "-f", "--filter",
        help="Filter profiles by name (case-insensitive substring match)",
    )
    status_parser.add_argument(
        "-v", "--valid",
        action="store_true",
        help="Show only VALID profiles",
    )
    status_parser.add_argument(
        "-u", "--unknown",
        action="store_true",
        help="Show only UNKNOWN profiles",
    )
    status_parser.add_argument(
        "-x", "--expired",
        action="store_true",
        help="Show only EXPIRED profiles",
    )
    status_parser.add_argument(
        "-p", "--profile",
        help="Show status for a single profile only",
    )

    # --- auth ---
    auth_parser = subparsers.add_parser(
        "auth",
        aliases=["a"],
        help="Authenticate and get credentials for a profile",
    )
    auth_parser.add_argument(
        "profile",
        help="Profile name to authenticate",
    )
    auth_parser.add_argument(
        "--fastpass", "-fp",
        action="store_true",
        help="Use Okta FastPass (biometric/device auth, no password)",
    )
    auth_parser.add_argument(
        "--stored-password", "-sp",
        action="store_true",
        default=True,
        help="Use stored password (default: enabled)",
    )
    auth_parser.add_argument(
        "--no-stored-password",
        action="store_true",
        help="Prompt for password instead of using stored",
    )
    auth_parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Show browser window during login",
    )
    auth_parser.add_argument(
        "--browser", "-b",
        help="Browser to use (chrome, firefox)",
    )
    auth_parser.add_argument(
        "--encrypted", "-e",
        action="store_true",
        help="Display encrypted credentials after auth",
    )

    args = parser.parse_args()

    if args.command in ("auth", "a"):
        cmd_auth(args)
    else:
        # Default to status (handles None, "status", "s")
        cmd_status(args)


if __name__ == "__main__":
    main()
